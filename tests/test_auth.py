"""Tests for the authentication module."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from flameconnect.auth import _REDIRECT_URI, MsalAuth, TokenAuth
from flameconnect.const import AUTHORITY, CLIENT_ID, SCOPES
from flameconnect.exceptions import AuthenticationError

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
        mock_app.get_accounts.return_value = [
            {"username": "user@example.com"}
        ]
        mock_app.acquire_token_silent.return_value = {
            "access_token": "cached-token-789"
        }
        mock_msal.PublicClientApplication.return_value = mock_app

        auth = MsalAuth(cache_path=cache_path)
        token = await auth.get_token()

        assert token == "cached-token-789"
        mock_app.acquire_token_silent.assert_called_once()

    @patch("flameconnect.auth.msal")
    async def test_no_accounts_triggers_interactive(
        self, mock_msal, tmp_path
    ):
        """When no cached accounts exist, interactive flow is started."""
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

        async def fake_prompt(
            auth_uri: str, redirect_uri: str
        ) -> str:
            return "https://redirect?code=abc123"

        auth = MsalAuth(
            cache_path=cache_path, prompt_callback=fake_prompt
        )

        token = await auth.get_token()

        assert token == "interactive-token-abc"

    @patch("flameconnect.auth.msal")
    async def test_cache_saved_on_state_change(
        self, mock_msal, tmp_path
    ):
        """Cache is written to disk when has_state_changed is True."""
        cache_path = tmp_path / "token_cache.json"

        mock_cache = MagicMock()
        mock_cache.has_state_changed = True
        mock_cache.serialize.return_value = '{"cached": true}'
        mock_msal.SerializableTokenCache.return_value = mock_cache

        mock_app = MagicMock()
        mock_app.get_accounts.return_value = [
            {"username": "user@example.com"}
        ]
        mock_app.acquire_token_silent.return_value = {
            "access_token": "refreshed-token"
        }
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
        result = MsalAuth._parse_redirect_url(
            "https://redirect?code=abc123&state=xyz"
        )
        assert result["code"] == "abc123"
        assert result["state"] == "xyz"

    def test_ellipsis_raises(self):
        with pytest.raises(AuthenticationError, match="ellipsis"):
            MsalAuth._parse_redirect_url(
                "https://redirect?code=abc\u2026def"
            )

    def test_no_code_raises(self):
        with pytest.raises(
            AuthenticationError, match="No authorization code"
        ):
            MsalAuth._parse_redirect_url(
                "https://redirect?state=xyz"
            )

    def test_error_in_url_raises(self):
        with pytest.raises(AuthenticationError, match="Auth error"):
            MsalAuth._parse_redirect_url(
                "https://redirect?error=access_denied"
                "&error_description=User+cancelled"
            )

    def test_fragment_url_parsing(self):
        """URLs with # fragment should also be parsed."""
        result = MsalAuth._parse_redirect_url(
            "https://redirect#code=frag-code-999&state=frag-state"
        )
        assert result["code"] == "frag-code-999"
        assert result["state"] == "frag-state"

    def test_error_without_description_raises(self):
        """URL with error but no error_description still raises."""
        with pytest.raises(
            AuthenticationError, match="Auth error.*server_error"
        ):
            MsalAuth._parse_redirect_url(
                "https://redirect?error=server_error"
            )


# ---------------------------------------------------------------------------
# MsalAuth -- additional edge cases
# ---------------------------------------------------------------------------


