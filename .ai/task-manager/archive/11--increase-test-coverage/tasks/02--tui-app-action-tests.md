---
id: 2
group: "increase-test-coverage"
dependencies: []
status: "completed"
created: 2026-02-25
skills:
  - "python-testing"
  - "mocking"
---
# Expand TUI app action method tests

## Objective
Add tests to `tests/test_tui_actions.py` to cover the ~285 missed statements in `src/flameconnect/tui/app.py`. Focus on uncovered action methods and lifecycle methods.

## Skills Required
- python-testing: pytest, pytest-asyncio
- mocking: unittest.mock for DashboardScreen, FlameConnectClient

## Acceptance Criteria
- [ ] Expanded `tests/test_tui_actions.py` with new tests
- [ ] Tests cover lifecycle methods: `_load_fires`, `show_auth_screen`, `_run_command`
- [ ] Tests cover uncovered action methods (toggle power, screen navigation actions, etc.)
- [ ] Tests cover `_resolve_version` and `FireplaceCommandsProvider`
- [ ] All tests pass (both existing and new)
- [ ] No files in `src/` are modified

## Technical Requirements
- Follow the EXACT pattern already used in `tests/test_tui_actions.py` — read this file first to understand the mocking setup
- The existing tests mock `DashboardScreen` with `current_parameters` and a mocked `FlameConnectClient`
- Use `AsyncMock` for client methods, `PropertyMock` for properties
- For `_load_fires`, mock `client.get_fires()` return value
- For `show_auth_screen`, mock the screen push mechanism
- For `_resolve_version`, mock subprocess calls

## Input Dependencies
None — independent task.

## Output Artifacts
- Updated `tests/test_tui_actions.py` with additional test functions

## Implementation Notes
- Read `src/flameconnect/tui/app.py` to identify all uncovered action methods from the coverage report
- Read existing `tests/test_tui_actions.py` to understand the established testing pattern
- Coverage report shows uncovered lines: 58, 67, 81-82, 113-117, 126, 174-179, 183-185, 189, 193-224, 228-236, 245-259, 267-268, 283, 305-309, 313-318, 335-354, 362-382, 392, 413, 415, 420, 440, 447, 467, 474, 494, 501, 521, 528, 548, 555, 571-591, 601, 608, 619-639, 649, 656, 680-684, 695-713, 724, 731, 742-760, 771, 778, 789-808, 823, 852, 875-898, 905-918, 940, 943-950, 963, 965, 970, 989, 991, 1021-1081
- Skip any methods that require complex Textual lifecycle management that can't be mocked
