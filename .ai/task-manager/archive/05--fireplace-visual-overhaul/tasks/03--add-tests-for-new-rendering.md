---
id: 3
group: "fireplace-visual-overhaul"
dependencies: [1]
status: "completed"
created: 2026-02-24
skills:
  - python
  - pytest
---
# Add Tests for the New Fireplace Visual Rendering

## Objective
Write tests covering the new `_build_fire_art` rendering function and `FireplaceVisual.update_state` with various parameter states, ensuring correctness of the frame structure, state-driven coloring, and height adaptation.

## Skills Required
- Python: Unit testing with pytest
- pytest: Parametrized tests, assertions on Rich `Text` objects

## Acceptance Criteria
- [ ] Test that the rendering produces the correct frame structure (top edge, outer frame, inner frame, LED strip, media bed, hearth)
- [ ] Test that flames are shown when `FireMode.MANUAL` and hidden when `FireMode.STANDBY`
- [ ] Test that flame colors change based on `FlameColor` presets
- [ ] Test that LED strip color reflects `overhead_color` / `overhead_light`
- [ ] Test that inner media bed color reflects `media_color`
- [ ] Test that outer hearth is always dim
- [ ] Test height adaptation: verify flame row count adjusts based on available height parameter
- [ ] Test RGBW-to-RGB helper function with various inputs (including white channel blending and clamping)
- [ ] Test default rendering when no state has been set (safe defaults)
- [ ] All existing tests still pass

## Technical Requirements
- Create or update test file in `tests/` directory
- Use `rich.text.Text.plain` to extract plain text for structural assertions
- Use `rich.text.Text.spans` or style checks for color assertions
- Test the rendering function directly (unit tests), not through Textual app simulation

## Input Dependencies
- Task 01: The new rendering function and `update_state` method must exist

## Output Artifacts
- Test file with comprehensive coverage of the new rendering

## Implementation Notes
- The rendering function should be testable by calling it directly with width, height, and state params
- Check that `Text.plain` contains expected structural characters (`▁`, `┌`, `└`, `░`, `▓`)
- For color tests, verify that the `Text` object contains spans with expected style strings (e.g. `rgb(255,0,0)`)
- Parametrize flame color tests across multiple `FlameColor` enum values