class TestMsalAuthEdgeCases:
    """Test error paths in MsalAuth.get_token / _interactive_flow."""

    @patch("flameconnect.auth.msal")
    async def test_existing_cache_is_loaded(
        self, mock_msal, tmp_path
    ):
        """When the cache file exists, deserialize is called."""
        cache_path = tmp_path / "token_cache.json"
        cache_path.write_text('{"cached": "data"}')

        mock_cache = MagicMock()
        mock_cache.has_state_changed = False
        mock_msal.SerializableTokenCache.return_value = mock_cache

        mock_app = MagicMock()
        mock_app.get_accounts.return_value = [
            {"username": "u@ex.com"}
        ]
        mock_app.acquire_token_silent.return_value = {
            "access_token": "loaded-token"
        }
        mock_msal.PublicClientApplication.return_value = mock_app

        auth = MsalAuth(cache_path=cache_path)
        token = await auth.get_token()

        assert token == "loaded-token"
        mock_cache.deserialize.assert_called_once_with(
            '{"cached": "data"}'
        )

    @patch("flameconnect.auth.msal")
    async def test_no_auth_uri_in_flow_raises(
        self, mock_msal, tmp_path
    ):
        """initiate_auth_code_flow with no auth_uri raises."""
        cache_path = tmp_path / "token_cache.json"

        mock_cache = MagicMock()
        mock_cache.has_state_changed = False
        mock_msal.SerializableTokenCache.return_value = mock_cache

        mock_app = MagicMock()
        mock_app.get_accounts.return_value = []
        mock_app.initiate_auth_code_flow.return_value = {
            "error": "something_went_wrong",
        }
        mock_msal.PublicClientApplication.return_value = mock_app

        async def fake_prompt(
            auth_uri: str, redirect_uri: str
        ) -> str:
            return "https://redirect?code=abc123"

        auth = MsalAuth(
            cache_path=cache_path, prompt_callback=fake_prompt
        )

        with pytest.raises(
            AuthenticationError, match="Failed to initiate"
        ):
            await auth.get_token()

    @patch("flameconnect.auth.msal")
    async def test_no_prompt_callback_raises(
        self, mock_msal, tmp_path
    ):
        """No prompt_callback provided raises on interactive login."""
        cache_path = tmp_path / "token_cache.json"

        mock_cache = MagicMock()
        mock_cache.has_state_changed = False
        mock_msal.SerializableTokenCache.return_value = mock_cache

        mock_app = MagicMock()
        mock_app.get_accounts.return_value = []
        mock_app.initiate_auth_code_flow.return_value = {
            "auth_uri": "https://example.com/auth",
        }
        mock_msal.PublicClientApplication.return_value = mock_app

        auth = MsalAuth(cache_path=cache_path)

        with pytest.raises(
            AuthenticationError, match="no prompt_callback"
        ):
            await auth.get_token()

    @patch("flameconnect.auth.msal")
    async def test_token_exchange_failure_raises(
        self, mock_msal, tmp_path
    ):
        """acquire_token_by_auth_code_flow with no access_token."""
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
            "error": "invalid_grant",
            "error_description": "Code expired",
        }
        mock_msal.PublicClientApplication.return_value = mock_app

        async def fake_prompt(
            auth_uri: str, redirect_uri: str
        ) -> str:
            return "https://redirect?code=expired-code"

        auth = MsalAuth(
            cache_path=cache_path, prompt_callback=fake_prompt
        )

        with pytest.raises(
            AuthenticationError, match="Token exchange failed"
        ):
            await auth.get_token()


# ---------------------------------------------------------------------------
# MsalAuth -- mutant-killing tests for _build_app kwargs
# ---------------------------------------------------------------------------


