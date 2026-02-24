---
id: 4
group: "tui-actions"
dependencies: [2, 3]
status: "completed"
created: "2026-02-23"
skills:
  - python
  - textual
complexity_score: 4
complexity_notes: "Many methods but all follow established patterns; toggle methods are near-identical"
---
# Add Ten New TUI Keybindings and Action Methods

## Objective
Add 10 new keybindings to `FlameConnectApp` (6 toggles + 4 dialog openers) and their corresponding action methods, plus update the status bar in `DashboardScreen` to show the new bindings.

## Skills Required
- Python: async methods, dataclasses.replace(), read-modify-write pattern
- Textual: App BINDINGS, push_screen, run_worker, ModalScreen callbacks

## Acceptance Criteria
- [ ] 10 new entries in `FlameConnectApp.BINDINGS` list (e, g, c, m, l, d, o, v, s, a)
- [ ] 6 toggle action methods: flame effect, pulsating, media light, overhead light, light status, ambient sensor
- [ ] 4 dialog action methods + apply methods: flame color, media theme, media color, overhead color
- [ ] All toggle methods follow the `action_toggle_brightness` pattern (write guard, read-modify-write, refresh)
- [ ] All dialog methods follow the `action_set_flame_speed` / `_apply_flame_speed` pattern
- [ ] Status bar in `DashboardScreen._update_display()` updated with new keybindings
- [ ] `ruff check` and `mypy --strict` pass

## Technical Requirements
- Existing `FlameConnectApp` class in `src/flameconnect/tui/app.py`
- Existing `DashboardScreen` in `src/flameconnect/tui/screens.py`
- `FlameColorScreen`, `MediaThemeScreen`, `ColorScreen` from tasks 2 and 3
- `FlameEffectParam`, `FlameEffect`, `FlameColor`, `MediaTheme`, `LightStatus`, `PulsatingEffect`, `RGBWColor` from `models.py`

## Input Dependencies
- Task 2: `FlameColorScreen` and `MediaThemeScreen` must exist
- Task 3: `ColorScreen` must exist

## Output Artifacts
- Modified `src/flameconnect/tui/app.py` (BINDINGS + action methods)
- Modified `src/flameconnect/tui/screens.py` (status bar text)

## Implementation Notes

<details>
<summary>Detailed implementation guidance</summary>

### 1. BINDINGS list update in `app.py`

Add these 10 entries to the existing `BINDINGS` list (lines 43-52):

```python
BINDINGS = [
    ("q", "quit", "Quit"),
    ("r", "refresh", "Refresh"),
    ("p", "toggle_power", "Power On/Off"),
    ("e", "toggle_flame_effect", "Flame Effect"),
    ("f", "set_flame_speed", "Flame Speed"),
    ("b", "toggle_brightness", "Brightness"),
    ("g", "toggle_pulsating", "Pulsating"),
    ("c", "set_flame_color", "Flame Color"),
    ("m", "set_media_theme", "Media Theme"),
    ("l", "toggle_media_light", "Media Light"),
    ("d", "set_media_color", "Media Color"),
    ("o", "toggle_overhead_light", "Overhead Light"),
    ("v", "set_overhead_color", "Overhead Color"),
    ("s", "toggle_light_status", "Light Status"),
    ("a", "toggle_ambient_sensor", "Ambient Sensor"),
    ("h", "cycle_heat_mode", "Heat Mode"),
    ("t", "toggle_timer", "Timer"),
    ("u", "toggle_temp_unit", "Temp Unit"),
]
```

### 2. Six toggle action methods

Each follows the exact same pattern as `action_toggle_brightness` (lines 256-288). The template is:

```python
async def action_toggle_flame_effect(self) -> None:
    """Handle the 'e' key binding to toggle flame effect on/off."""
    from flameconnect.models import FlameEffect, FlameEffectParam

    screen = self.screen
    if not isinstance(screen, DashboardScreen):
        return
    if self.fire_id is None:
        return
    if self._write_in_progress:
        return

    self._write_in_progress = True
    try:
        params = screen.current_parameters
        current = params.get(FlameEffectParam)
        if not isinstance(current, FlameEffectParam):
            return
        new_val = (
            FlameEffect.OFF
            if current.flame_effect == FlameEffect.ON
            else FlameEffect.ON
        )
        new_param = replace(current, flame_effect=new_val)
        await self.client.write_parameters(self.fire_id, [new_param])
        label = "On" if new_val == FlameEffect.ON else "Off"
        screen.log_message(f"Flame effect set to {label}")
        await screen.refresh_state()
    except Exception as exc:
        _LOGGER.exception("Failed to toggle flame effect")
        screen.log_message(f"Flame effect toggle failed: {exc}", level=logging.ERROR)
    finally:
        self._write_in_progress = False
```

