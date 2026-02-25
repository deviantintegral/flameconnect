---
id: 8
group: "tui-fixes-and-features"
dependencies: [3, 4]
status: "completed"
created: 2026-02-25
skills:
  - "textual"
  - "python"
---
# Temperature Adjustment Dialog

## Objective
Add a TUI dialog for setting the heater setpoint temperature, with a keybinding, command palette entry, and clickable field support.

## Skills Required
Textual framework (ModalScreen, Input, Button), Python

## Acceptance Criteria
- [ ] New `TemperatureScreen(ModalScreen[float | None])` created in `temperature_screen.py`
- [ ] Dialog displays current `HeatParam.setpoint_temperature` and active unit (°C or °F)
- [ ] `Input` field (type `"number"`) for entering desired temperature
- [ ] Validation enforces range: 5-35°C or 40-95°F depending on active unit
- [ ] Dismiss with new temperature on submit, `None` on cancel
- [ ] `ArrowNavMixin` applied to the screen (from Task 04)
- [ ] Keybinding `n` bound to `action_set_temperature` with description "Set Temp"
- [ ] Command palette entry added to `_CONTROL_COMMANDS`
- [ ] `action_set_temperature()` method in `FlameConnectApp` extracts current `HeatParam` and `TempUnitParam`, opens dialog
- [ ] `_apply_temperature(temp: float)` method writes via `client.write_parameters()` using `dataclasses.replace(current_heat_param, setpoint_temperature=temp)`
- [ ] All existing tests pass

## Technical Requirements
### New File: `src/flameconnect/tui/temperature_screen.py`
Follow the pattern from `HeatModeScreen` and `FlameSpeedScreen`:
- `TemperatureScreen(ArrowNavMixin, ModalScreen[float | None])`
- Constructor takes `current_temp: float`, `unit: TempUnitParam`
- `compose()`: Title showing current temp with unit, `Input` field (type "number", placeholder with valid range), Submit/Cancel buttons
- `on_button_pressed()`: Submit validates and dismisses with float, Cancel dismisses with None
- `on_input_submitted()`: Same as Submit button
- Validation: Parse float, check range based on unit (CELSIUS: 5.0-35.0, FAHRENHEIT: 40.0-95.0), show error notification if invalid
- `BINDINGS`: escape → cancel

### Updates to `app.py`
- Add `Binding("n", "set_temperature", "Set Temp")` to BINDINGS
- Add `("Set Temperature", "Adjust heater setpoint temperature", "set_temperature")` to `_CONTROL_COMMANDS`
- Add `action_set_temperature()`:
  ```python
  def action_set_temperature(self) -> None:
      dashboard = self.query_one(DashboardScreen)
      params = dashboard.current_parameters
      heat_param = params.get(HeatParam)
      temp_unit = params.get(TempUnitParam)
      if heat_param is None:
          return
      self.push_screen(
          TemperatureScreen(heat_param.setpoint_temperature, temp_unit),
          callback=self._apply_temperature_callback,
      )
  ```
- Add `_apply_temperature(temp: float)` using `dataclasses.replace()` and `client.write_parameters()`

## Input Dependencies
- Task 03: Temperature unit display logic (provides unit suffix patterns)
- Task 04: ArrowNavMixin (provides arrow key navigation for the dialog)

## Output Artifacts
- New `temperature_screen.py` file
- Updated `app.py` with keybinding, command palette entry, action, and apply method

## Implementation Notes
- The CLI already implements temperature setting (`_set_heat_temp` in `cli.py`). The protocol/client layers support writing `HeatParam` with modified `setpoint_temperature`. Only the TUI surface is missing.
- Follow the established `ModalScreen[T | None]` pattern: `push_screen(screen, callback)` → `call_later(_apply_*)`.
- The `n` key is available and unused in the current keybinding map.