class TestBuildAppArgs:
    """Verify _build_app passes correct args to MSAL."""

    @patch("flameconnect.auth.msal")
    async def test_build_app_passes_client_id(
        self, mock_msal, tmp_path
    ):
        """PublicClientApplication receives CLIENT_ID as first arg."""
        cache_path = tmp_path / "token_cache.json"

        mock_cache = MagicMock()
        mock_cache.has_state_changed = False
        mock_msal.SerializableTokenCache.return_value = mock_cache

        mock_app = MagicMock()
        mock_app.get_accounts.return_value = [{"username": "u"}]
        mock_app.acquire_token_silent.return_value = {
            "access_token": "t"
        }
        mock_msal.PublicClientApplication.return_value = mock_app

        auth = MsalAuth(cache_path=cache_path)
        await auth.get_token()

        mock_msal.PublicClientApplication.assert_called_once_with(
            CLIENT_ID,
            authority=AUTHORITY,
            validate_authority=False,
            token_cache=mock_cache,
        )

    @patch("flameconnect.auth.msal")
    async def test_build_app_cache_passed_as_token_cache(
        self, mock_msal, tmp_path
    ):
        """The SerializableTokenCache instance is used as token_cache."""
        cache_path = tmp_path / "token_cache.json"

        mock_cache = MagicMock()
        mock_cache.has_state_changed = False
        mock_msal.SerializableTokenCache.return_value = mock_cache

        mock_app = MagicMock()
        mock_app.get_accounts.return_value = [{"username": "u"}]
        mock_app.acquire_token_silent.return_value = {
            "access_token": "t"
        }
        mock_msal.PublicClientApplication.return_value = mock_app

        auth = MsalAuth(cache_path=cache_path)
        await auth.get_token()

        _, kwargs = mock_msal.PublicClientApplication.call_args
        assert kwargs["token_cache"] is mock_cache
        assert kwargs["authority"] == AUTHORITY
        assert kwargs["validate_authority"] is False


# ---------------------------------------------------------------------------
# MsalAuth -- mutant-killing tests for acquire_token_silent args
# ---------------------------------------------------------------------------


class TestSilentAcquisitionArgs:
    """Verify acquire_token_silent receives correct args."""

    @patch("flameconnect.auth.msal")
    async def test_silent_uses_scopes_and_first_account(
        self, mock_msal, tmp_path
    ):
        """acquire_token_silent gets SCOPES and accounts[0]."""
        cache_path = tmp_path / "token_cache.json"

        mock_cache = MagicMock()
        mock_cache.has_state_changed = False
        mock_msal.SerializableTokenCache.return_value = mock_cache

        acct = {"username": "user@example.com"}
        mock_app = MagicMock()
        mock_app.get_accounts.return_value = [acct]
        mock_app.acquire_token_silent.return_value = {
            "access_token": "tok"
        }
        mock_msal.PublicClientApplication.return_value = mock_app

        auth = MsalAuth(cache_path=cache_path)
        await auth.get_token()

        mock_app.acquire_token_silent.assert_called_once_with(
            SCOPES, account=acct
        )

    @patch("flameconnect.auth.msal")
    async def test_silent_none_result_falls_through(
        self, mock_msal, tmp_path
    ):
        """When acquire_token_silent returns None, fall to interactive."""
        cache_path = tmp_path / "token_cache.json"

        mock_cache = MagicMock()
        mock_cache.has_state_changed = False
        mock_msal.SerializableTokenCache.return_value = mock_cache

        mock_app = MagicMock()
        mock_app.get_accounts.return_value = [{"username": "u"}]
        mock_app.acquire_token_silent.return_value = None
        mock_app.initiate_auth_code_flow.return_value = {
            "auth_uri": "https://example.com/auth",
        }
        mock_app.acquire_token_by_auth_code_flow.return_value = {
            "access_token": "interactive-tok"
        }
        mock_msal.PublicClientApplication.return_value = mock_app

        async def fake_prompt(
            auth_uri: str, redirect_uri: str
        ) -> str:
            return "https://redirect?code=abc123"

        auth = MsalAuth(
            cache_path=cache_path, prompt_callback=fake_prompt
        )
        token = await auth.get_token()

        assert token == "interactive-tok"
        mock_app.initiate_auth_code_flow.assert_called_once()

    @patch("flameconnect.auth.msal")
    async def test_silent_result_without_access_token_key(
        self, mock_msal, tmp_path
    ):
        """Result dict without 'access_token' falls to interactive."""
        cache_path = tmp_path / "token_cache.json"

        mock_cache = MagicMock()
        mock_cache.has_state_changed = False
        mock_msal.SerializableTokenCache.return_value = mock_cache

        mock_app = MagicMock()
        mock_app.get_accounts.return_value = [{"username": "u"}]
        # Result is truthy but has no access_token key
        mock_app.acquire_token_silent.return_value = {
            "error": "interaction_required"
        }
        mock_app.initiate_auth_code_flow.return_value = {
            "auth_uri": "https://example.com/auth",
        }
        mock_app.acquire_token_by_auth_code_flow.return_value = {
            "access_token": "fallback-tok"
        }
        mock_msal.PublicClientApplication.return_value = mock_app

        async def fake_prompt(
            auth_uri: str, redirect_uri: str
        ) -> str:
            return "https://redirect?code=abc123"

        auth = MsalAuth(
            cache_path=cache_path, prompt_callback=fake_prompt
        )
        token = await auth.get_token()

        assert token == "fallback-tok"
        mock_app.initiate_auth_code_flow.assert_called_once()


