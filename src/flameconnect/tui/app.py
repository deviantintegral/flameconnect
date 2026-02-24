"""Main Textual application for the FlameConnect TUI."""

from __future__ import annotations

import logging
import sys
from dataclasses import replace
from typing import TYPE_CHECKING

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, OptionList, Static
from textual.widgets.option_list import Option

from flameconnect.tui.auth_screen import AuthScreen
from flameconnect.tui.screens import DashboardScreen

if TYPE_CHECKING:
    import asyncio

    from flameconnect.client import FlameConnectClient
    from flameconnect.models import Fire

_LOGGER = logging.getLogger(__name__)

_APP_CSS = """
#fire-selector {
    margin: 2 4;
}
#loading-label {
    text-align: center;
    margin: 2 4;
    color: $text-muted;
}
"""


class FlameConnectApp(App[None]):
    """Textual TUI application for monitoring and controlling fireplaces."""

    TITLE = "FlameConnect"
    CSS = _APP_CSS

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("p", "toggle_power", "Power On/Off"),
        ("f", "set_flame_speed", "Flame Speed"),
        ("b", "toggle_brightness", "Brightness"),
        ("h", "cycle_heat_mode", "Heat Mode"),
        ("t", "toggle_timer", "Timer"),
        ("u", "toggle_temp_unit", "Temp Unit"),
    ]

    def __init__(self, client: FlameConnectClient) -> None:
        super().__init__()
        self.client = client
        self.fire_id: str | None = None
        self.fires: list[Fire] = []
        self._write_in_progress = False

    def compose(self) -> ComposeResult:
        """Compose the initial app layout with fireplace selector."""
        yield Header()
        yield Static("[bold]Loading fireplaces...[/bold]", id="loading-label")
        yield Footer()

    def on_mount(self) -> None:
        """Fetch the list of fireplaces on startup."""
        self.call_after_refresh(self._load_fires)

    async def _load_fires(self) -> None:
        """Fetch fireplaces and either auto-select or show a list."""
        try:
            self.fires = await self.client.get_fires()
        except Exception as exc:
            _LOGGER.exception("Failed to fetch fireplaces")
            self.notify(f"Failed to load fireplaces: {exc}", severity="error")
            return

        loading = self.query_one("#loading-label", Static)

        if not self.fires:
            loading.update("[bold red]No fireplaces found.[/bold red]")
            return

        if len(self.fires) == 1:
            # Auto-select the only fireplace
            fire = self.fires[0]
            self.fire_id = fire.fire_id
            loading.remove()
            self._push_dashboard(fire)
            return

        # Show a selection list
        loading.update("[bold]Select a fireplace:[/bold]")
        options = [
            Option(
                f"{fire.friendly_name} ({fire.connection_state.name})",
                id=fire.fire_id,
            )
            for fire in self.fires
        ]
        selector = OptionList(*options, id="fire-selector")
        await self.mount(selector, before="#loading-label")

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle fireplace selection from the option list."""
        option_id = event.option.id
        if option_id is None:
            return

        for fire in self.fires:
            if fire.fire_id == option_id:
                self.fire_id = fire.fire_id
                self._push_dashboard(fire)
                break

    def show_auth_screen(
        self,
        auth_uri: str,
        redirect_uri: str,
        future: asyncio.Future[str],
    ) -> None:
        """Push the authentication modal and resolve *future* on dismiss."""
        from flameconnect.exceptions import AuthenticationError

        screen = AuthScreen(auth_uri=auth_uri, redirect_uri=redirect_uri)

        def _on_dismiss(result: str | None) -> None:
            if future.done():
                return
            if result is None:
                future.set_exception(
                    AuthenticationError("Authentication cancelled")
                )
            else:
                future.set_result(result)

        self.push_screen(screen, callback=_on_dismiss)

    def _push_dashboard(self, fire: Fire) -> None:
        """Push the dashboard screen for the selected fireplace.

        Args:
            fire: The selected Fire instance.
        """
        screen = DashboardScreen(
            client=self.client,
            fire_id=fire.fire_id,
            fire_name=fire.friendly_name,
        )
        self.push_screen(screen)

    async def action_refresh(self) -> None:
        """Handle the 'r' key binding to refresh the dashboard."""
        screen = self.screen
        if isinstance(screen, DashboardScreen):
            screen.log_message("Refreshing...")
            await screen.refresh_state()
            screen.log_message("Refresh complete")

    async def action_toggle_power(self) -> None:
        """Handle the 'p' key binding to toggle fireplace power."""
        import logging

        from flameconnect.models import FireMode

        screen = self.screen
        if not isinstance(screen, DashboardScreen):
            return

        if self.fire_id is None:
            screen.log_message("No fireplace selected", level=logging.WARNING)
            return

        if self._write_in_progress:
            return

        self._write_in_progress = True
        current_mode = screen.current_mode
        try:
            if current_mode is not None and current_mode.mode == FireMode.MANUAL:
                await self.client.turn_off(self.fire_id)
                screen.log_message("Turning off...")
            else:
                await self.client.turn_on(self.fire_id)
                screen.log_message("Turning on...")
            # Refresh after toggling
            await screen.refresh_state()
        except Exception as exc:
            _LOGGER.exception("Failed to toggle power")
            screen.log_message(f"Power toggle failed: {exc}", level=logging.ERROR)
        finally:
            self._write_in_progress = False

    async def action_set_flame_speed(self) -> None:
        """Handle the 'f' key binding to open flame speed dialog."""
        from flameconnect.models import FlameEffectParam
        from flameconnect.tui.flame_speed_screen import FlameSpeedScreen

        screen = self.screen
        if not isinstance(screen, DashboardScreen):
            return
        if self.fire_id is None:
            return

        params = screen.current_parameters
        current = params.get(FlameEffectParam)
        if not isinstance(current, FlameEffectParam):
            return

        current_speed = current.flame_speed

        def _on_speed_selected(speed: int | None) -> None:
            if speed is not None and speed != current_speed:
                self.run_worker(
                    self._apply_flame_speed(speed),
                    exclusive=True,
                    thread=False,
                )

        self.push_screen(
            FlameSpeedScreen(current_speed), callback=_on_speed_selected
        )

    async def _apply_flame_speed(self, speed: int) -> None:
        """Write the selected flame speed to the fireplace."""
        from flameconnect.models import FlameEffectParam

        screen = self.screen
        if not isinstance(screen, DashboardScreen):
            return
        if self.fire_id is None:
            return
        if self._write_in_progress:
            return

        self._write_in_progress = True
        try:
            params = screen.current_parameters
            current = params.get(FlameEffectParam)
            if not isinstance(current, FlameEffectParam):
                return
            new_param = replace(current, flame_speed=speed)
            await self.client.write_parameters(self.fire_id, [new_param])
            screen.log_message(f"Flame speed set to {speed}")
            await screen.refresh_state()
        except Exception as exc:
            _LOGGER.exception("Failed to set flame speed")
            screen.log_message(
                f"Flame speed change failed: {exc}", level=logging.ERROR
            )
        finally:
            self._write_in_progress = False

    async def action_toggle_brightness(self) -> None:
        """Handle the 'b' key binding to toggle brightness high/low."""
        from flameconnect.models import Brightness, FlameEffectParam

        screen = self.screen
        if not isinstance(screen, DashboardScreen):
            return
        if self.fire_id is None:
            return
        if self._write_in_progress:
            return

        self._write_in_progress = True
        try:
            params = screen.current_parameters
            current = params.get(FlameEffectParam)
            if not isinstance(current, FlameEffectParam):
                return
            new_brightness = (
                Brightness.LOW
                if current.brightness == Brightness.HIGH
                else Brightness.HIGH
            )
            new_param = replace(current, brightness=new_brightness)
            await self.client.write_parameters(self.fire_id, [new_param])
            label = "Low" if new_brightness == Brightness.LOW else "High"
            screen.log_message(f"Brightness set to {label}")
            await screen.refresh_state()
        except Exception as exc:
            _LOGGER.exception("Failed to toggle brightness")
            screen.log_message(f"Brightness toggle failed: {exc}", level=logging.ERROR)
        finally:
            self._write_in_progress = False

    async def action_cycle_heat_mode(self) -> None:
        """Handle the 'h' key binding to cycle heat mode."""
        from flameconnect.models import HeatMode, HeatParam

        screen = self.screen
        if not isinstance(screen, DashboardScreen):
            return
        if self.fire_id is None:
            return
        if self._write_in_progress:
            return

        self._write_in_progress = True
        try:
            params = screen.current_parameters
            current = params.get(HeatParam)
            if not isinstance(current, HeatParam):
                return
            modes = [HeatMode.NORMAL, HeatMode.BOOST, HeatMode.ECO, HeatMode.FAN_ONLY]
            try:
                idx = modes.index(current.heat_mode)
            except ValueError:
                idx = -1
            new_mode = modes[(idx + 1) % len(modes)]
            new_param = replace(current, heat_mode=new_mode)
            await self.client.write_parameters(self.fire_id, [new_param])
            mode_label = new_mode.name.replace("_", " ").title()
            screen.log_message(f"Heat mode set to {mode_label}")
            await screen.refresh_state()
        except Exception as exc:
            _LOGGER.exception("Failed to cycle heat mode")
            screen.log_message(f"Heat mode change failed: {exc}", level=logging.ERROR)
        finally:
            self._write_in_progress = False

    async def action_toggle_timer(self) -> None:
        """Handle the 't' key binding to toggle the timer."""
        from flameconnect.models import TimerParam, TimerStatus

        screen = self.screen
        if not isinstance(screen, DashboardScreen):
            return
        if self.fire_id is None:
            return
        if self._write_in_progress:
            return

        self._write_in_progress = True
        try:
            params = screen.current_parameters
            current = params.get(TimerParam)
            if not isinstance(current, TimerParam):
                return
            if current.timer_status == TimerStatus.ENABLED:
                new_param = TimerParam(timer_status=TimerStatus.DISABLED, duration=0)
                screen.log_message("Timer disabled")
            else:
                new_param = TimerParam(timer_status=TimerStatus.ENABLED, duration=60)
                screen.log_message("Timer enabled (60 min)")
            await self.client.write_parameters(self.fire_id, [new_param])
            await screen.refresh_state()
        except Exception as exc:
            _LOGGER.exception("Failed to toggle timer")
            screen.log_message(f"Timer toggle failed: {exc}", level=logging.ERROR)
        finally:
            self._write_in_progress = False

    async def action_toggle_temp_unit(self) -> None:
        """Handle the 'u' key binding to toggle temperature unit."""
        from flameconnect.models import TempUnit, TempUnitParam

        screen = self.screen
        if not isinstance(screen, DashboardScreen):
            return
        if self.fire_id is None:
            return
        if self._write_in_progress:
            return

        self._write_in_progress = True
        try:
            params = screen.current_parameters
            current = params.get(TempUnitParam)
            if not isinstance(current, TempUnitParam):
                return
            new_unit = (
                TempUnit.CELSIUS
                if current.unit == TempUnit.FAHRENHEIT
                else TempUnit.FAHRENHEIT
            )
            new_param = TempUnitParam(unit=new_unit)
            await self.client.write_parameters(self.fire_id, [new_param])
            unit_label = (
                "Celsius"
                if new_unit == TempUnit.CELSIUS
                else "Fahrenheit"
            )
            screen.log_message(
                f"Temperature unit set to {unit_label}"
            )
            await screen.refresh_state()
        except Exception as exc:
            _LOGGER.exception("Failed to toggle temperature unit")
            screen.log_message(
                f"Temperature unit toggle failed: {exc}",
                level=logging.ERROR,
            )
        finally:
            self._write_in_progress = False


async def run_tui(*, verbose: bool = False) -> None:
    """Launch the FlameConnect TUI dashboard.

    Creates an authenticated client and runs the Textual application.
    The client session is managed via an async context manager.

    Args:
        verbose: When True, set the flameconnect logger to DEBUG so that
            all log messages appear in the TUI messages panel.
    """
    import asyncio

    from flameconnect.auth import MsalAuth
    from flameconnect.client import FlameConnectClient

    app: FlameConnectApp | None = None

    async def _tui_auth_prompt(auth_uri: str, redirect_uri: str) -> str:
        """Show a Textual modal for credential entry.

        Uses an asyncio.Future so the Textual event loop keeps running
        while the user interacts with the auth dialog.
        """
        assert app is not None  # noqa: S101
        loop = asyncio.get_running_loop()
        future: asyncio.Future[str] = loop.create_future()
        app.show_auth_screen(auth_uri, redirect_uri, future)
        return await future

    # Suppress stderr log output so it doesn't corrupt the TUI rendering.
    # The DashboardScreen installs its own handler to capture logs in-app.
    root_logger = logging.getLogger()
    saved_handlers: list[logging.Handler] = []
    for handler in root_logger.handlers[:]:
        if isinstance(handler, logging.StreamHandler):
            root_logger.removeHandler(handler)
            saved_handlers.append(handler)

    # Only promote to DEBUG when the user passed -v/--verbose.
    fc_logger = logging.getLogger("flameconnect")
    prev_level = fc_logger.level
    if verbose:
        fc_logger.setLevel(logging.DEBUG)

    auth = MsalAuth(prompt_callback=_tui_auth_prompt)
    try:
        async with FlameConnectClient(auth=auth) as client:
            app = FlameConnectApp(client)
            await app.run_async()
    finally:
        # Defensive terminal cleanup using terminfo.  Textual hardcodes
        # xterm escape codes, but in GNU Screen / tmux without altscreen
        # the alternate buffer is a no-op, so the TUI content stays on the
        # main buffer.  Sending `clear` after rmcup/cnorm guarantees a
        # clean exit in every environment.
        import curses as _curses

        try:
            _curses.setupterm(fd=sys.__stderr__.fileno())
            rmcup = _curses.tigetstr("rmcup") or b""
            cnorm = _curses.tigetstr("cnorm") or b""
            clear = _curses.tigetstr("clear") or b""
            sys.__stderr__.buffer.write(rmcup + cnorm + clear)
            sys.__stderr__.flush()
        except Exception:  # noqa: BLE001
            pass

        # Restore the logger state so post-TUI CLI output works normally.
        fc_logger.setLevel(prev_level)
        for handler in saved_handlers:
            root_logger.addHandler(handler)
