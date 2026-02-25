---
id: 2
group: "tui-fixes-and-features"
dependencies: []
status: "completed"
created: 2026-02-25
skills:
  - "textual"
  - "python"
---
# Add Version to Header and Fix Help Panel Toggle

## Objective
Show the library version in the app header and make the `?` key toggle the help panel open/closed (currently it only opens).

## Skills Required
Textual framework, Python

## Acceptance Criteria
- [ ] App header displays "FlameConnect v0.1.0" (using `__version__` from `__init__.py`)
- [ ] Pressing `?` opens the help panel when it's closed
- [ ] Pressing `?` closes the help panel when it's open
- [ ] Help toggle state tracks correctly across multiple presses
- [ ] All existing tests pass

## Technical Requirements
### Version in Header
In `app.py`:
- Import `__version__` from `flameconnect`
- Change `TITLE = "FlameConnect"` to `TITLE = f"FlameConnect v{__version__}"`

### Help Panel Toggle
In `app.py` (`FlameConnectApp`):
- Add instance attribute `_help_visible: bool = False`
- Modify `action_toggle_help()` to:
  - If `_help_visible` is True: call `self.action_hide_help_panel()` and set `_help_visible = False`
  - If `_help_visible` is False: call `self.action_show_help_panel()` and set `_help_visible = True`

## Input Dependencies
None.

## Output Artifacts
- Updated `app.py` with version in TITLE and working help toggle

## Implementation Notes
Using a boolean flag avoids depending on internal Textual DOM state for help panel visibility detection. The `action_show_help_panel()` and `action_hide_help_panel()` are built-in Textual App methods.