# ---------------------------------------------------------------------------
# MsalAuth -- mutant-killing tests for _interactive_flow args
# ---------------------------------------------------------------------------


class TestInteractiveFlowArgs:
    """Verify _interactive_flow passes correct args to MSAL."""

    def _setup_interactive_mocks(self, mock_msal, tmp_path):
        """Set up standard mocks for an interactive flow test."""
        cache_path = tmp_path / "token_cache.json"

        mock_cache = MagicMock()
        mock_cache.has_state_changed = True
        mock_cache.serialize.return_value = "{}"
        mock_msal.SerializableTokenCache.return_value = mock_cache

        mock_app = MagicMock()
        mock_app.get_accounts.return_value = []
        flow_dict = {
            "auth_uri": "https://example.com/auth?foo=bar",
        }
        mock_app.initiate_auth_code_flow.return_value = flow_dict
        mock_app.acquire_token_by_auth_code_flow.return_value = {
            "access_token": "new-token-xyz"
        }
        mock_msal.PublicClientApplication.return_value = mock_app

        return cache_path, mock_cache, mock_app, flow_dict

    @patch("flameconnect.auth.msal")
    async def test_initiate_flow_receives_scopes_and_redirect(
        self, mock_msal, tmp_path
    ):
        """initiate_auth_code_flow gets SCOPES and _REDIRECT_URI."""
        cache_path, _, mock_app, _ = self._setup_interactive_mocks(
            mock_msal, tmp_path
        )

        async def fake_prompt(
            auth_uri: str, redirect_uri: str
        ) -> str:
            return "https://redirect?code=c1"

        auth = MsalAuth(
            cache_path=cache_path, prompt_callback=fake_prompt
        )
        await auth.get_token()

        mock_app.initiate_auth_code_flow.assert_called_once_with(
            scopes=SCOPES,
            redirect_uri=_REDIRECT_URI,
        )

    @patch("flameconnect.auth.msal")
    async def test_prompt_callback_receives_auth_and_redirect_uri(
        self, mock_msal, tmp_path
    ):
        """prompt_callback gets auth_uri from flow and _REDIRECT_URI."""
        cache_path, _, mock_app, _ = self._setup_interactive_mocks(
            mock_msal, tmp_path
        )
        received_args: list[tuple[str, str]] = []

        async def capturing_prompt(
            auth_uri: str, redirect_uri: str
        ) -> str:
            received_args.append((auth_uri, redirect_uri))
            return "https://redirect?code=c1"

        auth = MsalAuth(
            cache_path=cache_path, prompt_callback=capturing_prompt
        )
        await auth.get_token()

        assert len(received_args) == 1
        assert received_args[0][0] == (
            "https://example.com/auth?foo=bar"
        )
        assert received_args[0][1] == _REDIRECT_URI

    @patch("flameconnect.auth.msal")
    async def test_acquire_token_by_auth_code_flow_args(
        self, mock_msal, tmp_path
    ):
        """acquire_token_by_auth_code_flow gets flow and parsed URL."""
        (
            cache_path,
            _,
            mock_app,
            flow_dict,
        ) = self._setup_interactive_mocks(mock_msal, tmp_path)

        async def fake_prompt(
            auth_uri: str, redirect_uri: str
        ) -> str:
            return "https://redirect?code=c1&state=s1"

        auth = MsalAuth(
            cache_path=cache_path, prompt_callback=fake_prompt
        )
        await auth.get_token()

        args = (
            mock_app.acquire_token_by_auth_code_flow.call_args
        )
        # First positional arg is the flow dict
        assert args[0][0] is flow_dict
        # Second positional arg is parsed redirect URL dict
        assert args[0][1] == {"code": "c1", "state": "s1"}

    @patch("flameconnect.auth.msal")
    async def test_interactive_flow_saves_cache(
        self, mock_msal, tmp_path
    ):
        """After successful interactive flow, cache is saved."""
        cache_path, mock_cache, mock_app, _ = (
            self._setup_interactive_mocks(mock_msal, tmp_path)
        )

        async def fake_prompt(
            auth_uri: str, redirect_uri: str
        ) -> str:
            return "https://redirect?code=c1"

        auth = MsalAuth(
            cache_path=cache_path, prompt_callback=fake_prompt
        )
        token = await auth.get_token()

        assert token == "new-token-xyz"
        # Cache should be written (has_state_changed = True)
        assert cache_path.exists()

    @patch("flameconnect.auth.msal")
    async def test_interactive_flow_strips_redirect_response(
        self, mock_msal, tmp_path
    ):
        """redirect_response is stripped before parsing."""
        cache_path, _, mock_app, _ = self._setup_interactive_mocks(
            mock_msal, tmp_path
        )

        async def fake_prompt(
            auth_uri: str, redirect_uri: str
        ) -> str:
            return "  https://redirect?code=c1  \n"

        auth = MsalAuth(
            cache_path=cache_path, prompt_callback=fake_prompt
        )
        token = await auth.get_token()
        assert token == "new-token-xyz"

    @patch("flameconnect.auth.msal")
    async def test_auth_uri_from_flow_used_in_prompt(
        self, mock_msal, tmp_path
    ):
        """The auth_uri extracted from flow dict is passed to prompt."""
        cache_path = tmp_path / "token_cache.json"

        mock_cache = MagicMock()
        mock_cache.has_state_changed = False
        mock_msal.SerializableTokenCache.return_value = mock_cache

        specific_uri = "https://specific.example.com/authorize?x=1"
        mock_app = MagicMock()
        mock_app.get_accounts.return_value = []
        mock_app.initiate_auth_code_flow.return_value = {
            "auth_uri": specific_uri,
        }
        mock_app.acquire_token_by_auth_code_flow.return_value = {
            "access_token": "t"
        }
        mock_msal.PublicClientApplication.return_value = mock_app

        captured_uri = None

        async def capturing_prompt(
            auth_uri: str, redirect_uri: str
        ) -> str:
            nonlocal captured_uri
            captured_uri = auth_uri
            return "https://redirect?code=c1"

        auth = MsalAuth(
            cache_path=cache_path,
            prompt_callback=capturing_prompt,
        )
        await auth.get_token()

        assert captured_uri == specific_uri


