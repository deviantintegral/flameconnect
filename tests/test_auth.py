"""Tests for the authentication module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from flameconnect.auth import MsalAuth, TokenAuth

# ---------------------------------------------------------------------------
# TokenAuth
# ---------------------------------------------------------------------------


class TestTokenAuth:
    """Test TokenAuth with string and async callable."""

    async def test_string_token(self):
        auth = TokenAuth("my-static-token")
        token = await auth.get_token()
        assert token == "my-static-token"

    async def test_callable_token(self):
        async def token_factory() -> str:
            return "dynamic-token-456"

        auth = TokenAuth(token_factory)
        token = await auth.get_token()
        assert token == "dynamic-token-456"

    async def test_callable_called_each_time(self):
        call_count = 0

        async def counting_factory() -> str:
            nonlocal call_count
            call_count += 1
            return f"token-{call_count}"

        auth = TokenAuth(counting_factory)
        t1 = await auth.get_token()
        t2 = await auth.get_token()
        assert t1 == "token-1"
        assert t2 == "token-2"
        assert call_count == 2


# ---------------------------------------------------------------------------
# MsalAuth
# ---------------------------------------------------------------------------


class TestMsalAuth:
    """Test MsalAuth with mocked MSAL library."""

    @patch("flameconnect.auth.msal")
    async def test_silent_acquisition(self, mock_msal, tmp_path):
        """When cached token exists, acquire_token_silent returns it."""
        cache_path = tmp_path / "token_cache.json"

        mock_cache = MagicMock()
        mock_cache.has_state_changed = False
        mock_msal.SerializableTokenCache.return_value = mock_cache

        mock_app = MagicMock()
        mock_app.get_accounts.return_value = [{"username": "user@example.com"}]
        mock_app.acquire_token_silent.return_value = {
            "access_token": "cached-token-789"
        }
        mock_msal.PublicClientApplication.return_value = mock_app

        auth = MsalAuth(cache_path=cache_path)
        token = await auth.get_token()

        assert token == "cached-token-789"
        mock_app.acquire_token_silent.assert_called_once()

    @patch("flameconnect.auth.msal")
    async def test_no_accounts_triggers_interactive(self, mock_msal, tmp_path):
        """When no cached accounts exist, interactive flow is initiated."""
        cache_path = tmp_path / "token_cache.json"

        mock_cache = MagicMock()
        mock_cache.has_state_changed = False
        mock_msal.SerializableTokenCache.return_value = mock_cache

        mock_app = MagicMock()
        mock_app.get_accounts.return_value = []
        mock_app.initiate_auth_code_flow.return_value = {
            "auth_uri": "https://example.com/auth",
        }
        mock_app.acquire_token_by_auth_code_flow.return_value = {
            "access_token": "interactive-token-abc"
        }
        mock_msal.PublicClientApplication.return_value = mock_app

        async def fake_prompt(auth_uri: str, redirect_uri: str) -> str:
            return "https://redirect?code=abc123"

        auth = MsalAuth(cache_path=cache_path, prompt_callback=fake_prompt)

        token = await auth.get_token()

        assert token == "interactive-token-abc"

    @patch("flameconnect.auth.msal")
    async def test_cache_saved_on_state_change(self, mock_msal, tmp_path):
        """Cache is written to disk when has_state_changed is True."""
        cache_path = tmp_path / "token_cache.json"

        mock_cache = MagicMock()
        mock_cache.has_state_changed = True
        mock_cache.serialize.return_value = '{"cached": true}'
        mock_msal.SerializableTokenCache.return_value = mock_cache

        mock_app = MagicMock()
        mock_app.get_accounts.return_value = [{"username": "user@example.com"}]
        mock_app.acquire_token_silent.return_value = {"access_token": "refreshed-token"}
        mock_msal.PublicClientApplication.return_value = mock_app

        auth = MsalAuth(cache_path=cache_path)
        await auth.get_token()

        assert cache_path.exists()
        assert cache_path.read_text() == '{"cached": true}'


# ---------------------------------------------------------------------------
# MsalAuth._parse_redirect_url
# ---------------------------------------------------------------------------


class TestParseRedirectUrl:
    """Test the URL parsing helper."""

    def test_parses_code(self):
        result = MsalAuth._parse_redirect_url("https://redirect?code=abc123&state=xyz")
        assert result["code"] == "abc123"
        assert result["state"] == "xyz"

    def test_ellipsis_raises(self):
        from flameconnect.exceptions import AuthenticationError

        with pytest.raises(AuthenticationError, match="ellipsis"):
            MsalAuth._parse_redirect_url("https://redirect?code=abc\u2026def")

    def test_no_code_raises(self):
        from flameconnect.exceptions import AuthenticationError

        with pytest.raises(AuthenticationError, match="No authorization code"):
            MsalAuth._parse_redirect_url("https://redirect?state=xyz")

    def test_error_in_url_raises(self):
        from flameconnect.exceptions import AuthenticationError

        with pytest.raises(AuthenticationError, match="Auth error"):
            MsalAuth._parse_redirect_url(
                "https://redirect?error=access_denied&error_description=User+cancelled"
            )
