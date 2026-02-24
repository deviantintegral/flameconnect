---
id: 1
group: "fireplace-state-controls"
dependencies: []
status: "completed"
created: 2026-02-23
skills:
  - "python"
---
# Refactor Existing Write Handlers to Use dataclasses.replace()

## Objective
Refactor all existing FlameEffectParam and HeatParam manual field-copy construction sites to use `dataclasses.replace()`, reducing boilerplate and preventing field-copy bugs.

## Skills Required
- Python dataclasses (frozen dataclasses, `dataclasses.replace()`)

## Acceptance Criteria
- [ ] `_set_flame_speed` in `cli.py` uses `dataclasses.replace(current, flame_speed=speed)` instead of manual 12-field construction
- [ ] `_set_brightness` in `cli.py` uses `dataclasses.replace(current, brightness=brightness)` instead of manual construction
- [ ] `_set_heat_mode` in `cli.py` uses `dataclasses.replace(current, heat_mode=heat_mode)` instead of manual construction
- [ ] `_set_heat_temp` in `cli.py` uses `dataclasses.replace(current, setpoint_temperature=temp)` instead of manual construction
- [ ] `turn_on` in `client.py` uses `dataclasses.replace(current_flame, flame_effect=FlameEffect.ON)` instead of manual construction
- [ ] All existing tests still pass
- [ ] `uv run ruff check` and `uv run mypy --strict src/` pass

Use your internal Todo tool to track these and keep on track.

## Technical Requirements
- `from dataclasses import replace` (stdlib, no new deps)
- All parameter dataclasses are `@dataclass(frozen=True, slots=True)` — `replace()` works by creating a new instance
- The refactor must be behavior-preserving: no functional changes, only structural simplification

## Input Dependencies
None — works on existing codebase.

## Output Artifacts
- Refactored `cli.py` with simplified write handlers
- Refactored `client.py` with simplified `turn_on` method
- These simplified patterns serve as the template for new handlers in subsequent tasks

## Implementation Notes
- The key files are `src/flameconnect/cli.py` (functions: `_set_flame_speed`, `_set_brightness`, `_set_heat_mode`, `_set_heat_temp`) and `src/flameconnect/client.py` (method: `turn_on`)
- Example transformation for `_set_flame_speed`:
  Before: `new_param = FlameEffectParam(flame_effect=current.flame_effect, flame_speed=speed, brightness=current.brightness, ...)` (12 fields)
  After: `new_param = replace(current, flame_speed=speed)`
- Run `uv run pytest tests/` to verify no regressions
