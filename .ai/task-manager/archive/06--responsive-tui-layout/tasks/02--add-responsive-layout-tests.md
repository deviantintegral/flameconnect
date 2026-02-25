---
id: 2
group: "responsive-tui-layout"
dependencies: [1]
status: "completed"
created: 2026-02-24
skills:
  - "pytest"
  - "textual-testing"
---
# Add Tests for Responsive Layout

## Objective
Add tests to verify the responsive layout behavior of `DashboardScreen`, covering CSS class toggling, compact mode styles, and layout direction switching.

## Skills Required
- pytest (test structure, assertions)
- Textual testing (async app testing, widget querying, CSS verification)

## Acceptance Criteria
- [ ] Test that `.compact` class is added when terminal size is below threshold
- [ ] Test that `.compact` class is removed when terminal size is above threshold
- [ ] Test that `#status-section` uses `Container` (not `Horizontal`)
- [ ] Test that `#param-panel` is wrapped in `VerticalScroll`
- [ ] All tests pass (`pytest`)
- [ ] Linting passes (`ruff check`)

## Technical Requirements

### Test File
Create `tests/test_responsive_layout.py`

### Key Test Cases
1. **Compact class toggling**: Simulate resize to 80x24, verify `.compact` in screen classes. Simulate resize to 120x40, verify `.compact` not in screen classes.
2. **Container type**: Verify `#status-section` is a `Container` (not `Horizontal`).
3. **Scroll wrapper**: Verify `#param-scroll` exists and wraps `#param-panel`.
4. **Threshold boundary**: Test at exactly width=100, height=30 (should NOT be compact).

### Test Approach
Use Textual's `async with app.run_test()` pattern. The `DashboardScreen` requires a `FlameConnectClient` and `Fire` object — use mocks or the existing test fixtures from `tests/fixtures/`.

## Input Dependencies
- Task 01 must be completed (responsive layout implemented in screens.py)

## Output Artifacts
- New test file `tests/test_responsive_layout.py`
