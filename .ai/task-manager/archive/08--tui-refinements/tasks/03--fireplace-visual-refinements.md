---
id: 3
group: "tui-refinements"
dependencies: []
status: "completed"
created: 2026-02-25
skills:
  - "textual-css"
  - "python"
---
# Fireplace Visual Refinements

## Objective
Three related visual improvements to the fireplace: make it 50% width, move heat indicator above the frame, and reverse flame animation direction to bottom-to-top.

## Skills Required
- Textual CSS layout (fr units)
- ASCII art rendering logic
- Color palette rotation algorithms

## Acceptance Criteria
- [ ] Fireplace visual takes 50% of horizontal space in standard (non-compact) mode
- [ ] Compact mode is unaffected (fireplace hidden, parameter panel full width)
- [ ] Heat indicator rows render above the fireplace outer frame (`top edge` and `outer frame top`)
- [ ] Heat rows span full outer frame width (no `|` border characters on sides)
- [ ] Total widget height remains constant (flame rows reduced by heat row count)
- [ ] Flame animation colors rise bottom-to-top (base color ascends through zones each frame)
- [ ] All existing tests pass
- [ ] No lint errors

## Technical Requirements

### 50% Width (screens.py)
Change CSS in `screens.py`:
- `#param-scroll` from `width: 2fr` to `width: 1fr`

This makes `#fireplace-visual` (already `1fr`) and `#param-scroll` equal. Compact mode is unaffected because `#fireplace-visual` gets `display: none` in compact mode and the parameter panel fills naturally.

### Heat Above Frame (widgets.py - `_build_fire_art`)
Currently heat rows render inside the frame (lines ~723-738), between inner border columns (`||`). Move them to the very top of the output, before the top edge (`_`) and outer frame top (`+---+`).

Heat rows should span full outer frame width `w` (same width as `outer frame top` row which is `ow + 2` characters including corners). No vertical border characters on sides — just wavy characters (`wavy` and `tilde`) styled with `bright_red`, padded/repeated to fill full outer width.

Rendering order becomes: `[heat rows] -> top edge -> outer frame -> inner frame -> LED -> blank -> flames -> media -> inner bottom -> hearth -> outer bottom`.

### Flame Animation Direction (widgets.py - `_rotate_palette`)
Current rotation:
- Frame 0: `(tip, mid, base)` — original
- Frame 1: `(base, tip, mid)` — base jumps to tip
- Frame 2: `(mid, base, tip)` — mid at tip

Swap Frame 1 and Frame 2 return values:
- Frame 0: `(tip, mid, base)` — original
- Frame 1: `(mid, base, tip)` — mid rises to tip
- Frame 2: `(base, tip, mid)` — base rises to tip

### Files
- `src/flameconnect/tui/screens.py`: CSS width change
- `src/flameconnect/tui/widgets.py`: `_build_fire_art()`, `_rotate_palette()`

## Input Dependencies
None

## Output Artifacts
- Updated CSS for 50/50 layout
- Relocated heat rows above frame in `_build_fire_art()`
- Reversed flame animation direction in `_rotate_palette()`

## Implementation Notes
- The total height budget in `_build_fire_art()` remains unchanged — flame rows are still reduced by the heat row count. The visual just shifts upward.
- Test the heat row width carefully: it should match exactly the outer frame width characters.
