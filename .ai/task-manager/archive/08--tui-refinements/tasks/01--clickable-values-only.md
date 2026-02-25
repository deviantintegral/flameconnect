---
id: 1
group: "tui-refinements"
dependencies: []
status: "completed"
created: 2026-02-25
skills:
  - "textual-widgets"
  - "python"
---
# Clickable Values Only

## Objective
Split each `ClickableParam` widget so only the value portion is interactive (underlined, hoverable, clickable), while the label is plain static text. Currently the entire line is clickable.

## Skills Required
- Textual widget composition (Horizontal containers, Static widgets)
- Python Rich markup parsing

## Acceptance Criteria
- [ ] Labels are plain, non-interactive `Static` widgets
- [ ] Only value portions are underlined, hoverable, and clickable
- [ ] Display-only fields (action is `None`) have no underline/hover/click behavior on the value
- [ ] Indented sub-fields under `_format_flame_effect()` split correctly (e.g., `"  Speed: "` label, `"3/5"` value)
- [ ] Multi-part values (RGBW) remain as a single clickable string
- [ ] Composite values (Timer) keep full composite as the value
- [ ] All existing tests pass
- [ ] No lint errors

## Technical Requirements

### Format Function Changes
The `_format_*` functions in `widgets.py` currently return `list[tuple[str, str | None]]` where the string is the complete Rich markup line. Change the return type to `list[tuple[str, str, str | None]]` — a 3-tuple of `(label, value, action)`.

**Top-level fields** use `[bold]Label:[/bold]` markup. Split so label is `"[bold]Mode:[/bold] "` and value is `"On"`.

**Indented sub-fields** under `_format_flame_effect()` use a leading two-space indent (e.g., `"  Speed: 3/5"`). Label is `"  Speed: "` and value is `"3/5"`. There are 12 such sub-fields.

### Widget Changes
Transform `ClickableParam` from a `Static` to a `Horizontal` container:
- Child 1: `Static(label)` — plain, non-interactive, `width: auto`
- Child 2: `Static(value)` — when action is not `None`: underlined, hoverable, clickable. When action is `None`: plain text.

Update `ParameterPanel.update_parameters()` and `format_parameters()` to use the new 3-tuple format.

### Files
- `src/flameconnect/tui/widgets.py`: `ClickableParam`, all `_format_*` functions, `format_parameters`, `ParameterPanel.update_parameters`

## Input Dependencies
None

## Output Artifacts
- Updated `_format_*` return type: `list[tuple[str, str, str | None]]`
- Refactored `ClickableParam` as `Horizontal` container with label/value split

## Implementation Notes
- No existing tests cover `_format_*`, `format_parameters`, `ClickableParam`, or `ParameterPanel`. Changes will not trigger test failures but visual regression should be verified.
- The `_format_flame_effect` function returns 12 indented sub-fields with `"  "` prefix.
- Keep `ClickableParam` CSS classes (`clickable`, hover styles) on the value child only.
