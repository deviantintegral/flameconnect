"""Tests for the B2C direct login module."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from http.cookies import Morsel
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
import yarl
from multidict import CIMultiDict

from flameconnect.b2c_login import (
    _B2C_POLICY,
    _USER_AGENT,
    _build_cookie_header,
    _extract_base_path,
    _log_request,
    _log_response,
    _parse_login_page,
    b2c_login_with_credentials,
)
from flameconnect.exceptions import AuthenticationError

# -------------------------------------------------------------------
# Sample B2C HTML used by tests
# -------------------------------------------------------------------

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
    "?tx=StateProperties="
    "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9"
)

_CLIENT_ID = "1af761dc-085a-411f-9cb9-53e5e2115bd2"
REDIRECT_URL = f"msal{_CLIENT_ID}://auth?code=test-auth-code-123&state=test-state"

AUTH_URI = "https://example.com/authorize"


# -------------------------------------------------------------------
# _extract_base_path
# -------------------------------------------------------------------


class TestExtractBasePath:
    """Test _extract_base_path helper."""

    def test_short_path_returns_root(self):
        """URL with fewer than 2 path segments returns '/'."""
        assert _extract_base_path("https://example.com/single") == "/"

    def test_no_path_returns_root(self):
        """URL with no path returns '/'."""
        assert _extract_base_path("https://example.com") == "/"

    def test_normal_b2c_url(self):
        """Normal B2C URL extracts tenant / hardcoded policy."""
        url = (
            "https://host.com/tenant.onmicrosoft.com/"
            f"{_POLICY}/"
            "oauth2/v2.0/authorize?params"
        )
        result = _extract_base_path(url)
        expected = f"/tenant.onmicrosoft.com/{_POLICY}/"
        assert result == expected

    def test_exactly_two_segments(self):
        """URL with exactly 2 path segments uses first as tenant.

        Kills mutants that change ``>= 2`` to ``> 2`` or
        ``>= 3``.
        """
        url = "https://host.com/mytenant/mypolicy"
        result = _extract_base_path(url)
        assert result == f"/mytenant/{_POLICY}/"

    def test_strip_slash_matters(self):
        """Verify leading/trailing slashes are stripped properly.

        Kills mutant that changes strip('/') to strip('XX/XX').
        """
        url = "https://host.com/a/b/c"
        result = _extract_base_path(url)
        assert result.startswith("/a/")
        assert result == f"/a/{_POLICY}/"


# -------------------------------------------------------------------
# _parse_login_page
# -------------------------------------------------------------------


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
        assert result["p"] == _POLICY

    def test_builds_post_url(self):
        result = _parse_login_page(SAMPLE_B2C_HTML, SAMPLE_PAGE_URL)
        expected_prefix = f"{_HOST}/{_TENANT}/{_POLICY}/SelfAsserted?"
        assert result["post_url"].startswith(expected_prefix)
        assert "tx=StateProperties" in result["post_url"]
        assert f"p={_POLICY}" in result["post_url"]

    def test_builds_confirmed_url(self):
        result = _parse_login_page(SAMPLE_B2C_HTML, SAMPLE_PAGE_URL)
        expected = f"{_HOST}/{_TENANT}/{_POLICY}/api/CombinedSigninAndSignup/confirmed"
        assert result["confirmed_url"] == expected

    def test_missing_csrf_raises_exact_msg(self):
        html = "<html><body>No settings here</body></html>"
        with pytest.raises(
            AuthenticationError,
            match=("^Could not find CSRF token in B2C login page$"),
        ):
            _parse_login_page(html, SAMPLE_PAGE_URL)

    def test_missing_trans_id_raises_exact_msg(self):
        html = '<script>{"csrf":"abc"}</script>'
        with pytest.raises(
            AuthenticationError,
            match=("^Could not find transId in B2C login page$"),
        ):
            _parse_login_page(html, SAMPLE_PAGE_URL)


# -------------------------------------------------------------------
# _build_cookie_header
# -------------------------------------------------------------------


class TestBuildCookieHeader:
    """Test _build_cookie_header directly."""

    def test_formats_cookies_unquoted(self):
        """Verify cookie jar is queried with given URL and
        output uses ``; `` separator (not ``XX; XX``)."""
        m1 = MagicMock(spec=Morsel)
        m1.key = "session"
        m1.value = "abc+123"
        m2 = MagicMock(spec=Morsel)
        m2.key = "token"
        m2.value = "xyz=456"

        jar = MagicMock(spec=aiohttp.CookieJar)
        jar.filter_cookies.return_value = {"a": m1, "b": m2}

        result = _build_cookie_header(jar, "https://example.com/path")
        jar.filter_cookies.assert_called_once_with(yarl.URL("https://example.com/path"))
        assert result == "session=abc+123; token=xyz=456"

    def test_empty_jar(self):
        jar = MagicMock(spec=aiohttp.CookieJar)
        jar.filter_cookies.return_value = {}
        result = _build_cookie_header(jar, "https://example.com")
        assert result == ""

    def test_single_cookie(self):
        m1 = MagicMock(spec=Morsel)
        m1.key = "x"
        m1.value = "y"
        jar = MagicMock(spec=aiohttp.CookieJar)
        jar.filter_cookies.return_value = {"a": m1}
        result = _build_cookie_header(jar, "https://example.com")
        assert result == "x=y"


# -------------------------------------------------------------------
# _log_request
# -------------------------------------------------------------------


class TestLogRequest:
    """Test _log_request with captured log records."""

    def test_basic_log(self, caplog):
        """Basic GET log includes method and URL."""
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            _log_request("GET", "https://example.com/api")
        assert ">>> GET https://example.com/api" in caplog.text

    def test_params_logged(self, caplog):
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            _log_request(
                "GET",
                "https://example.com",
                params={"k": "v"},
            )
        assert "params" in caplog.text.lower()
        assert "'k'" in caplog.text or '"k"' in caplog.text

    def test_headers_logged(self, caplog):
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            _log_request(
                "GET",
                "https://example.com",
                headers={"Auth": "Bearer tok"},
            )
        assert "headers" in caplog.text.lower()
        assert "Auth" in caplog.text

    def test_data_logged_with_password_masked(self, caplog):
        """Password values are masked as '***'."""
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            _log_request(
                "POST",
                "https://example.com",
                data={
                    "email": "a@b.com",
                    "password": "secret",
                },
            )
        assert "body" in caplog.text.lower()
        assert "***" in caplog.text
        assert "secret" not in caplog.text
        assert "a@b.com" in caplog.text

    def test_no_params_no_extra_log(self, caplog):
        """Without params/headers/data, only method+URL logged."""
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            _log_request("GET", "https://example.com")
        assert "params" not in caplog.text
        assert "headers" not in caplog.text
        assert "body" not in caplog.text


# -------------------------------------------------------------------
# _log_response
# -------------------------------------------------------------------


class TestLogResponse:
    """Test _log_response with captured log records."""

    def _make_resp(self, status=200, url="https://example.com"):
        resp = MagicMock()
        resp.status = status
        resp.url = url
        resp.headers = CIMultiDict({"X-Test": "yes"})
        return resp

    def test_basic_response_logged(self, caplog):
        resp = self._make_resp(status=200)
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            _log_response(resp)
        assert "200" in caplog.text
        assert "headers" in caplog.text.lower()

    def test_body_logged(self, caplog):
        resp = self._make_resp()
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            _log_response(resp, "Hello body")
        assert "body" in caplog.text.lower()
        assert "Hello body" in caplog.text

    def test_long_body_truncated(self, caplog):
        resp = self._make_resp()
        long_body = "x" * 3000
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            _log_response(resp, long_body)
        assert "bytes total" in caplog.text
        assert "3000" in caplog.text

    def test_body_exactly_2000_no_truncation(self, caplog):
        resp = self._make_resp()
        body_2000 = "y" * 2000
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            _log_response(resp, body_2000)
        assert "bytes total" not in caplog.text

    def test_body_2001_truncated(self, caplog):
        resp = self._make_resp()
        body_2001 = "z" * 2001
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            _log_response(resp, body_2001)
        assert "bytes total" in caplog.text
        assert "2001" in caplog.text

    def test_none_body_no_body_log(self, caplog):
        resp = self._make_resp()
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            _log_response(resp, None)
        # Should not have body line (None means no body log)
        # But status and headers are always logged
        assert "200" in caplog.text


# -------------------------------------------------------------------
# b2c_login_with_credentials -- full flow
# -------------------------------------------------------------------


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


def _make_mock_response_multiheader(
    status: int = 200,
    text: str = "",
    url: str = "https://example.com",
    headers: list[tuple[str, str]] | None = None,
) -> MagicMock:
    """Create a mock response with multi-valued headers."""
    resp = MagicMock()
    resp.status = status
    resp.text = AsyncMock(return_value=text)
    resp.url = url
    hdr = CIMultiDict(headers or [])
    resp.headers = hdr
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=False)
    return resp


def _make_mock_session(
    **kwargs: MagicMock,
) -> MagicMock:
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
def _patch_sessions(
    first_session: MagicMock,
    second_session: MagicMock | None = None,
):
    """Patch aiohttp.ClientSession to return different sessions
    for the two ``async with`` blocks (login + raw_session)
    and also patch CookieJar and DummyCookieJar."""
    if second_session is None:
        second_session = first_session

    sessions = iter([first_session, second_session])

    with (
        patch(
            f"{_MOD}.ClientSession",
            side_effect=lambda **kw: next(sessions),
        ),
        patch(f"{_MOD}.CookieJar") as mock_jar_cls,
        patch(f"{_MOD}.DummyCookieJar"),
    ):
        mock_jar = MagicMock()
        mock_jar.filter_cookies.return_value = {}
        mock_jar_cls.return_value = mock_jar
        yield mock_jar_cls, mock_jar


@contextmanager
def _patch_session(session: MagicMock):
    """Patch aiohttp.ClientSession and CookieJar (compat)."""
    with (
        patch(f"{_MOD}.ClientSession", return_value=session),
        patch(f"{_MOD}.CookieJar"),
    ):
        yield


class TestB2cLoginWithCredentials:
    """Test the full B2C login flow with mocked HTTP."""

    async def test_successful_login(self):
        """Happy path: credentials accepted, redirect."""
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )
        post_resp = _make_mock_response(status=200, text='{"status":"200"}')
        confirmed_resp = _make_mock_response(
            status=302,
            headers={"Location": REDIRECT_URL},
        )

        session = _make_mock_session(
            get=MagicMock(side_effect=[login_resp, confirmed_resp]),
            post=MagicMock(return_value=post_resp),
        )

        with _patch_session(session):
            result = await b2c_login_with_credentials(
                AUTH_URI, "user@test.com", "password123"
            )

        assert result == REDIRECT_URL
        assert "code=test-auth-code-123" in result

    async def test_bad_credentials_raises(self):
        """B2C status 400 raises AuthenticationError."""
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )
        post_resp = _make_mock_response(
            status=200,
            text='{"status":"400","message":"Invalid"}',
        )

        session = _make_mock_session(
            get=MagicMock(return_value=login_resp),
            post=MagicMock(return_value=post_resp),
        )

        with (
            _patch_session(session),
            pytest.raises(
                AuthenticationError,
                match="Invalid email or password",
            ),
        ):
            await b2c_login_with_credentials(AUTH_URI, "bad@test.com", "wrong")

    async def test_bad_credentials_spaced_json(self):
        """Status 400 with spaces around colon also caught."""
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )
        post_resp = _make_mock_response(
            status=200,
            text='{"status": "400"}',
        )

        session = _make_mock_session(
            get=MagicMock(return_value=login_resp),
            post=MagicMock(return_value=post_resp),
        )

        with (
            _patch_session(session),
            pytest.raises(
                AuthenticationError,
                match="Invalid email or password",
            ),
        ):
            await b2c_login_with_credentials(AUTH_URI, "bad@test.com", "wrong")

    async def test_login_page_http_error_raises(self):
        """Non-200 login page raises AuthenticationError."""
        login_resp = _make_mock_response(status=500, text="Server Error")
        session = _make_mock_session(
            get=MagicMock(return_value=login_resp),
        )

        with (
            _patch_session(session),
            pytest.raises(
                AuthenticationError,
                match="B2C login page returned HTTP 500",
            ),
        ):
            await b2c_login_with_credentials(AUTH_URI, "user@test.com", "pass")

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

        with (
            _patch_session(session),
            pytest.raises(AuthenticationError, match="CSRF token"),
        ):
            await b2c_login_with_credentials(AUTH_URI, "user@test.com", "pass")

    async def test_multi_hop_redirect(self):
        """Intermediate HTTP redirects before custom scheme."""
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )
        post_resp = _make_mock_response(status=200, text='{"status":"200"}')
        intermediate_resp = _make_mock_response(
            status=302,
            headers={"Location": "https://example.com/hop"},
        )
        final_resp = _make_mock_response(
            status=302,
            headers={"Location": REDIRECT_URL},
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
            result = await b2c_login_with_credentials(AUTH_URI, "user@test.com", "pass")

        assert result == REDIRECT_URL

    async def test_credential_post_http_error_raises(self):
        """Non-200 credential POST raises AuthenticationError."""
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )
        post_resp = _make_mock_response(status=500, text="Server Error")

        session = _make_mock_session(
            get=MagicMock(return_value=login_resp),
            post=MagicMock(return_value=post_resp),
        )

        with (
            _patch_session(session),
            pytest.raises(
                AuthenticationError,
                match="Credential submission returned HTTP 500",
            ),
        ):
            await b2c_login_with_credentials(AUTH_URI, "user@test.com", "pass")

    async def test_redirect_url_in_page_body(self):
        """Redirect URL in response body is captured."""
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )
        post_resp = _make_mock_response(status=200, text='{"status":"200"}')

        body = f'<html><script>window.location="{REDIRECT_URL}"</script></html>'
        confirmed_resp = _make_mock_response(status=200, text=body)

        session = _make_mock_session(
            get=MagicMock(side_effect=[login_resp, confirmed_resp]),
            post=MagicMock(return_value=post_resp),
        )

        with _patch_session(session):
            result = await b2c_login_with_credentials(AUTH_URI, "user@test.com", "pass")

        assert "code=test-auth-code-123" in result

    async def test_redirect_without_location_raises(self):
        """302 with no Location header raises."""
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )
        post_resp = _make_mock_response(status=200, text='{"status":"200"}')
        no_loc = _make_mock_response(status=302, headers={})

        session = _make_mock_session(
            get=MagicMock(side_effect=[login_resp, no_loc]),
            post=MagicMock(return_value=post_resp),
        )

        with (
            _patch_session(session),
            pytest.raises(
                AuthenticationError,
                match=r"^Redirect without Location header$",
            ),
        ):
            await b2c_login_with_credentials(AUTH_URI, "user@test.com", "pass")

    async def test_relative_redirect_resolved(self):
        """Relative Location is resolved against current URL."""
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )
        post_resp = _make_mock_response(status=200, text='{"status":"200"}')
        relative_resp = _make_mock_response(
            status=302,
            headers={"Location": "/some/relative/path"},
        )
        final_resp = _make_mock_response(
            status=302,
            headers={"Location": REDIRECT_URL},
        )

        session = _make_mock_session(
            get=MagicMock(
                side_effect=[
                    login_resp,
                    relative_resp,
                    final_resp,
                ]
            ),
            post=MagicMock(return_value=post_resp),
        )

        with _patch_session(session):
            result = await b2c_login_with_credentials(AUTH_URI, "user@test.com", "pass")

        assert result == REDIRECT_URL

    async def test_200_without_redirect_url_raises(self):
        """200 without msal redirect URL in body raises."""
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )
        post_resp = _make_mock_response(status=200, text='{"status":"200"}')
        no_redir = _make_mock_response(
            status=200,
            text="<html>No redirect here</html>",
        )

        session = _make_mock_session(
            get=MagicMock(side_effect=[login_resp, no_redir]),
            post=MagicMock(return_value=post_resp),
        )

        with (
            _patch_session(session),
            pytest.raises(
                AuthenticationError,
                match=r"^Reached 200 response without finding redirect URL$",
            ),
        ):
            await b2c_login_with_credentials(AUTH_URI, "user@test.com", "pass")

    async def test_unexpected_http_status_raises(self):
        """Unexpected HTTP status during redirect chain."""
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )
        post_resp = _make_mock_response(status=200, text='{"status":"200"}')
        forbidden = _make_mock_response(status=403, text="Forbidden")

        session = _make_mock_session(
            get=MagicMock(side_effect=[login_resp, forbidden]),
            post=MagicMock(return_value=post_resp),
        )

        with (
            _patch_session(session),
            pytest.raises(
                AuthenticationError,
                match=("Unexpected HTTP 403 during redirect chain"),
            ),
        ):
            await b2c_login_with_credentials(AUTH_URI, "user@test.com", "pass")

    async def test_too_many_redirects_raises(self):
        """Exceeding max redirect hops raises."""
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )
        post_resp = _make_mock_response(status=200, text='{"status":"200"}')
        redirect_resp = _make_mock_response(
            status=302,
            headers={"Location": "https://example.com/loop"},
        )

        session = _make_mock_session(
            get=MagicMock(side_effect=([login_resp] + [redirect_resp] * 21)),
            post=MagicMock(return_value=post_resp),
        )

        with (
            _patch_session(session),
            pytest.raises(
                AuthenticationError,
                match="Too many redirects during B2C login",
            ),
        ):
            await b2c_login_with_credentials(AUTH_URI, "user@test.com", "pass")

    async def test_network_error_wrapped(self):
        """aiohttp.ClientError wrapped in AuthError."""
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )

        session = _make_mock_session(
            get=MagicMock(side_effect=[login_resp]),
        )
        session.post = MagicMock(side_effect=aiohttp.ClientError("Connection reset"))

        with (
            _patch_session(session),
            pytest.raises(
                AuthenticationError,
                match="Network error during B2C login",
            ),
        ):
            await b2c_login_with_credentials(AUTH_URI, "user@test.com", "pass")


# -------------------------------------------------------------------
# Detailed arg verification tests (kill mutants in b2c flow)
# -------------------------------------------------------------------


class TestB2cLoginArgVerification:
    """Verify exact args passed to session methods."""

    async def test_session_created_with_cookie_jar(self):
        """First session uses CookieJar(unsafe=True)."""
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )
        post_resp = _make_mock_response(status=200, text='{"status":"200"}')
        confirmed_resp = _make_mock_response(
            status=302,
            headers={"Location": REDIRECT_URL},
        )

        login_session = _make_mock_session(
            get=MagicMock(return_value=login_resp),
        )
        raw_session = _make_mock_session(
            post=MagicMock(return_value=post_resp),
            get=MagicMock(return_value=confirmed_resp),
        )

        with _patch_sessions(login_session, raw_session) as (jar_cls, _jar):
            await b2c_login_with_credentials(AUTH_URI, "user@test.com", "pass")

        jar_cls.assert_called_once_with(unsafe=True)

    async def test_session_headers_user_agent(self):
        """Both sessions receive User-Agent header."""
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )
        post_resp = _make_mock_response(status=200, text='{"status":"200"}')
        confirmed_resp = _make_mock_response(
            status=302,
            headers={"Location": REDIRECT_URL},
        )

        cs_calls = []
        call_idx = [0]

        def capture_cs(**kwargs):
            cs_calls.append(kwargs)
            idx = call_idx[0]
            call_idx[0] += 1
            if idx == 0:
                return _make_mock_session(
                    get=MagicMock(return_value=login_resp),
                )
            return _make_mock_session(
                post=MagicMock(return_value=post_resp),
                get=MagicMock(return_value=confirmed_resp),
            )

        with (
            patch(
                f"{_MOD}.ClientSession",
                side_effect=capture_cs,
            ),
            patch(f"{_MOD}.CookieJar") as jar_cls,
            patch(f"{_MOD}.DummyCookieJar"),
        ):
            jar = MagicMock()
            jar.filter_cookies.return_value = {}
            jar_cls.return_value = jar
            await b2c_login_with_credentials(AUTH_URI, "user@test.com", "pass")

        assert len(cs_calls) == 2
        for i, call in enumerate(cs_calls):
            hdrs = call.get("headers", {})
            assert hdrs.get("User-Agent") == (_USER_AGENT), (
                f"Session {i} missing User-Agent"
            )

    async def test_get_auth_uri_with_redirects(self):
        """Initial GET uses auth_uri with allow_redirects."""
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )
        post_resp = _make_mock_response(status=200, text='{"status":"200"}')
        confirmed_resp = _make_mock_response(
            status=302,
            headers={"Location": REDIRECT_URL},
        )

        login_session = _make_mock_session(
            get=MagicMock(return_value=login_resp),
        )
        raw_session = _make_mock_session(
            post=MagicMock(return_value=post_resp),
            get=MagicMock(return_value=confirmed_resp),
        )

        with _patch_sessions(login_session, raw_session):
            await b2c_login_with_credentials(AUTH_URI, "user@test.com", "pass")

        # Verify initial GET
        call = login_session.get.call_args
        assert call[0][0] == AUTH_URI
        assert call[1]["allow_redirects"] is True

    async def test_post_data_fields(self):
        """POST includes email, password, request_type."""
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )
        post_resp = _make_mock_response(status=200, text='{"status":"200"}')
        confirmed_resp = _make_mock_response(
            status=302,
            headers={"Location": REDIRECT_URL},
        )

        login_session = _make_mock_session(
            get=MagicMock(return_value=login_resp),
        )
        raw_session = _make_mock_session(
            post=MagicMock(return_value=post_resp),
            get=MagicMock(return_value=confirmed_resp),
        )

        with _patch_sessions(login_session, raw_session):
            await b2c_login_with_credentials(AUTH_URI, "me@test.com", "mypass")

        call = raw_session.post.call_args
        data = call[1]["data"]
        assert data["request_type"] == "RESPONSE"
        assert data["email"] == "me@test.com"
        assert data["password"] == "mypass"

    async def test_post_headers(self):
        """POST includes correct headers."""
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )
        post_resp = _make_mock_response(status=200, text='{"status":"200"}')
        confirmed_resp = _make_mock_response(
            status=302,
            headers={"Location": REDIRECT_URL},
        )

        login_session = _make_mock_session(
            get=MagicMock(return_value=login_resp),
        )
        raw_session = _make_mock_session(
            post=MagicMock(return_value=post_resp),
            get=MagicMock(return_value=confirmed_resp),
        )

        with _patch_sessions(login_session, raw_session):
            await b2c_login_with_credentials(AUTH_URI, "me@test.com", "pass")

        call = raw_session.post.call_args
        hdrs = call[1]["headers"]
        assert hdrs["X-CSRF-TOKEN"] == ("dGVzdC1jc3JmLXRva2Vu")
        assert hdrs["X-Requested-With"] == ("XMLHttpRequest")
        assert hdrs["Referer"] == AUTH_URI
        assert "Origin" in hdrs
        assert hdrs["Accept"] == ("application/json, text/javascript, */*; q=0.01")
        assert hdrs["Content-Type"] == (
            "application/x-www-form-urlencoded; charset=UTF-8"
        )
        assert "Cookie" in hdrs

    async def test_post_no_redirects(self):
        """POST is sent with allow_redirects=False."""
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )
        post_resp = _make_mock_response(status=200, text='{"status":"200"}')
        confirmed_resp = _make_mock_response(
            status=302,
            headers={"Location": REDIRECT_URL},
        )

        login_session = _make_mock_session(
            get=MagicMock(return_value=login_resp),
        )
        raw_session = _make_mock_session(
            post=MagicMock(return_value=post_resp),
            get=MagicMock(return_value=confirmed_resp),
        )

        with _patch_sessions(login_session, raw_session):
            await b2c_login_with_credentials(AUTH_URI, "me@test.com", "pass")

        call = raw_session.post.call_args
        assert call[1]["allow_redirects"] is False

    async def test_confirmed_url_has_query(self):
        """Confirmed GET URL has correct query params."""
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )
        post_resp = _make_mock_response(status=200, text='{"status":"200"}')
        confirmed_resp = _make_mock_response(
            status=302,
            headers={"Location": REDIRECT_URL},
        )

        login_session = _make_mock_session(
            get=MagicMock(return_value=login_resp),
        )
        raw_session = _make_mock_session(
            post=MagicMock(return_value=post_resp),
            get=MagicMock(return_value=confirmed_resp),
        )

        with _patch_sessions(login_session, raw_session):
            await b2c_login_with_credentials(AUTH_URI, "me@test.com", "pass")

        # First GET on raw_session is the confirmed URL
        get_call = raw_session.get.call_args
        url_arg = get_call[1].get("url", get_call[0][0])
        url_str = str(url_arg)
        assert "?" in url_str
        assert "rememberMe=false" in url_str
        assert "csrf_token=" in url_str
        assert f"p={_POLICY}" in url_str
        assert "tx=" in url_str
        assert "api/CombinedSigninAndSignup/confirmed" in url_str

    async def test_confirmed_get_no_redirects(self):
        """Confirmed GET uses allow_redirects=False."""
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )
        post_resp = _make_mock_response(status=200, text='{"status":"200"}')
        confirmed_resp = _make_mock_response(
            status=302,
            headers={"Location": REDIRECT_URL},
        )

        login_session = _make_mock_session(
            get=MagicMock(return_value=login_resp),
        )
        raw_session = _make_mock_session(
            post=MagicMock(return_value=post_resp),
            get=MagicMock(return_value=confirmed_resp),
        )

        with _patch_sessions(login_session, raw_session):
            await b2c_login_with_credentials(AUTH_URI, "me@test.com", "pass")

        get_call = raw_session.get.call_args
        assert get_call[1]["allow_redirects"] is False

    async def test_confirmed_get_has_cookie_header(self):
        """Confirmed GET includes Cookie header."""
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )
        post_resp = _make_mock_response(status=200, text='{"status":"200"}')
        confirmed_resp = _make_mock_response(
            status=302,
            headers={"Location": REDIRECT_URL},
        )

        login_session = _make_mock_session(
            get=MagicMock(return_value=login_resp),
        )
        raw_session = _make_mock_session(
            post=MagicMock(return_value=post_resp),
            get=MagicMock(return_value=confirmed_resp),
        )

        with _patch_sessions(login_session, raw_session):
            await b2c_login_with_credentials(AUTH_URI, "me@test.com", "pass")

        get_call = raw_session.get.call_args
        hdrs = get_call[1]["headers"]
        assert "Cookie" in hdrs

    async def test_cookie_merging_from_post_response(self):
        """POST Set-Cookie headers merge into cookie_header."""
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )
        # Post response with Set-Cookie headers
        post_resp = _make_mock_response_multiheader(
            status=200,
            text='{"status":"200"}',
            headers=[
                (
                    "Set-Cookie",
                    "newcookie=newval; Path=/; HttpOnly",
                ),
                (
                    "Set-Cookie",
                    "token=updated; Path=/",
                ),
            ],
        )
        confirmed_resp = _make_mock_response(
            status=302,
            headers={"Location": REDIRECT_URL},
        )

        login_session = _make_mock_session(
            get=MagicMock(return_value=login_resp),
        )
        raw_session = _make_mock_session(
            post=MagicMock(return_value=post_resp),
            get=MagicMock(return_value=confirmed_resp),
        )

        with _patch_sessions(login_session, raw_session):
            result = await b2c_login_with_credentials(AUTH_URI, "me@test.com", "pass")

        assert result == REDIRECT_URL
        # Verify cookies were merged
        get_call = raw_session.get.call_args
        cookie_hdr = get_call[1]["headers"]["Cookie"]
        assert "newcookie=newval" in cookie_hdr
        assert "token=updated" in cookie_hdr

    async def test_all_redirect_status_codes(self):
        """All 3xx redirect status codes are followed."""
        for code in (301, 302, 303, 307, 308):
            login_resp = _make_mock_response(
                status=200,
                text=SAMPLE_B2C_HTML,
                url=SAMPLE_PAGE_URL,
            )
            post_resp = _make_mock_response(status=200, text='{"status":"200"}')
            redir = _make_mock_response(
                status=code,
                headers={"Location": ("https://example.com/hop")},
            )
            final = _make_mock_response(
                status=302,
                headers={"Location": REDIRECT_URL},
            )

            session = _make_mock_session(
                get=MagicMock(
                    side_effect=[
                        login_resp,
                        redir,
                        final,
                    ]
                ),
                post=MagicMock(return_value=post_resp),
            )

            with _patch_session(session):
                result = await b2c_login_with_credentials(
                    AUTH_URI,
                    "user@test.com",
                    "pass",
                )
            assert result == REDIRECT_URL, f"Failed for status {code}"


# -------------------------------------------------------------------
# Module-level constants
# -------------------------------------------------------------------


class TestConstants:
    """Kill mutants on module-level constant strings."""

    def test_b2c_policy_value(self):
        assert _B2C_POLICY == ("B2C_1A_FirePhoneSignUpOrSignInWithPhoneOrEmail")

    def test_user_agent_contains_mozilla(self):
        assert "Mozilla/5.0" in _USER_AGENT

    def test_user_agent_contains_firefox(self):
        assert "Firefox" in _USER_AGENT


# -------------------------------------------------------------------
# Additional tests to kill surviving mutants
# -------------------------------------------------------------------


class TestExtractBasePathMutants:
    """Additional extract_base_path tests to kill mutant 6 (strip mutation)."""

    def test_path_with_leading_x_characters(self):
        """URL with 'X' in the path differentiates strip('/') from strip('XX/XX').

        Mutant 6 changes strip('/') to strip('XX/XX'), which would also
        strip 'X' characters from path segments. By including 'X' in the
        tenant name we can detect this.
        """
        url = "https://host.com/Xtenant/policy/extra"
        result = _extract_base_path(url)
        # With correct strip('/'), first segment is 'Xtenant'
        assert result == f"/Xtenant/{_POLICY}/"

    def test_path_starting_with_x(self):
        """Tenant name starting with X should be preserved."""
        url = "https://host.com/XX/policy"
        result = _extract_base_path(url)
        assert result == f"/XX/{_POLICY}/"


class TestLogRequestMutants:
    """Kill surviving log_request mutants by asserting exact log format.

    Note: Some log_request mutants are essentially equivalent (they only
    change debug format strings that tests may not care about). However,
    we can kill them by asserting exact prefix formatting.
    """

    def test_exact_prefix_format(self, caplog):
        """Kill mutant 7: '>>> %s %s' -> 'XX>>> %s %sXX'."""
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            _log_request("GET", "https://example.com/api")
        assert ">>> GET https://example.com/api" in caplog.text
        # Ensure no XX corruption
        assert "XX" not in caplog.text

    def test_params_exact_prefix(self, caplog):
        """Mutant 13: params line prefix mutated."""
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            _log_request("GET", "https://example.com", params={"k": "v"})
        assert ">>>   params:" in caplog.text
        assert "XX" not in caplog.text

    def test_headers_exact_prefix(self, caplog):
        """Mutant 19: headers line prefix mutated."""
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            _log_request("GET", "https://example.com", headers={"H": "v"})
        assert ">>>   headers:" in caplog.text
        assert "XX" not in caplog.text

    def test_password_mask_exact(self, caplog):
        """Mutant 22: '***' -> 'XX***XX'."""
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            _log_request("POST", "https://example.com", data={"password": "secret"})
        # The masked value should be exactly '***', not 'XX***XX'
        assert "'***'" in caplog.text or '"***"' in caplog.text
        assert "XX***XX" not in caplog.text

    def test_body_exact_prefix(self, caplog):
        """Mutant 30: body line prefix mutated."""
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            _log_request("POST", "https://example.com", data={"k": "v"})
        assert ">>>   body:" in caplog.text
        assert "XX" not in caplog.text


class TestLogResponseMutants:
    """Kill surviving log_response mutants by asserting exact log format.

    Mutants 3, 7, 10, 12, 13, 18, 21, 25, 27.
    """

    def _make_resp(self, status=200, url="https://example.com"):
        resp = MagicMock()
        resp.status = status
        resp.url = url
        resp.headers = CIMultiDict({"X-Test": "yes"})
        return resp

    def test_url_logged_not_none(self, caplog):
        """Mutant 3: resp.url -> None."""
        resp = self._make_resp(url="https://specific.example.com/path")
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            _log_response(resp)
        assert "https://specific.example.com/path" in caplog.text

    def test_exact_status_line_prefix(self, caplog):
        """Mutant 7: '<<< %s %s' -> 'XX<<< %s %sXX'."""
        resp = self._make_resp(status=201)
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            _log_response(resp)
        assert "<<< 201" in caplog.text
        assert "XX" not in caplog.text

    def test_headers_logged_as_dict(self, caplog):
        """Mutant 10: dict(resp.headers) -> None."""
        resp = self._make_resp()
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            _log_response(resp)
        assert "X-Test" in caplog.text

    def test_headers_not_removed(self, caplog):
        """Mutant 12: removes dict(resp.headers) arg entirely."""
        resp = self._make_resp()
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            _log_response(resp)
        # The dict argument should be present and contain headers
        assert "yes" in caplog.text

    def test_headers_line_exact_prefix(self, caplog):
        """Mutant 13: '<<<   headers: %s' -> 'XX<<<   headers: %sXX'."""
        resp = self._make_resp()
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            _log_response(resp)
        assert "<<<   headers:" in caplog.text
        assert "XX" not in caplog.text

    def test_body_preview_exact_length(self, caplog):
        """Mutant 18: body[:2000] -> body[:2001].

        With a body of length 2001, the preview should be exactly 2000
        chars plus the truncation suffix. If the mutant changes to 2001,
        the preview would include the full body (no truncation because
        2001 == 2001 but len check is > 2000 so truncation message still
        appears but preview is 1 char longer).
        """
        resp = self._make_resp()
        # Use a unique marker at position 2001 that won't appear elsewhere
        body = "a" * 2000 + "\x07"  # 2001 chars, \x07 (BEL) is the extra char
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            _log_response(resp, body)
        # With correct code: body[:2000] means preview is 'a' * 2000
        # and '\x07' should NOT be in the preview
        # With mutant code: body[:2001] means '\x07' IS in the preview
        # Look at the body log line specifically
        body_lines = [x for x in caplog.text.splitlines() if "body:" in x]
        assert len(body_lines) == 1
        assert "\x07" not in body_lines[0]

    def test_body_logged_with_body_prefix(self, caplog):
        """Mutants 21, 25, 27 -- various format string mutations."""
        resp = self._make_resp()
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            _log_response(resp, "test body content")
        assert "<<<   body:" in caplog.text
        assert "test body content" in caplog.text


class TestB2cLoginCookieJarArgs:
    """Tests that verify CookieJar and DummyCookieJar arguments,
    killing mutants 4, 6, 130, 132."""

    async def test_first_session_receives_cookie_jar(self):
        """Mutants 4 (cookie_jar=None) and 6 (cookie_jar removed).

        Verify that the first ClientSession gets cookie_jar=jar
        (the CookieJar instance).
        """
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )
        post_resp = _make_mock_response(status=200, text='{"status":"200"}')
        confirmed_resp = _make_mock_response(
            status=302,
            headers={"Location": REDIRECT_URL},
        )

        cs_calls = []
        call_idx = [0]

        def capture_cs(**kwargs):
            cs_calls.append(kwargs)
            idx = call_idx[0]
            call_idx[0] += 1
            if idx == 0:
                return _make_mock_session(
                    get=MagicMock(return_value=login_resp),
                )
            return _make_mock_session(
                post=MagicMock(return_value=post_resp),
                get=MagicMock(return_value=confirmed_resp),
            )

        with (
            patch(f"{_MOD}.ClientSession", side_effect=capture_cs),
            patch(f"{_MOD}.CookieJar") as jar_cls,
            patch(f"{_MOD}.DummyCookieJar"),
        ):
            jar = MagicMock()
            jar.filter_cookies.return_value = {}
            jar_cls.return_value = jar
            await b2c_login_with_credentials(AUTH_URI, "user@test.com", "pass")

        # First session must have cookie_jar set to the jar instance
        assert "cookie_jar" in cs_calls[0], (
            "First session must receive cookie_jar kwarg"
        )
        assert cs_calls[0]["cookie_jar"] is jar, (
            "cookie_jar must be the CookieJar instance"
        )

    async def test_second_session_uses_dummy_cookie_jar(self):
        """Mutants 130 (cookie_jar=None) and 132 (cookie_jar removed).

        Verify the second ClientSession gets cookie_jar=DummyCookieJar().
        """
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )
        post_resp = _make_mock_response(status=200, text='{"status":"200"}')
        confirmed_resp = _make_mock_response(
            status=302,
            headers={"Location": REDIRECT_URL},
        )

        cs_calls = []
        call_idx = [0]

        def capture_cs(**kwargs):
            cs_calls.append(kwargs)
            idx = call_idx[0]
            call_idx[0] += 1
            if idx == 0:
                return _make_mock_session(
                    get=MagicMock(return_value=login_resp),
                )
            return _make_mock_session(
                post=MagicMock(return_value=post_resp),
                get=MagicMock(return_value=confirmed_resp),
            )

        with (
            patch(f"{_MOD}.ClientSession", side_effect=capture_cs),
            patch(f"{_MOD}.CookieJar") as jar_cls,
            patch(f"{_MOD}.DummyCookieJar") as dummy_cls,
        ):
            jar = MagicMock()
            jar.filter_cookies.return_value = {}
            jar_cls.return_value = jar
            dummy_jar = MagicMock()
            dummy_cls.return_value = dummy_jar
            await b2c_login_with_credentials(AUTH_URI, "user@test.com", "pass")

        # Second session must have cookie_jar set to DummyCookieJar instance
        assert len(cs_calls) == 2
        assert "cookie_jar" in cs_calls[1], (
            "Second session must receive cookie_jar kwarg"
        )
        assert cs_calls[1]["cookie_jar"] is dummy_jar, (
            "cookie_jar must be a DummyCookieJar instance"
        )


class TestB2cLoginPostUrlAndOrigin:
    """Tests that verify exact POST URL construction and Origin header,
    killing mutants 24, 70, 102, 107, 137, 141, 146, 147, 148, 151."""

    async def test_post_url_uses_yarl_url(self):
        """Mutants 137 (None), 141 (removed), 146-151 (encoded param changes).

        Verify that session.post() is called with a yarl.URL constructed
        from the fields['post_url'] with encoded=True.
        """
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )
        post_resp = _make_mock_response(status=200, text='{"status":"200"}')
        confirmed_resp = _make_mock_response(
            status=302,
            headers={"Location": REDIRECT_URL},
        )

        login_session = _make_mock_session(
            get=MagicMock(return_value=login_resp),
        )
        raw_session = _make_mock_session(
            post=MagicMock(return_value=post_resp),
            get=MagicMock(return_value=confirmed_resp),
        )

        with _patch_sessions(login_session, raw_session):
            await b2c_login_with_credentials(AUTH_URI, "user@test.com", "pass")

        call = raw_session.post.call_args
        url_arg = call[0][0] if call[0] else call[1].get("url")
        # Must be a yarl.URL, not None, not missing
        assert isinstance(url_arg, yarl.URL), f"Expected yarl.URL, got {type(url_arg)}"
        url_str = str(url_arg)
        # Must contain the SelfAsserted endpoint
        assert "SelfAsserted" in url_str
        # Must contain the tx and p query params
        assert "tx=" in url_str
        assert f"p={_POLICY}" in url_str

    async def test_origin_header_uses_page_url(self):
        """Mutants 24 (page_url=str(None)) and 70 (urlparse(None)).

        If page_url becomes 'None', the origin would be wrong.
        Verify Origin header matches the expected host.
        """
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )
        post_resp = _make_mock_response(status=200, text='{"status":"200"}')
        confirmed_resp = _make_mock_response(
            status=302,
            headers={"Location": REDIRECT_URL},
        )

        login_session = _make_mock_session(
            get=MagicMock(return_value=login_resp),
        )
        raw_session = _make_mock_session(
            post=MagicMock(return_value=post_resp),
            get=MagicMock(return_value=confirmed_resp),
        )

        with _patch_sessions(login_session, raw_session):
            await b2c_login_with_credentials(AUTH_URI, "user@test.com", "pass")

        call = raw_session.post.call_args
        hdrs = call[1]["headers"]
        # Origin must be the B2C host, not "None://"
        assert hdrs["Origin"] == _HOST
        assert "None" not in hdrs["Origin"]

    async def test_cookie_header_passed_to_post(self):
        """Mutant 107: post_headers['Cookie'] = None.

        Verify Cookie header is a string (result of _build_cookie_header),
        not None.
        """
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )
        post_resp = _make_mock_response(status=200, text='{"status":"200"}')
        confirmed_resp = _make_mock_response(
            status=302,
            headers={"Location": REDIRECT_URL},
        )

        login_session = _make_mock_session(
            get=MagicMock(return_value=login_resp),
        )
        raw_session = _make_mock_session(
            post=MagicMock(return_value=post_resp),
            get=MagicMock(return_value=confirmed_resp),
        )

        with _patch_sessions(login_session, raw_session):
            await b2c_login_with_credentials(AUTH_URI, "user@test.com", "pass")

        call = raw_session.post.call_args
        hdrs = call[1]["headers"]
        assert hdrs["Cookie"] is not None, "Cookie header must not be None"
        assert isinstance(hdrs["Cookie"], str), "Cookie header must be a string"

    async def test_build_cookie_header_receives_post_url(self):
        """Mutant 102: _build_cookie_header(jar, None).

        Verify cookie_header is built using the correct post_url.
        We can check by making filter_cookies track its argument.
        """
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )
        post_resp = _make_mock_response(status=200, text='{"status":"200"}')
        confirmed_resp = _make_mock_response(
            status=302,
            headers={"Location": REDIRECT_URL},
        )

        login_session = _make_mock_session(
            get=MagicMock(return_value=login_resp),
        )
        raw_session = _make_mock_session(
            post=MagicMock(return_value=post_resp),
            get=MagicMock(return_value=confirmed_resp),
        )

        with _patch_sessions(login_session, raw_session) as (_jar_cls, mock_jar):
            await b2c_login_with_credentials(AUTH_URI, "user@test.com", "pass")

        # filter_cookies should have been called with a yarl.URL of the post_url
        assert mock_jar.filter_cookies.called
        fc_arg = mock_jar.filter_cookies.call_args[0][0]
        fc_str = str(fc_arg)
        assert "SelfAsserted" in fc_str, (
            f"filter_cookies should receive post_url, got {fc_str}"
        )


class TestB2cLoginCookieMerging:
    """Tests that verify cookie parsing and merging logic,
    killing mutants 173, 174, 175, 177, 185, 191, 192, 194, 197, 198, 209."""

    async def test_cookie_split_separator(self):
        """Mutants 173 (split(None)), 174 (split('XX; XX')).

        When existing cookies contain '; ' separator, they must be
        parsed correctly. We verify by checking the merged cookie header.
        """
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )
        # POST response with Set-Cookie to trigger merging
        post_resp = _make_mock_response_multiheader(
            status=200,
            text='{"status":"200"}',
            headers=[
                ("Set-Cookie", "new=val; Path=/"),
            ],
        )
        confirmed_resp = _make_mock_response(
            status=302,
            headers={"Location": REDIRECT_URL},
        )

        # Pre-populate cookie jar with existing cookies that use '; ' separator
        m1 = MagicMock(spec=Morsel)
        m1.key = "existing"
        m1.value = "oldval"

        login_session = _make_mock_session(
            get=MagicMock(return_value=login_resp),
        )
        raw_session = _make_mock_session(
            post=MagicMock(return_value=post_resp),
            get=MagicMock(return_value=confirmed_resp),
        )

        with _patch_sessions(login_session, raw_session) as (_jar_cls, mock_jar):
            mock_jar.filter_cookies.return_value = {"a": m1}
            await b2c_login_with_credentials(AUTH_URI, "user@test.com", "pass")

        # The confirmed GET should have merged cookies
        get_call = raw_session.get.call_args
        cookie_hdr = get_call[1]["headers"]["Cookie"]
        # 'existing=oldval' from cookie jar + 'new=val' from Set-Cookie
        assert "existing=oldval" in cookie_hdr
        assert "new=val" in cookie_hdr

    async def test_cookie_equals_in_part(self):
        """Mutant 175: if '=' in part -> if 'XX=XX' in part.

        Cookie parts always contain '=' so this would break parsing.
        Verify that existing cookies with '=' are correctly parsed.
        """
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )
        post_resp = _make_mock_response(
            status=200,
            text='{"status":"200"}',
        )
        confirmed_resp = _make_mock_response(
            status=302,
            headers={"Location": REDIRECT_URL},
        )

        # Cookie with value containing '='
        m1 = MagicMock(spec=Morsel)
        m1.key = "token"
        m1.value = "abc=def"

        login_session = _make_mock_session(
            get=MagicMock(return_value=login_resp),
        )
        raw_session = _make_mock_session(
            post=MagicMock(return_value=post_resp),
            get=MagicMock(return_value=confirmed_resp),
        )

        with _patch_sessions(login_session, raw_session) as (_jar_cls, mock_jar):
            mock_jar.filter_cookies.return_value = {"a": m1}
            await b2c_login_with_credentials(AUTH_URI, "user@test.com", "pass")

        get_call = raw_session.get.call_args
        cookie_hdr = get_call[1]["headers"]["Cookie"]
        assert "token=abc=def" in cookie_hdr

    async def test_cookie_value_not_none(self):
        """Mutant 185: cookies[n] = v -> cookies[n] = None.

        Verify the cookie value is preserved (not None).
        """
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )
        post_resp = _make_mock_response(
            status=200,
            text='{"status":"200"}',
        )
        confirmed_resp = _make_mock_response(
            status=302,
            headers={"Location": REDIRECT_URL},
        )

        m1 = MagicMock(spec=Morsel)
        m1.key = "sess"
        m1.value = "myvalue"

        login_session = _make_mock_session(
            get=MagicMock(return_value=login_resp),
        )
        raw_session = _make_mock_session(
            post=MagicMock(return_value=post_resp),
            get=MagicMock(return_value=confirmed_resp),
        )

        with _patch_sessions(login_session, raw_session) as (_jar_cls, mock_jar):
            mock_jar.filter_cookies.return_value = {"a": m1}
            await b2c_login_with_credentials(AUTH_URI, "user@test.com", "pass")

        get_call = raw_session.get.call_args
        cookie_hdr = get_call[1]["headers"]["Cookie"]
        assert "sess=myvalue" in cookie_hdr
        assert "None" not in cookie_hdr

    async def test_set_cookie_split_by_semicolon(self):
        """Mutants 194 (split(None)), 197 (split no maxsplit), 198 (rsplit).

        Set-Cookie header 'name=value; Path=/' should be split on ';'
        to extract just 'name=value'.
        """
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )
        # Set-Cookie with attributes that include semicolons
        post_resp = _make_mock_response_multiheader(
            status=200,
            text='{"status":"200"}',
            headers=[
                ("Set-Cookie", "auth=tok123; Path=/; HttpOnly; Secure"),
            ],
        )
        confirmed_resp = _make_mock_response(
            status=302,
            headers={"Location": REDIRECT_URL},
        )

        login_session = _make_mock_session(
            get=MagicMock(return_value=login_resp),
        )
        raw_session = _make_mock_session(
            post=MagicMock(return_value=post_resp),
            get=MagicMock(return_value=confirmed_resp),
        )

        with _patch_sessions(login_session, raw_session):
            await b2c_login_with_credentials(AUTH_URI, "user@test.com", "pass")

        get_call = raw_session.get.call_args
        cookie_hdr = get_call[1]["headers"]["Cookie"]
        # Must contain just 'auth=tok123', not 'Path=/' etc.
        assert "auth=tok123" in cookie_hdr
        assert "Path" not in cookie_hdr

    async def test_set_cookie_split_equals_uses_split_not_rsplit(self):
        """Mutant 209: sc_pair.split('=', 1) -> sc_pair.rsplit('=', 1).

        With 'name=val=ue', split gives ('name', 'val=ue') while
        rsplit gives ('name=val', 'ue'). Verify correct behavior.
        """
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )
        post_resp = _make_mock_response_multiheader(
            status=200,
            text='{"status":"200"}',
            headers=[
                ("Set-Cookie", "data=abc=xyz; Path=/"),
            ],
        )
        confirmed_resp = _make_mock_response(
            status=302,
            headers={"Location": REDIRECT_URL},
        )

        login_session = _make_mock_session(
            get=MagicMock(return_value=login_resp),
        )
        raw_session = _make_mock_session(
            post=MagicMock(return_value=post_resp),
            get=MagicMock(return_value=confirmed_resp),
        )

        with _patch_sessions(login_session, raw_session):
            await b2c_login_with_credentials(AUTH_URI, "user@test.com", "pass")

        get_call = raw_session.get.call_args
        cookie_hdr = get_call[1]["headers"]["Cookie"]
        # split('=', 1) gives name='data', value='abc=xyz'
        # rsplit('=', 1) gives name='data=abc', value='xyz'
        assert "data=abc=xyz" in cookie_hdr

    async def test_set_cookie_header_case_insensitive(self):
        """Mutants 191 ('set-cookie') and 192 ('SET-COOKIE').

        CIMultiDict is case-insensitive, so getall('Set-Cookie') works
        regardless of actual header casing. These mutants are effectively
        equivalent with CIMultiDict. Document this fact.
        """
        # NOTE: Mutants 191 and 192 change the "Set-Cookie" string in
        # resp.headers.getall("Set-Cookie", []) to "set-cookie" or
        # "SET-COOKIE". Since resp.headers is a CIMultiDict (case-
        # insensitive), all three forms return the same results.
        # These are equivalent mutants.
        pass


class TestB2cLoginLogCallMutants:
    """Tests that kill logging-related mutants inside b2c_login_with_credentials.

    Mutants 11, 12, 15, 16, 26, 28, 37-47, 51-57, 111-118, 127, 155, 157, 169.
    Many of these modify _log_request/_log_response call args or
    _LOGGER.debug format strings.
    """

    async def _run_flow_with_logging(self, caplog):
        """Helper: run happy-path flow and return caplog."""
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )
        post_resp = _make_mock_response(status=200, text='{"status":"200"}')
        confirmed_resp = _make_mock_response(
            status=302,
            headers={"Location": REDIRECT_URL},
        )

        login_session = _make_mock_session(
            get=MagicMock(return_value=login_resp),
        )
        raw_session = _make_mock_session(
            post=MagicMock(return_value=post_resp),
            get=MagicMock(return_value=confirmed_resp),
        )

        with (
            _patch_sessions(login_session, raw_session),
            caplog.at_level(logging.DEBUG, "flameconnect"),
        ):
            result = await b2c_login_with_credentials(
                AUTH_URI, "user@test.com", "pass123"
            )
        return result

    async def test_log_request_get_method(self, caplog):
        """Mutants 11 (None), 15 ('XXGETXX'), 16 ('get').

        Verify the initial GET log includes correct method.
        """
        await self._run_flow_with_logging(caplog)
        assert ">>> GET" in caplog.text

    async def test_log_request_get_url(self, caplog):
        """Mutant 12: auth_uri -> None."""
        await self._run_flow_with_logging(caplog)
        assert AUTH_URI in caplog.text

    async def test_log_response_body_passed(self, caplog):
        """Mutants 26, 28: _log_response(resp, login_html) -> (resp, None) or (resp,).

        When body is None, _log_response skips body logging.
        With the real login_html, body should appear in logs.
        """
        await self._run_flow_with_logging(caplog)
        # The login HTML contains 'SETTINGS' which should appear in body log
        assert "SETTINGS" in caplog.text

    async def test_parsed_login_page_debug(self, caplog):
        """Mutants 37-47: _LOGGER.debug('Parsed login page: ...') mutations.

        Verify the debug message for parsed login page appears correctly.
        """
        await self._run_flow_with_logging(caplog)
        assert "Parsed login page:" in caplog.text
        # Verify csrf prefix is logged (first 16 chars of 'dGVzdC1jc3JmLXRva2Vu')
        assert "dGVzdC1jc3JmLXRv" in caplog.text  # first 16 chars
        # Verify tx prefix is logged (first 40 chars)
        assert "StateProperties=eyJ0eXAiOiJKV1QiLCJhbGci" in caplog.text

    async def test_parsed_debug_has_ellipsis(self, caplog):
        """Mutants 52, 57: '...' -> 'XX...XX'."""
        await self._run_flow_with_logging(caplog)
        assert "..." in caplog.text
        # XX...XX should not appear
        assert "XX...XX" not in caplog.text

    async def test_log_request_post_method(self, caplog):
        """Mutants 118 (None), 127 ('post'): _log_request('POST', ...) mutations."""
        await self._run_flow_with_logging(caplog)
        assert ">>> POST" in caplog.text

    async def test_cookies_debug_line(self, caplog):
        """Mutants 111-117: _LOGGER.debug('>>>   cookies: %s', ...) mutations."""
        await self._run_flow_with_logging(caplog)
        assert ">>>   cookies:" in caplog.text
        assert "XX" not in caplog.text.replace("XMLHttpRequest", "")

    async def test_log_response_post_body(self, caplog):
        """Mutants 155, 157: _log_response(resp, body) -> (resp, None) or (resp,)."""
        await self._run_flow_with_logging(caplog)
        # The POST response body is '{"status":"200"}', it should be logged
        assert '"status":"200"' in caplog.text

    async def test_error_message_exact(self):
        """Mutant 169: error message 'Invalid email or password' ->
        'XXInvalid email or passwordXX'."""
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )
        post_resp = _make_mock_response(
            status=200,
            text='{"status":"400","message":"Invalid"}',
        )

        login_session = _make_mock_session(
            get=MagicMock(return_value=login_resp),
        )
        raw_session = _make_mock_session(
            post=MagicMock(return_value=post_resp),
            get=MagicMock(return_value=MagicMock()),
        )

        with (
            _patch_sessions(login_session, raw_session),
            pytest.raises(
                AuthenticationError,
                match=r"^Invalid email or password$",
            ),
        ):
            await b2c_login_with_credentials(AUTH_URI, "bad@test.com", "wrong")


class TestB2cLoginConfirmedQueryString:
    """Test the confirmed GET request query string in detail.

    Kills mutants related to confirmed_qs construction (around lines 269-274).
    """

    async def test_confirmed_query_has_remember_me_false(self):
        """Verify rememberMe=false is in the confirmed URL query string."""
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )
        post_resp = _make_mock_response(status=200, text='{"status":"200"}')
        confirmed_resp = _make_mock_response(
            status=302,
            headers={"Location": REDIRECT_URL},
        )

        login_session = _make_mock_session(
            get=MagicMock(return_value=login_resp),
        )
        raw_session = _make_mock_session(
            post=MagicMock(return_value=post_resp),
            get=MagicMock(return_value=confirmed_resp),
        )

        with _patch_sessions(login_session, raw_session):
            await b2c_login_with_credentials(AUTH_URI, "user@test.com", "pass")

        get_call = raw_session.get.call_args
        url_str = str(get_call[0][0] if get_call[0] else get_call[1].get("url"))
        assert "rememberMe=false" in url_str
        # Verify all expected params
        assert "csrf_token=dGVzdC1jc3JmLXRva2Vu" in url_str
        assert f"p={_POLICY}" in url_str

    async def test_confirmed_get_url_uses_yarl_encoded(self):
        """Verify the confirmed GET uses yarl.URL with encoded=True."""
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )
        post_resp = _make_mock_response(status=200, text='{"status":"200"}')
        confirmed_resp = _make_mock_response(
            status=302,
            headers={"Location": REDIRECT_URL},
        )

        login_session = _make_mock_session(
            get=MagicMock(return_value=login_resp),
        )
        raw_session = _make_mock_session(
            post=MagicMock(return_value=post_resp),
            get=MagicMock(return_value=confirmed_resp),
        )

        with _patch_sessions(login_session, raw_session):
            await b2c_login_with_credentials(AUTH_URI, "user@test.com", "pass")

        get_call = raw_session.get.call_args
        url_arg = get_call[0][0] if get_call[0] else get_call[1].get("url")
        assert isinstance(url_arg, yarl.URL), f"Expected yarl.URL, got {type(url_arg)}"


class TestB2cLoginCustomSchemeDetection:
    """Kill mutants around the custom scheme redirect detection (line 297)."""

    async def test_redirect_with_msal_prefix_not_auth(self):
        """Ensure 'msal' prefix AND '://auth' must both match.

        A Location like 'msalXXX://other' should NOT be treated as the
        custom-scheme redirect.
        """
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )
        post_resp = _make_mock_response(status=200, text='{"status":"200"}')
        # A redirect that starts with 'msal' but doesn't have '://auth'
        not_auth_resp = _make_mock_response(
            status=302,
            headers={"Location": "msaltest://notauth?code=abc"},
        )
        # Then the real redirect
        final_resp = _make_mock_response(
            status=302,
            headers={"Location": REDIRECT_URL},
        )

        session = _make_mock_session(
            get=MagicMock(side_effect=[login_resp, not_auth_resp, final_resp]),
            post=MagicMock(return_value=post_resp),
        )

        with _patch_session(session):
            result = await b2c_login_with_credentials(AUTH_URI, "user@test.com", "pass")
        assert result == REDIRECT_URL

    async def test_msal_redirect_detected_correctly(self):
        """Verify the exact msal redirect URL is returned without modification."""
        redirect = (
            "msal1af761dc-085a-411f-9cb9-53e5e2115bd2://auth?code=ABC123&state=XYZ"
        )
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )
        post_resp = _make_mock_response(status=200, text='{"status":"200"}')
        confirmed_resp = _make_mock_response(
            status=302,
            headers={"Location": redirect},
        )

        login_session = _make_mock_session(
            get=MagicMock(return_value=login_resp),
        )
        raw_session = _make_mock_session(
            post=MagicMock(return_value=post_resp),
            get=MagicMock(return_value=confirmed_resp),
        )

        with _patch_sessions(login_session, raw_session):
            result = await b2c_login_with_credentials(AUTH_URI, "user@test.com", "pass")
        assert result == redirect


# -------------------------------------------------------------------
# Additional mutant-killing tests (round 2)
# -------------------------------------------------------------------


class TestRelativeRedirectUrlResolution:
    """Kill mutants M295, M300, M301 related to relative URL handling."""

    async def test_relative_redirect_resolved_to_absolute_url(self):
        """M295: flips not in startswith check.
        M300: urljoin(None, location).
        M301: urljoin(next_url, None).

        Verify that after a relative redirect, the GET URL is absolute
        (contains the scheme/host from the confirmed URL).
        """
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )
        post_resp = _make_mock_response(status=200, text='{"status":"200"}')
        # First: relative redirect
        relative_resp = _make_mock_response(
            status=302,
            headers={"Location": "/relative/next"},
        )
        # Then: final msal redirect
        final_resp = _make_mock_response(
            status=302,
            headers={"Location": REDIRECT_URL},
        )

        login_session = _make_mock_session(
            get=MagicMock(return_value=login_resp),
        )
        raw_session = _make_mock_session(
            post=MagicMock(return_value=post_resp),
            get=MagicMock(side_effect=[relative_resp, final_resp]),
        )

        with _patch_sessions(login_session, raw_session):
            result = await b2c_login_with_credentials(AUTH_URI, "user@test.com", "pass")

        assert result == REDIRECT_URL

        # The second GET (after relative redirect) must be an absolute URL
        # that includes the host from the confirmed URL, not just "/relative/next"
        second_get_call = raw_session.get.call_args_list[1]
        resolved_url = str(
            second_get_call[0][0]
            if second_get_call[0]
            else second_get_call[1].get("url")
        )
        # With correct code: urljoin resolves "/relative/next" against the confirmed URL
        # With M295 (flipped): "/relative/next" is used as-is (not absolute)
        # With M300: urljoin(None, "/relative/next") → "/relative/next" (not absolute)
        # With M301: urljoin(base, None) → base (wrong URL entirely)
        assert resolved_url.startswith("http"), (
            f"Relative redirect must be resolved to absolute URL, got: {resolved_url}"
        )
        assert "/relative/next" in resolved_url


class TestCookieParsingMultipleCookies:
    """Kill mutants M173, M174, M215 related to cookie header separator parsing."""

    async def test_two_cookies_split_correctly(self):
        """M173: split('; ') → split(None) — splits on whitespace, causing trailing ';'.
        M174: split('; ') → split('XX; XX') — no match, whole string is one part.
        M215: '; '.join → 'XX; XX'.join — wrong separator in output.

        With 2+ cookies from the jar, the cookie header must be properly
        split and re-joined with '; ' separator.
        """
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )
        post_resp = _make_mock_response_multiheader(
            status=200,
            text='{"status":"200"}',
            headers=[("Set-Cookie", "added=new; Path=/")],
        )
        confirmed_resp = _make_mock_response(
            status=302,
            headers={"Location": REDIRECT_URL},
        )

        # Two cookies in the jar
        m1 = MagicMock(spec=Morsel)
        m1.key = "alpha"
        m1.value = "111"
        m2 = MagicMock(spec=Morsel)
        m2.key = "beta"
        m2.value = "222"

        login_session = _make_mock_session(
            get=MagicMock(return_value=login_resp),
        )
        raw_session = _make_mock_session(
            post=MagicMock(return_value=post_resp),
            get=MagicMock(return_value=confirmed_resp),
        )

        with _patch_sessions(login_session, raw_session) as (_jar_cls, mock_jar):
            mock_jar.filter_cookies.return_value = {"a": m1, "b": m2}
            await b2c_login_with_credentials(AUTH_URI, "user@test.com", "pass")

        get_call = raw_session.get.call_args
        cookie_hdr = get_call[1]["headers"]["Cookie"]
        # All three cookies must be present as separate key=value pairs
        assert "alpha=111" in cookie_hdr
        assert "beta=222" in cookie_hdr
        assert "added=new" in cookie_hdr
        # No double-semicolons (caused by M173 split(None) trailing ';')
        assert ";;" not in cookie_hdr
        # No "XX" in separator (caused by M215 "XX; XX".join)
        assert "XX" not in cookie_hdr


class TestSetCookieSemicolonParsing:
    """Kill mutant M194: split(';', 1) → split(None, 1) for Set-Cookie."""

    async def test_set_cookie_value_no_trailing_semicolon(self):
        """M194: split(None, 1) splits on whitespace instead of ';',
        leaving a trailing ';' on the cookie pair.

        Set-Cookie: 'sess=abc123; Path=/; HttpOnly'
        Correct: split(';', 1)[0] → 'sess=abc123'
        Mutant:  split(None, 1)[0] → 'sess=abc123;' (trailing semicolon)

        Verify the merged cookie value doesn't have a trailing ';'.
        """
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )
        post_resp = _make_mock_response_multiheader(
            status=200,
            text='{"status":"200"}',
            headers=[
                ("Set-Cookie", "sess=abc123; Path=/; HttpOnly"),
            ],
        )
        confirmed_resp = _make_mock_response(
            status=302,
            headers={"Location": REDIRECT_URL},
        )

        login_session = _make_mock_session(
            get=MagicMock(return_value=login_resp),
        )
        raw_session = _make_mock_session(
            post=MagicMock(return_value=post_resp),
            get=MagicMock(return_value=confirmed_resp),
        )

        with _patch_sessions(login_session, raw_session):
            await b2c_login_with_credentials(AUTH_URI, "user@test.com", "pass")

        get_call = raw_session.get.call_args
        cookie_hdr = get_call[1]["headers"]["Cookie"]
        assert "sess=abc123" in cookie_hdr
        # M194 would produce "sess=abc123;" — check no trailing semicolon
        # by checking the exact value doesn't include "abc123;"
        assert "abc123;" not in cookie_hdr


class TestCookieSplitVsRsplit:
    """Kill mutant M182: part.split('=', 1) → part.rsplit('=', 1)."""

    async def test_cookie_with_equals_in_value_overridden_by_set_cookie(self):
        """M182: rsplit('=', 1) on 'token=abc=def' gives ('token=abc', 'def')
        instead of ('token', 'abc=def'). When a Set-Cookie also sets 'token',
        the split version replaces the old 'token' value but the rsplit
        version creates a separate 'token=abc' key.

        Verify that after Set-Cookie sets 'token=updated', the old
        'token=abc=def' is gone (replaced, not duplicated).
        """
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )
        post_resp = _make_mock_response_multiheader(
            status=200,
            text='{"status":"200"}',
            headers=[("Set-Cookie", "token=updated; Path=/")],
        )
        confirmed_resp = _make_mock_response(
            status=302,
            headers={"Location": REDIRECT_URL},
        )

        # Cookie jar has a cookie with '=' in its value
        m1 = MagicMock(spec=Morsel)
        m1.key = "token"
        m1.value = "abc=def"

        login_session = _make_mock_session(
            get=MagicMock(return_value=login_resp),
        )
        raw_session = _make_mock_session(
            post=MagicMock(return_value=post_resp),
            get=MagicMock(return_value=confirmed_resp),
        )

        with _patch_sessions(login_session, raw_session) as (_jar_cls, mock_jar):
            mock_jar.filter_cookies.return_value = {"a": m1}
            await b2c_login_with_credentials(AUTH_URI, "user@test.com", "pass")

        get_call = raw_session.get.call_args
        cookie_hdr = get_call[1]["headers"]["Cookie"]
        # With correct split('=', 1): cookies['token'] = 'abc=def', then
        # Set-Cookie overrides cookies['token'] = 'updated'
        # Result: "token=updated" only
        assert "token=updated" in cookie_hdr
        # With rsplit('=', 1): cookies['token=abc'] = 'def', then
        # Set-Cookie adds cookies['token'] = 'updated'
        # Result: "token=abc=def; token=updated" — old value persists
        assert cookie_hdr.count("token") == 1, (
            f"Expected 'token' to appear once (overridden), got: {cookie_hdr}"
        )


class TestLogNoneDetection:
    """Kill logging mutants M11 and M12 by detecting 'None' in log output."""

    async def test_no_none_in_log_method_or_url(self, caplog):
        """M11: _log_request(None, auth_uri) — logs '>>> None ...'
        M12: _log_request('GET', None) — logs '>>> GET None'

        Verify that no log line contains 'None' where a method or URL should be.
        """
        login_resp = _make_mock_response(
            status=200,
            text=SAMPLE_B2C_HTML,
            url=SAMPLE_PAGE_URL,
        )
        post_resp = _make_mock_response(status=200, text='{"status":"200"}')
        confirmed_resp = _make_mock_response(
            status=302,
            headers={"Location": REDIRECT_URL},
        )

        login_session = _make_mock_session(
            get=MagicMock(return_value=login_resp),
        )
        raw_session = _make_mock_session(
            post=MagicMock(return_value=post_resp),
            get=MagicMock(return_value=confirmed_resp),
        )

        with (
            _patch_sessions(login_session, raw_session),
            caplog.at_level(logging.DEBUG, "flameconnect"),
        ):
            await b2c_login_with_credentials(AUTH_URI, "user@test.com", "pass")

        # Check that ">>> " log lines don't contain "None" as method or URL
        request_lines = [x for x in caplog.text.splitlines() if ">>>" in x]
        for line in request_lines:
            # Method/URL should never be None
            if ">>> GET " in line or ">>> POST " in line:
                assert " None" not in line.split(">>>")[1], (
                    f"Found 'None' in log line: {line}"
                )
