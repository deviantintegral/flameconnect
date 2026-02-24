---
id: 3
group: "dialogs"
dependencies: [2]
status: "completed"
created: "2026-02-24"
skills:
  - python
  - textual
---
# Add heat mode selection dialog, fireplace switcher dialog, and CLI heat-mode update

## Objective
Create two new modal dialog screens (HeatModeScreen and FireSelectScreen), replace the broken heat mode cycling in `app.py` with a dialog-based approach, add a fireplace switcher keybinding, and update the CLI `_set_heat_mode` to support `boost:<minutes>` syntax.

## Skills Required
- Python (Textual ModalScreen, Input widget, argparse, dataclasses.replace)
- Textual (Button, Input, ModalScreen dismiss/callback pattern)

## Acceptance Criteria
- [ ] `heat_mode_screen.py` created: `HeatModeScreen(ModalScreen)` with Normal/Eco/Boost buttons, boost duration Input (1-20 min), keyboard shortcuts n/e/b/escape
- [ ] `fire_select_screen.py` created: `FireSelectScreen(ModalScreen)` listing all fires with name/brand/model/connection, number key shortcuts, escape to cancel
- [ ] `action_cycle_heat_mode` replaced by `action_set_heat_mode` + `_apply_heat_mode` in `app.py`
- [ ] `_apply_heat_mode` uses `replace(current, heat_mode=mode, boost_duration=minutes)` for Boost, `replace(current, heat_mode=mode)` for Normal/Eco
- [ ] BINDINGS entry for `h` updated to `set_heat_mode`
- [ ] `action_switch_fire` added with `w` keybinding (show=False), re-fetches fire list, opens FireSelectScreen
- [ ] Fire switch callback: pops DashboardScreen, updates `self.fire_id`, pushes new dashboard
- [ ] Single-fire guard: notifies "Only one fireplace available" without opening dialog
- [ ] CLI `_set_heat_mode`: `fan-only` removed from `_HEAT_MODE_LOOKUP`; `boost:15` syntax parsed; validation 1 ≤ duration ≤ 20
- [ ] `uv run ruff check` passes on all modified/new files
- [ ] `uv run mypy --strict` passes on all modified/new files

Use your internal Todo tool to track these and keep on track.

## Technical Requirements
- Follow the `FlameSpeedScreen` pattern (in `flame_speed_screen.py`) for both modal dialogs
- `HeatModeScreen` result type: `tuple[HeatMode, int | None] | None` — (mode, boost_minutes) or None on cancel
- `FireSelectScreen` result type: `Fire | None` — selected Fire or None on cancel/same-fire
- Both screens need CSS strings for dialog styling (centered modal, bordered container)
- `_display_name()` from widgets should be used for mode labels in log messages
- CLI `_set_heat_mode` must handle: `normal`, `eco`, `boost:N` where N is 1-20

## Input Dependencies
- Task 02 must be complete: BINDINGS already using Binding class with show=False, DashboardScreen accepts Fire object, _push_dashboard passes Fire, _display_name imported in app.py

## Output Artifacts
- New file: `src/flameconnect/tui/heat_mode_screen.py`
- New file: `src/flameconnect/tui/fire_select_screen.py`
- Updated `src/flameconnect/tui/app.py` (new actions, updated BINDINGS)
- Updated `src/flameconnect/cli.py` (heat-mode syntax)

## Implementation Notes

<details>
<summary>Detailed implementation guidance</summary>

### heat_mode_screen.py
Follow `flame_speed_screen.py` closely. Key differences:
- Three buttons instead of five: Normal, Eco, Boost
- Boost button shows/focuses an `Input` widget for duration
- Constructor: `def __init__(self, current_mode: HeatMode, current_boost: int, name=None)`
- BINDINGS: `("n", "select_mode('normal')", "Normal")`, `("e", "select_mode('eco')", "Eco")`, `("b", "select_boost", "Boost")`, `("escape", "cancel", "Cancel")`
- When Normal/Eco is selected, dismiss with `(HeatMode.NORMAL, None)` or `(HeatMode.ECO, None)`
- When Boost is selected, show the duration Input. On Enter/Confirm, validate 1-20 and dismiss with `(HeatMode.BOOST, duration)`
- If user presses n/e while duration input is visible, dismiss immediately with that mode
- CSS: center the dialog, ~45 chars wide, auto height

### fire_select_screen.py
- Constructor: `def __init__(self, fires: list[Fire], current_fire_id: str, name=None)`
- Layout: title + vertical list of buttons, one per fire
- Button label: `f"{fire.friendly_name} — {fire.brand} {fire.product_model} ({connection_state})"`
- Currently selected fire uses `variant="primary"`
- Number keys 1-9 for quick selection
- Dismiss with `Fire` object or `None` (cancel or same fire selected)

### app.py Changes
Replace `action_cycle_heat_mode` (lines 768-801) with:
```python
async def action_set_heat_mode(self) -> None:
    from flameconnect.models import HeatParam
    from flameconnect.tui.heat_mode_screen import HeatModeScreen
    screen = self.screen
    if not isinstance(screen, DashboardScreen):
        return
    params = screen.current_parameters
    current = params.get(HeatParam)
    if not isinstance(current, HeatParam):
        return
    def _on_selected(result):
        if result is not None:
            mode, boost_minutes = result
            self.run_worker(self._apply_heat_mode(mode, boost_minutes), ...)
    self.push_screen(HeatModeScreen(current.heat_mode, current.boost_duration), callback=_on_selected)
```

Add `action_switch_fire`:
```python
async def action_switch_fire(self) -> None:
    from flameconnect.tui.fire_select_screen import FireSelectScreen
    try:
        self.fires = await self.client.get_fires()
    except Exception:
        ...
    if len(self.fires) <= 1:
        self.notify("Only one fireplace available")
        return
    def _on_selected(fire):
        if fire is not None:
            self.pop_screen()
            self.fire_id = fire.fire_id
            self._push_dashboard(fire)
    self.push_screen(FireSelectScreen(self.fires, self.fire_id), callback=_on_selected)
```

Add to BINDINGS:
```python
Binding("w", "switch_fire", "Switch Fire", show=False),
```

### CLI Changes
In `cli.py`, update `_HEAT_MODE_LOOKUP` — remove `"fan-only"` entry. Update `_set_heat_mode`:
```python
async def _set_heat_mode(client, fire_id, value):
    if value.startswith("boost:"):
        try:
            minutes = int(value.split(":")[1])
        except (ValueError, IndexError):
            print("Error: boost format is boost:<minutes> (e.g., boost:15)")
            sys.exit(1)
        if not 1 <= minutes <= 20:
            print("Error: boost duration must be 1-20 minutes.")
            sys.exit(1)
        heat_mode = HeatMode.BOOST
        # ... replace(current, heat_mode=heat_mode, boost_duration=minutes)
    elif value in _HEAT_MODE_LOOKUP:
        heat_mode = _HEAT_MODE_LOOKUP[value]
        # ... replace(current, heat_mode=heat_mode)
    else:
        valid = ", ".join([*_HEAT_MODE_LOOKUP, "boost:<minutes>"])
        print(f"Error: heat-mode must be one of: {valid}.")
        sys.exit(1)
```

</details>
