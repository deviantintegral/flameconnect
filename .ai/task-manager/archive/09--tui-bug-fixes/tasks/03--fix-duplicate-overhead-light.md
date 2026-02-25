---
id: 3
group: "tui-bug-fixes"
dependencies: []
status: "completed"
created: 2026-02-25
skills:
  - "python"
---
# Fix Duplicate Overhead Light Labels

## Objective
Revert the `light_status` field labels from "Overhead Light" back to "Light Status" to distinguish it from the `overhead_light` field.

## Skills Required
- String replacement across multiple files

## Acceptance Criteria
- [ ] `light_status` field shows as "Light Status" in the TUI parameter panel (not "Overhead Light")
- [ ] `overhead_light` field still shows as "Overhead Light" (unchanged)
- [ ] Command palette has distinct entries: "Overhead Light" for `toggle_overhead_light` and "Light Status" for `toggle_light_status`
- [ ] Key binding 's' shows description "Light Status" (not "Overhead Light")
- [ ] CLI displays `light_status` as "Light Status:" (not "Overhead Light:")
- [ ] All existing tests pass
- [ ] No lint errors

## Technical Requirements

Four locations need updating:

1. **widgets.py** `_format_flame_effect()`: Find the tuple that displays `param.light_status` with label `"  Overhead Light: "` and change the label to `"  Light Status: "`. The OTHER "Overhead Light" entry that displays `param.overhead_light` should remain unchanged.

2. **app.py** `_CONTROL_COMMANDS`: Find the entry `("Overhead Light", "Toggle light status on/off", "toggle_light_status")` and change to `("Light Status", "Toggle light status on/off", "toggle_light_status")`. The OTHER entry `("Overhead Light", "Toggle overhead light on/off", "toggle_overhead_light")` remains unchanged.

3. **app.py** BINDINGS: Find the binding for key `"s"` with action `"toggle_light_status"` and description `"Overhead Light"`, change description to `"Light Status"`.

4. **cli.py**: Find where `param.light_status` is displayed with the "Overhead Light:" label and change to "Light Status:". Keep the OTHER "Overhead Light:" line that displays `param.overhead_light` or `param.overhead_color` unchanged.

## Input Dependencies
None

## Output Artifacts
- Renamed labels in widgets.py, app.py, cli.py

## Implementation Notes
- Be careful to change ONLY the `light_status`-related labels, not the `overhead_light`-related ones
- The `overhead_light` field (byte 13) controls the overhead light fixture
- The `light_status` field (byte 18) is a separate hardware setting whose exact purpose is unknown

## Files
- `src/flameconnect/tui/widgets.py`
- `src/flameconnect/tui/app.py`
- `src/flameconnect/cli.py`
