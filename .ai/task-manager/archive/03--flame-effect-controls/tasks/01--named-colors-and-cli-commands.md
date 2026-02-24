---
id: 1
group: "cli"
dependencies: []
status: "completed"
created: "2026-02-23"
skills:
  - python
---
# Add NAMED_COLORS Lookup and Seven New CLI Set Commands

## Objective
Define the shared `NAMED_COLORS` dict in `models.py` and add seven new CLI `set` command handlers to `cli.py` for the remaining FlameEffectParam fields: `flame-effect`, `media-light`, `media-color`, `overhead-light`, `overhead-color`, `light-status`, and `ambient-sensor`.

## Skills Required
- Python: CLI handler functions, lookup dicts, dataclass manipulation with `dataclasses.replace()`

## Acceptance Criteria
- [ ] `NAMED_COLORS: dict[str, RGBWColor]` defined in `models.py` with 14 entries (7 dark + 7 light)
- [ ] Seven new handler functions in `cli.py` all follow the read-modify-write pattern
- [ ] `_SET_PARAM_NAMES` constant and argparse help text updated with all new parameter names
- [ ] `cmd_set()` dispatcher routes all 7 new parameter names to their handlers
- [ ] Colour commands accept both RGBW format (`255,0,0,0`) and named preset strings (`light-red`)
- [ ] Invalid values produce clear error messages and `sys.exit(1)`
- [ ] All quality gates pass: `ruff check`, `mypy --strict`, existing tests still pass

## Technical Requirements
- Python 3.13+, `dataclasses.replace()`, `FlameEffectParam` from `flameconnect.models`
- Existing `_find_param()` helper and `FlameConnectClient.write_parameters()` API

## Input Dependencies
None — builds on existing codebase.

## Output Artifacts
- Modified `src/flameconnect/models.py` with `NAMED_COLORS` dict
- Modified `src/flameconnect/cli.py` with 7 new handlers and updated dispatcher/help

## Implementation Notes

<details>
<summary>Detailed implementation guidance</summary>

### 1. NAMED_COLORS in models.py

Add after the `RGBWColor` dataclass definition (around line 142). This dict is the single source of truth for named colour presets, imported by both CLI and TUI.

```python
NAMED_COLORS: dict[str, RGBWColor] = {
    "dark-red": RGBWColor(red=180, green=0, blue=0, white=0),
    "light-red": RGBWColor(red=255, green=0, blue=0, white=80),
    "dark-yellow": RGBWColor(red=180, green=120, blue=0, white=0),
    "light-yellow": RGBWColor(red=255, green=200, blue=0, white=80),
    "dark-green": RGBWColor(red=0, green=180, blue=0, white=0),
    "light-green": RGBWColor(red=0, green=255, blue=0, white=80),
    "dark-cyan": RGBWColor(red=0, green=180, blue=180, white=0),
    "light-cyan": RGBWColor(red=0, green=255, blue=255, white=80),
    "dark-blue": RGBWColor(red=0, green=0, blue=180, white=0),
    "light-blue": RGBWColor(red=0, green=0, blue=255, white=80),
    "dark-purple": RGBWColor(red=128, green=0, blue=180, white=0),
    "light-purple": RGBWColor(red=180, green=0, blue=255, white=80),
    "dark-pink": RGBWColor(red=180, green=0, blue=80, white=0),
    "light-pink": RGBWColor(red=255, green=0, blue=128, white=80),
}
```

### 2. CLI handlers in cli.py

**Add import**: Add `NAMED_COLORS` to the imports from `flameconnect.models`.

**Update `_SET_PARAM_NAMES`** (line 129-132): Add the 7 new names:
```python
_SET_PARAM_NAMES = (
    "mode, flame-speed, brightness, pulsating, flame-color,"
    " media-theme, heat-mode, heat-temp, timer, temp-unit,"
    " flame-effect, media-light, media-color, overhead-light,"
    " overhead-color, light-status, ambient-sensor"
)
```

