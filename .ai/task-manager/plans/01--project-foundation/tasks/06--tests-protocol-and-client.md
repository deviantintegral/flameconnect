---
id: 6
group: "testing"
dependencies: [5]
created: "2026-02-23"
skills:
  - python
  - unit-testing
status: "completed"
---
# Implement tests for protocol, client, and auth modules

## Objective
Write comprehensive tests for the core library: wire protocol round-trip tests, async client tests with mocked HTTP responses, and auth module tests. Focus on testing custom business logic (binary encoding/decoding, API response parsing, auth token handling) — not framework functionality.

## Skills Required
- Python testing (pytest, pytest-asyncio, aioresponses)

## Acceptance Criteria
- [ ] `tests/test_protocol.py` — round-trip encode/decode tests for all 11 parameter types
- [ ] `tests/test_client.py` — async client tests with mocked aiohttp responses for GetFires, GetFireOverview, WriteWifiParameters, turn_on, turn_off
- [ ] `tests/test_auth.py` — TokenAuth tests (string and callable), MsalAuth mocked token flow
- [ ] `tests/test_models.py` — dataclass construction, enum value mapping
- [ ] `tests/fixtures/` directory with JSON fixture files for API responses
- [ ] `tests/conftest.py` with shared fixtures (mock client factory, sample fire data)
- [ ] All tests pass with `pytest`
- [ ] Tests use fixtures/mocks — no live API calls
- [ ] mutmut catches meaningful mutants in protocol.py

Use your internal Todo tool to track these and keep on track.

## Technical Requirements
- Use `aioresponses` to mock aiohttp requests in client tests
- Use `pytest-asyncio` for async test functions
- Protocol tests should use known-good base64 values from `flameconnect_reader.py` as test vectors, supplemented by real API response payloads captured during Task 05 live validation
- Test edge cases: malformed data raises `ProtocolError`, API errors raise `ApiError`
- Auth tests: mock `msal.PublicClientApplication` methods

### Meaningful Test Strategy Guidelines

Your critical mantra for test generation is: "write a few tests, mostly integration".

**When TO Write Tests:**
- Custom business logic and algorithms (wire protocol encoding/decoding is the core logic)
- Critical user workflows (turn_on, turn_off orchestration)
- Edge cases and error conditions (malformed binary data, API error responses)
- Integration between protocol + client (end-to-end: mock HTTP → parse response → decode parameters)

**When NOT to Write Tests:**
- aiohttp framework functionality
- MSAL library token exchange internals
- Simple dataclass construction (unless custom __post_init__ logic)
- Enum membership tests

## Input Dependencies
- Task 5: `client.py` (FlameConnectClient)
- Task 3: `protocol.py` (encode/decode functions)
- Task 4: `auth.py` (TokenAuth, MsalAuth)
- Task 2: `models.py`, `exceptions.py`

## Output Artifacts
- `tests/test_protocol.py`
- `tests/test_client.py`
- `tests/test_auth.py`
- `tests/test_models.py`
- `tests/conftest.py` (populated)
- `tests/fixtures/` (JSON files)

## Implementation Notes

<details>
<summary>Detailed implementation guidance</summary>

1. **Protocol round-trip tests** (highest priority — the most delicate code):
   - For each parameter type, create a known dataclass instance → encode → decode → assert equal
   - Use specific byte values from the existing script as test vectors. For example, encode a ModeParam(mode=FireMode.MANUAL, temperature=22.5), verify the base64 output matches expected, then decode and verify fields.
   - Test FlameEffect specifically for the RGBW byte order (R, B, G, W on wire vs R, G, B, W in model)
   - Test temperature encoding edge cases: 0.0, 7.0 (minimum), 37.5, integer values like 22.0
   - Test that decoding truncated/malformed data raises `ProtocolError`

2. **Client integration tests** (mock HTTP, real protocol):
   - Create JSON fixtures from real API response payloads captured during Task 05 live validation, supplemented by `FLAMECONNECT_API_REPORT.md` example responses
   - `tests/fixtures/get_fires.json`: List of fire objects with all fields
   - `tests/fixtures/get_fire_overview.json`: FireOverview with WifiFireOverview.Parameters containing base64 values
   - Use `aioresponses` to mock the API endpoints
   - Test `get_fires` returns `list[Fire]` with correct field mapping
   - Test `get_fire_overview` decodes all parameter types correctly
   - Test `write_parameters` sends correct JSON payload
   - Test `turn_on` reads state then writes Mode+FlameEffect
   - Test `turn_off` writes Mode=Standby
   - Test non-2xx response raises `ApiError`

3. **Auth tests**:
   - `TokenAuth` with string: `get_token()` returns the string
   - `TokenAuth` with async callable: `get_token()` calls the callable
   - `MsalAuth`: mock `msal.PublicClientApplication` so `acquire_token_silent` returns a token dict — verify `get_token()` returns the access_token string
   - `MsalAuth` failure: mock acquire_token_silent returning None — verify `AuthenticationError` is raised (or interactive flow is triggered)

4. **conftest.py fixtures**:
   ```python
   @pytest.fixture
   def sample_fire_data() -> dict[str, Any]:
       """Raw API response for a single fire."""
       ...

   @pytest.fixture
   async def mock_client(aioresponses) -> AsyncGenerator[FlameConnectClient, None]:
       """Client with mocked auth and HTTP."""
       auth = TokenAuth("test-token")
       async with FlameConnectClient(auth=auth) as client:
           yield client
   ```

5. **mutmut focus**: Run `mutmut run --paths-to-mutate=src/flameconnect/protocol.py` to verify protocol tests catch mutations in the encoding/decoding logic.
</details>
