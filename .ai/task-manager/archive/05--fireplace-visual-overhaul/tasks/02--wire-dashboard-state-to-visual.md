---
id: 2
group: "fireplace-visual-overhaul"
dependencies: [1]
status: "completed"
created: 2026-02-24
skills:
  - python
  - textual
---
# Wire Dashboard State to FireplaceVisual

## Objective
Update `DashboardScreen._update_display` in `src/flameconnect/tui/screens.py` to extract `ModeParam` and `FlameEffectParam` from the overview parameters and pass them to `FireplaceVisual.update_state`.

## Skills Required
- Python: Iterating parameter lists, type checking with `isinstance`
- Textual: Querying widgets with `query_one`

## Acceptance Criteria
- [ ] `_update_display` extracts `ModeParam` and `FlameEffectParam` from `overview.parameters`
- [ ] Calls `FireplaceVisual.update_state(mode, flame_effect)` with the extracted params (or `None` if not present)
- [ ] The fireplace visual updates its display when new state is received from the API
- [ ] No changes to any other files

## Technical Requirements
- Modify `src/flameconnect/tui/screens.py` only
- Use the existing pattern where `_update_display` already iterates `overview.parameters`
- Query the visual widget with `self.query_one("#fireplace-visual", FireplaceVisual)`

## Input Dependencies
- Task 01: `FireplaceVisual.update_state` method must exist

## Output Artifacts
- Updated `_update_display` method that feeds state to the visual widget

## Implementation Notes
- The method already loops through params to find `ModeParam` for `_current_mode`; extend this loop to also capture `FlameEffectParam`
- Keep it simple: extract, pass, done
