---
id: 5
group: "increase-test-coverage"
dependencies: []
status: "completed"
created: 2026-02-25
skills:
  - "python-testing"
  - "mocking"
---
# Add core module edge case tests

## Objective
Cover the ~38 remaining missed statements across `auth.py`, `b2c_login.py`, `client.py`, `protocol.py`, and `__main__.py` by adding targeted edge-case tests.

## Skills Required
- python-testing: pytest, pytest-asyncio
- mocking: unittest.mock, aioresponses

## Acceptance Criteria
- [ ] New file `tests/test_main.py` for `__main__.py` (2 statements)
- [ ] Added edge-case tests to `tests/test_auth.py` for uncovered lines (83, 145, 150, 169-171, 195-196, 210)
- [ ] Added edge-case tests to `tests/test_b2c_login.py` for uncovered lines (47, 129, 152, 277-278, 282-285, 323, 340, 353-363, 368-369)
- [ ] Added edge-case tests to `tests/test_client.py` for uncovered lines (52-57, 206-208)
- [ ] Added edge-case tests to `tests/test_protocol.py` for uncovered lines (465-466)
- [ ] All tests pass (both existing and new)
- [ ] No files in `src/` are modified

## Technical Requirements
- For `__main__.py`: mock `flameconnect.cli.main` and import `__main__`
- For `auth.py`: mock MSAL library to trigger error paths in `_save_cache`, `acquire_token_silent`, etc.
- For `b2c_login.py`: use `aioresponses` to simulate error HTTP responses and edge cases in HTML parsing
- For `client.py`: use `aioresponses` to simulate context manager error paths and response parsing edge cases
- For `protocol.py`: create a parameter object that doesn't match any known type to trigger the else branch

## Input Dependencies
None — independent task.

## Output Artifacts
- `tests/test_main.py` (new)
- Updated `tests/test_auth.py`, `tests/test_b2c_login.py`, `tests/test_client.py`, `tests/test_protocol.py`

## Implementation Notes
- Read each source file's uncovered lines to understand exactly what code path needs to be triggered
- Read each existing test file to understand the established patterns before adding new tests
- These are surgical additions — typically 1-3 test functions per file
- For protocol.py lines 465-466: this is likely a `TypeError` or fallback branch for unknown parameter types
- For client.py lines 52-57: likely the `__aenter__`/`__aexit__` error path
- For client.py lines 206-208: likely an HTTP error response handling path
