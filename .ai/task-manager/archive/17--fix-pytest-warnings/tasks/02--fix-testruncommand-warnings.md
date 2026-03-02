---
id: 2
group: "fix-pytest-warnings"
dependencies: []
status: "completed"
created: 2026-03-02
skills:
  - python-testing
  - async-coroutines
---
# Fix TestRunCommand unawaited coroutine warnings in test_tui_actions.py

## Objective
Eliminate the `coroutine 'AsyncMockMixin._execute_mock_call' was never awaited` and `coroutine '_worker' was never awaited` RuntimeWarnings from `test_no_op_when_not_dashboard` and `test_sets_write_in_progress` in `tests/test_tui_actions.py`.

## Skills Required
- Python async/await and coroutine lifecycle
- unittest.mock (AsyncMock)

## Acceptance Criteria
- [ ] `test_no_op_when_not_dashboard` no longer produces an unawaited coroutine warning
- [ ] `test_sets_write_in_progress` no longer produces unawaited coroutine warnings (both AsyncMock and _worker)
- [ ] Both tests continue to pass with their existing assertions
- [ ] No new warnings introduced

## Technical Requirements

**`test_no_op_when_not_dashboard`** (line 2307): Creates `coro = AsyncMock()()` and passes it to `_run_command`. Since `screen` is not a `DashboardScreen`, `_run_command` returns early and `coro` is abandoned.
**Fix**: Call `coro.close()` after the assertion.

**`test_sets_write_in_progress`** (line 2320): Creates `coro = AsyncMock()()` and passes it to `_run_command`. `_run_command` proceeds, creating an inner `_worker()` coroutine stored via `_capture_worker`. The test intentionally never runs the workers.
**Fix**: Close all captured workers after assertions: loop over `app._captured_workers` calling `.close()`.

**File to modify**: `tests/test_tui_actions.py`
**Tests to modify**: Lines 2307-2329, class `TestRunCommand`

## Input Dependencies
None — this is an independent fix.

## Output Artifacts
Modified `tests/test_tui_actions.py` with the two `TestRunCommand` tests updated to close abandoned coroutines.
