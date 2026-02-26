---
id: 2
group: "documentation"
dependencies: [1]
status: "completed"
created: 2026-02-25
skills:
  - documentation
  - markdown
---
# Update README CLI and TUI Documentation

## Objective
Rewrite the README's CLI "Set parameters" section to document all 17 `set` parameters, and expand the TUI keybindings table to show all 21 user-facing keys.

## Acceptance Criteria
- [ ] README lists all 17 `set` parameters with correct syntax and values
- [ ] README TUI keybindings table includes all 21 keys
- [ ] No incorrect values remain (brightness 200, fan-only, etc.)
- [ ] Parameters grouped logically by category

## Technical Requirements
- CLI set parameters: mode, flame-speed, brightness, pulsating, flame-color, flame-effect, media-theme, media-light, media-color, overhead-light, overhead-color, ambient-sensor, heat-status, heat-mode, heat-temp, timer, temp-unit
- TUI keybindings: 19 from BINDINGS + r (refresh) + q (quit) = 21 (excluding ctrl+p)

## Input Dependencies
- Task 1 must be complete so heat-status is included

## Output Artifacts
- Modified `README.md`
