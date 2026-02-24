---
id: 3
group: "tui-dialogs"
dependencies: [1]
status: "completed"
created: "2026-02-23"
skills:
  - python
  - textual
complexity_score: 5
complexity_notes: "Most complex dialog — combines Input widgets with button grid and keyboard shortcuts"
---
# Create ColorScreen Reusable RGBW Colour Picker Dialog

## Objective
Create a reusable Textual modal dialog (`ColorScreen`) that allows users to set RGBW colour values via either 14 named colour presets (with keyboard shortcuts) or direct RGBW numeric input. Used by both the media colour (`d`) and overhead colour (`v`) keybindings.

## Skills Required
- Python: ModalScreen pattern, input validation
- Textual: Input widgets, Button grid layout, CSS styling, key bindings with Shift+letter

## Acceptance Criteria
- [ ] `ColorScreen` is a `ModalScreen[RGBWColor | None]` reusable with different titles
- [ ] 14 named preset buttons arranged in two rows (Dark, Light) of 7 colours each
- [ ] Lowercase letter shortcuts select dark presets, Shift+letter (uppercase) selects light presets
- [ ] Four `Input` widgets (R, G, B, W) pre-populated with current values
- [ ] A "Set" button applies the RGBW input values after validating 0-255 range
- [ ] Invalid RGBW input shows an error notification (does not dismiss)
- [ ] Escape cancels (dismisses `None`)
- [ ] `ruff check` and `mypy --strict` pass

## Technical Requirements
- Textual `ModalScreen`, `Button`, `Static`, `Input`, `Horizontal`, `Vertical` containers
- `RGBWColor` and `NAMED_COLORS` from `flameconnect.models`
- Constructor: `__init__(self, current: RGBWColor, title: str, name: str | None = None)`

## Input Dependencies
- Task 1: `NAMED_COLORS` dict must exist in `models.py`

## Output Artifacts
- New file: `src/flameconnect/tui/color_screen.py`

## Implementation Notes

<details>
<summary>Detailed implementation guidance</summary>

### File: `src/flameconnect/tui/color_screen.py`

**Class**: `ColorScreen(ModalScreen[RGBWColor | None])`

**Constructor**:
```python
def __init__(self, current: RGBWColor, title: str, name: str | None = None) -> None:
    super().__init__(name=name)
    self._current = current
    self._title = title
```

### BINDINGS

Lowercase for dark, uppercase (Shift+letter) for light:
```python
BINDINGS = [
    ("escape", "cancel", "Cancel"),
    ("r", "select_preset('dark-red')", "Dark Red"),
    ("R", "select_preset('light-red')", "Light Red"),
    ("y", "select_preset('dark-yellow')", "Dark Yellow"),
    ("Y", "select_preset('light-yellow')", "Light Yellow"),
    ("g", "select_preset('dark-green')", "Dark Green"),
    ("G", "select_preset('light-green')", "Light Green"),
    ("c", "select_preset('dark-cyan')", "Dark Cyan"),
    ("C", "select_preset('light-cyan')", "Light Cyan"),
    ("b", "select_preset('dark-blue')", "Dark Blue"),
    ("B", "select_preset('light-blue')", "Light Blue"),
    ("p", "select_preset('dark-purple')", "Dark Purple"),
    ("P", "select_preset('light-purple')", "Light Purple"),
    ("k", "select_preset('dark-pink')", "Dark Pink"),
    ("K", "select_preset('light-pink')", "Light Pink"),
]
```

### Layout (compose method)

```
Vertical #color-dialog
├── Static (title: "Fuel Bed Color" or "Overhead Color", showing current RGBW)
├── Static ("Dark Presets:")
├── Horizontal #dark-presets
│   └── 7 Buttons: "[R] Red", "[Y] Yellow", "[G] Green", "[C] Cyan", "[B] Blue", "[P] Purple", "[K] Pink"
├── Static ("Light Presets (Shift+letter):")
├── Horizontal #light-presets
│   └── 7 Buttons: "[R] Red", "[Y] Yellow", "[G] Green", "[C] Cyan", "[B] Blue", "[P] Purple", "[K] Pink"
├── Static ("Custom RGBW:")
├── Horizontal #rgbw-inputs
│   └── 4 Input widgets: R, G, B, W (each with placeholder="0-255")
└── Horizontal #rgbw-actions
    └── Button "Set" (id="set-rgbw")
```

### Button IDs and handling

Preset buttons use `id=f"preset-{name}"` where `name` matches a NAMED_COLORS key (e.g., `preset-dark-red`, `preset-light-blue`).

**on_button_pressed**:
- If button ID starts with `preset-`: look up the name in `NAMED_COLORS` and dismiss with that `RGBWColor`.
- If button ID is `set-rgbw`: read the 4 Input values, validate, and dismiss.

### action_select_preset(preset_name: str)

```python
def action_select_preset(self, preset_name: str) -> None:
    from flameconnect.models import NAMED_COLORS
    color = NAMED_COLORS.get(preset_name)
    if color is not None:
        self.dismiss(color)
```

### RGBW Input validation

When "Set" is pressed:
1. Read values from the 4 Input widgets (query by ID: `#input-r`, `#input-g`, `#input-b`, `#input-w`)
2. Try to convert each to `int`
3. Validate all are in 0-255 range
4. If valid: `self.dismiss(RGBWColor(red=r, green=g, blue=b, white=w))`
5. If invalid: `self.notify("RGBW values must be integers 0-255", severity="error")`

### Input widgets

Use Textual's `Input` widget:
```python
from textual.widgets import Input

Input(value=str(self._current.red), id="input-r", placeholder="0-255", type="integer")
```

Note: `type="integer"` restricts Input to numeric characters. Pre-populate with current values.

Each Input should have a label. Use a pattern like:
```python
with Horizontal(id="rgbw-inputs"):
    yield Static("R:")
    yield Input(value=str(self._current.red), id="input-r", type="integer")
    yield Static("G:")
    yield Input(value=str(self._current.green), id="input-g", type="integer")
    # ... B, W similarly
```

### CSS

```css
ColorScreen {
    align: center middle;
}
#color-dialog {
    width: 70;
    height: auto;
    padding: 1 2;
    border: thick $primary;
    background: $surface;
}
#color-title {
    text-align: center;
    text-style: bold;
    margin-bottom: 1;
}
#dark-presets Button, #light-presets Button {
    margin: 0 1;
    min-width: 10;
}
#rgbw-inputs Input {
    width: 8;
    margin: 0 1;
}
```

### Important: Keyboard shortcut note

When Input widgets are focused, letter keybindings won't fire because Input captures keypresses. This is acceptable — users will use the keyboard shortcuts when no Input is focused (e.g., when the dialog first opens). The `stop=True` parameter is NOT needed on Input; Textual handles this naturally.

### Type annotations

Use `from __future__ import annotations`, guard `ComposeResult` behind `TYPE_CHECKING`. The class is `ModalScreen[RGBWColor | None]`.

</details>
