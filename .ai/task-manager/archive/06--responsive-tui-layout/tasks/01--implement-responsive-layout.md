---
id: 1
group: "responsive-tui-layout"
dependencies: []
status: "completed"
created: 2026-02-24
skills:
  - "textual-css"
  - "python"
---
# Implement Responsive Layout in DashboardScreen

## Objective
Modify `DashboardScreen` in `src/flameconnect/tui/screens.py` to support responsive layout that works at 80x24 while preserving the current side-by-side layout at larger terminal sizes.

## Skills Required
- Textual CSS (class toggling, layout properties, responsive selectors)
- Python (Textual widget composition, event handlers)

## Acceptance Criteria
- [ ] `compose()` uses `Container` (not `Horizontal`) for `#status-section` with CSS-controlled `layout: horizontal` default
- [ ] `ParameterPanel` is wrapped in a `VerticalScroll` container (`#param-scroll`)
- [ ] `on_resize` handler toggles `.compact` CSS class when `width < 100 or height < 30`
- [ ] Compact CSS rules: vertical stacking, no borders, reduced padding, capped heights, scrollable params
- [ ] Standard layout at large sizes is visually unchanged (side-by-side, full borders/padding)
- [ ] All existing tests pass (`pytest`)
- [ ] Linting passes (`ruff check`)

## Technical Requirements

### compose() Changes
- Import `Container` from `textual.containers` and `VerticalScroll`
- Replace `Horizontal(id="status-section")` with `Container(id="status-section")`
- Wrap `ParameterPanel(id="param-panel")` inside `VerticalScroll(id="param-scroll")`

### Default CSS Updates
- Add `#status-section { layout: horizontal; }` (replaces the implicit direction from `Horizontal`)
- Add `#param-scroll { height: auto; }` (VerticalScroll wrapper, unconstrained in standard mode)

### Compact CSS Rules (under `.compact` descendant selectors)
- `.compact #dashboard-container { padding: 0 1; }`
- `.compact #status-section { layout: vertical; }`
- `.compact #fireplace-visual { border: none; padding: 0; max-height: 10; width: 1fr; }`
- `.compact #param-scroll { max-height: 7; height: auto; overflow-y: auto; }`
- `.compact #param-panel { border: none; padding: 0; width: 1fr; }`
- `.compact #messages-label { margin-top: 0; }`
- `.compact #messages-panel { border: none; min-height: 2; }`

### on_resize Handler
```
def on_resize(self, event: events.Resize) -> None:
    compact = event.size.width < 100 or event.size.height < 30
    self.set_class(compact, "compact")
```

## Input Dependencies
None — this is the first task.

## Output Artifacts
- Modified `src/flameconnect/tui/screens.py` with responsive layout support
