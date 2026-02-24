---
id: 2
group: "tui-dialogs"
dependencies: []
status: "completed"
created: "2026-02-23"
skills:
  - python
  - textual
---
# Create FlameColorScreen and MediaThemeScreen Modal Dialogs

## Objective
Create two new Textual modal dialog screens: `FlameColorScreen` for selecting from 7 flame colour presets, and `MediaThemeScreen` for selecting from 9 media theme presets with unique single-letter keyboard shortcuts.

## Skills Required
- Python: ModalScreen pattern, type-safe generics
- Textual: Containers, Buttons, Static widgets, CSS styling, key bindings

## Acceptance Criteria
- [ ] `FlameColorScreen` is a `ModalScreen[FlameColor | None]` with 7 buttons and letter shortcuts
- [ ] `MediaThemeScreen` is a `ModalScreen[MediaTheme | None]` with 9 buttons and unique letter shortcuts
- [ ] Both dialogs highlight the current value with `variant="primary"`
- [ ] Escape cancels (dismisses `None`) in both dialogs
- [ ] Button click and keyboard shortcut both dismiss with the selected value
- [ ] `ruff check` and `mypy --strict` pass on both new files

## Technical Requirements
- Textual `ModalScreen`, `Button`, `Static`, `Horizontal`, `Vertical` containers
- `FlameColor` and `MediaTheme` enums from `flameconnect.models`
- Follow the `FlameSpeedScreen` pattern exactly (see `src/flameconnect/tui/flame_speed_screen.py`)

## Input Dependencies
None — uses existing enums from `models.py`.

## Output Artifacts
- New file: `src/flameconnect/tui/flame_color_screen.py`
- New file: `src/flameconnect/tui/media_theme_screen.py`

## Implementation Notes

<details>
<summary>Detailed implementation guidance</summary>

### FlameColorScreen (`src/flameconnect/tui/flame_color_screen.py`)

Follow `flame_speed_screen.py` structure exactly. Key differences:

**Class**: `FlameColorScreen(ModalScreen[FlameColor | None])`

**Constructor**: `__init__(self, current_color: FlameColor, name: str | None = None)`

**BINDINGS**:
```python
BINDINGS = [
    ("escape", "cancel", "Cancel"),
    ("a", "select_color('ALL')", "All"),
    ("y", "select_color('YELLOW_RED')", "Yellow/Red"),
    ("w", "select_color('YELLOW_BLUE')", "Yellow/Blue"),
    ("b", "select_color('BLUE')", "Blue"),
    ("r", "select_color('RED')", "Red"),
    ("e", "select_color('YELLOW')", "Yellow"),
    ("d", "select_color('BLUE_RED')", "Blue/Red"),
]
```

**Compose**: Vertical container with title Static showing `f"Flame Color (current: {display_name})"` and a Horizontal row of 7 Buttons. Each button gets `variant="primary"` if it matches `current_color`.

**Button labels**: Use display-friendly names: "All", "Yellow/Red", "Yellow/Blue", "Blue", "Red", "Yellow", "Blue/Red". Include shortcut letter in brackets: `"[A] All"`, `"[Y] Yellow/Red"`, etc.

**Button IDs**: `id=f"color-{flame_color.name.lower()}"` (e.g., `color-all`, `color-blue`)

**on_button_pressed**: Parse the button ID to find the FlameColor enum member and dismiss with it.

**action_select_color(color_name: str)**: Look up `FlameColor[color_name]` and dismiss.

**action_cancel**: Dismiss `None`.

**CSS**: Adapt from `FlameSpeedScreen` CSS. Use `#flame-color-dialog` and `#flame-color-buttons` IDs. Increase dialog width to ~60 to fit 7 buttons.

**Display name helper**: Map `FlameColor` values to display strings. Can use a module-level dict or the enum `.name` with formatting.

### MediaThemeScreen (`src/flameconnect/tui/media_theme_screen.py`)

Same pattern, different content.

**Class**: `MediaThemeScreen(ModalScreen[MediaTheme | None])`

**Constructor**: `__init__(self, current_theme: MediaTheme, name: str | None = None)`

**BINDINGS** — unique letter per theme:
```python
BINDINGS = [
    ("escape", "cancel", "Cancel"),
    ("u", "select_theme('USER_DEFINED')", "User Defined"),
    ("w", "select_theme('WHITE')", "White"),
    ("b", "select_theme('BLUE')", "Blue"),
    ("p", "select_theme('PURPLE')", "Purple"),
    ("r", "select_theme('RED')", "Red"),
    ("g", "select_theme('GREEN')", "Green"),
    ("i", "select_theme('PRISM')", "Prism"),
    ("k", "select_theme('KALEIDOSCOPE')", "Kaleidoscope"),
    ("m", "select_theme('MIDNIGHT')", "Midnight"),
]
```

**Button labels** with shortcut letter: `"[U] User Defined"`, `"[W] White"`, `"[B] Blue"`, `"[P] Purple"`, `"[R] Red"`, `"[G] Green"`, `"[I] Prism"`, `"[K] Kaleidoscope"`, `"[M] Midnight"`.

**Layout**: Since there are 9 buttons, consider wrapping to two rows (e.g., 5+4) using two `Horizontal` containers, or use a single `Horizontal` with smaller buttons and a wider dialog (~70).

**Button IDs**: `id=f"theme-{theme.name.lower()}"` (e.g., `theme-white`, `theme-prism`)

**on_button_pressed**: Parse `button_id.removeprefix("theme-").upper()` → `MediaTheme[name]` → dismiss.

**action_select_theme(theme_name: str)**: `MediaTheme[theme_name]` → dismiss.

**action_cancel**: Dismiss `None`.

**CSS**: Adapted from FlameSpeedScreen. `#media-theme-dialog`, `#media-theme-buttons`. Width ~70.

### Type checking notes

Both files must use `from __future__ import annotations` and guard `ComposeResult` behind `TYPE_CHECKING`.

Use the string form in BINDINGS action parameters (e.g., `"select_color('ALL')"`) so Textual's action dispatch calls the method with the string argument. The action method then converts the string to the enum: `FlameColor[color_name]`.

</details>
