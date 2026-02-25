---
id: 7
group: "tui-fixes-and-features"
dependencies: [1]
status: "completed"
created: 2026-02-25
skills:
  - "textual"
  - "python"
---
# Clickable Parameter Fields

## Objective
Redesign `ParameterPanel` from a single `Static` widget to a container of individually clickable parameter widgets, each invoking the same action as its hotkey/command palette entry.

## Skills Required
Textual framework (widget composition, CSS, events), Python, Rich markup

## Acceptance Criteria
- [ ] `ParameterPanel` changed from `Static` to `Vertical` (or container widget)
- [ ] `ClickableParam(Static)` widget created that accepts markup text and optional action name
- [ ] Clicking a `ClickableParam` calls `self.app.run_action(action_name)` for editable fields
- [ ] Non-editable fields (Heat Control, Sound, Log Effect, Software, Errors) use plain `Static`
- [ ] Clickable fields have visual indicator (underline or distinct cursor)
- [ ] `_format_*` functions refactored to return structured data (text + action mapping)
- [ ] `update_parameters()` clears and re-composes child widgets when data changes
- [ ] Compact mode still works correctly (one widget per line within scroll container)
- [ ] All field-to-action mappings are correct per the plan
- [ ] All existing tests pass

## Technical Requirements
### New Widget (`widgets.py`)
```python
class ClickableParam(Static):
    """A single parameter field that is optionally clickable."""
    DEFAULT_CSS = "ClickableParam { width: 1fr; }"

    def __init__(self, content: str, action: str | None = None) -> None:
        super().__init__(content)
        self._action = action

    def on_click(self) -> None:
        if self._action:
            self.app.run_action(self._action)
```

### ParameterPanel Redesign (`widgets.py`)
- Change base class from `Static` to `Vertical`
- Replace `render()` / `content_text` reactive with `compose()` that yields `ClickableParam` and `Static` widgets
- Refactor `_format_*` functions to return list of `(text: str, action: str | None)` tuples
- `update_parameters()` must clear children and mount new ones: `self.remove_children()` then `self.mount(*new_widgets)`
- Remove pipe-join format (`  |  `) — each field is its own widget now

### Field-to-Action Mapping
| Field | Action |
|-------|--------|
| Mode | `toggle_power` |
| Target Temp | `set_temperature` |
| Heat status/mode/setpoint/boost | `set_heat_mode` |
| Heat Control | (display only) |
| Flame Effect | `toggle_flame_effect` |
| Speed | `set_flame_speed` |
| Brightness | `toggle_brightness` |
| Pulsating | `toggle_pulsating` |
| Flame Color | `set_flame_color` |
| Overhead Light (was Light Status) | `toggle_light_status` |
| Ambient Sensor | `toggle_ambient_sensor` |
| Media Theme | `set_media_theme` |
| Media Light | `toggle_media_light` |
| Media Color | `set_media_color` |
| Overhead Light on/off | `toggle_overhead_light` |
| Overhead Color | `set_overhead_color` |
| Timer | `toggle_timer` |
| Temp Unit | `toggle_temp_unit` |
| Sound | (display only) |
| Log Effect | (display only) |
| Software | (display only) |
| Errors | (display only) |

### CSS (`screens.py`)
- Add styles for `ClickableParam` (e.g., `text-style: underline` when action is set, cursor styling)
- Ensure container layout works in both normal and compact modes

## Input Dependencies
- Task 01 (Fix Parameter Panel Border) must be completed first — provides correct panel width

## Output Artifacts
- Redesigned `ParameterPanel` with clickable fields in `widgets.py`
- New `ClickableParam` widget class
- Updated CSS in `screens.py`

## Implementation Notes
- This is a significant refactoring. The existing `_format_*` functions should be refactored incrementally.
- Use Textual's `remove_children()` + `mount()` pattern for dynamic updates.
- The pipe-join format (`  |  `) is an artifact of single-string rendering and is no longer needed.
- Compact mode: individual widgets render one-per-line within the scroll container. Textual's layout handles stacking.
