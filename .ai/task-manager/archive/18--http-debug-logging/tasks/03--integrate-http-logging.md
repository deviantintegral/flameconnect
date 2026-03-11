---
id: 3
group: "http-debug-logging"
dependencies: [1, 2]
status: "completed"
created: 2026-03-11
skills:
  - python
  - aiohttp
---
# Integrate shared HTTP logging into client and b2c_login

## Objective
Wire the shared `_http_logging` module into `client.py._request` and migrate `b2c_login.py` to use the shared helpers. Add tests for all new and migrated functionality.

## Skills Required
- Python async programming with `aiohttp`
- Python `logging` module

## Acceptance Criteria
- [ ] `client.py._request` calls `log_request` before the HTTP call and `log_response` after
- [ ] `b2c_login.py` no longer defines its own `_log_request` or `_log_response` functions
- [ ] `b2c_login.py` imports and uses `log_request`/`log_response` from `flameconnect._http_logging`
- [ ] All `b2c_login.py` call sites pass `_LOGGER` as the first argument
- [ ] `redact_headers` is tested: Authorization shows `"Bearer ***"`, Cookie/Set-Cookie/X-CSRF-TOKEN show `"***"`, non-sensitive headers pass through, case-insensitive matching works
- [ ] `redact_body` is tested: password key is redacted, other keys pass through
- [ ] `log_request` and `log_response` are tested: correct DEBUG-level calls, redaction applied, body truncation works
- [ ] `client.py._request` HTTP logging is tested: headers and body logged at DEBUG with redaction
- [ ] Existing `b2c_login` tests still pass (no behaviour change, just code moved)
- [ ] mypy strict passes, ruff passes, test coverage ≥ 95%

## Technical Requirements
- In `client.py._request`, call `log_request` with the headers dict (including Authorization) and optional JSON body
- In `client.py._request`, after getting the response, read the body text for logging, then call `log_response`
- Note: `_request` currently calls `response.json()` — to log the body, capture `response.text()` first, then parse JSON from that text (or log after `json()` by serializing the result)
- In `b2c_login.py`, replace `from`-less `_log_request(...)` calls with `log_request(_LOGGER, ...)` and similarly for `_log_response`

## Input Dependencies
- Task 01: `src/flameconnect/_http_logging.py` must exist
- Task 02: `client.py` request summary line must already be promoted to INFO (so DEBUG logging additions don't conflict)

## Output Artifacts
- Modified `src/flameconnect/client.py` — HTTP debug logging added to `_request`
- Modified `src/flameconnect/b2c_login.py` — local helpers removed, shared helpers imported
- New test file `tests/test_http_logging.py` — tests for `_http_logging` module
- Updated `tests/test_b2c_login.py` — adjusted for shared helper imports if needed

## Implementation Notes
- For `client.py._request`, consider reading `await response.text()` and then using `json.loads()` to parse it, rather than `response.json()`, so the raw body is available for logging. Alternatively, log `json.dumps(result)` after parsing.
- The `b2c_login.py` migration is a straightforward find-and-replace: `_log_request(` → `log_request(_LOGGER, ` and `_log_response(` → `log_response(_LOGGER, `.
- Ensure tests cover the edge case where `body` is `None` in `log_response`.