**Update argparse help** in `build_parser()` (around line 647) to match `_SET_PARAM_NAMES`.

**Update `cmd_set()`** (lines 379-418): Add 7 new `if param == "..." return` blocks before the "unknown parameter" error at the end.

**Five simple on/off handlers** — follow the exact pattern of `_set_pulsating()` (lines 478-494):

- `_set_flame_effect(client, fire_id, value)`: Validates "on"/"off", maps to `FlameEffect.ON`/`FlameEffect.OFF`, read-modify-write with `replace(current, flame_effect=...)`.
- `_set_media_light(client, fire_id, value)`: Validates "on"/"off", maps to `LightStatus.ON`/`LightStatus.OFF`, field is `media_light`.
- `_set_overhead_light(client, fire_id, value)`: Same pattern, field is `overhead_light`.
- `_set_light_status(client, fire_id, value)`: Same pattern, field is `light_status`.
- `_set_ambient_sensor(client, fire_id, value)`: Same pattern, field is `ambient_sensor`.

Each follows this exact template:
```python
async def _set_flame_effect(
    client: FlameConnectClient, fire_id: str, value: str
) -> None:
    """Set flame effect on or off."""
    lookup = {"on": FlameEffect.ON, "off": FlameEffect.OFF}
    if value not in lookup:
        print("Error: flame-effect must be 'on' or 'off'.")
        sys.exit(1)
    effect = lookup[value]
    overview = await client.get_fire_overview(fire_id)
    current = _find_param(overview.parameters, FlameEffectParam)
    if current is None:
        print("Error: no FlameEffect parameter found.")
        sys.exit(1)
    new_param = replace(current, flame_effect=effect)
    await client.write_parameters(fire_id, [new_param])
    print(f"Flame effect set to {value}.")
```

**Two colour handlers** — these are more complex because they accept both RGBW and named presets:

- `_set_media_color(client, fire_id, value)`: Parse value as either `R,G,B,W` ints or a named preset key from `NAMED_COLORS`. Field is `media_color`.
- `_set_overhead_color(client, fire_id, value)`: Identical pattern, field is `overhead_color`.

Colour parsing logic:
```python
async def _set_media_color(
    client: FlameConnectClient, fire_id: str, value: str
) -> None:
    """Set media (fuel bed) color via RGBW values or named preset."""
    color = _parse_color(value)
    if color is None:
        named = ", ".join(NAMED_COLORS)
        print(f"Error: media-color must be R,G,B,W (0-255) or one of: {named}.")
        sys.exit(1)
    overview = await client.get_fire_overview(fire_id)
    current = _find_param(overview.parameters, FlameEffectParam)
    if current is None:
        print("Error: no FlameEffect parameter found.")
        sys.exit(1)
    new_param = replace(current, media_color=color)
    await client.write_parameters(fire_id, [new_param])
    print(f"Media color set to {value}.")
```

Add a shared `_parse_color()` helper:
```python
def _parse_color(value: str) -> RGBWColor | None:
    """Parse a color value as either R,G,B,W integers or a named preset."""
    if value in NAMED_COLORS:
        return NAMED_COLORS[value]
    parts = value.split(",")
    if len(parts) == 4:
        try:
            r, g, b, w = (int(p) for p in parts)
        except ValueError:
            return None
        if all(0 <= v <= 255 for v in (r, g, b, w)):
            return RGBWColor(red=r, green=g, blue=b, white=w)
    return None
```

**Add `_find_param` overload** for `FlameEffectParam` if not already present (it already exists at lines 151-153).

### 3. Ensure imports are added

Add to the import block at the top of `cli.py`:
- `FlameEffect` (for flame-effect handler)
- `NAMED_COLORS` (for colour handlers)
- `LightStatus` is already imported — verify

`LightStatus` is NOT currently imported in `cli.py`. It is used in display names (`_LIGHT_STATUS_NAMES`) but the display code uses `int` keys, not the enum. You will need to add `LightStatus` and `FlameEffect` to the imports from `flameconnect.models`.

</details>
