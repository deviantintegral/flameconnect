---
id: 5
group: "core-library"
dependencies: [3, 4]
created: "2026-02-23"
skills:
  - python
  - api-endpoints
status: "completed"
---
# Implement async API client (FlameConnectClient)

## Objective
Create `client.py` with the `FlameConnectClient` class — the primary public API of the library. It is an async context manager that wraps aiohttp, handles authentication via the auth module, and exposes typed methods for all core API endpoints (GetFires, GetFireOverview, WriteWifiParameters). All methods return typed dataclasses, and the binary wire protocol is fully encapsulated.

## Skills Required
- Python async programming (aiohttp, asyncio)
- REST API client design

## Acceptance Criteria
- [ ] `src/flameconnect/client.py` exists with `FlameConnectClient` class
- [ ] Implements `async __aenter__` / `async __aexit__` (async context manager)
- [ ] Accepts optional `aiohttp.ClientSession` injection (creates its own if not provided)
- [ ] Accepts auth via `AbstractAuth` (token injection or MSAL)
- [ ] `async def get_fires(self) -> list[Fire]` — calls GetFires, returns typed list
- [ ] `async def get_fire_overview(self, fire_id: str) -> FireOverview` — calls GetFireOverview, decodes all parameters via protocol module
- [ ] `async def write_parameters(self, fire_id: str, params: list[...]) -> None` — calls WriteWifiParameters with encoded params
- [ ] High-level convenience methods: `turn_on(fire_id)`, `turn_off(fire_id)`
- [ ] All API calls include required HTTP headers from `const.py`
- [ ] Raises `ApiError` on non-2xx responses with status code and message
- [ ] Passes `mypy --strict` and `ruff check`
- [ ] Uses `logging.getLogger(__name__)` — no `print()`
- [ ] Validated against live API (see Live API Validation Protocol below)

Use your internal Todo tool to track these and keep on track.

## Technical Requirements
- aiohttp `ClientSession` with JSON content type and Bearer auth header
- Token is fetched via `self._auth.get_token()` before each request (supports refresh)
- `FireOverview` dataclass should contain the fire info plus a list of decoded parameter dataclasses
- `write_parameters` accepts parameter dataclasses, encodes them via `protocol.encode_parameter`, and sends JSON payload
- `turn_on` reads current state (to preserve flame settings), then writes Mode=Manual + FlameEffect=On (port logic from lines 340-360 of existing script)
- `turn_off` writes Mode=Standby (port from lines 363-368)
- Session lifecycle: if client creates its own session, it must close it in `__aexit__`; if injected, leave it alone

## Input Dependencies
- Task 3: `protocol.py` (encode/decode functions)
- Task 4: `auth.py` (AbstractAuth, TokenAuth, MsalAuth)
- Task 2: `models.py` (Fire, FireOverview, parameter dataclasses), `const.py` (API_BASE, headers), `exceptions.py` (ApiError)

## Output Artifacts
- `src/flameconnect/client.py`
- Updated `src/flameconnect/__init__.py` with public exports (FlameConnectClient, TokenAuth, MsalAuth)

## Implementation Notes

<details>
<summary>Detailed implementation guidance</summary>

1. **Reference existing API call functions** in `flameconnect_reader.py`:
   - `get_fires` (line 209-213): GET `/api/Fires/GetFires`
   - `get_fire_overview` (line 216-220): GET `/api/Fires/GetFireOverview?FireId={fire_id}`
   - `write_parameters` (line 321-329): POST `/api/Fires/WriteWifiParameters`
   - `turn_on` (line 340-360): Read current state, set Mode=Manual, FlameEffect=On
   - `turn_off` (line 363-368): Set Mode=Standby

2. **Client structure**:
   ```python
   class FlameConnectClient:
       def __init__(
           self,
           auth: AbstractAuth,
           session: aiohttp.ClientSession | None = None,
       ) -> None:
           self._auth = auth
           self._external_session = session is not None
           self._session = session

       async def __aenter__(self) -> FlameConnectClient:
           if self._session is None:
               self._session = aiohttp.ClientSession()
           return self

       async def __aexit__(self, *exc: object) -> None:
           if not self._external_session and self._session:
               await self._session.close()
   ```

3. **Request helper**: Create a private `_request` method that:
   - Calls `self._auth.get_token()` for the current token
   - Sets `Authorization: Bearer {token}` + default headers from `const.py`
   - Makes the aiohttp request
   - Checks response status, raises `ApiError` on non-2xx
   - Returns parsed JSON

4. **GetFires response parsing**: The API returns a list of fire objects. Map each to a `Fire` dataclass. Use snake_case field names in the dataclass, mapping from the PascalCase JSON keys.

5. **GetFireOverview response parsing**: The response has a `WifiFireOverview.Parameters` list where each entry has `ParameterId` and `Value` (base64). For each parameter:
   - Decode the base64 `Value` to bytes
   - Call `protocol.decode_parameter(pid, raw_bytes)` to get a typed dataclass
   - Collect all decoded params into the `FireOverview` dataclass

6. **WriteWifiParameters payload**:
   ```json
   {
     "FireId": "...",
     "Parameters": [
       {"ParameterId": 321, "Value": "<base64>"},
       {"ParameterId": 322, "Value": "<base64>"}
     ]
   }
   ```
   The client's `write_parameters` should accept parameter dataclasses and call `protocol.encode_parameter()` to produce the base64 values.

7. **Logging**: `_LOGGER = logging.getLogger(__name__)`. Log requests at DEBUG level (method, URL), responses at DEBUG level (status, truncated body).

8. **Update `__init__.py`** to export: `FlameConnectClient`, `TokenAuth`, `MsalAuth`, `Fire`, `FireOverview`, key param types, and `FlameConnectError`.

9. **Live API Validation Protocol**: After implementing the client, validate it against the real API. For each validation step, follow this mandatory three-step process:
   - **Explain**: Tell the user exactly which API endpoint you will call, what parameters will be sent, and what effect it will have (e.g., "I will call GET /api/Fires/GetFires to list registered fireplaces — this is a read-only call with no side effects").
   - **Confirm**: Wait for the user to explicitly approve the call before executing it.
   - **Verify**: After the call, show the user the result and ask them to confirm whether it matches their expectations (e.g., "Does this list match the fireplaces you have registered?").

   Recommended validation sequence:
   1. `get_fires()` — read-only, lists fireplaces. Confirm fire IDs/names with user.
   2. `get_fire_overview(fire_id)` — read-only, reads current state. Confirm parameters match the fireplace's actual state.
   3. `turn_on(fire_id)` — **write operation**, turns on the fireplace. User must confirm the fireplace is safe to turn on.
   4. `get_fire_overview(fire_id)` — read-only, verify state changed to Manual/On.
   5. `turn_off(fire_id)` — **write operation**, turns off the fireplace. User must confirm.
   6. `get_fire_overview(fire_id)` — read-only, verify state changed to Standby.

   Save real API response payloads during validation — these can be used to create test fixtures in Task 06.
</details>
