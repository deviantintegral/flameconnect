---
id: 6
group: "tui-fixes-and-features"
dependencies: []
status: "completed"
created: 2026-02-25
skills:
  - "python"
  - "logging"
---
# Investigate Media Theme Regression

## Objective
Add diagnostic debug logging around the media theme switching flow to determine why switching from Prism back to User Defined turns off the media bed lights.

## Skills Required
Python, stdlib logging

## Acceptance Criteria
- [ ] `_LOGGER.debug()` call before the write in `_apply_media_theme()` logs the current `FlameEffectParam` (including `media_color`)
- [ ] `_LOGGER.debug()` call logs the new `FlameEffectParam` being sent
- [ ] `_LOGGER.debug()` call after the write logs the refreshed state
- [ ] Debug logging does not affect normal operation (only visible at DEBUG level)
- [ ] All existing tests pass

## Technical Requirements
In `app.py`, in the `_apply_media_theme()` method:
1. Before constructing the new param: log `"Media theme change: current=%s"` with the current `FlameEffectParam`
2. After constructing but before writing: log `"Media theme change: sending=%s"` with the new `FlameEffectParam`
3. After the write and refresh: log `"Media theme change: after_refresh=%s"` with the refreshed `FlameEffectParam`

Use `_LOGGER.debug()` (not info/warning) since this is diagnostic data.

## Input Dependencies
None.

## Output Artifacts
- Diagnostic logging in `app.py` for media theme regression analysis

## Implementation Notes
- Investigation shows the client code is correct: `dataclasses.replace(current, media_theme=MediaTheme.USER_DEFINED)` preserves `media_color`. The likely cause is device firmware behavior.
- This is investigation-only — no code fix is expected. The diagnostic data will confirm whether the issue is client-side or device-side.
