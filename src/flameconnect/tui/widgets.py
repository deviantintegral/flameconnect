"""Custom Textual widgets for the FlameConnect TUI."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import Static

from flameconnect.models import FireMode

if TYPE_CHECKING:
    from enum import IntEnum

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


def _display_name(value: IntEnum) -> str:
    """Convert an enum member name to Title Case for display."""
    return value.name.replace("_", " ").title()


def _format_rgbw(color: RGBWColor) -> str:
    """Format an RGBW color value for display."""
    return (
        f"R:{color.red} G:{color.green} "
        f"B:{color.blue} W:{color.white}"
    )


_MODE_DISPLAY: dict[FireMode, str] = {
    FireMode.STANDBY: "Standby",
    FireMode.MANUAL: "On",
}


def _format_mode(param: ModeParam) -> str:
    """Format the mode parameter for display."""
    mode_label = _MODE_DISPLAY.get(
        param.mode, _display_name(param.mode)
    )
    return (
        f"[bold]Mode:[/bold] {mode_label}  |  "
        f"[bold]Target Temp:[/bold] "
        f"{param.target_temperature}\u00b0"
    )


def _format_flame_effect(param: FlameEffectParam) -> str:
    """Format the flame effect parameter for display."""
    lines = [
        (
            f"[bold]Flame Effect:[/bold] "
            f"{_display_name(param.flame_effect)}  |  "
            f"Speed: {param.flame_speed}/5  |  "
            f"Brightness: {_display_name(param.brightness)}"
            f"  |  "
            f"Pulsating: "
            f"{_display_name(param.pulsating_effect)}"
        ),
        (
            f"  Flame Color: "
            f"{_display_name(param.flame_color)}  |  "
            f"Light: {_display_name(param.light_status)}"
            f"  |  "
            f"Ambient Sensor: "
            f"{_display_name(param.ambient_sensor)}"
        ),
        (
            f"  Media Theme: "
            f"{_display_name(param.media_theme)}  |  "
            f"Media Light: "
            f"{_display_name(param.media_light)}  |  "
            f"Media Color: {_format_rgbw(param.media_color)}"
        ),
        (
            f"  Overhead Light: "
            f"{_display_name(param.overhead_light)}  |  "
            f"Overhead Color: "
            f"{_format_rgbw(param.overhead_color)}"
        ),
    ]
    return "\n".join(lines)


def _format_heat(param: HeatParam) -> str:
    """Format the heat settings parameter for display."""
    from flameconnect.models import HeatMode

    boost_text = (
        f"Boost: {param.boost_duration}min"
        if param.heat_mode == HeatMode.BOOST
        else "Boost: Off"
    )
    return (
        f"[bold]Heat:[/bold] "
        f"{_display_name(param.heat_status)}  |  "
        f"Mode: {_display_name(param.heat_mode)}  |  "
        f"Setpoint: {param.setpoint_temperature}\u00b0"
        f"  |  {boost_text}"
    )


def _format_heat_mode(param: HeatModeParam) -> str:
    """Format the heat mode/control parameter for display."""
    return (
        f"[bold]Heat Control:[/bold] "
        f"{_display_name(param.heat_control)}"
    )


def _format_timer(param: TimerParam) -> str:
    """Format the timer parameter for display."""
    from datetime import datetime, timedelta

    from flameconnect.models import TimerStatus

    line = (
        f"[bold]Timer:[/bold] "
        f"{_display_name(param.timer_status)}  |  "
        f"Duration: {param.duration}min"
    )
    if (
        param.timer_status == TimerStatus.ENABLED
        and param.duration > 0
    ):
        off_time = datetime.now() + timedelta(
            minutes=param.duration
        )
        line += (
            f"  |  Off at {off_time.strftime('%H:%M')}"
        )
    return line


def _format_software_version(
    param: SoftwareVersionParam,
) -> str:
    """Format the software version parameter for display."""
    return (
        f"[bold]Software:[/bold] "
        f"UI {param.ui_major}.{param.ui_minor}"
        f".{param.ui_test}  |  "
        f"Control {param.control_major}"
        f".{param.control_minor}"
        f".{param.control_test}  |  "
        f"Relay {param.relay_major}"
        f".{param.relay_minor}.{param.relay_test}"
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
            f"0x{param.error_byte1:02X} "
            f"0x{param.error_byte2:02X} "
            f"0x{param.error_byte3:02X} "
            f"0x{param.error_byte4:02X}"
        )
    return "[bold]Errors:[/bold] No Errors Recorded"


def _format_temp_unit(param: TempUnitParam) -> str:
    """Format the temperature unit parameter for display."""
    return (
        f"[bold]Temp Unit:[/bold] "
        f"{_display_name(param.unit)}"
    )


def _format_sound(param: SoundParam) -> str:
    """Format the sound parameter for display."""
    return (
        f"[bold]Sound:[/bold] Volume {param.volume}"
        f"  |  File: {param.sound_file}"
    )


def _format_log_effect(param: LogEffectParam) -> str:
    """Format the log effect parameter for display."""
    return (
        f"[bold]Log Effect:[/bold] "
        f"{_display_name(param.log_effect)}  |  "
        f"Color: {_format_rgbw(param.color)}  |  "
        f"Pattern: {param.pattern}"
    )


def format_parameters(params: list[Parameter]) -> str:
    """Format a list of parameters for display.

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

    # Collect formatted lines keyed by type.
    formatted: dict[type, str] = {}
    for param in params:
        if isinstance(param, ModeParam):
            formatted[ModeParam] = _format_mode(param)
        elif isinstance(param, HeatParam):
            formatted[HeatParam] = _format_heat(param)
        elif isinstance(param, HeatModeParam):
            formatted[HeatModeParam] = (
                _format_heat_mode(param)
            )
        elif isinstance(param, FlameEffectParam):
            formatted[FlameEffectParam] = (
                _format_flame_effect(param)
            )
        elif isinstance(param, TimerParam):
            formatted[TimerParam] = (
                _format_timer(param)
            )
        elif isinstance(param, SoftwareVersionParam):
            formatted[SoftwareVersionParam] = (
                _format_software_version(param)
            )
        elif isinstance(param, ErrorParam):
            formatted[ErrorParam] = (
                _format_error(param)
            )
        elif isinstance(param, TempUnitParam):
            formatted[TempUnitParam] = (
                _format_temp_unit(param)
            )
        elif isinstance(param, SoundParam):
            formatted[SoundParam] = (
                _format_sound(param)
            )
        elif isinstance(param, LogEffectParam):
            formatted[LogEffectParam] = (
                _format_log_effect(param)
            )

    # Desired display order (ErrorParam last).
    display_order: list[type] = [
        ModeParam,
        HeatParam,
        HeatModeParam,
        FlameEffectParam,
        TimerParam,
        SoftwareVersionParam,
        TempUnitParam,
        SoundParam,
        LogEffectParam,
        ErrorParam,
    ]
    lines = [
        formatted[t]
        for t in display_order
        if t in formatted
    ]

    if not lines:
        return "[dim]No parameters available[/dim]"

    return "\n".join(lines)