# ---------------------------------------------------------------------------
# MsalAuth -- mutant-killing tests for token exchange error details
# ---------------------------------------------------------------------------


class TestTokenExchangeErrorDetails:
    """Verify exact error/description in token exchange failures."""

    @patch("flameconnect.auth.msal")
    async def test_error_and_description_in_exception_message(
        self, mock_msal, tmp_path
    ):
        """Exception includes both error and error_description."""
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
            "error": "invalid_grant",
            "error_description": "Code expired",
        }
        mock_msal.PublicClientApplication.return_value = mock_app

        async def fake_prompt(
            auth_uri: str, redirect_uri: str
        ) -> str:
            return "https://redirect?code=expired-code"

        auth = MsalAuth(
            cache_path=cache_path, prompt_callback=fake_prompt
        )

        with pytest.raises(AuthenticationError) as exc_info:
            await auth.get_token()

        msg = str(exc_info.value)
        assert "invalid_grant" in msg
        assert "Code expired" in msg

    @patch("flameconnect.auth.msal")
    async def test_exchange_error_defaults_when_missing(
        self, mock_msal, tmp_path
    ):
        """Default error='unknown' and description='N/A' used."""
        cache_path = tmp_path / "token_cache.json"

        mock_cache = MagicMock()
        mock_cache.has_state_changed = False
        mock_msal.SerializableTokenCache.return_value = mock_cache

        mock_app = MagicMock()
        mock_app.get_accounts.return_value = []
        mock_app.initiate_auth_code_flow.return_value = {
            "auth_uri": "https://example.com/auth",
        }
        # No error or error_description keys at all
        mock_app.acquire_token_by_auth_code_flow.return_value = {
            "some_other_key": "value",
        }
        mock_msal.PublicClientApplication.return_value = mock_app

        async def fake_prompt(
            auth_uri: str, redirect_uri: str
        ) -> str:
            return "https://redirect?code=bad-code"

        auth = MsalAuth(
            cache_path=cache_path, prompt_callback=fake_prompt
        )

        with pytest.raises(AuthenticationError) as exc_info:
            await auth.get_token()

        msg = str(exc_info.value)
        # Check exact defaults: "unknown" and "N/A"
        # Use boundary checks so XX-prefixed mutants fail
        assert ": unknown " in msg or msg.endswith("unknown")
        # The em-dash format is "error -- description"
        assert msg.endswith("N/A")


