---
id: 8
group: "interfaces"
dependencies: [5]
created: "2026-02-23"
skills:
  - python
  - textual-tui
complexity_score: 5
complexity_notes: "TUI requires textual App/Screen/Widget composition with async data refresh. Moderate complexity due to interactive controls and live state updates."
status: "completed"
---
# Implement textual TUI dashboard

## Objective
Create the `tui/` subpackage with a textual-based interactive terminal UI for monitoring and controlling fireplaces. The TUI shows a fireplace list, a status dashboard with live-updating parameters, and interactive controls for power, flame, and heat settings.

## Skills Required
- Python textual framework (App, Screen, Widget)

## Acceptance Criteria
- [ ] `src/flameconnect/tui/__init__.py` exports `run_tui` async function
- [ ] `src/flameconnect/tui/app.py` — textual `App` subclass with key bindings and screen management
- [ ] `src/flameconnect/tui/screens.py` — Dashboard screen showing fireplace state
- [ ] `src/flameconnect/tui/widgets.py` — Custom widgets for fireplace data display and controls
- [ ] Fireplace list view showing name, ID, connection state
- [ ] Dashboard view for selected fireplace: mode, flame effect (speed, brightness, color), heat settings (status, temp, mode), timer, errors
- [ ] Interactive controls: toggle power on/off, adjust flame speed, toggle heat
- [ ] Auto-refresh of fireplace state on a configurable interval (default: 10 seconds)
- [ ] `flameconnect tui` launches the app (via CLI lazy import)
- [ ] Passes `mypy --strict` and `ruff check`
- [ ] Validated against live API (see Live API Validation Protocol below)

Use your internal Todo tool to track these and keep on track.

## Technical Requirements
- textual `App` with at least one `Screen` (dashboard)
- Use textual `DataTable` or `ListView` for fireplace list
- Use textual `Static`, `Label`, and custom `Widget` subclasses for status display
- Async data fetch: use `set_interval` or `Timer` to periodically call `client.get_fire_overview()`
- Control actions should call client methods (turn_on/off, write_parameters) and refresh display
- Handle API errors gracefully in the UI (show error notification, don't crash)
- The `run_tui` function should create MsalAuth, FlameConnectClient, and launch the App

## Input Dependencies
- Task 5: `client.py` (FlameConnectClient — all API methods)
- Task 4: `auth.py` (MsalAuth for standalone auth)
- Task 2: `models.py` (all types for display)

## Output Artifacts
- `src/flameconnect/tui/__init__.py`
- `src/flameconnect/tui/app.py`
- `src/flameconnect/tui/screens.py`
- `src/flameconnect/tui/widgets.py`

## Implementation Notes

<details>
<summary>Detailed implementation guidance</summary>

1. **App structure**:
   ```python
   class FlameConnectApp(App):
       TITLE = "FlameConnect"
       BINDINGS = [
           ("q", "quit", "Quit"),
           ("r", "refresh", "Refresh"),
           ("p", "toggle_power", "Power On/Off"),
       ]

       def __init__(self, client: FlameConnectClient) -> None:
           super().__init__()
           self.client = client
   ```

2. **Dashboard screen layout**: Use textual's container/grid layout to organize:
   - Left panel: Fireplace list (if multiple)
   - Main panel: Current fireplace status (decoded parameters)
   - Bottom bar: Key bindings help

3. **Status display widgets**: Create widgets that take parameter dataclasses and render them:
   - `FireplaceStatus` — shows mode, connection state
   - `FlameDisplay` — shows flame effect, speed, brightness, color
   - `HeatDisplay` — shows heat status, mode, temperature
   - `TimerDisplay` — shows timer status and duration

4. **Auto-refresh**: Use textual's `set_interval`:
   ```python
   def on_mount(self) -> None:
       self.set_interval(10, self.refresh_state)

   async def refresh_state(self) -> None:
       try:
           overview = await self.client.get_fire_overview(self.fire_id)
           self.update_display(overview)
       except FlameConnectError as exc:
           self.notify(str(exc), severity="error")
   ```

5. **Interactive controls**: Bind keys or buttons to client actions:
   - Toggle power: call `turn_on` or `turn_off` based on current mode
   - After any control action, trigger an immediate refresh

6. **`run_tui` function** in `tui/__init__.py`:
   ```python
   async def run_tui() -> None:
       auth = MsalAuth()
       async with FlameConnectClient(auth=auth) as client:
           app = FlameConnectApp(client)
           await app.run_async()
   ```

7. **Error handling**: Wrap all client calls in try/except. Use textual's `self.notify()` for error messages. Never let an API error crash the TUI.

8. **Logging**: Use `logging.getLogger(__name__)`. No `print()`.

9. **Live API Validation Protocol**: After implementing the TUI, validate it against the real API. For every live API call, follow this mandatory three-step process:
   - **Explain**: Tell the user what you will do (e.g., "I will launch `flameconnect tui` which will authenticate and fetch your fireplace list via GET /api/Fires/GetFires").
   - **Confirm**: Wait for the user to explicitly approve before launching.
   - **Verify**: Ask the user to confirm the TUI is displaying correct data and controls are working.

   Since the TUI is interactive, the user will be driving the controls themselves. The validation focuses on:
   1. Launch the TUI — confirm it authenticates and shows the fireplace list.
   2. Select a fireplace — confirm the dashboard shows correct current state.
   3. Toggle power — user tests the power control and confirms the fireplace responded.
   4. Verify auto-refresh — confirm state updates appear after changes.
</details>
