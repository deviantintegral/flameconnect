---
id: 1
group: "tui-fixes-and-features"
dependencies: []
status: "completed"
created: 2026-02-25
skills:
  - "textual-css"
  - "python"
---
# Fix Parameter Panel Right Border

## Objective
Ensure the parameter panel's right border is always visible by fixing the CSS width allocation and removing the parent-clamped width workaround from `render()`.

## Skills Required
Textual CSS layout, Python

## Acceptance Criteria
- [ ] `#param-scroll` has `width: 2fr` (moved from `#param-panel`)
- [ ] `#param-panel` has `width: 1fr` (fills scroll container exactly)
- [ ] Parent-clamped width workaround in `ParameterPanel.render()` is removed
- [ ] Full-mode `_expand_piped_text` call uses `self.content_region.width` for width
- [ ] Right border is visible at terminal widths 80-200+
- [ ] Compact mode still works correctly
- [ ] All existing tests pass

## Technical Requirements
In `screens.py`:
- Move `width: 2fr` from `#param-panel` CSS rule to `#param-scroll`
- Set `#param-panel` to `width: 1fr`
- Update compact CSS rules accordingly (`#param-panel.compact` should keep `width: 1fr`)

In `widgets.py`:
- In `ParameterPanel.render()`, remove the parent-clamping logic that computes width from the parent container
- For full mode (no `.compact` class), pass `self.content_region.width` to `_expand_piped_text` so lines that exceed panel width get wrapped
- Keep `_expand_piped_text`, `_wrap_piped_text`, `_expand_piped_line`, `_wrap_piped_line` functions — they remain useful for formatting
- The compact mode path using `_wrap_piped_text` should continue using `self.content_region.width`

## Input Dependencies
None — this is a standalone CSS and rendering fix.

## Output Artifacts
- Fixed CSS layout in `screens.py` with correct width allocation
- Simplified `ParameterPanel.render()` in `widgets.py`
- Correct panel width for downstream task (Clickable Parameter Fields)

## Implementation Notes
The root cause is that `#param-panel` has `width: 2fr` inside a `VerticalScroll` container. Textual resolves this fractional width against the grandparent layout context, not the scroll viewport, causing the panel to render wider than its parent viewport.
