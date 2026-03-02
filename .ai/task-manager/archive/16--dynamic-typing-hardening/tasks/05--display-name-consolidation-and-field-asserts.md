---
id: 5
group: "dynamic-typing-hardening"
dependencies: [2, 4]
status: "completed"
created: 2026-03-01
skills:
  - "python-typing"
  - "refactoring"
---
# Consolidate Display Overrides and Add Field Validation Asserts

## Objective
Remove duplicate display-name override dicts from `cli.py` and `tui/widgets.py`, replacing them with the centralized `display_name()` overrides from Task 02. Add module-level asserts to validate stringly-typed field access patterns. Covers Components 5 and 6 of the plan.

## Skills Required
Python dataclasses introspection, refactoring.

## Acceptance Criteria
- [ ] `_FIRE_MODE_DISPLAY` removed from `cli.py`; callers use `display_name()` directly
- [ ] `_FLAME_COLOR_DISPLAY` removed from `cli.py`; callers use `display_name()` directly
- [ ] `_MODE_DISPLAY` removed from `tui/widgets.py`; callers use `display_name()` directly
- [ ] Module-level assert in `cli.py` validates `_FEATURE_LABELS` field names against `FireFeatures`
- [ ] Module-level assert in `cli.py` validates `_FLAME_EFFECT_SETTERS` field names against `FlameEffectParam`
- [ ] `uv run ruff check .` passes
- [ ] `uv run mypy src/` passes
- [ ] `uv run pytest` passes

## Technical Requirements

### Display Override Consolidation (Component 6)

**In `cli.py`:**
- Remove `_FIRE_MODE_DISPLAY` dict (currently `{FireMode.MANUAL: "On"}`)
- Remove `_FLAME_COLOR_DISPLAY` dict (currently maps 3 slash-separated FlameColor names)
- Find all places that use these dicts (e.g., `_FIRE_MODE_DISPLAY.get(mode, display_name(mode))`) and replace with just `display_name(mode)` since the overrides are now baked into `display_name()`.

**In `tui/widgets.py`:**
- Remove `_MODE_DISPLAY` dict (currently `{FireMode.STANDBY: "Standby", FireMode.MANUAL: "On"}`)
- Find all places that use `_MODE_DISPLAY.get(...)` and replace with `display_name(...)`.

### Field Validation Asserts (Component 5)

**In `cli.py`, after `_FEATURE_LABELS` definition:**
```python
assert {fn for fn, _ in _FEATURE_LABELS} == {
    f.name for f in dataclasses.fields(FireFeatures)
}, "_FEATURE_LABELS field names do not match FireFeatures fields"
```
This requires importing `dataclasses` and `FireFeatures`.

**In `cli.py`, after `_FLAME_EFFECT_SETTERS` definition:**
```python
assert all(
    setter.field in {f.name for f in dataclasses.fields(FlameEffectParam)}
    for setter in _FLAME_EFFECT_SETTERS.values()
), "_FLAME_EFFECT_SETTERS contains invalid FlameEffectParam field names"
```
This requires importing `FlameEffectParam`. Note: after Task 04, `_FLAME_EFFECT_SETTERS` uses `_FlameEffectSetter` NamedTuple, so access is `setter.field`.

## Input Dependencies
- Task 02: Provides centralized `display_name()` with overrides in `models.py`
- Task 04: Provides `_FlameEffectSetter` NamedTuple (so asserts use `.field` attribute)

## Output Artifacts
- Cleaned up `cli.py` and `tui/widgets.py` without duplicate override dicts
- Module-level validation asserts for field-name strings

## Implementation Notes
- Search for all uses of `_FIRE_MODE_DISPLAY`, `_FLAME_COLOR_DISPLAY`, and `_MODE_DISPLAY` to ensure none are missed.
- The assert for `_FEATURE_LABELS` uses set equality (`==`) to also catch extra fields in `_FEATURE_LABELS` that don't exist in `FireFeatures`.
- The assert for `_FLAME_EFFECT_SETTERS` uses subset check (`in`) since the setters only cover a subset of `FlameEffectParam` fields (not all fields have setters).