# ---------------------------------------------------------------------------
# MsalAuth -- mutant-killing tests for __init__ defaults
# ---------------------------------------------------------------------------


class TestMsalAuthInit:
    """Verify MsalAuth.__init__ sets correct defaults."""

    def test_app_defaults_to_none(self):
        """self._app should be None, not empty string."""
        auth = MsalAuth()
        assert auth._app is None

    def test_cache_defaults_to_none(self):
        """self._cache should be None, not empty string."""
        auth = MsalAuth()
        assert auth._cache is None


# ---------------------------------------------------------------------------
# MsalAuth -- mutant-killing tests for _save_cache
# ---------------------------------------------------------------------------


class TestSaveCacheNotCalledWhenUnchanged:
    """Verify cache is NOT saved when has_state_changed is False."""

    @patch("flameconnect.auth.msal")
    async def test_cache_not_written_when_unchanged(
        self, mock_msal, tmp_path
    ):
        """When has_state_changed is False, file is NOT written."""
        cache_path = tmp_path / "token_cache.json"

        mock_cache = MagicMock()
        mock_cache.has_state_changed = False
        mock_msal.SerializableTokenCache.return_value = mock_cache

        mock_app = MagicMock()
        mock_app.get_accounts.return_value = [{"username": "u"}]
        mock_app.acquire_token_silent.return_value = {
            "access_token": "t"
        }
        mock_msal.PublicClientApplication.return_value = mock_app

        auth = MsalAuth(cache_path=cache_path)
        await auth.get_token()

        # File should NOT exist since cache was unchanged
        assert not cache_path.exists()


# ---------------------------------------------------------------------------
# MsalAuth -- log message assertions to kill logger mutants
# ---------------------------------------------------------------------------


