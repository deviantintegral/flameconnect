---
id: 4
group: "increase-test-coverage"
dependencies: []
status: "completed"
created: 2026-02-25
skills:
  - "python-testing"
  - "textual-tui"
---
# Add TUI modal screen tests

## Objective
Create `tests/test_tui_screens.py` to cover the ~470 missed statements across 9 TUI screen files: `screens.py`, `auth_screen.py`, `color_screen.py`, `temperature_screen.py`, `heat_mode_screen.py`, `media_theme_screen.py`, `flame_color_screen.py`, `flame_speed_screen.py`, and `fire_select_screen.py`.

## Skills Required
- python-testing: pytest, pytest-asyncio
- textual-tui: Textual's testing framework (run_test(), pilot interactions)

## Acceptance Criteria
- [ ] New file `tests/test_tui_screens.py` created
- [ ] Tests cover `DashboardScreen` lifecycle methods (from screens.py): `_load_overview`, refresh logic
- [ ] Tests cover modal screens at 0%: `ColorScreen`, `TemperatureScreen`, `MediaThemeScreen`, `FlameColorScreen`, `FlameSpeedScreen`
- [ ] Tests cover partially-tested screens: `AuthScreen`, `HeatModeScreen`, `FireSelectScreen`
- [ ] Each modal screen test verifies: compose (renders without error), user interaction, dismiss with result
- [ ] All tests pass
- [ ] No files in `src/` are modified

## Technical Requirements
- Use Textual's `run_test()` context manager to mount screens
- For modal screens: create a minimal host App, push the modal, interact via pilot, capture dismissed result
- Mock `FlameConnectClient` for screens that make API calls
- Mock B2C login flow for `AuthScreen`
- Reference patterns from `test_tui_actions.py` and `test_responsive_layout.py`

## Input Dependencies
None — independent task.

## Output Artifacts
- `tests/test_tui_screens.py`

## Implementation Notes
- Read each screen file to understand its constructor parameters, compose structure, and dismiss behavior
- Modal screens typically: accept an initial value → compose buttons/inputs → user selects → dismiss(result)
- Start with the simplest screens (FlameSpeedScreen, FlameColorScreen) then progress to more complex ones
- For `AuthScreen`, the B2C login flow is heavily async — mock `B2CLogin` class
- For `DashboardScreen`, mock the client's `get_fire_overview()` return value
- Skip any screen interaction that requires src/ changes to make testable
- Coverage report uncovered lines per screen:
  - screens.py: 121-122, 183, 224-227, 237, 248-282, 290-300, 310
  - auth_screen.py: 84-87, 90-99, 102, 105-108, 111-112, 115-118, 121-133, 140-149, 152-182, 185-190, 193, 198-200, 203, 206-208, 211, 214-216, 219-221
  - color_screen.py: 3-167 (entire file)
  - temperature_screen.py: 3-155 (entire file)
  - heat_mode_screen.py: 86-105, 112-113, 116-120, 123-129, 132-133, 136-144, 147-150, 153-158, 161
  - media_theme_screen.py: 3-122 (entire file)
  - flame_color_screen.py: 3-108 (entire file)
  - flame_speed_screen.py: 3-86 (entire file)
  - fire_select_screen.py: 77-92, 99-102, 105-111, 114, 117
