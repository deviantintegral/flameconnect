"""Custom Textual widgets for the FlameConnect TUI."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import Static

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from flameconnect.models import (
        ConnectionState,
        ErrorParam,
        FlameEffectParam,
        HeatModeParam,
        HeatParam,
        LogEffectParam,
        ModeParam,
        Parameter,
        RGBWColor,
        SoftwareVersionParam,
        SoundParam,
        TempUnitParam,
        TimerParam,
    )


def _format_rgbw(color: RGBWColor) -> str:
    """Format an RGBW color value for display."""
    return f"R:{color.red} G:{color.green} B:{color.blue} W:{color.white}"


def _format_mode(param: ModeParam) -> str:
    """Format the mode parameter for display."""
    return (
        f"[bold]Mode:[/bold] {param.mode.name}  |  "
        f"[bold]Temperature:[/bold] {param.temperature}\u00b0"
    )


def _format_flame_effect(param: FlameEffectParam) -> str:
    """Format the flame effect parameter for display."""
    lines = [
        f"[bold]Flame Effect:[/bold] {param.flame_effect.name}  |  "
        f"Speed: {param.flame_speed}/5  |  "
        f"Brightness: {param.brightness}",
        f"  Flame Color: {param.flame_color.name}  |  "
        f"Light: {param.light_status.name}  |  "
        f"Ambient Sensor: {param.ambient_sensor.name}",
        f"  Media Theme: {param.media_theme.name}  |  "
        f"Media Light: {param.media_light.name}  |  "
        f"Media Color: {_format_rgbw(param.media_color)}",
        f"  Overhead Light: {param.overhead_light.name}  |  "
        f"Overhead Color: {_format_rgbw(param.overhead_color)}",
    ]
    return "\n".join(lines)


def _format_heat(param: HeatParam) -> str:
    """Format the heat settings parameter for display."""
    return (
        f"[bold]Heat:[/bold] {param.heat_status.name}  |  "
        f"Mode: {param.heat_mode.name}  |  "
        f"Setpoint: {param.setpoint_temperature}\u00b0  |  "
        f"Boost: {param.boost_duration}min"
    )


def _format_heat_mode(param: HeatModeParam) -> str:
    """Format the heat mode/control parameter for display."""
    return f"[bold]Heat Control:[/bold] {param.heat_control.name}"


def _format_timer(param: TimerParam) -> str:
    """Format the timer parameter for display."""
    return (
        f"[bold]Timer:[/bold] {param.timer_status.name}  |  "
        f"Duration: {param.duration}min"
    )


def _format_software_version(param: SoftwareVersionParam) -> str:
    """Format the software version parameter for display."""
    return (
        f"[bold]Software:[/bold] "
        f"UI {param.ui_major}.{param.ui_minor}.{param.ui_test}  |  "
        f"Control {param.control_major}.{param.control_minor}.{param.control_test}  |  "
        f"Relay {param.relay_major}.{param.relay_minor}.{param.relay_test}"
    )


def _format_error(param: ErrorParam) -> str:
    """Format the error parameter for display."""
    has_error = any(
        b != 0
        for b in (
            param.error_byte1,
            param.error_byte2,
            param.error_byte3,
            param.error_byte4,
        )
    )
    if has_error:
        return (
            f"[bold red]Error:[/bold red] "
            f"0x{param.error_byte1:02X} 0x{param.error_byte2:02X} "
            f"0x{param.error_byte3:02X} 0x{param.error_byte4:02X}"
        )
    return "[bold]Error:[/bold] None"


def _format_temp_unit(param: TempUnitParam) -> str:
    """Format the temperature unit parameter for display."""
    return f"[bold]Temp Unit:[/bold] {param.unit.name}"


def _format_sound(param: SoundParam) -> str:
    """Format the sound parameter for display."""
    return f"[bold]Sound:[/bold] Volume {param.volume}  |  File: {param.sound_file}"


def _format_log_effect(param: LogEffectParam) -> str:
    """Format the log effect parameter for display."""
    return (
        f"[bold]Log Effect:[/bold] {param.log_effect.name}  |  "
        f"Color: {_format_rgbw(param.color)}  |  "
        f"Pattern: {param.pattern}"
    )


def format_parameters(params: list[Parameter]) -> str:
    """Format a list of parameters into a Rich-markup string for display.

    Args:
        params: A list of parameter dataclass instances.

    Returns:
        A multi-line string with Rich markup formatting.
    """
    from flameconnect.models import (
        ErrorParam,
        FlameEffectParam,
        HeatModeParam,
        HeatParam,
        LogEffectParam,
        ModeParam,
        SoftwareVersionParam,
        SoundParam,
        TempUnitParam,
        TimerParam,
    )

    lines: list[str] = []
    for param in params:
        if isinstance(param, ModeParam):
            lines.append(_format_mode(param))
        elif isinstance(param, FlameEffectParam):
            lines.append(_format_flame_effect(param))
        elif isinstance(param, HeatParam):
            lines.append(_format_heat(param))
        elif isinstance(param, HeatModeParam):
            lines.append(_format_heat_mode(param))
        elif isinstance(param, TimerParam):
            lines.append(_format_timer(param))
        elif isinstance(param, SoftwareVersionParam):
            lines.append(_format_software_version(param))
        elif isinstance(param, ErrorParam):
            lines.append(_format_error(param))
        elif isinstance(param, TempUnitParam):
            lines.append(_format_temp_unit(param))
        elif isinstance(param, SoundParam):
            lines.append(_format_sound(param))
        elif isinstance(param, LogEffectParam):
            lines.append(_format_log_effect(param))

    if not lines:
        return "[dim]No parameters available[/dim]"

    return "\n".join(lines)


def _format_connection_state(state: ConnectionState) -> str:
    """Format connection state with appropriate color markup."""
    from flameconnect.models import ConnectionState as CS

    color_map: dict[CS, str] = {
        CS.CONNECTED: "green",
        CS.NOT_CONNECTED: "red",
        CS.UPDATING_FIRMWARE: "yellow",
        CS.UNKNOWN: "dim",
    }
    color = color_map.get(state, "dim")
    return f"[{color}]{state.name}[/{color}]"


class FireplaceVisual(Static):
    """Static ASCII-art fireplace visual (placeholder for future animation)."""

    def render(self) -> str:
        """Render the ASCII fireplace art with Rich markup."""
        return (
            "[dim]┌──────────────────────┐[/dim]\n"
            "[dim]│[/dim]    [dim]╱╲      ╱╲[/dim]    [dim]│[/dim]\n"
            "[dim]│[/dim]   [yellow]╱[/yellow][red]@@[/red][yellow]╲[/yellow]  [yellow]╱[/yellow][red]@@[/red][yellow]╲[/yellow]   [dim]│[/dim]\n"
            "[dim]│[/dim]  [yellow]╱[/yellow][red]@@@@[/red][yellow]╲╱[/yellow][red]@@@@[/red][yellow]╲[/yellow]  [dim]│[/dim]\n"
            "[dim]│[/dim]  [yellow]║[/yellow][red]@@@@@@@@@@@@[/red][yellow]║[/yellow]  [dim]│[/dim]\n"
            "[dim]│[/dim]  [yellow]║[/yellow][red]@@[/red][yellow]@@[/yellow][red]@@[/red][yellow]@@[/yellow][red]@@[/red][yellow]@@[/yellow][yellow]║[/yellow]  [dim]│[/dim]\n"
            "[dim]│[/dim]   [yellow]║[/yellow][yellow]@@[/yellow][red]@@@@[/red][yellow]@@[/yellow][yellow]║[/yellow]   [dim]│[/dim]\n"
            "[dim]│[/dim]    [yellow]║[/yellow][yellow]@@@@@@[/yellow][yellow]║[/yellow]    [dim]│[/dim]\n"
            "[dim]│[/dim]     [yellow]╚════╝[/yellow]     [dim]│[/dim]\n"
            "[dim]│[/dim]  [dim]══════════════[/dim]  [dim]│[/dim]\n"
            "[dim]│[/dim]  [dim]║            ║[/dim]  [dim]│[/dim]\n"
            "[dim]└──────────────────────┘[/dim]"
        )


class FireplaceInfo(Static):
    """Widget showing fire name, ID, and connection state."""

    fire_name: reactive[str] = reactive("--")
    fire_id: reactive[str] = reactive("--")
    connection: reactive[str] = reactive("UNKNOWN")

    def render(self) -> str:
        """Render the fireplace info display."""
        return (
            f"[bold]{self.fire_name}[/bold]  |  "
            f"ID: {self.fire_id}  |  "
            f"Connection: {self.connection}"
        )


class ParameterPanel(Static):
    """Widget displaying all decoded parameters in a formatted panel."""

    content_text: reactive[str] = reactive("[dim]Loading...[/dim]")

    def render(self) -> str:
        """Render the parameter panel content."""
        return self.content_text

    def watch_content_text(self) -> None:
        """Force a layout recalculation when content changes."""
        self.refresh(layout=True)

    def update_parameters(self, params: list[Parameter]) -> None:
        """Update the panel with new parameter data.

        Args:
            params: A list of parameter dataclass instances.
        """
        self.content_text = format_parameters(params)


class FireplaceSelector(Vertical):
    """Widget for selecting a fireplace from a list."""

    def compose(self) -> ComposeResult:
        """Compose the fireplace selector layout."""
        yield Static("[bold]Select a fireplace:[/bold]", id="selector-title")
        yield Vertical(id="fire-list")