Repeat for:
- `action_toggle_pulsating`: Toggle `pulsating_effect` between `PulsatingEffect.ON`/`OFF`, label "On"/"Off"
- `action_toggle_media_light`: Toggle `media_light` between `LightStatus.ON`/`OFF`, label "On"/"Off"
- `action_toggle_overhead_light`: Toggle `overhead_light` between `LightStatus.ON`/`OFF`, label "On"/"Off"
- `action_toggle_light_status`: Toggle `light_status` between `LightStatus.ON`/`OFF`, label "On"/"Off"
- `action_toggle_ambient_sensor`: Toggle `ambient_sensor` between `LightStatus.ON`/`OFF`, label "On"/"Off"

### 3. Two simple dialog action methods (FlameColor, MediaTheme)

Follow the `action_set_flame_speed` / `_apply_flame_speed` pattern exactly (lines 196-254).

**action_set_flame_color**:
```python
async def action_set_flame_color(self) -> None:
    """Handle the 'c' key binding to open flame color dialog."""
    from flameconnect.models import FlameColor, FlameEffectParam
    from flameconnect.tui.flame_color_screen import FlameColorScreen

    screen = self.screen
    if not isinstance(screen, DashboardScreen):
        return
    if self.fire_id is None:
        return

    params = screen.current_parameters
    current = params.get(FlameEffectParam)
    if not isinstance(current, FlameEffectParam):
        return

    current_color = current.flame_color

    def _on_color_selected(color: FlameColor | None) -> None:
        if color is not None and color != current_color:
            self.run_worker(
                self._apply_flame_color(color),
                exclusive=True,
                thread=False,
            )

    self.push_screen(
        FlameColorScreen(current_color), callback=_on_color_selected
    )
```

**_apply_flame_color**:
```python
async def _apply_flame_color(self, color: FlameColor) -> None:
    """Write the selected flame color to the fireplace."""
    from flameconnect.models import FlameEffectParam

    screen = self.screen
    if not isinstance(screen, DashboardScreen):
        return
    if self.fire_id is None:
        return
    if self._write_in_progress:
        return

    self._write_in_progress = True
    try:
        params = screen.current_parameters
        current = params.get(FlameEffectParam)
        if not isinstance(current, FlameEffectParam):
            return
        new_param = replace(current, flame_color=color)
        await self.client.write_parameters(self.fire_id, [new_param])
        label = color.name.replace("_", " ").title()
        screen.log_message(f"Flame color set to {label}")
        await screen.refresh_state()
    except Exception as exc:
        _LOGGER.exception("Failed to set flame color")
        screen.log_message(f"Flame color change failed: {exc}", level=logging.ERROR)
    finally:
        self._write_in_progress = False
```

**action_set_media_theme / _apply_media_theme**: Same pattern using `MediaThemeScreen` and `media_theme` field.

### 4. Two colour dialog action methods (MediaColor, OverheadColor)

Follow the same dialog pattern but use `ColorScreen`:

**action_set_media_color**:
```python
async def action_set_media_color(self) -> None:
    """Handle the 'd' key binding to open media color dialog."""
    from flameconnect.models import FlameEffectParam, RGBWColor
    from flameconnect.tui.color_screen import ColorScreen

    screen = self.screen
    if not isinstance(screen, DashboardScreen):
        return
    if self.fire_id is None:
        return

    params = screen.current_parameters
    current = params.get(FlameEffectParam)
    if not isinstance(current, FlameEffectParam):
        return

    def _on_color_selected(color: RGBWColor | None) -> None:
        if color is not None:
            self.run_worker(
                self._apply_media_color(color),
                exclusive=True,
                thread=False,
            )

    self.push_screen(
        ColorScreen(current.media_color, "Fuel Bed Color"),
        callback=_on_color_selected,
    )
```

**_apply_media_color**: Same as `_apply_flame_color` but writes `media_color` field.

**action_set_overhead_color / _apply_overhead_color**: Same pattern with `overhead_color` field and title `"Overhead Color"`.

### 5. Status bar update in `screens.py`

In `DashboardScreen._update_display()` (line 214-224), update the status bar text. With 18 keybindings, show a condensed format:

```python
status_bar.update(
    "[dim][bold]r[/bold]efresh | "
    "[bold]p[/bold]ower | "
    "[bold]e[/bold]ffect | "
    "[bold]f[/bold]lame spd | "
    "[bold]b[/bold]right | "
    "pulsatin[bold]g[/bold] | "
    "[bold]c[/bold]olor | "
    "the[bold]m[/bold]e | "
    "media [bold]l[/bold]ight | "
    "me[bold]d[/bold]ia clr | "
    "[bold]o[/bold]verhead | "
    "o[bold]v[/bold]hd clr | "
    "light [bold]s[/bold]tat | "
    "[bold]a[/bold]mbient | "
    "[bold]h[/bold]eat | "
    "[bold]t[/bold]imer | "
    "temp [bold]u[/bold]nit | "
    "[bold]q[/bold]uit[/dim]"
)
```

If this is too long, simplify further or rely on the Textual `Footer` widget which already renders `BINDINGS`.

### 6. Import notes

All action methods use deferred imports (inside the method body) following the existing pattern in `app.py`. This avoids circular imports and keeps the import block clean.

The `logging` module is already imported at the top of `app.py`. The `replace` function is already imported from `dataclasses`.

</details>
