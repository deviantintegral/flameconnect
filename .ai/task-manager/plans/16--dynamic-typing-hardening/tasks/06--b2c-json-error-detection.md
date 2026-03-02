---
id: 6
group: "dynamic-typing-hardening"
dependencies: [4]
status: "pending"
created: 2026-03-01
skills:
  - "python-typing"
  - "refactoring"
---
# Replace B2C String-Matching Error Detection with JSON Parsing

## Objective
Replace fragile `'"status":"400"' in body` string matching in `b2c_login.py` with proper JSON parsing for error detection. This task also depends on Task 04 since that task introduces `_B2CLoginFields` in the same file.

## Skills Required
Python JSON parsing, error handling.

## Acceptance Criteria
- [ ] String-matching pattern replaced with `json.loads()` + field check
- [ ] Wrapped in `try/except (json.JSONDecodeError, KeyError, TypeError)` for graceful fallback
- [ ] Non-JSON responses fall through without raising (matching current behavior)
- [ ] `uv run ruff check .` passes
- [ ] `uv run mypy src/` passes
- [ ] `uv run pytest` passes

## Technical Requirements

In `src/flameconnect/b2c_login.py`, around line 242, replace:

```python
if '"status":"400"' in body or '"status": "400"' in body:
    raise AuthenticationError("Invalid email or password")
```

With:

```python
try:
    resp_data = json.loads(body)
    if str(resp_data.get("status")) == "400":
        raise AuthenticationError("Invalid email or password")
except (json.JSONDecodeError, KeyError, TypeError):
    pass
```

Import `json` at the top of the file.

## Input Dependencies
- Task 04: Modifies the same file (`b2c_login.py`) with `_B2CLoginFields`. This task must run after Task 04 to avoid merge conflicts.

## Output Artifacts
Robust JSON-based error detection in `b2c_login.py`.

## Implementation Notes
- Use `str(resp_data.get("status"))` to handle both string `"400"` and integer `400` status values.
- The `try/except` ensures that if the response is ever not JSON (HTML error page, empty body), it falls through gracefully — exactly like the current string-matching behavior where non-matching bodies proceed to the next step.
- The B2C SelfAsserted endpoint is called with `X-Requested-With: XMLHttpRequest`, so JSON responses are expected. The `try/except` is defensive.
- Update existing tests for this code path if they mock the response body.
