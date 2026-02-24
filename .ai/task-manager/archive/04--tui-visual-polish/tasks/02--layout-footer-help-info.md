---
id: 2
group: "layout-restructuring"
dependencies: [1]
status: "completed"
created: "2026-02-24"
skills:
  - python
  - textual
---
# Restructure layout, simplify footer, add help panel, and enhance fireplace info

## Objective
Move fireplace info from the top bordered section to the bottom status bar (with brand/model), replace the dense keybinding bar with Textual's native HelpPanel and command palette, simplify the Footer to show only essential bindings, update DashboardScreen to accept a full `Fire` object, and standardise `.name` usages in `app.py`.

## Skills Required
- Python (dataclass handling, Textual Binding class)
- Textual (HelpPanel, Footer, CSS layout, ModalScreen patterns)

## Acceptance Criteria
- [ ] `FireplaceInfo` import removed from `screens.py`; `yield FireplaceInfo(...)` removed from `compose()`
- [ ] `#fire-info` CSS styles removed from `_DASHBOARD_CSS`
- [ ] `DashboardScreen.__init__` accepts `fire: Fire` instead of `fire_id: str` + `fire_name: str`; derives `self.fire_id` and `self.fire_name` from it
- [ ] `_update_display()` writes info to `#status-bar`: `[bold]{name}[/bold] | {brand} {model} | {connection} | Updated: {time}` — omitting brand/model if empty
- [ ] `_push_dashboard()` in `app.py` passes full `Fire` object
- [ ] `?` keybinding added with custom `action_toggle_help()` that checks HelpPanel mount state
- [ ] `COMMAND_PALETTE_DISPLAY = "Palette"` set on `FlameConnectApp`
- [ ] `Binding` class imported from `textual.app`; all non-essential bindings use `Binding(..., show=False)`
- [ ] Footer shows only: Quit, Refresh, Help (+ Palette via COMMAND_PALETTE_DISPLAY)
- [ ] All 4 `.name` usages in `app.py` replaced with `_display_name()` from widgets
- [ ] `uv run ruff check src/flameconnect/tui/screens.py src/flameconnect/tui/app.py` passes
- [ ] `uv run mypy --strict src/flameconnect/tui/screens.py src/flameconnect/tui/app.py` passes

Use your internal Todo tool to track these and keep on track.

## Technical Requirements
- Import `Binding` from `textual.app` alongside existing `App` import
- Import `_display_name` from `flameconnect.tui.widgets`
- Import `Fire` from `flameconnect.models` (may need to add to TYPE_CHECKING block in screens.py)
- `HelpPanel` check: `self.query("HelpPanel")` or `self.app.query("HelpPanel")` to detect if mounted
- Textual's `action_show_help_panel()` and `action_hide_help_panel()` are built-in App methods

## Input Dependencies
- Task 01 must be complete: `_display_name()` exported from `widgets.py`, `FireplaceInfo` class deleted

## Output Artifacts
- Updated `screens.py` with new layout, DashboardScreen constructor, status bar format, CSS
- Updated `app.py` with Binding imports, show=False, help toggle, COMMAND_PALETTE_DISPLAY, _display_name usages, Fire-based _push_dashboard

## Implementation Notes

<details>
<summary>Detailed implementation guidance</summary>

### DashboardScreen Constructor Change
Replace:
```python
def __init__(self, client, fire_id: str, fire_name: str, name=None):
    self.fire_id = fire_id
    self.fire_name = fire_name
```
With:
```python
def __init__(self, client, fire: Fire, name=None):
    self._fire = fire
    self.fire_id = fire.fire_id
    self.fire_name = fire.friendly_name
```
Add `Fire` to the TYPE_CHECKING imports.

### Layout Changes in compose()
Remove `yield FireplaceInfo(id="fire-info")`. Remove the `FireplaceInfo` import. The `#status-bar` Static remains — it now shows fireplace info instead of keybindings.

### _update_display() Status Bar
Replace the keybinding text (lines 214-234) with:
```python
brand_model = f"{self._fire.brand} {self._fire.product_model}".strip()
parts = [f"[bold]{overview.fire.friendly_name}[/bold]"]
if brand_model:
    parts.append(brand_model)
parts.append(_format_connection_state(overview.fire.connection_state))
parts.append(f"[dim]Updated: {datetime.now().strftime('%H:%M:%S')}[/dim]")
status_bar.update(" | ".join(parts))
```
Remove the `fire_info = self.query_one("#fire-info", FireplaceInfo)` block and its property updates.

### CSS Updates
Remove the `#fire-info` block from `_DASHBOARD_CSS`:
```css
#fire-info {
    height: auto;
    padding: 1 2;
    border: solid $primary;
}
```

### Help Panel Toggle
```python
def action_toggle_help(self) -> None:
    if self.query("HelpPanel"):
        self.action_hide_help_panel()
    else:
        self.action_show_help_panel()
```

### Footer Simplification
Convert all BINDINGS entries to use `Binding` class. Keep `show=True` (default) for: `q` Quit, `r` Refresh, `?` Help. Set `show=False` for all others (p, e, f, b, g, c, m, l, d, o, v, s, a, h, t, u). Example:
```python
BINDINGS = [
    ("q", "quit", "Quit"),
    ("r", "refresh", "Refresh"),
    ("question_mark", "toggle_help", "Help"),
    Binding("p", "toggle_power", "Power On/Off", show=False),
    # ... all others with show=False
]
```

### app.py _display_name Usages
- Line 108: `f"{fire.friendly_name} ({_display_name(fire.connection_state)})"` in `_load_fires`
- Line 572: `label = _display_name(color)` in flame color action
- Line 633: `label = _display_name(theme)` in media theme action
- Line 794: This line is in `action_cycle_heat_mode` which will be replaced by Task 03 — but if it still exists at this point, update it too.

### _push_dashboard Update
```python
def _push_dashboard(self, fire: Fire) -> None:
    screen = DashboardScreen(client=self.client, fire=fire)
    self.push_screen(screen)
```

</details>
