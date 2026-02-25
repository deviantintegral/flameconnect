---
id: 3
group: "increase-test-coverage"
dependencies: []
status: "completed"
created: 2026-02-25
skills:
  - "python-testing"
---
# Add TUI widget format function tests

## Objective
Create `tests/test_widgets_format.py` to cover the ~157 missed statements in `src/flameconnect/tui/widgets.py`. Focus on pure formatting functions and the `format_parameters` dispatcher.

## Skills Required
- python-testing: pytest with model object construction

## Acceptance Criteria
- [ ] New file `tests/test_widgets_format.py` created
- [ ] Tests cover format functions: `_format_mode`, `_format_flame_effect`, `_format_heat`, `_format_heat_mode`, `_format_timer`, `_format_software_version`, `_format_error`, `_format_temp_unit`, `_format_connection_state`, `_format_light_param`, `_format_flame_effect_param`
- [ ] Tests cover `format_parameters` dispatcher with various parameter types
- [ ] Tests cover `_display_name` helper
- [ ] Tests cover widget classes `ParameterPanel` and `FireplaceSelector` where feasible
- [ ] All tests pass
- [ ] No files in `src/` are modified

## Technical Requirements
- Import format functions directly from `flameconnect.tui.widgets`
- Construct model objects (from `flameconnect.models`) as inputs
- Assert on return values (these functions return tuples/strings, not print output)
- For widget classes, use Textual's `run_test()` if needed, or test the data flow

## Input Dependencies
None — independent task.

## Output Artifacts
- `tests/test_widgets_format.py`

## Implementation Notes
- Read `src/flameconnect/tui/widgets.py` to understand each format function's signature and return type
- The format functions are pure — they take model objects and return display data (typically tuples of label/value strings)
- The `format_parameters` function dispatches to individual formatters based on parameter type
- Reference `test_fireplace_visual.py` for patterns on testing widget rendering
- Coverage report shows uncovered lines: 46-59, 74-77, 81-82, 100-103, 107-108, 120, 134-136, 147-149, 160-170, 191, 258-272, 299, 315-333, 343, 365-385, 401, 417, 434, 456-545, 552-562, 681-683, 765-777, 858-859, 868-922, 929, 931, 942, 947-954, 966, 997-1004, 1012-1016
