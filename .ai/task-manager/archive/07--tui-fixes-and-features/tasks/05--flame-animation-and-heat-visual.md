---
id: 5
group: "tui-fixes-and-features"
dependencies: []
status: "completed"
created: 2026-02-25
skills:
  - "textual"
  - "python"
---
# Fireplace Visual — Flame Color Animation and Heat Visualization

## Objective
Animate flames by cycling colors through a gradient based on the active palette and speed. Show wavy heat indicator rows above the fireplace when heat is active.

## Skills Required
Textual framework (set_interval, refresh), Python, Rich styling

## Acceptance Criteria
- [ ] Flame colors cycle through gradient steps based on active `FlameColor` palette
- [ ] Animation speed maps from `flame_speed` (1-5) to interval timing (speed 1 = ~600ms, speed 5 = ~150ms)
- [ ] Animation stops when fireplace is off (`fire_on=False`)
- [ ] Timer is cancelled and recreated when speed changes
- [ ] Wavy heat characters (`~` or `≈`) appear above the fireplace top edge when heat is on
- [ ] Heat rows disappear when heat is off
- [ ] Total widget height remains constant (heat rows reduce flame zone budget)
- [ ] `FireplaceVisual.update_state()` accepts optional `HeatParam`
- [ ] `DashboardScreen._update_display()` passes `HeatParam` to the visual
- [ ] All existing tests pass

## Technical Requirements
### Flame Color Animation (`widgets.py`)
- Define gradient sequences for each palette in `_flame_palettes`. Each palette's 3 colors (tip, mid, base) rotate through positions, creating the animation frames:
  - Frame 0: tip=color_a, mid=color_b, base=color_c
  - Frame 1: tip=color_c, mid=color_a, base=color_b
  - Frame 2: tip=color_b, mid=color_c, base=color_a
  - (cycle back to frame 0)
- Add instance state to `FireplaceVisual`:
  - `_anim_frame: int = 0` — current frame index
  - `_anim_timer: Timer | None = None` — reference to set_interval timer
  - `_flame_speed: int = 3` — current speed for interval calculation
- Map speed to interval: `{1: 0.6, 2: 0.45, 3: 0.3, 4: 0.2, 5: 0.15}` (approximate)
- In `update_state()`: when flame effect/speed changes, cancel existing timer and create new one with updated interval. When `fire_on=False`, cancel timer.
- Timer callback: increment `_anim_frame`, wrap around, call `self.refresh()`
- In `render()` / `_build_fire_art()`: use the current frame's rotated palette instead of the static palette

### Heat Visualization (`widgets.py`, `screens.py`)
- Add `heat_on: bool = False` parameter to `_build_fire_art()`
- When `heat_on=True`: render 1-2 rows of wavy characters (`~` or `≈`) above the top structural row, styled with `"bright_red"` or `"yellow"`
- Reduce `flame_rows` by the number of heat rows to keep total height constant
- In `FireplaceVisual.update_state()`: add optional `heat_param: HeatParam | None = None` parameter. Store `heat_on` state based on whether heat mode is active.
- In `screens.py` `DashboardScreen._update_display()`: extract `HeatParam` from the parameter list and pass it to `visual.update_state()`

## Input Dependencies
None.

## Output Artifacts
- Animated `FireplaceVisual` with gradient cycling and heat indicators
- Updated `_build_fire_art()` supporting both features
- Updated data flow from `DashboardScreen` to `FireplaceVisual`

## Implementation Notes
- Gradient definitions should be co-located with the existing `_flame_palettes` dict.
- Only change style strings per tick, not the entire frame structure, for performance.
- Heat rows are independent of flame animation — they render unconditionally when `heat_on=True`.
