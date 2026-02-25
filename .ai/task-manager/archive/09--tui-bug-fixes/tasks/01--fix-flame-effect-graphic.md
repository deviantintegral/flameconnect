---
id: 1
group: "tui-bug-fixes"
dependencies: []
status: "completed"
created: 2026-02-25
skills:
  - "python"
---
# Fix Flame Effect OFF Not Updating Graphic

## Objective
Make the fireplace visual respect the `flame_effect` on/off state so that toggling flame effect OFF visually extinguishes the flames.

## Skills Required
- Python, Textual widget rendering

## Acceptance Criteria
- [ ] When flame effect is toggled OFF (key 'e'), the fireplace graphic stops showing flames
- [ ] When flame effect is toggled back ON, flames reappear
- [ ] When power mode is STANDBY, flames are still hidden regardless of flame effect
- [ ] LED and media bed styling still reflect configured colors when power is ON but flames are OFF
- [ ] Animation timer stops when flames are off and restarts when they come back on
- [ ] All existing tests pass
- [ ] No lint errors

## Technical Requirements

In `FireplaceVisual.render()` (widgets.py, around lines 929-957):

The `fire_on` variable currently only checks `mode.mode == FireMode.MANUAL`. Add an additional check: if `flame_effect` is not None and `flame_effect.flame_effect != FlameEffect.ON`, set `fire_on = False`.

This means `fire_on` should be True ONLY when:
1. `mode.mode == FireMode.MANUAL` (power is on), AND
2. `flame_effect` is None OR `flame_effect.flame_effect == FlameEffect.ON`

When `fire_on` is False but power is ON (flames disabled), the LED and media bed colors should still be active. Currently, LED/media styling is only applied when `fire_on and flame_effect is not None`. Split this: apply LED/media styling when power is ON (regardless of flame effect), but only show flames when `fire_on` is True.

Also ensure the animation timer behavior is correct — the timer should not tick when flames are off. Look at `update_state()` and `_start_animation`/`_stop_animation` to verify this works correctly with the new `fire_on` logic.

Import `FlameEffect` from `flameconnect.models` if not already imported.

## Input Dependencies
None

## Output Artifacts
- Updated `FireplaceVisual.render()` with flame effect state check

## Implementation Notes
- `FlameEffect` is an IntEnum with values `OFF = 0` and `ON = 1`
- The `fire_on` flag is passed to `_build_fire_art()` which controls flame rendering
- Be careful to preserve LED/media colors when power is on but flames are disabled

## Files
- `src/flameconnect/tui/widgets.py`
