---
id: 4
group: "core-library"
dependencies: [2]
status: "pending"
created: "2026-02-23"
skills:
  - python
  - authentication
---
# Implement authentication module with token injection and MSAL

## Objective
Create `auth.py` with a dual authentication strategy: token injection (for Home Assistant and other consumers that manage their own tokens) and built-in MSAL credential flow (for CLI/standalone use). MSAL operations must be wrapped in `asyncio.to_thread()` since msal is synchronous.

## Skills Required
- Python async programming (asyncio)
- Azure AD B2C / MSAL authentication

## Acceptance Criteria
- [ ] `src/flameconnect/auth.py` exists
- [ ] `AbstractAuth` base class/protocol defining `async def get_token(self) -> str`
- [ ] `TokenAuth` class: accepts a string token or an async callable returning a token
- [ ] `MsalAuth` class: wraps MSAL PublicClientApplication with persistent token cache, silent refresh, and interactive auth code flow
- [ ] All MSAL blocking calls use `asyncio.to_thread()`
- [ ] Token cache file path is configurable (default: `~/.flameconnect_token.json`)
- [ ] Raises `AuthenticationError` on failure
- [ ] Passes `mypy --strict` and `ruff check`
- [ ] Uses `logging.getLogger(__name__)` — no `print()` statements
- [ ] Validated against live API (see Live API Validation Protocol below)

Use your internal Todo tool to track these and keep on track.

## Technical Requirements
- `TokenAuth` must handle both `str` tokens and `Callable[[], Awaitable[str]]` callables
- MSAL configuration: CLIENT_ID, AUTHORITY, SCOPES from `const.py`
- MSAL token cache: `SerializableTokenCache` persisted to disk as JSON
- Silent token acquisition: try `acquire_token_silent` first, fall back to interactive flow
- Interactive flow: `initiate_auth_code_flow` + prompt user for redirect URL + `acquire_token_by_auth_code_flow`
- Redirect URI: `msal{CLIENT_ID}://auth`

## Input Dependencies
- Task 2: `const.py` (CLIENT_ID, AUTHORITY, SCOPES), `exceptions.py` (AuthenticationError)

## Output Artifacts
- `src/flameconnect/auth.py`

## Implementation Notes

<details>
<summary>Detailed implementation guidance</summary>

1. **Reference the existing auth code** in `flameconnect_reader.py` lines 66-186. The logic is correct and tested — the task is to restructure it into an async class hierarchy.

2. **Auth protocol/ABC**:
   ```python
   class AbstractAuth(Protocol):
       async def get_token(self) -> str: ...
   ```
   Or use an ABC with `@abstractmethod`. The protocol approach is more flexible for duck typing.

3. **TokenAuth implementation**:
   ```python
   class TokenAuth:
       def __init__(self, token: str | Callable[[], Awaitable[str]]) -> None:
           self._token = token

       async def get_token(self) -> str:
           if callable(self._token):
               return await self._token()
           return self._token
   ```

4. **MsalAuth implementation**:
   - Constructor takes optional `cache_path: Path | None = None` (default to `~/.flameconnect_token.json`)
   - `_build_app()` creates `msal.PublicClientApplication` with token cache (port from lines 66-79)
   - `async def get_token()`:
     1. Try `await asyncio.to_thread(app.acquire_token_silent, SCOPES, account)`
     2. If no cached token, run interactive flow via `await asyncio.to_thread(app.initiate_auth_code_flow, ...)`
     3. Prompt user (via logging at INFO level + input()) for redirect URL
     4. Exchange code via `await asyncio.to_thread(app.acquire_token_by_auth_code_flow, ...)`
     5. Save cache if changed
     6. Raise `AuthenticationError` if any step fails

5. **Logging**: Use `_LOGGER = logging.getLogger(__name__)`. Log at DEBUG level for token acquisition steps, INFO for user-facing prompts. No `print()`.

6. **input() in async context**: The `input()` call in interactive auth blocks the event loop. Wrap it: `redirect_url = await asyncio.to_thread(input, "Paste the redirect URL here: ")`.

7. **URL validation**: Port the ellipsis detection and query string parsing from lines 144-173 of the existing script.

8. **Live API Validation Protocol**: After implementing the auth module, validate it works with the real Azure AD B2C endpoint. Follow this mandatory three-step process:
   - **Explain**: Tell the user you will attempt to authenticate with Azure AD B2C using the MsalAuth class. If a cached token exists (from the existing `flameconnect_reader.py` usage), it will attempt silent refresh. Otherwise, it will start the interactive browser login flow.
   - **Confirm**: Wait for the user to explicitly approve the authentication attempt.
   - **Verify**: After authentication, confirm a valid access token was obtained. You can verify by checking the token is a non-empty JWT string. Ask the user if the auth flow worked as expected.

   Note: The existing `.flameconnect_token.json` cache file may be reusable if the token cache path is compatible. Check whether silent refresh works with the existing cache before requiring a fresh interactive login.
</details>
