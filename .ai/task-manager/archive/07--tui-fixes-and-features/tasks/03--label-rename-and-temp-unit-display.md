---
id: 3
group: "tui-fixes-and-features"
dependencies: []
status: "completed"
created: 2026-02-25
skills:
  - "python"
---
# Rename Light Status to Overhead Light and Fix Temperature Unit Display

## Objective
Change the user-facing label "Light Status" to "Overhead Light" everywhere in the UI and CLI. Add the correct temperature unit suffix (°C or °F) to all temperature displays.

## Skills Required
Python

## Acceptance Criteria
- [ ] "Light Status" renamed to "Overhead Light" in command palette entry in `app.py`
- [ ] "Light Status" renamed to "Overhead Light" in keybinding description in `app.py`
- [ ] "Light Status" renamed to "Overhead Light" in CLI output in `cli.py`
- [ ] "Light Status" renamed to "Overhead Light" in parameter display in `widgets.py`
- [ ] Internal field name `light_status` and `LightStatus` enum remain unchanged
- [ ] Temperature values display as `72°F` or `22°C` (with unit suffix)
- [ ] `_format_mode()` accepts and uses temperature unit parameter
- [ ] `_format_heat()` accepts and uses temperature unit parameter
- [ ] `format_parameters()` extracts `TempUnitParam` and passes it to formatting functions
- [ ] CLI temperature output includes unit suffix
- [ ] All existing tests pass

## Technical Requirements
### Label Rename
Update these occurrences (do NOT rename internal identifiers):
- `app.py`: `_CONTROL_COMMANDS` entry `("Light Status", ..., "toggle_light_status")` → `("Overhead Light", ...)`
- `app.py`: `Binding("s", "toggle_light_status", "Light Status")` → `"Overhead Light"`
- `cli.py`: `"Light Status:"` → `"Overhead Light:"`
- `widgets.py`: In `_format_flame_effect()`, change `"Light: {_display_name(...)}"` to `"Overhead Light: {_display_name(...)}"`

### Temperature Unit Display
- In `format_parameters()`: Extract `TempUnitParam` from the parameter list at the start. Pass it to `_format_mode()` and `_format_heat()`.
- In `_format_mode()`: Add optional `temp_unit: TempUnitParam | None = None` parameter. Compute suffix `"C"` if CELSIUS, `"F"` if FAHRENHEIT. Append after `°` symbol.
- In `_format_heat()`: Same approach — add optional `temp_unit` parameter, append unit suffix after degree symbol.
- In `cli.py`: Where temperatures are printed with `°`, include the unit suffix.

## Input Dependencies
None.

## Output Artifacts
- Updated label and temperature display in `widgets.py`, `app.py`, `cli.py`
- The temperature unit extraction logic will be reused by the Temperature Adjustment Dialog (Task 08)

## Implementation Notes
- The `TempUnitParam` is always present in API responses and is already in the parameter list passed to `format_parameters()`.
- The internal field name `light_status` and `LightStatus` enum reflect the wire protocol and must NOT be renamed.
