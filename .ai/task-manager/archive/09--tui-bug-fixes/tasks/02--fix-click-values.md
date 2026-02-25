---
id: 2
group: "tui-bug-fixes"
dependencies: []
status: "completed"
created: 2026-02-25
skills:
  - "python"
---
# Fix Click Values Not Working

## Objective
Make field value clicks in the parameter panel trigger the associated actions (open dialogs, toggle settings).

## Skills Required
- Python async/await, Textual event handling

## Acceptance Criteria
- [ ] Clicking a clickable field value triggers the corresponding action
- [ ] Dialogs open when clicking values like "Mode", "Target Temp", "Flame Speed", etc.
- [ ] Toggle actions execute when clicking values like "Flame Effect", "Brightness", etc.
- [ ] Non-clickable values (action is None) remain unaffected
- [ ] All existing tests pass
- [ ] No lint errors

## Technical Requirements

The `_ClickableValue.on_click()` method in widgets.py (around line 73) calls `self.app.run_action(self._action)` without `await`. In Textual, `run_action()` is a coroutine — calling it without `await` creates a coroutine object that is never executed.

Fix: Change `on_click` from sync to async:
- Change `def on_click(self) -> None:` to `async def on_click(self) -> None:`
- Change `self.app.run_action(self._action)` to `await self.app.run_action(self._action)`

Textual supports async event handlers natively — `async def on_click()` is fully supported.

Also ensure the existing `param-label` CSS fix (`ClickableParam > .param-label { width: auto; }`) is still in place — this was applied in the working tree but not yet committed. Without it, labels consume all horizontal space and values are invisible (can't be clicked).

## Input Dependencies
None

## Output Artifacts
- Fixed `_ClickableValue.on_click()` as async with awaited `run_action()`

## Implementation Notes
- The `param-label` CSS fix should already be in the working tree from the earlier fix
- Action strings like `"toggle_power"` correspond to `action_toggle_power()` methods on the app

## Files
- `src/flameconnect/tui/widgets.py`
