"""Authentication providers for the flameconnect library."""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol
from urllib.parse import unquote

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

import msal  # type: ignore[import-untyped]

from flameconnect.const import AUTHORITY, CLIENT_ID, SCOPES
from flameconnect.exceptions import AuthenticationError

_LOGGER = logging.getLogger(__name__)

_REDIRECT_URI = f"msal{CLIENT_ID}://auth"


def _default_cache_path() -> Path:
    """Return the default token cache path per XDG Base Directory Specification.

    Uses ``$XDG_CACHE_HOME/flameconnect/token.json`` when the environment
    variable is set, otherwise falls back to ``~/.cache/flameconnect/token.json``.
    """
    xdg_cache = os.environ.get("XDG_CACHE_HOME")
    if xdg_cache:
        return Path(xdg_cache) / "flameconnect" / "token.json"
    return Path.home() / ".cache" / "flameconnect" / "token.json"


class AbstractAuth(Protocol):
    """Protocol for authentication providers."""

    async def get_token(self) -> str:
        """Return a valid access token."""
        ...


class TokenAuth:
    """Authentication provider using a pre-existing token or token factory.

    This is intended for Home Assistant and other consumers that manage
    their own OAuth tokens externally.
    """

    def __init__(self, token: str | Callable[[], Awaitable[str]]) -> None:
        self._token = token

    async def get_token(self) -> str:
        """Return a valid access token."""
        if callable(self._token):
            return await self._token()
        return self._token


class MsalAuth:
    """Authentication provider using MSAL interactive auth code flow.

    Wraps ``msal.PublicClientApplication`` with:
    - Persistent token cache via ``msal.SerializableTokenCache``
    - Silent refresh (tries ``acquire_token_silent`` first)
    - Interactive auth code flow as fallback
    - All blocking MSAL calls wrapped in ``asyncio.to_thread()``

    Args:
        cache_path: Path to the persistent token cache file.  Defaults to
            ``$XDG_CACHE_HOME/flameconnect/token.json`` (or
            ``~/.cache/flameconnect/token.json`` when the variable is unset).
        prompt_callback: An async callable that receives the auth URI
            and the redirect URI, and must return the full redirect URL
            pasted by the user. If not provided, raises
            ``AuthenticationError`` when interactive login is needed.
    """

    def __init__(
        self,
        cache_path: Path | None = None,
        prompt_callback: Callable[[str, str], Awaitable[str]] | None = None,
    ) -> None:
        self._cache_path = (cache_path or _default_cache_path()).expanduser()
        self._prompt_callback = prompt_callback
        self._app: msal.PublicClientApplication | None = None
        self._cache: msal.SerializableTokenCache | None = None

    def _build_app(
        self,
    ) -> tuple[msal.PublicClientApplication, msal.SerializableTokenCache]:
        """Build an MSAL PublicClientApplication with persistent token cache."""
        cache = msal.SerializableTokenCache()
        if self._cache_path.exists():
            cache.deserialize(self._cache_path.read_text())

        app = msal.PublicClientApplication(
            CLIENT_ID,
            authority=AUTHORITY,
            validate_authority=False,
            token_cache=cache,
        )
        return app, cache

    def _save_cache(self, cache: msal.SerializableTokenCache) -> None:
        """Persist the MSAL token cache to disk if it has changed."""
        if cache.has_state_changed:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            self._cache_path.write_text(cache.serialize())
            _LOGGER.debug("Token cache saved to %s", self._cache_path)

    async def get_token(self) -> str:
        """Return a valid access token.

        Tries silent acquisition first. Falls back to interactive auth code
        flow if no cached token is available.

        Raises:
            AuthenticationError: If authentication fails at any stage.
        """
        app, cache = await asyncio.to_thread(self._build_app)

        # Try silent token acquisition from cache (uses refresh token)
        _LOGGER.debug("Attempting silent token acquisition")
        accounts: list[Any] = app.get_accounts()
        if accounts:
            result: dict[str, Any] | None = await asyncio.to_thread(
                app.acquire_token_silent, SCOPES, account=accounts[0]
            )
            if result and "access_token" in result:
                await asyncio.to_thread(self._save_cache, cache)
                _LOGGER.debug("Token acquired silently (refreshed from cache)")
                return str(result["access_token"])

        # No cached token — start interactive auth code flow
        _LOGGER.debug("No cached token, initiating interactive auth code flow")
        token = await self._interactive_flow(app, cache)
        return token

    async def _interactive_flow(
        self,
        app: msal.PublicClientApplication,
        cache: msal.SerializableTokenCache,
    ) -> str:
        """Run the interactive auth code flow.

        Raises:
            AuthenticationError: If the flow cannot be initiated, the user
                provides an invalid URL, or the token exchange fails.
        """
        flow: dict[str, Any] = await asyncio.to_thread(
            app.initiate_auth_code_flow,
            scopes=SCOPES,
            redirect_uri=_REDIRECT_URI,
        )

        if "auth_uri" not in flow:
            raise AuthenticationError(f"Failed to initiate auth flow: {flow}")

        auth_uri: str = flow["auth_uri"]

        if self._prompt_callback is None:
            raise AuthenticationError(
                "Interactive login is required but no prompt_callback "
                f"was provided. Auth URI: {auth_uri}"
            )

        redirect_response = await self._prompt_callback(
            auth_uri,
            _REDIRECT_URI,
        )
        redirect_response = redirect_response.strip()

        auth_response = self._parse_redirect_url(redirect_response)

        _LOGGER.debug("Exchanging authorization code for token")
        result: dict[str, Any] = await asyncio.to_thread(
            app.acquire_token_by_auth_code_flow, flow, auth_response
        )

        if "access_token" not in result:
            error = result.get("error", "unknown")
            description = result.get("error_description", "N/A")
            raise AuthenticationError(f"Token exchange failed: {error} — {description}")

        await asyncio.to_thread(self._save_cache, cache)
        _LOGGER.debug("Authentication successful, token acquired")
        return str(result["access_token"])

    @staticmethod
    def _parse_redirect_url(url: str) -> dict[str, str]:
        """Parse the redirect URL into key-value pairs for MSAL.

        Raises:
            AuthenticationError: If the URL contains a Unicode ellipsis
                (indicating browser truncation) or no authorization code.
        """
        if "\u2026" in url:
            raise AuthenticationError(
                "The URL contains an ellipsis character (\u2026). "
                "Your browser truncated the long URL in the address bar. "
                "Use F12 > Console > copy(location.href) to get the full URL."
            )

        query_string = ""
        if "?" in url:
            query_string = url.split("?", 1)[1]
        elif "#" in url:
            query_string = url.split("#", 1)[1]

        auth_response: dict[str, str] = {}
        for part in query_string.split("&"):
            if "=" in part:
                key, val = part.split("=", 1)
                auth_response[key] = unquote(val)

        if "code" not in auth_response:
            if "error_description" in auth_response:
                raise AuthenticationError(
                    f"Auth error: {auth_response['error_description']}"
                )
            if "error" in auth_response:
                raise AuthenticationError(f"Auth error: {auth_response['error']}")
            raise AuthenticationError("No authorization code found in the URL.")

        return auth_response
