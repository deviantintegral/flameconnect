"""Main Textual application for the FlameConnect TUI."""

from __future__ import annotations

import logging
import subprocess
import sys
from dataclasses import replace
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Awaitable

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.command import Hit, Hits, Provider
from textual.widgets import Footer, Header, OptionList, Static
from textual.widgets.option_list import Option

from flameconnect import __version__
from flameconnect.tui.auth_screen import AuthScreen
from flameconnect.tui.screens import DashboardScreen
from flameconnect.tui.widgets import _display_name

if TYPE_CHECKING:
    import asyncio

    from flameconnect.client import FlameConnectClient
    from flameconnect.models import (
        Fire,
        FlameColor,
        HeatMode,
        MediaTheme,
        RGBWColor,
    )

_LOGGER = logging.getLogger(__name__)


def _resolve_version() -> str:
    """Return a human-readable build identifier.

    Strategy:
    1. If the current commit has a tag matching ``__version__``, return
       ``v{__version__}`` (e.g. ``v0.1.0``).
    2. Otherwise return the short git hash, with a ``-dirty`` suffix when
       the working tree has uncommitted changes **or** untracked files.
    3. If git is unavailable (not installed, not a repo, timeout), fall
       back to ``v{__version__}``.
    """
    try:
        tag_result = subprocess.run(
            ["git", "describe", "--tags", "--exact-match", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if tag_result.returncode == 0 and __version__ in tag_result.stdout.strip():
            return f"v{__version__}"

        hash_result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if hash_result.returncode != 0:
            return f"v{__version__}"

        short_hash = hash_result.stdout.strip()

        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if status_result.returncode == 0 and status_result.stdout.strip():
            short_hash += "-dirty"

        return short_hash
    except Exception:  # noqa: BLE001
        return f"v{__version__}"


_resolved_version: str = _resolve_version()

_CONTROL_COMMANDS: list[tuple[str, str, str]] = [
    ("Power On/Off", "Toggle fireplace power", "toggle_power"),
    ("Flame Effect", "Toggle flame effect on/off", "toggle_flame_effect"),
    ("Flame Color", "Set flame color", "set_flame_color"),
    ("Flame Speed", "Set flame speed", "set_flame_speed"),
    ("Brightness", "Toggle brightness high/low", "toggle_brightness"),
    ("Pulsating", "Toggle pulsating effect", "toggle_pulsating"),
    ("Media Theme", "Set media theme", "set_media_theme"),
    ("Media Light", "Toggle media light on/off", "toggle_media_light"),
    ("Media Color", "Set media color", "set_media_color"),
    ("Overhead Light", "Toggle overhead light on/off", "toggle_overhead_light"),
    ("Overhead Color", "Set overhead color", "set_overhead_color"),
    ("Ambient Sensor", "Toggle ambient sensor", "toggle_ambient_sensor"),
    ("Heat On/Off", "Toggle heater on/off", "toggle_heat"),
    ("Heat Mode", "Set heat mode", "set_heat_mode"),
    ("Switch Fire", "Switch between fireplaces", "switch_fire"),
    ("Timer", "Toggle timer on/off", "toggle_timer"),
    ("Temp Unit", "Toggle temperature unit (°C/°F)", "toggle_temp_unit"),
    ("Set Temperature", "Adjust heater setpoint temperature", "set_temperature"),
]


class FireplaceCommandsProvider(Provider):
    """Command palette provider exposing fireplace control actions."""

    async def search(self, query: str) -> Hits:
        matcher = self.matcher(query)
        for name, help_text, action in _CONTROL_COMMANDS:
            score = matcher.match(name)
            if score > 0:
                yield Hit(
                    score,
                    matcher.highlight(name),
                    partial(self.app.run_action, action),
                    help=help_text,
                )


def _get_fireplace_commands() -> type[FireplaceCommandsProvider]:
    return FireplaceCommandsProvider


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

    TITLE = f"FlameConnect {_resolved_version}"
    CSS = _APP_CSS
    COMMANDS = App.COMMANDS | {_get_fireplace_commands}

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("question_mark", "toggle_help", "Help"),
        Binding("ctrl+p", "command_palette", "Palette", show=False, priority=True),
        Binding("p", "toggle_power", "Power On/Off", show=False),
        Binding("e", "toggle_flame_effect", "Flame Effect", show=False),
        Binding("c", "set_flame_color", "Flame Color", show=False),
        Binding("f", "set_flame_speed", "Flame Speed", show=False),
        Binding("b", "toggle_brightness", "Brightness", show=False),
        Binding("g", "toggle_pulsating", "Pulsating", show=False),
        Binding("m", "set_media_theme", "Media Theme", show=False),
        Binding("l", "toggle_media_light", "Media Light", show=False),
        Binding("d", "set_media_color", "Media Color", show=False),
        Binding("o", "toggle_overhead_light", "Overhead Light", show=False),
        Binding("v", "set_overhead_color", "Overhead Color", show=False),
        Binding("a", "toggle_ambient_sensor", "Ambient Sensor", show=False),
        Binding("s", "toggle_heat", "Heat On/Off", show=False),
        Binding("h", "set_heat_mode", "Heat Mode", show=False),
        Binding("w", "switch_fire", "Switch Fire", show=False),
        Binding("t", "toggle_timer", "Timer", show=False),
        Binding("u", "toggle_temp_unit", "Temp Unit", show=False),
        Binding("n", "set_temperature", "Set Temp", show=False),
    ]

    def __init__(self, client: FlameConnectClient) -> None:
        super().__init__()
        self.client = client
        self.fire_id: str | None = None
        self.fires: list[Fire] = []
        self._write_in_progress = False
        self._help_visible: bool = False

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
                f"{fire.friendly_name} ({_display_name(fire.connection_state)})",
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
        screen = DashboardScreen(client=self.client, fire=fire)
        self.push_screen(screen)

    def _run_command(
        self,
        coro: Awaitable[object],
        feedback: str,
        error_prefix: str,
    ) -> None:
        """Log *feedback* immediately and run *coro* in a background worker.

        This ensures the user sees the message before the API call starts,
        even when invoked from the command palette (which batches updates).
        """
        screen = self.screen
        if not isinstance(screen, DashboardScreen):
            return
        self._write_in_progress = True
        screen.log_message(feedback)

        async def _worker() -> None:
            try:
                await coro
                s = self.screen
                if isinstance(s, DashboardScreen):
                    await s.refresh_state()
            except Exception as exc:
                _LOGGER.exception(error_prefix)
                s = self.screen
                if isinstance(s, DashboardScreen):
                    s.log_message(f"{error_prefix}: {exc}", level=logging.ERROR)
            finally:
                self._write_in_progress = False

        self.run_worker(_worker(), exclusive=True, thread=False)

    async def action_refresh(self) -> None:
        """Handle the 'r' key binding to refresh the dashboard."""
        screen = self.screen
        if isinstance(screen, DashboardScreen):
            screen.log_message("Refreshing...")
            await screen.refresh_state()
            screen.log_message("Refresh complete")

    def action_toggle_help(self) -> None:
        """Toggle the help panel open or closed."""
        if self._help_visible:
            self.action_hide_help_panel()
            self._help_visible = False
        else:
            self.action_show_help_panel()
            self._help_visible = True

    def deliver_screenshot(
        self,
        filename: str | None = None,
        path: str | None = None,
        time_format: str | None = None,
    ) -> str | None:
        """Deliver a screenshot, creating the save directory if needed."""
        from platformdirs import user_downloads_path

        save_dir = Path(path) if path else user_downloads_path()
        save_dir.mkdir(parents=True, exist_ok=True)
        return super().deliver_screenshot(filename, str(save_dir), time_format)

    def action_toggle_power(self) -> None:
        """Handle the 'p' key binding to toggle fireplace power."""
        from flameconnect.models import FireMode

        screen = self.screen
        if not isinstance(screen, DashboardScreen):
            return
        if self.fire_id is None:
            screen.log_message("No fireplace selected", level=logging.WARNING)
            return
        if self._write_in_progress:
            return

        current_mode = screen.current_mode
        if current_mode is not None and current_mode.mode == FireMode.MANUAL:
            self._run_command(
                self.client.turn_off(self.fire_id),
                "Turning off...",
                "Power toggle failed",
            )
        else:
            self._run_command(
                self.client.turn_on(self.fire_id),
                "Turning on...",
                "Power toggle failed",
            )

    def action_set_flame_speed(self) -> None:
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
                self.call_later(self._apply_flame_speed, speed)

        self.push_screen(
            FlameSpeedScreen(current_speed), callback=_on_speed_selected
        )

    def _apply_flame_speed(self, speed: int) -> None:
        """Write the selected flame speed to the fireplace."""
        from flameconnect.models import FlameEffectParam

        screen = self.screen
        if not isinstance(screen, DashboardScreen):
            return
        if self.fire_id is None or self._write_in_progress:
            return

        params = screen.current_parameters
        current = params.get(FlameEffectParam)
        if not isinstance(current, FlameEffectParam):
            return
        new_param = replace(current, flame_speed=speed)
        self._run_command(
            self.client.write_parameters(self.fire_id, [new_param]),
            f"Setting flame speed to {speed}...",
            "Flame speed change failed",
        )

    def action_toggle_brightness(self) -> None:
        """Handle the 'b' key binding to toggle brightness high/low."""
        from flameconnect.models import Brightness, FlameEffectParam

        screen = self.screen
        if not isinstance(screen, DashboardScreen):
            return
        if self.fire_id is None or self._write_in_progress:
            return

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
        label = "Low" if new_brightness == Brightness.LOW else "High"
        self._run_command(
            self.client.write_parameters(self.fire_id, [new_param]),
            f"Setting brightness to {label}...",
            "Brightness toggle failed",
        )

    def action_toggle_flame_effect(self) -> None:
        """Handle the 'e' key binding to toggle flame effect on/off."""
        from flameconnect.models import FlameEffect, FlameEffectParam

        screen = self.screen
        if not isinstance(screen, DashboardScreen):
            return
        if self.fire_id is None or self._write_in_progress:
            return

        params = screen.current_parameters
        current = params.get(FlameEffectParam)
        if not isinstance(current, FlameEffectParam):
            return
        new_val = (
            FlameEffect.OFF
            if current.flame_effect == FlameEffect.ON
            else FlameEffect.ON
        )
        new_param = replace(current, flame_effect=new_val)
        label = "On" if new_val == FlameEffect.ON else "Off"
        self._run_command(
            self.client.write_parameters(self.fire_id, [new_param]),
            f"Setting flame effect to {label}...",
            "Flame effect toggle failed",
        )

    def action_toggle_pulsating(self) -> None:
        """Handle the 'g' key binding to toggle pulsating on/off."""
        from flameconnect.models import FlameEffectParam, PulsatingEffect

        screen = self.screen
        if not isinstance(screen, DashboardScreen):
            return
        if self.fire_id is None or self._write_in_progress:
            return

        params = screen.current_parameters
        current = params.get(FlameEffectParam)
        if not isinstance(current, FlameEffectParam):
            return
        new_val = (
            PulsatingEffect.OFF
            if current.pulsating_effect == PulsatingEffect.ON
            else PulsatingEffect.ON
        )
        new_param = replace(current, pulsating_effect=new_val)
        label = "On" if new_val == PulsatingEffect.ON else "Off"
        self._run_command(
            self.client.write_parameters(self.fire_id, [new_param]),
            f"Setting pulsating to {label}...",
            "Pulsating toggle failed",
        )

    def action_toggle_media_light(self) -> None:
        """Handle the 'l' key binding to toggle media light on/off."""
        from flameconnect.models import FlameEffectParam, LightStatus

        screen = self.screen
        if not isinstance(screen, DashboardScreen):
            return
        if self.fire_id is None or self._write_in_progress:
            return

        params = screen.current_parameters
        current = params.get(FlameEffectParam)
        if not isinstance(current, FlameEffectParam):
            return
        new_val = (
            LightStatus.OFF
            if current.media_light == LightStatus.ON
            else LightStatus.ON
        )
        new_param = replace(current, media_light=new_val)
        label = "On" if new_val == LightStatus.ON else "Off"
        self._run_command(
            self.client.write_parameters(self.fire_id, [new_param]),
            f"Setting media light to {label}...",
            "Media light toggle failed",
        )

    def action_toggle_overhead_light(self) -> None:
        """Handle the 'o' key binding to toggle overhead light on/off."""
        from flameconnect.models import FlameEffectParam, LightStatus

        screen = self.screen
        if not isinstance(screen, DashboardScreen):
            return
        if self.fire_id is None or self._write_in_progress:
            return

        params = screen.current_parameters
        current = params.get(FlameEffectParam)
        if not isinstance(current, FlameEffectParam):
            return
        new_val = (
            LightStatus.OFF
            if current.light_status == LightStatus.ON
            else LightStatus.ON
        )
        new_param = replace(current, light_status=new_val)
        label = "On" if new_val == LightStatus.ON else "Off"
        self._run_command(
            self.client.write_parameters(self.fire_id, [new_param]),
            f"Setting overhead light to {label}...",
            "Overhead light toggle failed",
        )

    def action_toggle_ambient_sensor(self) -> None:
        """Handle the 'a' key binding to toggle ambient sensor on/off."""
        from flameconnect.models import FlameEffectParam, LightStatus

        screen = self.screen
        if not isinstance(screen, DashboardScreen):
            return
        if self.fire_id is None or self._write_in_progress:
            return

        params = screen.current_parameters
        current = params.get(FlameEffectParam)
        if not isinstance(current, FlameEffectParam):
            return
        new_val = (
            LightStatus.OFF
            if current.ambient_sensor == LightStatus.ON
            else LightStatus.ON
        )
        new_param = replace(current, ambient_sensor=new_val)
        label = "On" if new_val == LightStatus.ON else "Off"
        self._run_command(
            self.client.write_parameters(self.fire_id, [new_param]),
            f"Setting ambient sensor to {label}...",
            "Ambient sensor toggle failed",
        )

    def action_set_flame_color(self) -> None:
        """Handle the 'c' key binding to open flame color dialog."""
        from flameconnect.models import FlameEffectParam
        from flameconnect.tui.flame_color_screen import FlameColorScreen

        screen = self.screen
        if not isinstance(screen, DashboardScreen):
            return
        if self.fire_id is None:
            return

        params = screen.current_parameters
        current = params.get(FlameEffectParam)
        if not isinstance(current, FlameEffectParam):
            return

        current_color = current.flame_color

        def _on_color_selected(color: FlameColor | None) -> None:
            if color is not None and color != current_color:
                self.call_later(self._apply_flame_color, color)

        self.push_screen(
            FlameColorScreen(current_color), callback=_on_color_selected
        )

    def _apply_flame_color(self, color: FlameColor) -> None:
        """Write the selected flame color to the fireplace."""
        from flameconnect.models import FlameEffectParam

        screen = self.screen
        if not isinstance(screen, DashboardScreen):
            return
        if self.fire_id is None or self._write_in_progress:
            return

        params = screen.current_parameters
        current = params.get(FlameEffectParam)
        if not isinstance(current, FlameEffectParam):
            return
        new_param = replace(current, flame_color=color)
        label = _display_name(color)
        self._run_command(
            self.client.write_parameters(self.fire_id, [new_param]),
            f"Setting flame color to {label}...",
            "Flame color change failed",
        )

    def action_set_media_theme(self) -> None:
        """Handle the 'm' key binding to open media theme dialog."""
        from flameconnect.models import FlameEffectParam
        from flameconnect.tui.media_theme_screen import MediaThemeScreen

        screen = self.screen
        if not isinstance(screen, DashboardScreen):
            return
        if self.fire_id is None:
            return

        params = screen.current_parameters
        current = params.get(FlameEffectParam)
        if not isinstance(current, FlameEffectParam):
            return

        current_theme = current.media_theme

        def _on_theme_selected(theme: MediaTheme | None) -> None:
            if theme is not None and theme != current_theme:
                self.call_later(self._apply_media_theme, theme)

        self.push_screen(
            MediaThemeScreen(current_theme), callback=_on_theme_selected
        )

    def _apply_media_theme(self, theme: MediaTheme) -> None:
        """Write the selected media theme to the fireplace."""
        from flameconnect.models import FlameEffectParam

        screen = self.screen
        if not isinstance(screen, DashboardScreen):
            return
        if self.fire_id is None or self._write_in_progress:
            return

        params = screen.current_parameters
        current = params.get(FlameEffectParam)
        if not isinstance(current, FlameEffectParam):
            return

        _LOGGER.debug("Media theme change: current=%s", current)

        new_param = replace(current, media_theme=theme)

        _LOGGER.debug("Media theme change: sending=%s", new_param)

        label = _display_name(theme)
        fire_id = self.fire_id
        self._write_in_progress = True
        screen.log_message(f"Setting media theme to {label}...")

        async def _worker() -> None:
            try:
                await self.client.write_parameters(fire_id, [new_param])
                s = self.screen
                if isinstance(s, DashboardScreen):
                    await s.refresh_state()
                    refreshed_params = s.current_parameters
                    refreshed = refreshed_params.get(FlameEffectParam)
                    _LOGGER.debug(
                        "Media theme change: after_refresh=%s", refreshed
                    )
            except Exception as exc:
                _LOGGER.exception("Media theme change failed")
                s = self.screen
                if isinstance(s, DashboardScreen):
                    s.log_message(
                        f"Media theme change failed: {exc}",
                        level=logging.ERROR,
                    )
            finally:
                self._write_in_progress = False

        self.run_worker(_worker(), exclusive=True, thread=False)

    def action_set_media_color(self) -> None:
        """Handle the 'd' key binding to open media color dialog."""
        from flameconnect.models import FlameEffectParam
        from flameconnect.tui.color_screen import ColorScreen

        screen = self.screen
        if not isinstance(screen, DashboardScreen):
            return
        if self.fire_id is None:
            return

        params = screen.current_parameters
        current = params.get(FlameEffectParam)
        if not isinstance(current, FlameEffectParam):
            return

        def _on_color_selected(color: RGBWColor | None) -> None:
            if color is not None:
                self.call_later(self._apply_media_color, color)

        self.push_screen(
            ColorScreen(current.media_color, "Media Color"),
            callback=_on_color_selected,
        )

    def _apply_media_color(self, color: RGBWColor) -> None:
        """Write the selected media color to the fireplace."""
        from flameconnect.models import FlameEffectParam

        screen = self.screen
        if not isinstance(screen, DashboardScreen):
            return
        if self.fire_id is None or self._write_in_progress:
            return

        params = screen.current_parameters
        current = params.get(FlameEffectParam)
        if not isinstance(current, FlameEffectParam):
            return
        new_param = replace(current, media_color=color)
        self._run_command(
            self.client.write_parameters(self.fire_id, [new_param]),
            f"Setting media color to R={color.red} G={color.green} "
            f"B={color.blue} W={color.white}...",
            "Media color change failed",
        )

    def action_set_overhead_color(self) -> None:
        """Handle the 'v' key binding to open overhead color dialog."""
        from flameconnect.models import FlameEffectParam
        from flameconnect.tui.color_screen import ColorScreen

        screen = self.screen
        if not isinstance(screen, DashboardScreen):
            return
        if self.fire_id is None:
            return

        params = screen.current_parameters
        current = params.get(FlameEffectParam)
        if not isinstance(current, FlameEffectParam):
            return

        def _on_color_selected(color: RGBWColor | None) -> None:
            if color is not None:
                self.call_later(self._apply_overhead_color, color)

        self.push_screen(
            ColorScreen(current.overhead_color, "Overhead Color"),
            callback=_on_color_selected,
        )

    def _apply_overhead_color(self, color: RGBWColor) -> None:
        """Write the selected overhead color to the fireplace."""
        from flameconnect.models import FlameEffectParam

        screen = self.screen
        if not isinstance(screen, DashboardScreen):
            return
        if self.fire_id is None or self._write_in_progress:
            return

        params = screen.current_parameters
        current = params.get(FlameEffectParam)
        if not isinstance(current, FlameEffectParam):
            return
        new_param = replace(current, overhead_color=color)
        self._run_command(
            self.client.write_parameters(self.fire_id, [new_param]),
            f"Setting overhead color to R={color.red} G={color.green} "
            f"B={color.blue} W={color.white}...",
            "Overhead color change failed",
        )

    def action_toggle_heat(self) -> None:
        """Handle the 's' key binding to toggle heater on/off."""
        from flameconnect.models import HeatParam, HeatStatus

        screen = self.screen
        if not isinstance(screen, DashboardScreen):
            return
        if self.fire_id is None or self._write_in_progress:
            return

        params = screen.current_parameters
        current = params.get(HeatParam)
        if not isinstance(current, HeatParam):
            return
        new_val = (
            HeatStatus.OFF
            if current.heat_status == HeatStatus.ON
            else HeatStatus.ON
        )
        new_param = replace(current, heat_status=new_val)
        label = "On" if new_val == HeatStatus.ON else "Off"
        self._run_command(
            self.client.write_parameters(
                self.fire_id, [new_param]
            ),
            f"Setting heat to {label}...",
            "Heat toggle failed",
        )

    def action_set_heat_mode(self) -> None:
        """Handle the 'h' key binding to open heat mode dialog."""
        from flameconnect.models import HeatParam
        from flameconnect.tui.heat_mode_screen import HeatModeScreen

        screen = self.screen
        if not isinstance(screen, DashboardScreen):
            return
        if self.fire_id is None:
            return

        params = screen.current_parameters
        current = params.get(HeatParam)
        if not isinstance(current, HeatParam):
            return

        def _on_selected(
            result: tuple[HeatMode, int | None] | None,
        ) -> None:
            if result is not None:
                mode, boost_minutes = result
                self.call_later(self._apply_heat_mode, mode, boost_minutes)

        self.push_screen(
            HeatModeScreen(current.heat_mode, current.boost_duration),
            callback=_on_selected,
        )

    def _apply_heat_mode(
        self, mode: HeatMode, boost_minutes: int | None
    ) -> None:
        """Write the selected heat mode to the fireplace."""
        from flameconnect.models import HeatMode, HeatParam

        screen = self.screen
        if not isinstance(screen, DashboardScreen):
            return
        if self.fire_id is None or self._write_in_progress:
            return

        params = screen.current_parameters
        current = params.get(HeatParam)
        if not isinstance(current, HeatParam):
            return
        if mode == HeatMode.BOOST and boost_minutes is not None:
            new_param = replace(
                current, heat_mode=mode, boost_duration=boost_minutes
            )
        else:
            new_param = replace(current, heat_mode=mode)
        mode_label = _display_name(mode)
        self._run_command(
            self.client.write_parameters(self.fire_id, [new_param]),
            f"Setting heat mode to {mode_label}...",
            "Heat mode change failed",
        )

    def action_set_temperature(self) -> None:
        """Handle the 'n' key binding to open temperature adjustment dialog."""
        from flameconnect.models import HeatParam, TempUnitParam
        from flameconnect.tui.temperature_screen import TemperatureScreen

        screen = self.screen
        if not isinstance(screen, DashboardScreen):
            return
        if self.fire_id is None:
            return

        params = screen.current_parameters
        heat_param = params.get(HeatParam)
        temp_unit = params.get(TempUnitParam)
        if not isinstance(heat_param, HeatParam):
            return
        if not isinstance(temp_unit, TempUnitParam):
            return

        current_temp = heat_param.setpoint_temperature

        def _on_temperature_dismiss(temp: float | None) -> None:
            if temp is not None and temp != current_temp:
                self.call_later(self._apply_temperature, temp)

        self.push_screen(
            TemperatureScreen(current_temp, temp_unit.unit),
            callback=_on_temperature_dismiss,
        )

    def _apply_temperature(self, temp: float) -> None:
        """Write the selected temperature to the fireplace."""
        from flameconnect.models import HeatParam

        screen = self.screen
        if not isinstance(screen, DashboardScreen):
            return
        if self.fire_id is None or self._write_in_progress:
            return

        params = screen.current_parameters
        current = params.get(HeatParam)
        if not isinstance(current, HeatParam):
            return
        new_param = replace(current, setpoint_temperature=temp)
        self._run_command(
            self.client.write_parameters(self.fire_id, [new_param]),
            f"Setting temperature to {temp}...",
            "Temperature change failed",
        )

    async def action_switch_fire(self) -> None:
        """Handle the 'w' key binding to switch between fireplaces."""
        from flameconnect.tui.fire_select_screen import FireSelectScreen

        try:
            self.fires = await self.client.get_fires()
        except Exception as exc:
            _LOGGER.exception("Failed to fetch fireplaces")
            self.notify(f"Failed to load fireplaces: {exc}", severity="error")
            return

        if len(self.fires) <= 1:
            self.notify("Only one fireplace available")
            return

        if self.fire_id is None:
            return

        def _on_selected(fire: Fire | None) -> None:
            if fire is not None:

                def _switch() -> None:
                    self.pop_screen()
                    self.fire_id = fire.fire_id
                    self._push_dashboard(fire)

                self.call_later(_switch)

        self.push_screen(
            FireSelectScreen(self.fires, self.fire_id),
            callback=_on_selected,
        )

    def action_toggle_timer(self) -> None:
        """Handle the 't' key binding to toggle the timer."""
        from flameconnect.models import TimerParam, TimerStatus
        from flameconnect.tui.timer_screen import TimerScreen

        screen = self.screen
        if not isinstance(screen, DashboardScreen):
            return
        if self.fire_id is None or self._write_in_progress:
            return

        params = screen.current_parameters
        current = params.get(TimerParam)
        if not isinstance(current, TimerParam):
            return
        if current.timer_status == TimerStatus.ENABLED:
            new_param = TimerParam(timer_status=TimerStatus.DISABLED, duration=0)
            feedback = "Disabling timer..."
            self._run_command(
                self.client.write_parameters(self.fire_id, [new_param]),
                feedback,
                "Timer toggle failed",
            )
        else:
            def _on_timer_dismiss(duration: int | None) -> None:
                if duration is not None:
                    self.call_later(self._apply_timer, duration)

            self.push_screen(
                TimerScreen(current.duration or 60),
                callback=_on_timer_dismiss,
            )

    def _apply_timer(self, duration: int) -> None:
        """Write the selected timer duration to the fireplace."""
        from flameconnect.models import TimerParam, TimerStatus

        screen = self.screen
        if not isinstance(screen, DashboardScreen):
            return
        if self.fire_id is None or self._write_in_progress:
            return
        new_param = TimerParam(timer_status=TimerStatus.ENABLED, duration=duration)
        feedback = f"Enabling timer ({duration} min)..."
        self._run_command(
            self.client.write_parameters(self.fire_id, [new_param]),
            feedback,
            "Timer toggle failed",
        )

    def action_toggle_temp_unit(self) -> None:
        """Handle the 'u' key binding to toggle temperature unit."""
        from flameconnect.models import TempUnit, TempUnitParam

        screen = self.screen
        if not isinstance(screen, DashboardScreen):
            return
        if self.fire_id is None or self._write_in_progress:
            return

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
        unit_label = "Celsius" if new_unit == TempUnit.CELSIUS else "Fahrenheit"
        self._run_command(
            self.client.write_parameters(self.fire_id, [new_param]),
            f"Setting temperature unit to {unit_label}...",
            "Temperature unit toggle failed",
        )


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