class TestMsalAuthLogMessages:
    """Verify exact log messages emitted by MsalAuth."""

    @patch("flameconnect.auth.msal")
    async def test_silent_acquisition_log_messages(
        self, mock_msal, tmp_path, caplog
    ):
        """Verify all log messages for silent token acquisition."""
        cache_path = tmp_path / "token_cache.json"

        mock_cache = MagicMock()
        mock_cache.has_state_changed = False
        mock_msal.SerializableTokenCache.return_value = mock_cache

        mock_app = MagicMock()
        mock_app.get_accounts.return_value = [{"username": "u"}]
        mock_app.acquire_token_silent.return_value = {
            "access_token": "tok"
        }
        mock_msal.PublicClientApplication.return_value = mock_app

        auth = MsalAuth(cache_path=cache_path)
        with caplog.at_level(logging.DEBUG):
            await auth.get_token()

        messages = [r.message for r in caplog.records]
        assert any(
            m == "Attempting silent token acquisition"
            for m in messages
        )
        assert any(
            m.startswith("Token acquired silently")
            for m in messages
        )

    @patch("flameconnect.auth.msal")
    async def test_interactive_flow_log_messages(
        self, mock_msal, tmp_path, caplog
    ):
        """Verify all log messages for interactive flow."""
        cache_path = tmp_path / "token_cache.json"

        mock_cache = MagicMock()
        mock_cache.has_state_changed = True
        mock_cache.serialize.return_value = "{}"
        mock_msal.SerializableTokenCache.return_value = mock_cache

        mock_app = MagicMock()
        mock_app.get_accounts.return_value = []
        mock_app.initiate_auth_code_flow.return_value = {
            "auth_uri": "https://example.com/auth",
        }
        mock_app.acquire_token_by_auth_code_flow.return_value = {
            "access_token": "tok"
        }
        mock_msal.PublicClientApplication.return_value = mock_app

        async def fake_prompt(
            auth_uri: str, redirect_uri: str
        ) -> str:
            return "https://redirect?code=c1"

        auth = MsalAuth(
            cache_path=cache_path, prompt_callback=fake_prompt
        )
        with caplog.at_level(logging.DEBUG):
            await auth.get_token()

        messages = [r.message for r in caplog.records]
        assert any(
            m.startswith("No cached token") for m in messages
        )
        assert any(
            m.startswith("Exchanging authorization code")
            for m in messages
        )
        assert any(
            m.startswith("Authentication successful")
            for m in messages
        )

    @patch("flameconnect.auth.msal")
    async def test_save_cache_log_message(
        self, mock_msal, tmp_path, caplog
    ):
        """Verify log message when cache is saved."""
        cache_path = tmp_path / "token_cache.json"

        mock_cache = MagicMock()
        mock_cache.has_state_changed = True
        mock_cache.serialize.return_value = "{}"
        mock_msal.SerializableTokenCache.return_value = mock_cache

        mock_app = MagicMock()
        mock_app.get_accounts.return_value = [{"username": "u"}]
        mock_app.acquire_token_silent.return_value = {
            "access_token": "tok"
        }
        mock_msal.PublicClientApplication.return_value = mock_app

        auth = MsalAuth(cache_path=cache_path)
        with caplog.at_level(logging.DEBUG):
            await auth.get_token()

        messages = [r.message for r in caplog.records]
        assert any(
            m.startswith("Token cache saved to")
            for m in messages
        )
        # Verify the cache path is included in the log message
        assert any(
            str(cache_path) in m for m in messages
        )


# ---------------------------------------------------------------------------
# MsalAuth -- no-prompt-callback error message exact match
# ---------------------------------------------------------------------------


class TestNoPromptCallbackErrorMessage:
    """Kill mutants that alter the no-prompt error message."""

    @patch("flameconnect.auth.msal")
    async def test_no_prompt_error_contains_interactive_login(
        self, mock_msal, tmp_path
    ):
        """Error message mentions 'Interactive login'."""
        cache_path = tmp_path / "token_cache.json"

        mock_cache = MagicMock()
        mock_cache.has_state_changed = False
        mock_msal.SerializableTokenCache.return_value = mock_cache

        mock_app = MagicMock()
        mock_app.get_accounts.return_value = []
        mock_app.initiate_auth_code_flow.return_value = {
            "auth_uri": "https://example.com/auth",
        }
        mock_msal.PublicClientApplication.return_value = mock_app

        auth = MsalAuth(cache_path=cache_path)

        with pytest.raises(AuthenticationError) as exc_info:
            await auth.get_token()

        msg = str(exc_info.value)
        assert msg.startswith("Interactive login is required")
        assert "Auth URI:" in msg
