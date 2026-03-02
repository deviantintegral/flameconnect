---
id: 3
group: "dynamic-typing-hardening"
dependencies: [2]
status: "completed"
created: 2026-03-01
skills:
  - "python-typing"
  - "refactoring"
---
# Auto-Generate String-to-Enum Lookups in CLI

## Objective
Replace the 5 hand-maintained `dict[str, EnumType]` lookup tables in `cli.py` with auto-generated equivalents using `kebab_name()` from `models.py`.

## Skills Required
Python IntEnum, dict comprehensions, refactoring.

## Acceptance Criteria
- [ ] All 5 lookup dicts replaced with `kebab_name()`-based generation
- [ ] `_HEAT_MODE_LOOKUP` uses explicit member list (NORMAL, BOOST, ECO only)
- [ ] `_PULSATING_LOOKUP`, `_FLAME_COLOR_LOOKUP`, `_MEDIA_THEME_LOOKUP`, `_TEMP_UNIT_LOOKUP` are fully auto-generated
- [ ] CLI behavior is identical (same valid string values accepted, same errors on invalid)
- [ ] `uv run ruff check .` passes
- [ ] `uv run mypy src/` passes
- [ ] `uv run pytest` passes

## Technical Requirements

In `src/flameconnect/cli.py`, replace each lookup dict:

1. `_HEAT_MODE_LOOKUP` → `{kebab_name(m): m for m in (HeatMode.NORMAL, HeatMode.BOOST, HeatMode.ECO)}`
   - Must NOT include `FAN_ONLY` or `SCHEDULE`

2. `_PULSATING_LOOKUP` → `{kebab_name(m): m for m in PulsatingEffect}`

3. `_FLAME_COLOR_LOOKUP` → `{kebab_name(m): m for m in FlameColor}`

4. `_MEDIA_THEME_LOOKUP` → `{kebab_name(m): m for m in MediaTheme}`

5. `_TEMP_UNIT_LOOKUP` → `{kebab_name(m): m for m in TempUnit}`

Import `kebab_name` from `flameconnect.models`.

## Input Dependencies
Task 02 must be complete — provides `kebab_name()` in `models.py`.

## Output Artifacts
Auto-generated lookup dicts in `cli.py`.

## Implementation Notes
- Verify that the auto-generated keys exactly match the current manual keys. For example, `FlameColor.YELLOW_RED` → `kebab_name()` → `"yellow-red"` which matches the existing `"yellow-red"` key.
- The `_PULSATING_LOOKUP` currently has keys `"on"` and `"off"` which match `PulsatingEffect.ON` and `PulsatingEffect.OFF` via `kebab_name()`.
