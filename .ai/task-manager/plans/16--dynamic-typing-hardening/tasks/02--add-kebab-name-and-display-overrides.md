---
id: 2
group: "dynamic-typing-hardening"
dependencies: []
status: "pending"
created: 2026-03-01
skills:
  - "python-typing"
  - "refactoring"
---
# Add kebab_name() and Display Name Overrides to models.py

## Objective
Add the `kebab_name()` utility and centralized display-name overrides to `models.py`, then update `display_name()` to use the overrides. This provides the foundation for Components 2 and 6 of the plan.

## Skills Required
Python IntEnum utilities, refactoring.

## Acceptance Criteria
- [ ] `kebab_name(value: IntEnum) -> str` added to `models.py` — converts member name to lowercase kebab-case (e.g., `YELLOW_RED` → `"yellow-red"`)
- [ ] `_DISPLAY_OVERRIDES` dict added to `models.py` with entries for `FireMode.MANUAL` → `"On"`, `FlameColor.YELLOW_RED` → `"Yellow/Red"`, `FlameColor.YELLOW_BLUE` → `"Yellow/Blue"`, `FlameColor.BLUE_RED` → `"Blue/Red"`
- [ ] `display_name()` updated to check `_DISPLAY_OVERRIDES` first, then fall back to existing logic
- [ ] Both `kebab_name` and updated `display_name` added/kept in `__all__` in `__init__.py`
- [ ] `uv run ruff check .` passes
- [ ] `uv run mypy src/` passes
- [ ] `uv run pytest` passes (existing tests for `display_name()` must still pass; some may need updating if they test overridden values)

## Technical Requirements

In `src/flameconnect/models.py`:

1. Add `kebab_name()`:
   - Signature: `def kebab_name(value: IntEnum) -> str`
   - Implementation: `return value.name.lower().replace("_", "-")`

2. Add `_DISPLAY_OVERRIDES: dict[IntEnum, str]` (private, not exported):
   - `FireMode.MANUAL: "On"`
   - `FlameColor.YELLOW_RED: "Yellow/Red"`
   - `FlameColor.YELLOW_BLUE: "Yellow/Blue"`
   - `FlameColor.BLUE_RED: "Blue/Red"`

3. Update `display_name()` to:
   - Check `_DISPLAY_OVERRIDES.get(value)` first
   - Fall back to `value.name.replace("_", " ").title()`

4. Add `kebab_name` to `__all__` in `__init__.py`.

## Input Dependencies
None — this is a standalone task.

## Output Artifacts
- `kebab_name()` function for use by Task 03 (auto-generated lookups)
- Updated `display_name()` with overrides for use by Task 05 (display consolidation)

## Implementation Notes
- `display_name` is already in `__all__`, just add `kebab_name`.
- Existing tests for `display_name()` may test values like `display_name(FireMode.MANUAL)` expecting `"Manual"` — these tests must be updated to expect `"On"` since the override now applies.
- The `_DISPLAY_OVERRIDES` dict uses `IntEnum` as the key type to satisfy mypy strict.
