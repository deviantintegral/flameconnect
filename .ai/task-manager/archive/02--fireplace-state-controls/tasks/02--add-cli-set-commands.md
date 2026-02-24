---
id: 2
group: "fireplace-state-controls"
dependencies: [1]
status: "completed"
created: 2026-02-23
skills:
  - "python"
  - "cli-argparse"
---
# Add Missing CLI Set Sub-Parameters

## Objective
Add CLI `set` support for pulsating, flame-color, media-theme, and temp-unit parameters so users can control all requested fireplace settings from the command line.

## Skills Required
- Python argparse CLI patterns
- FlameConnect parameter dataclasses and enums

## Acceptance Criteria
- [ ] `flameconnect set <fire_id> pulsating on|off` works — writes FlameEffectParam with updated pulsating_effect field
- [ ] `flameconnect set <fire_id> flame-color <color>` works — accepts: all, yellow-red, yellow-blue, blue, red, yellow, blue-red
- [ ] `flameconnect set <fire_id> media-theme <theme>` works — accepts: user-defined, white, blue, purple, red, green, prism, kaleidoscope, midnight
- [ ] `flameconnect set <fire_id> temp-unit fahrenheit|celsius` works — writes TempUnitParam
- [ ] Invalid values produce clear error messages and `sys.exit(1)`
- [ ] `_SET_PARAM_NAMES` constant updated with all valid parameter names
- [ ] `build_parser` help text updated
- [ ] `uv run ruff check` and `uv run mypy --strict src/` pass

Use your internal Todo tool to track these and keep on track.

## Technical Requirements
- New handler functions in `cli.py`: `_set_pulsating`, `_set_flame_color`, `_set_media_theme`, `_set_temp_unit`
- Each FlameEffectParam handler uses read-modify-write pattern: fetch current state via `get_fire_overview`, use `dataclasses.replace()` to change target field, call `write_parameters`
- `_set_temp_unit` creates a fresh `TempUnitParam` directly (single-field param, no read needed)
- Lookup dicts needed:
  - `_PULSATING_LOOKUP`: `{"on": PulsatingEffect.ON, "off": PulsatingEffect.OFF}`
  - `_FLAME_COLOR_LOOKUP`: maps CLI strings to `FlameColor` enum values
  - `_MEDIA_THEME_LOOKUP`: maps CLI strings to `MediaTheme` enum values
  - `_TEMP_UNIT_LOOKUP`: `{"fahrenheit": TempUnit.FAHRENHEIT, "celsius": TempUnit.CELSIUS}`
- Add new imports: `PulsatingEffect`, `FlameColor`, `MediaTheme`, `TempUnit` from models
- Wire into `cmd_set()` dispatch with new `if param == "..."` branches

## Input Dependencies
- Task 01 (refactor) must be complete so new handlers follow the `dataclasses.replace()` pattern

## Output Artifacts
- Updated `src/flameconnect/cli.py` with 4 new set handlers and updated help text

## Implementation Notes
- Follow the existing pattern of `_set_brightness` (after Task 01 refactor) as the template
- The `_find_param` function with overloads is available for type-safe parameter lookup — add overloads for any new param types used if needed
- FlameColor and MediaTheme enum values are already defined in `models.py`
