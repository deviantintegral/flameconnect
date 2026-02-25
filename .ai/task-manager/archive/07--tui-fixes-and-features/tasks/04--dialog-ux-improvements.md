---
id: 4
group: "tui-fixes-and-features"
dependencies: []
status: "completed"
created: 2026-02-25
skills:
  - "textual"
  - "python"
---
# Dialog UX — Fix Color Dialog and Add Arrow Key Navigation

## Objective
Fix the color dialog layout (cut-off preset buttons, broken Enter key for custom RGBW inputs) and add arrow key navigation to all dialog screens via a shared mixin.

## Skills Required
Textual framework, Python

## Acceptance Criteria
- [ ] Color dialog width increased to ~86 chars so all 7 preset buttons per row are visible
- [ ] Pressing Enter in a custom RGBW Input field submits the value (via `on_input_submitted`)
- [ ] Arrow keys (left/right) move focus between buttons in all dialog screens
- [ ] Arrow keys (up/down) also work in multi-row dialogs
- [ ] Arrow keys do NOT interfere with Input widgets (only intercept when focused widget is a Button)
- [ ] ArrowNavMixin is created as a shared class to avoid handler duplication
- [ ] All existing tests pass

## Technical Requirements
### Color Dialog Fix (`color_screen.py`)
- Change `#color-dialog` CSS width from `70` to `86` (7 buttons × ~10 chars + margins + padding + border)
- Add `on_input_submitted(self, event: Input.Submitted) -> None` method that calls `self._apply_custom_rgbw()`. This matches the existing "Set" button behavior.

### Arrow Key Navigation (shared mixin)
- Create `ArrowNavMixin` class (in a shared location, e.g., `widgets.py` or a new `mixins.py`) with an `on_key` method:
  - Check if `self.focused` is a `Button` instance
  - On `left` or `up`: call `self.focus_previous()`
  - On `right` or `down`: call `self.focus_next()`
- Apply the mixin to these dialog screens:
  - `FlameSpeedScreen` (`flame_speed_screen.py`)
  - `FlameColorScreen` (`flame_color_screen.py`)
  - `MediaThemeScreen` (`media_theme_screen.py`)
  - `ColorScreen` (`color_screen.py`)
  - `HeatModeScreen` (`heat_mode_screen.py`)
- The mixin class should be positioned before `ModalScreen` in the MRO for each dialog class.

## Input Dependencies
None.

## Output Artifacts
- Fixed `color_screen.py` with wider dialog and Enter key support
- `ArrowNavMixin` class available for all current and future dialog screens (including the Temperature Adjustment Dialog in Task 08)
- Updated dialog screen files with mixin applied

## Implementation Notes
- The existing `_apply_custom_rgbw()` method validates integer inputs (0-255 range) and is correct — no changes needed to validation logic.
- `focus_next()` and `focus_previous()` are built-in Textual `Screen` methods.
- The mixin must check widget type to avoid breaking cursor movement in `Input` fields.
