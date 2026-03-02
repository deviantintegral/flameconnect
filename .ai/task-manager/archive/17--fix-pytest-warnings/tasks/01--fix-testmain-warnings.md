---
id: 1
group: "fix-pytest-warnings"
dependencies: []
status: "completed"
created: 2026-03-02
skills:
  - python-testing
  - unittest-mock
---
# Fix TestMain unawaited coroutine warnings in test_cli_commands.py

## Objective
Eliminate the `coroutine 'async_main' was never awaited` RuntimeWarnings produced by all three `TestMain` tests in `tests/test_cli_commands.py`.

## Skills Required
- Python testing with pytest
- unittest.mock (MagicMock, patch)

## Acceptance Criteria
- [ ] All three `TestMain` tests (`test_main_calls_async_main`, `test_main_verbose_logging`, `test_main_no_verbose_logging`) no longer produce unawaited coroutine warnings
- [ ] All three tests continue to pass with their existing assertions
- [ ] No new warnings introduced

## Technical Requirements

All three tests patch `flameconnect.cli.asyncio` with a `MagicMock`, making `asyncio.run` a no-op. However, `async_main(args)` at `cli.py:894` is the real function — calling it creates a real coroutine that is passed to the mocked `asyncio.run()` and discarded.

**Fix**: Additionally patch `flameconnect.cli.async_main` in each test. When `async_main` is a `MagicMock`, calling `async_main(args)` returns a `MagicMock` (not a coroutine), so no RuntimeWarning is produced.

**File to modify**: `tests/test_cli_commands.py`
**Tests to modify**: Lines 1421-1471, class `TestMain`

## Input Dependencies
None — this is an independent fix.

## Output Artifacts
Modified `tests/test_cli_commands.py` with the three `TestMain` tests updated to also patch `async_main`.
