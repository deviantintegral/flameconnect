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
                match=("Redirect without Location header"),
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
                match=("Reached 200 response without finding redirect URL"),
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
