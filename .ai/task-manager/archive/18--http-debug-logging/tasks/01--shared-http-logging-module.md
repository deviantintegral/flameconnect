---
id: 1
group: "http-debug-logging"
dependencies: []
status: "completed"
created: 2026-03-11
skills:
  - python
  - logging
---
# Create shared HTTP logging module

## Objective
Create `src/flameconnect/_http_logging.py` with redaction utilities and HTTP logging helpers that will be shared by `client.py` and `b2c_login.py`.

## Skills Required
- Python stdlib `logging` module
- Type annotations compatible with mypy strict mode

## Acceptance Criteria
- [ ] `src/flameconnect/_http_logging.py` exists with all four functions
- [ ] `redact_headers` redacts Authorization (preserving scheme prefix), Cookie, Set-Cookie, X-CSRF-TOKEN (case-insensitive matching)
- [ ] `redact_body` redacts the `password` key in form data dicts
- [ ] `log_request` logs method, URL, redacted headers, redacted body, and params at DEBUG level using `>>>` prefix
- [ ] `log_response` logs status, URL, redacted headers, and truncated body (2000 chars) at DEBUG level using `<<<` prefix
- [ ] All functions accept a `logger` parameter (not a module-level logger)
- [ ] `log_response` accepts an `aiohttp.ClientResponse` for status/url/headers, and an optional `str` body
- [ ] mypy strict passes, ruff passes

## Technical Requirements
- Function signatures as specified in the plan:
  - `redact_headers(headers: Mapping[str, str]) -> dict[str, str]`
  - `redact_body(data: Mapping[str, str]) -> dict[str, str]`
  - `log_request(logger: logging.Logger, method: str, url: str, *, headers: Mapping[str, str] | None = None, data: Mapping[str, str] | None = None, params: Mapping[str, str] | None = None) -> None`
  - `log_response(logger: logging.Logger, response: aiohttp.ClientResponse, body: str | None = None) -> None`
- Case-insensitive header key matching for redaction
- For `Authorization` header: preserve scheme prefix (e.g. `"Bearer ***"`)
- Body truncation to 2000 characters with `"... (N bytes total)"` suffix

## Input Dependencies
None — this is a new module.

## Output Artifacts
- `src/flameconnect/_http_logging.py` — shared module imported by tasks 02 and 03.

## Implementation Notes
- Port the `>>>` / `<<<` logging pattern from `b2c_login.py` lines 117-151.
- The `_SENSITIVE_HEADERS` set should use lowercased keys for case-insensitive matching.
- Use `from __future__ import annotations` for forward references.
- Import `aiohttp` under `TYPE_CHECKING` to avoid a hard runtime dependency for the type signature.
