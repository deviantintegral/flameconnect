"""Tests for the B2C direct login module."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from multidict import CIMultiDict

from flameconnect.b2c_login import (
    _parse_login_page,
    b2c_login_with_credentials,
)
from flameconnect.exceptions import AuthenticationError

# ---------------------------------------------------------------------------
# Sample B2C HTML used by tests
# ---------------------------------------------------------------------------

SAMPLE_B2C_HTML = """
<!DOCTYPE html>
<html>
<head><title>Sign In</title></head>
<body>
<script>
var SETTINGS = {
    "csrf": "dGVzdC1jc3JmLXRva2Vu",
    "transId": "StateProperties=eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9",
    "remoteResource": "https://example.com/resource"
};
</script>
<form id="localAccountForm" action="SelfAsserted">
  <input type="email" name="signInName" />
  <input type="password" name="password" />
</form>
</body>
</html>
"""

_POLICY = "B2C_1A_FirePhoneSignUpOrSignInWithPhoneOrEmail"
_TENANT = "gdhvb2cflameconnect.onmicrosoft.com"
_HOST = "https://gdhvb2cflameconnect.b2clogin.com"

SAMPLE_PAGE_URL = (
    f"{_HOST}/{_TENANT}/"
    f"{_POLICY}/oauth2/v2.0/authorize"
    "?tx=StateProperties=eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9"
)

_CLIENT_ID = "1af761dc-085a-411f-9cb9-53e5e2115bd2"
REDIRECT_URL = (
    f"msal{_CLIENT_ID}://auth"
    "?code=test-auth-code-123&state=test-state"
)

AUTH_URI = "https://example.com/authorize"


# ---------------------------------------------------------------------------
# _parse_login_page
# ---------------------------------------------------------------------------


class TestParseLoginPage:
    """Test HTML parsing of the B2C login page."""

    def test_extracts_csrf_token(self):
        result = _parse_login_page(SAMPLE_B2C_HTML, SAMPLE_PAGE_URL)
        assert result["csrf"] == "dGVzdC1jc3JmLXRva2Vu"

    def test_extracts_transaction_id(self):
        result = _parse_login_page(SAMPLE_B2C_HTML, SAMPLE_PAGE_URL)
        tx = "StateProperties=eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9"
        assert result["tx"] == tx

    def test_uses_hardcoded_policy(self):
        result = _parse_login_page(SAMPLE_B2C_HTML, SAMPLE_PAGE_URL)
        expected = "B2C_1A_FirePhoneSignUpOrSignInWithPhoneOrEmail"
        assert result["p"] == expected

    def test_builds_post_url(self):
        result = _parse_login_page(SAMPLE_B2C_HTML, SAMPLE_PAGE_URL)
        expected_prefix = (
            f"{_HOST}/{_TENANT}/{_POLICY}/SelfAsserted?"
        )
        assert result["post_url"].startswith(expected_prefix)
        assert "tx=StateProperties" in result["post_url"]
        assert "p=B2C_1A_Fire" in result["post_url"]

    def test_builds_confirmed_url(self):
        result = _parse_login_page(SAMPLE_B2C_HTML, SAMPLE_PAGE_URL)
        expected = (
            f"{_HOST}/{_TENANT}/{_POLICY}/"
            "api/CombinedSigninAndSignup/confirmed"
        )
        assert result["confirmed_url"] == expected

    def test_missing_csrf_raises(self):
        html = "<html><body>No settings here</body></html>"
        with pytest.raises(AuthenticationError, match="CSRF token"):
            _parse_login_page(html, SAMPLE_PAGE_URL)

    def test_missing_trans_id_raises(self):
        html = '<script>var SETTINGS = {"csrf":"abc"};</script>'
        with pytest.raises(AuthenticationError, match="transId"):
            _parse_login_page(html, SAMPLE_PAGE_URL)


# ---------------------------------------------------------------------------
# b2c_login_with_credentials — full flow
# ---------------------------------------------------------------------------


def _make_mock_response(
    status: int = 200,
    text: str = "",
    url: str = "https://example.com",
    headers: dict[str, str] | None = None,
) -> MagicMock:
    """Create a mock aiohttp response."""
    resp = MagicMock()
    resp.status = status
    resp.text = AsyncMock(return_value=text)
    resp.url = url
    resp.headers = CIMultiDict(headers or {})
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=False)
    return resp


def _make_mock_session(**kwargs: MagicMock) -> MagicMock:
    """Create a mock aiohttp.ClientSession."""
    session = MagicMock()
    if "get" in kwargs:
        session.get = kwargs["get"]
    if "post" in kwargs:
        session.post = kwargs["post"]
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session


_MOD = "flameconnect.b2c_login.aiohttp"


@contextmanager
def _patch_session(session: MagicMock):
    """Patch aiohttp.ClientSession and CookieJar."""
    with (
        patch(f"{_MOD}.ClientSession", return_value=session),
        patch(f"{_MOD}.CookieJar"),
    ):
        yield


class TestB2cLoginWithCredentials:
    """Test the full B2C login flow with mocked HTTP."""

    async def test_successful_login(self):
        """Happy path: credentials accepted, redirect captured."""
        login_resp = _make_mock_response(
            status=200, text=SAMPLE_B2C_HTML, url=SAMPLE_PAGE_URL
        )
        post_resp = _make_mock_response(
            status=200, text='{"status":"200"}'
        )
        confirmed_resp = _make_mock_response(
            status=302, headers={"Location": REDIRECT_URL}
        )

        session = _make_mock_session(
            get=MagicMock(
                side_effect=[login_resp, confirmed_resp]
            ),
            post=MagicMock(return_value=post_resp),
        )

        with _patch_session(session):
            result = await b2c_login_with_credentials(
                AUTH_URI, "user@test.com", "password123"
            )

        assert result == REDIRECT_URL
        assert "code=test-auth-code-123" in result

    async def test_bad_credentials_raises(self):
        """When B2C returns status 400, raises AuthenticationError."""
        login_resp = _make_mock_response(
            status=200, text=SAMPLE_B2C_HTML, url=SAMPLE_PAGE_URL
        )
        post_resp = _make_mock_response(
            status=200,
            text='{"status":"400","message":"Invalid"}',
        )

        session = _make_mock_session(
            get=MagicMock(return_value=login_resp),
            post=MagicMock(return_value=post_resp),
        )

        with _patch_session(session), pytest.raises(
            AuthenticationError, match="Invalid email"
        ):
            await b2c_login_with_credentials(
                AUTH_URI, "bad@test.com", "wrong"
            )

    async def test_login_page_http_error_raises(self):
        """Non-200 login page raises AuthenticationError."""
        login_resp = _make_mock_response(
            status=500, text="Server Error"
        )
        session = _make_mock_session(
            get=MagicMock(return_value=login_resp),
        )

        with _patch_session(session), pytest.raises(
            AuthenticationError, match="HTTP 500"
        ):
            await b2c_login_with_credentials(
                AUTH_URI, "user@test.com", "pass"
            )

    async def test_parse_failure_raises(self):
        """Unparseable HTML raises AuthenticationError."""
        login_resp = _make_mock_response(
            status=200,
            text="<html>Unexpected page content</html>",
            url=SAMPLE_PAGE_URL,
        )
        session = _make_mock_session(
            get=MagicMock(return_value=login_resp),
        )

        with _patch_session(session), pytest.raises(
            AuthenticationError, match="CSRF token"
        ):
            await b2c_login_with_credentials(
                AUTH_URI, "user@test.com", "pass"
            )

    async def test_multi_hop_redirect(self):
        """Intermediate HTTP redirects before custom scheme."""
        login_resp = _make_mock_response(
            status=200, text=SAMPLE_B2C_HTML, url=SAMPLE_PAGE_URL
        )
        post_resp = _make_mock_response(
            status=200, text='{"status":"200"}'
        )
        intermediate_resp = _make_mock_response(
            status=302,
            headers={"Location": "https://example.com/hop"},
        )
        final_resp = _make_mock_response(
            status=302, headers={"Location": REDIRECT_URL}
        )

        session = _make_mock_session(
            get=MagicMock(
                side_effect=[
                    login_resp,
                    intermediate_resp,
                    final_resp,
                ]
            ),
            post=MagicMock(return_value=post_resp),
        )

        with _patch_session(session):
            result = await b2c_login_with_credentials(
                AUTH_URI, "user@test.com", "pass"
            )

        assert result == REDIRECT_URL

    async def test_credential_post_http_error_raises(self):
        """Non-200 credential POST raises AuthenticationError."""
        login_resp = _make_mock_response(
            status=200, text=SAMPLE_B2C_HTML, url=SAMPLE_PAGE_URL
        )
        post_resp = _make_mock_response(
            status=500, text="Server Error"
        )

        session = _make_mock_session(
            get=MagicMock(return_value=login_resp),
            post=MagicMock(return_value=post_resp),
        )

        with _patch_session(session), pytest.raises(
            AuthenticationError, match="HTTP 500"
        ):
            await b2c_login_with_credentials(
                AUTH_URI, "user@test.com", "pass"
            )

    async def test_redirect_url_in_page_body(self):
        """Redirect URL in response body is captured."""
        login_resp = _make_mock_response(
            status=200, text=SAMPLE_B2C_HTML, url=SAMPLE_PAGE_URL
        )
        post_resp = _make_mock_response(
            status=200, text='{"status":"200"}'
        )

        body = (
            "<html><script>"
            f'window.location="{REDIRECT_URL}"'
            "</script></html>"
        )
        confirmed_resp = _make_mock_response(
            status=200, text=body
        )

        session = _make_mock_session(
            get=MagicMock(
                side_effect=[login_resp, confirmed_resp]
            ),
            post=MagicMock(return_value=post_resp),
        )

        with _patch_session(session):
            result = await b2c_login_with_credentials(
                AUTH_URI, "user@test.com", "pass"
            )

        assert "code=test-auth-code-123" in result
