---
id: 4
group: "tui-refinements"
dependencies: [1]
status: "completed"
created: 2026-02-25
skills:
  - "python"
---
# Client-Side Temperature Conversion

## Objective
Implement client-side Celsius-to-Fahrenheit conversion so temperature values display correctly when the user's display unit is Fahrenheit. The device always returns Celsius regardless of the unit setting.

## Skills Required
- Python arithmetic (temperature conversion)
- Textual widget integration
- CLI display formatting

## Acceptance Criteria
- [ ] Temperature values converted C->F when display unit is Fahrenheit (F = C * 9/5 + 32)
- [ ] Values unchanged when display unit is Celsius
- [ ] Converted values rounded to 1 decimal place
- [ ] `_format_mode()` converts `target_temperature` before display
- [ ] `_format_heat()` converts `setpoint_temperature` before display
- [ ] CLI `_display_mode()` and `_display_heat()` convert temperatures
- [ ] `TemperatureScreen` displays current temp in the active unit (C->F if Fahrenheit)
- [ ] `TemperatureScreen` validates input range in the active unit
- [ ] `TemperatureScreen` converts entered value F->C before dismissing (device writes Celsius)
- [ ] All existing tests pass
- [ ] No lint errors

## Technical Requirements

### Conversion Helper
Add `_convert_temp(celsius: float, unit: TempUnit) -> float` in `widgets.py`:
- Returns value unchanged if unit is CELSIUS
- Returns `round(celsius * 9 / 5 + 32, 1)` if FAHRENHEIT

### TUI Format Functions (widgets.py)
Apply conversion in:
- `_format_mode()`: convert `param.target_temperature` before display. This function already receives `temp_unit` parameter.
- `_format_heat()`: convert `param.setpoint_temperature` before display. This function also already receives `temp_unit`.

**Important**: After Task 01 completes, these functions return `list[tuple[str, str, str | None]]` (3-tuples). Work with the updated signatures.

### CLI Functions (cli.py)
- `_display_mode()` and `_display_heat()` currently receive `unit_suffix: str`. Refactor to pass `TempUnit` enum (or the full `TempUnitParam`) instead of just the suffix string.
- Add a matching `_convert_temp()` helper in `cli.py` or import from a shared location.
- The existing `_temp_suffix()` helper in `cli.py` can be reused alongside conversion.

### TemperatureScreen Dialog (temperature_screen.py)
The dialog currently receives `current_temp: float` (raw Celsius) and `unit: TempUnit`. When unit is Fahrenheit:
1. Convert displayed current temperature C->F
2. Show/validate input range in Fahrenheit (40.0-95.0 F)
3. On submit, convert entered value F->C before dismissing (caller writes Celsius)

The dialog already handles range validation per unit. The key changes:
- In `__init__` or `compose`: convert `self._current_temp` for display when unit is F
- In `_validate_and_dismiss`: convert the entered F value back to C before calling `self.dismiss()`

### Files
- `src/flameconnect/tui/widgets.py`: `_convert_temp()`, `_format_mode()`, `_format_heat()`
- `src/flameconnect/cli.py`: `_convert_temp()`, `_display_mode()`, `_display_heat()`
- `src/flameconnect/tui/temperature_screen.py`: bidirectional conversion

## Input Dependencies
- Task 01 (Clickable Values Only): format function signatures change to 3-tuple return type

## Output Artifacts
- `_convert_temp()` helper function(s)
- Updated format/display functions with conversion
- Updated TemperatureScreen with bidirectional conversion

## Implementation Notes
- The device firmware always returns Celsius. The `TempUnitParam` is purely a display preference.
- Always store/transmit in Celsius. Only convert for display and user input.
- Round to 1 decimal for display to avoid floating-point artifacts (e.g., 22.0C -> 71.6F not 71.60000001F).
