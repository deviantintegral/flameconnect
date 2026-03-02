---
id: 3
group: "fix-pytest-warnings"
dependencies: []
status: "completed"
created: 2026-03-02
skills:
  - python-testing
  - unittest-mock
---
# Fix TestAuthScreen unawaited coroutine warnings in test_tui_screens.py

## Objective
Eliminate the `coroutine 'AuthScreen._do_credential_login' was never awaited` RuntimeWarnings from `test_credential_submit_triggers_worker` and `test_password_submitted_triggers_on_submit` in `tests/test_tui_screens.py`.

## Skills Required
- Python testing with pytest
- unittest.mock (MagicMock, patch, call_args)

## Acceptance Criteria
- [ ] `test_credential_submit_triggers_worker` no longer produces an unawaited coroutine warning
- [ ] `test_password_submitted_triggers_on_submit` no longer produces an unawaited coroutine warning
- [ ] Both tests continue to pass with their existing assertions
- [ ] No new warnings introduced

## Technical Requirements

Both source tests follow the same pattern: they set email/password input values, trigger `_submit_credentials` (via button press or input submit), which calls `self.run_worker(self._do_credential_login(email, password), ...)`. Since `run_worker` is already patched with a `MagicMock`, the mock receives and discards the `_do_credential_login` coroutine without awaiting it.

**Fix**: After assertions, retrieve the coroutine from `mock_worker.call_args[0][0]` and call `.close()` on it. This explicitly finalizes the coroutine.

**`test_credential_submit_triggers_worker`** (line 1238): Uses `patch.object(app.screen, "run_worker") as mock_worker`. Add `mock_worker.call_args[0][0].close()` after `mock_worker.assert_called_once()`.

**`test_password_submitted_triggers_on_submit`** (line 1308): Uses `patch.object(app.screen, "run_worker")` without naming the mock. Capture the mock via `as mock_worker` and close the coroutine arg after the test body.

**File to modify**: `tests/test_tui_screens.py`
**Tests to modify**: Lines 1238-1248 and lines 1308-1318, class `TestAuthScreen`

## Input Dependencies
None — this is an independent fix.

## Output Artifacts
Modified `tests/test_tui_screens.py` with the two `TestAuthScreen` tests updated to close abandoned coroutines.
