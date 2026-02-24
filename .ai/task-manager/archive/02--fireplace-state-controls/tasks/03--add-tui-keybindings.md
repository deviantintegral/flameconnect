---
id: 3
group: "fireplace-state-controls"
dependencies: [1]
status: "completed"
created: 2026-02-23
skills:
  - "python"
  - "textual-tui"
---
# Add TUI Interactive Keybindings for Fireplace Controls

## Objective
Add 5 new keybindings to the TUI dashboard so users can control flame speed, brightness, heat mode, timer, and temperature unit directly from the interface.

## Skills Required
- Python async programming
- Textual TUI framework (App bindings, action methods, Screen interaction)

## Acceptance Criteria
- [ ] `DashboardScreen` exposes a `current_parameters` property returning `dict[type, Parameter]`
- [ ] `FlameConnectApp` has a `_write_in_progress` boolean flag, initialized to `False`
- [ ] Key `f` cycles flame speed 1→2→3→4→5→1 and writes FlameEffectParam
- [ ] Key `b` toggles brightness between High and Low and writes FlameEffectParam
- [ ] Key `h` cycles heat mode Normal→Boost→Eco→Fan Only→Normal and writes HeatParam
- [ ] Key `t` toggles timer: if enabled, disables (duration=0); if disabled, enables with 60-minute default
- [ ] Key `u` toggles temp unit between Fahrenheit and Celsius and writes TempUnitParam
- [ ] All actions log a message to the messages panel (e.g., "Flame speed set to 3")
- [ ] All actions call `screen.refresh_state()` after the write
- [ ] Write-in-progress guard prevents concurrent writes (early return if `_write_in_progress` is True)
- [ ] Status bar text updated to show new keybindings
- [ ] `uv run ruff check` and `uv run mypy --strict src/` pass

Use your internal Todo tool to track these and keep on track.

## Technical Requirements

### DashboardScreen changes (`tui/screens.py`):
- Add `current_parameters` property: `return dict(self._previous_params)`

### FlameConnectApp changes (`tui/app.py`):
- Add to `BINDINGS`: `("f", "cycle_flame_speed", "Flame Speed")`, `("b", "toggle_brightness", "Brightness")`, `("h", "cycle_heat_mode", "Heat Mode")`, `("t", "toggle_timer", "Timer")`, `("u", "toggle_temp_unit", "Temp Unit")`
- Add `self._write_in_progress = False` in `__init__`
- Each action method pattern:
  1. Guard: `screen` is `DashboardScreen` and `fire_id` is set
  2. Guard: `if self._write_in_progress: return`
  3. `self._write_in_progress = True`
  4. Try block: read param from `screen.current_parameters`, compute new value, `dataclasses.replace()`, `client.write_parameters()`, log message, `screen.refresh_state()`
  5. Finally: `self._write_in_progress = False`
- Imports needed: `dataclasses.replace`, `FlameEffectParam`, `HeatParam`, `HeatMode`, `TimerParam`, `TimerStatus`, `TempUnitParam`, `TempUnit`, `Brightness`
- Cycle helpers: for flame speed `(current + 1 - 1) % 5 + 1` (wraps 5→1); for heat mode use a list of modes and modular index

### Status bar update (`tui/screens.py`):
- Update the status bar text in `_update_display` to include hints for all keybindings

## Input Dependencies
- Task 01 (refactor) must be complete so `dataclasses.replace()` pattern is established

## Output Artifacts
- Updated `src/flameconnect/tui/app.py` with 5 new action methods and bindings
- Updated `src/flameconnect/tui/screens.py` with `current_parameters` property and updated status bar

## Implementation Notes
- Follow the existing `action_toggle_power` as the structural template
- The `_write_in_progress` flag should also gate the existing `action_toggle_power` for consistency
- For heat mode cycling, handle the case where HeatParam is not found (fireplace may not have heat)
- Timer toggle: use `TimerStatus.DISABLED` with `duration=0` to disable, `TimerStatus.ENABLED` with `duration=60` to enable