def _format_connection_state(
    state: ConnectionState,
) -> str:
    """Format connection state with color markup."""
    from flameconnect.models import ConnectionState as CS

    color_map: dict[CS, str] = {
        CS.CONNECTED: "green",
        CS.NOT_CONNECTED: "red",
        CS.UPDATING_FIRMWARE: "yellow",
        CS.UNKNOWN: "dim",
    }
    color = color_map.get(state, "dim")
    label = _display_name(state)
    return f"[{color}]{label}[/{color}]"


# -- Fireplace ASCII art ----------------------------------------
# Built as a list of pre-rendered Rich-markup strings.
# Shorthand aliases keep individual source lines under the
# linter's 88-char limit.
_D = "[dim]"
_d = "[/dim]"
_Y = "[yellow]"
_y = "[/yellow]"
_R = "[red]"
_r = "[/red]"
_B = "[bright_red]"
_b = "[/bright_red]"

# Width: 48 visible chars  |  Height: 17 lines
_W = 48  # outer width (visible)
_IW = _W - 2  # inner width between │ walls


def _row(content: str, vis_len: int) -> str:
    """Wrap *content* in dim │ borders, right-padded."""
    pad = _IW - vis_len
    return (
        f"{_D}│{_d}"
        f"{content}{' ' * pad}"
        f"{_D}│{_d}"
    )


_FIRE_ART: list[str] = [
    # ── mantel ──
    f"{_D}{'═' * _W}{_d}",
    # ── firebox top ──
    f"{_D}┌{'─' * _IW}┐{_d}",
    # blank
    _row("", 0),
    # flame tip
    _row(
        f"      {_Y}(  .  \\      /  .  ){_y}",
        26,
    ),
    # outer flames
    _row(
        f"     {_B}(   \\ \\    / /   ){_b}",
        23,
    ),
    # mid flames
    _row(
        f"    {_R}(  \\  \\\\ //  /   ){_r}",
        22,
    ),
    # bright core
    _row(
        f"   {_B}(   \\ {_b}"
        f"{_Y}||||{_y}"
        f"{_B}  /   ){_b}",
        20,
    ),
    # spread
    _row(
        f"   {_R}(  \\ {_r}"
        f"{_Y}/ || \\{_y}"
        f"{_R}  /  ){_r}",
        20,
    ),
    # lower
    _row(
        f"   {_R}( {_r}"
        f"{_Y}/ / {_y}"
        f"{_B}||{_b}"
        f"{_Y} \\ \\ {_y}"
        f"{_R}){_r}",
        17,
    ),
    # base flames
    _row(
        f"    {_Y}(/ /  {_y}"
        f"{_R}||{_r}"
        f"{_Y}  \\ \\){_y}",
        18,
    ),
    # embers
    _row(
        f"    {_Y}(__/  {_y}"
        f"{_B}/==\\{_b}"
        f"{_Y}  \\__){_y}",
        20,
    ),
    # coal bed
    _row(
        f"  {_D}{'▓' * 30}{_d}",
        32,
    ),
    # blank
    _row("", 0),
    # ── firebox bottom ──
    f"{_D}└{'─' * _IW}┘{_d}",
    # hearth slab
    f"{_D}{'█' * _W}{_d}",
    # base mantel
    f"{_D}{'═' * _W}{_d}",
]


class FireplaceVisual(Static):
    """Static ASCII-art fireplace visual."""

    def render(self) -> str:
        """Render the fireplace art with Rich markup."""
        return "\n".join(_FIRE_ART)


class ParameterPanel(Static):
    """Widget displaying decoded parameters in a panel."""

    content_text: reactive[str] = reactive(
        "[dim]Loading...[/dim]"
    )

    def render(self) -> str:
        """Render the parameter panel content."""
        return self.content_text

    def watch_content_text(self) -> None:
        """Force a layout recalculation on change."""
        self.refresh(layout=True)

    def update_parameters(
        self, params: list[Parameter]
    ) -> None:
        """Update the panel with new parameter data.

        Args:
            params: Parameter dataclass instances.
        """
        self.content_text = format_parameters(params)


class FireplaceSelector(Vertical):
    """Widget for selecting a fireplace from a list."""

    def compose(self) -> ComposeResult:
        """Compose the fireplace selector layout."""
        yield Static(
            "[bold]Select a fireplace:[/bold]",
            id="selector-title",
        )
        yield Vertical(id="fire-list")
