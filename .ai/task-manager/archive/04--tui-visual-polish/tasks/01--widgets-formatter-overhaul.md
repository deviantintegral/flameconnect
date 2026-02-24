---
id: 1
group: "display-fixes"
dependencies: []
status: "completed"
created: "2026-02-24"
skills:
  - python
  - textual
---
# Overhaul widgets.py: formatters, display name helper, case standardisation, ASCII art, and FireplaceInfo deletion

## Objective
Fix all display-related issues in `widgets.py`: the boost duration bug, inconsistent enum casing, broken ASCII art, and remove the now-unnecessary `FireplaceInfo` widget class. Add and export a `_display_name()` helper for Title Case conversion.

## Skills Required
- Python (enum handling, string formatting, Rich markup)
- Textual (Static widget, CSS, reactive properties)

## Acceptance Criteria
- [ ] `_format_heat()` shows "Off" for boost when `heat_mode != HeatMode.BOOST`, duration only when active
- [ ] `_display_name(enum_value)` helper function exists and is exported (added to import surface)
- [ ] All 15 `.name` references in widgets.py replaced with `_display_name()` calls
- [ ] `_format_connection_state()` uses `_display_name()` before colour markup wrapping
- [ ] `_BRIGHTNESS_NAMES` and `_PULSATING_NAMES` lookup dicts removed (replaced by `_display_name()`)
- [ ] `_MODE_DISPLAY` dict retained (MANUAL → "On" override)
- [ ] `FireplaceInfo` widget class deleted and removed from exports/imports
- [ ] `FireplaceVisual.render()` returns a larger (~40-50 chars wide, ~16-20 lines tall) fireplace design
- [ ] ASCII art uses Rich markup for colour (red/yellow/orange flames, dim grey surround)
- [ ] `#fireplace-visual` CSS updated with `content-align: center middle;`
- [ ] `uv run ruff check src/flameconnect/tui/widgets.py` passes
- [ ] `uv run mypy --strict src/flameconnect/tui/widgets.py` passes

Use your internal Todo tool to track these and keep on track.

## Technical Requirements
- Import `HeatMode` from `flameconnect.models` inside `_format_heat()` body (lazy import pattern used elsewhere)
- `_display_name()` signature: `def _display_name(value: enum.IntEnum) -> str` — uses `value.name.replace("_", " ").title()`
- Export `_display_name` alongside other public names so `app.py` can import it
- `FireplaceVisual` inherits from `Static`; its `render()` returns a Rich-markup string
- `_DASHBOARD_CSS` in `screens.py` has the `#fireplace-visual` CSS selector — update it there (coordinate: the CSS string lives in `screens.py`, not `widgets.py`)

## Input Dependencies
None — this is a foundational task.

## Output Artifacts
- Updated `widgets.py` with all formatter fixes, `_display_name()` exported, `FireplaceInfo` deleted, improved `FireplaceVisual`
- Updated `#fireplace-visual` CSS in `screens.py` `_DASHBOARD_CSS` (only the `#fireplace-visual` selector — do NOT touch other selectors or layout)

## Implementation Notes

<details>
<summary>Detailed implementation guidance</summary>

### Boost Duration Bug Fix
In `_format_heat()` (line 72-79 of `widgets.py`), change the boost line from:
```
f"Boost: {param.boost_duration}min"
```
to a conditional that checks `param.heat_mode`:
```
f"Boost: {param.boost_duration}min" if param.heat_mode == HeatMode.BOOST else "Boost: Off"
```
Import `HeatMode` from `flameconnect.models` at the top of the function body (lazy import pattern).

### _display_name() Helper
Add a module-level function near the top of `widgets.py`:
```python
def _display_name(value: IntEnum) -> str:
    """Convert an enum member name to Title Case for display."""
    return value.name.replace("_", " ").title()
```
Import `IntEnum` from `enum`. Export `_display_name` by adding it to the imports surface used by `screens.py` and `app.py`. The function name starts with `_` but is still exported — this matches the existing `_format_connection_state` export pattern.

### Case Standardisation
Replace all 15 `.name` usages in formatter functions with `_display_name()` calls. The affected functions are:
- `_format_flame_effect()` — multiple `.name` references for FlameEffect, FlameColor, LightStatus, MediaTheme, MediaLight, OverheadLight, AmbientSensor, Brightness, Pulsating
- `_format_heat()` — `heat_status.name`, `heat_mode.name`
- `_format_heat_mode()` — `heat_control.name`
- `_format_timer()` — `timer_status.name`
- `_format_connection_state()` — `state.name` (convert BEFORE wrapping in Rich colour tags)

Remove `_BRIGHTNESS_NAMES` and `_PULSATING_NAMES` dicts. Keep `_MODE_DISPLAY` (it maps MANUAL → "On").

### FireplaceInfo Deletion
Delete the entire `FireplaceInfo` class (lines 254-271). Remove it from any `__all__` or export list. The import in `screens.py` will be handled by Task 02.

### ASCII Art
Replace `FireplaceVisual.render()` with a larger design (~40-50 chars wide, ~16-20 lines tall). Use Rich markup:
- `[red]` / `[yellow]` / `[bright_red]` for flames
- `[dim]` for stone/brick surround
- Include a mantel frame, firebox opening, flame shapes, and hearth/base

Update `#fireplace-visual` CSS in `_DASHBOARD_CSS` (in `screens.py`) — ONLY the `#fireplace-visual` selector:
```css
#fireplace-visual {
    width: 1fr;
    padding: 1 2;
    border: solid $primary;
    content-align: center middle;
}
```

</details>
