---
id: 1
group: "fireplace-visual-overhaul"
dependencies: []
status: "completed"
created: 2026-02-24
skills:
  - python
  - textual
---
# Rewrite FireplaceVisual Rendering with New ASCII Art Structure

## Objective
Replace the existing `_build_fire_art` function and `FireplaceVisual` widget in `src/flameconnect/tui/widgets.py` with a new implementation that renders the user's double-frame ASCII art design, supports state-driven coloring for three zones (LED strip, flames, media bed), and adapts the flame row count to the available container height.

## Skills Required
- Python: Rich `Text` object construction with styled spans
- Textual: Widget reactive attributes, `content_region` for dynamic sizing

## Acceptance Criteria
- [ ] New `_build_fire_art` produces the double-frame structure: top edge (`▁`), outer frame (`┌─┐`/`└─┘`), inner frame, LED strip (`░`), flame rows, inner media bed (`▓`), outer hearth (`▓` dim), matching the reference ASCII art
- [ ] Flame art uses multiple distinct columns spread across the width (not a single centered flame), with ~8 row definitions matching the reference
- [ ] LED strip (`░`) is colored by `overhead_color` / `overhead_light` from `FlameEffectParam`; dim when off
- [ ] Flames are colored according to `FlameColor` enum via a palette mapping (tip/mid/base styles per preset)
- [ ] Flames are hidden (blank space) when `FireMode.STANDBY`
- [ ] Inner media bed (`▓`) is colored by `media_color` RGBW from `FlameEffectParam`
- [ ] Outer hearth (`▓`) is always rendered in fixed dim grey
- [ ] Flame row count adapts to `content_region.height` minus 8 fixed structural rows, clamped to min 2, max full definition count
- [ ] RGBW-to-RGB helper function converts RGBW values to Rich `rgb(r,g,b)` style strings (white channel blended into RGB, clamped to 255)
- [ ] `FireplaceVisual` has an `update_state` method accepting `ModeParam` and `FlameEffectParam`, triggering re-render
- [ ] Falls back to sensible defaults (e.g. 12 rows, default colors) when height is 0 or no state has been set

## Technical Requirements
- Modify `src/flameconnect/tui/widgets.py` only
- Use Rich `Text` objects for styled rendering (same pattern as current `_build_fire_art`)
- Use `rgb(r,g,b)` Rich style strings for RGBW-derived colors
- Reuse or adapt the existing `_expand_flame` gap-distribution algorithm for horizontal scaling of multi-column flames
- Flame color palettes map each `FlameColor` enum value to three Rich style strings: tip, mid, base
- The widget must render correctly before `update_state` is called (use safe defaults)

## Input Dependencies
None — this is the foundational task.

## Output Artifacts
- Updated `FireplaceVisual` widget with `update_state(mode: ModeParam | None, flame_effect: FlameEffectParam | None)` method
- New `_build_fire_art` function accepting width, height, and state parameters
- RGBW-to-RGB helper function
- Flame color palette mapping

## Implementation Notes
- The current `_FLAME_DEFS`, `_expand_flame`, `_build_fire_art`, `_COAL_FRAC` can all be replaced
- The user's reference ASCII shows ~8 flame columns with varying heights; define these as atom groups per row similar to current `_FLAME_DEFS` but with more columns
- Width nesting: outer=w, between outer borders=w-2, between inner borders=w-4
- The LED and inner media bed render at innermost width (w-4); outer hearth at w-2
