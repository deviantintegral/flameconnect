---
id: 4
group: "fireplace-state-controls"
dependencies: [2, 3]
status: "completed"
created: 2026-02-23
skills:
  - "python"
  - "pytest"
---
# Add Tests for New CLI and TUI Write Operations

## Objective
Add automated tests for all new CLI set commands and TUI keybinding actions to maintain test coverage without requiring live API access.

## Skills Required
- pytest with aioresponses mocking
- Textual testing patterns (`app.run_test()`)

## Acceptance Criteria
- [ ] Tests for `_set_pulsating`: valid on/off values, invalid value error
- [ ] Tests for `_set_flame_color`: valid color string, invalid value error
- [ ] Tests for `_set_media_theme`: valid theme string, invalid value error
- [ ] Tests for `_set_temp_unit`: valid fahrenheit/celsius, invalid value error
- [ ] Tests for TUI `action_cycle_flame_speed`: verifies write_parameters called with incremented speed
- [ ] Tests for TUI `action_toggle_brightness`: verifies toggle between High/Low
- [ ] Tests for TUI `action_cycle_heat_mode`: verifies mode cycling
- [ ] Tests for TUI `action_toggle_timer`: verifies enable (60 min default) and disable
- [ ] Tests for TUI `action_toggle_temp_unit`: verifies toggle between F/C
- [ ] Test for write-in-progress guard: second action returns early while first is in flight
- [ ] All tests pass: `uv run pytest tests/`
- [ ] `uv run ruff check` and `uv run mypy --strict src/` pass

Use your internal Todo tool to track these and keep on track.

## Technical Requirements

### CLI Tests (in `tests/test_cli.py` or new `tests/test_cli_set.py`):
- Follow existing test patterns in `test_client.py` using `aioresponses` to mock HTTP
- Each test constructs a mock `get_fire_overview` response with known parameter values, then calls the set handler and asserts the `write_parameters` POST payload contains the expected parameter
- For invalid input tests: capture `sys.exit` via `pytest.raises(SystemExit)` and verify error message via `capsys`
- Use the existing fixture `get_fire_overview.json` as the base response payload

### TUI Tests (in `tests/test_tui.py` or new file):
- Use Textual's async testing: `async with app.run_test() as pilot:`
- Mock `FlameConnectClient` to capture `write_parameters` calls
- Simulate keypresses via `pilot.press("f")`, `pilot.press("b")`, etc.
- Assert the mocked `write_parameters` was called with expected parameter type and field values
- Assert messages panel contains confirmation text

## Input Dependencies
- Task 02 (CLI commands) and Task 03 (TUI keybindings) must be complete

## Output Artifacts
- New or updated test files with comprehensive coverage for all write operations

## Implementation Notes
- Check existing test files first (`tests/test_protocol.py`, `tests/test_client.py`, `tests/test_models.py`) to understand patterns
- The existing `tests/fixtures/get_fire_overview.json` contains sample API response data for mocking
- For TUI tests, you may need to mock the client at the method level rather than HTTP level for simplicity
- Consider using `unittest.mock.AsyncMock` for mocking async client methods in TUI tests
