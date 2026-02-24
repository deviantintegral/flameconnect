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
# Dynamically sized using rich.text.Text to avoid markup-escaping
# issues (Rich interprets ``\[`` as an escaped bracket).
#
# Each flame row is defined as a list of atoms:
#   (text, style, trailing_gap_weight)
# A builder distributes whitespace proportionally so the fire
# scales to fill whatever width the widget is given.

from rich.text import Text as _Text

_FLAME_DEFS: list[tuple[float, list[tuple[str, str, int]]]] = [
    # (body_width_fraction, atoms)
    # flame tip
    (0.90, [
        ("(", "yellow", 2), (".", "yellow", 2), ("\\", "yellow", 6),
        ("/", "yellow", 2), (".", "yellow", 2), (")", "yellow", 0),
    ]),
    # outer flames
    (0.82, [
        ("(", "bright_red", 3), ("\\", "bright_red", 1),
        ("\\", "bright_red", 5),
        ("/", "bright_red", 1), ("/", "bright_red", 3),
        (")", "bright_red", 0),
    ]),
    # mid flames
    (0.80, [
        ("(", "red", 2), ("\\", "red", 2), ("\\\\", "red", 4),
        ("//", "red", 2), ("/", "red", 3), (")", "red", 0),
    ]),
    # bright core
    (0.76, [
        ("(", "bright_red", 3), ("\\", "bright_red", 1),
        ("||||", "yellow", 1),
        ("/", "bright_red", 3), (")", "bright_red", 0),
    ]),
    # spread
    (0.76, [
        ("(", "red", 2), ("\\", "red", 1),
        ("/", "yellow", 1), ("||", "yellow", 1), ("\\", "red", 1),
        ("/", "red", 2), (")", "red", 0),
    ]),
    # lower
    (0.64, [
        ("(", "red", 1),
        ("/", "yellow", 1), ("/", "yellow", 1),
        ("||", "bright_red", 1),
        ("\\", "yellow", 1), ("\\", "yellow", 1),
        (")", "red", 0),
    ]),
    # base flames
    (0.68, [
        ("(/", "yellow", 1), ("/", "yellow", 2),
        ("||", "red", 2),
        ("\\", "yellow", 1), ("\\)", "yellow", 0),
    ]),
    # embers
    (0.76, [
        ("(__/", "yellow", 2),
        ("/==\\", "bright_red", 2),
        ("\\__)", "yellow", 0),
    ]),
]

_COAL_FRAC = 0.95


def _expand_flame(
    atoms: list[tuple[str, str, int]],
    body_width: int,
) -> _Text:
    """Build a single flame row as a Text object.

    Gaps between atoms are distributed proportionally according to
    each atom's trailing gap weight.
    """
    chars_w = sum(len(a[0]) for a in atoms)
    total_gap = max(body_width - chars_w, 0)
    total_weight = sum(a[2] for a in atoms) or 1

    line = _Text()
    remaining_gap = total_gap
    remaining_weight = total_weight
    for text, style, gap_w in atoms:
        line.append(text, style=style)
        if gap_w > 0 and remaining_weight > 0:
            sp = remaining_gap * gap_w // remaining_weight
            remaining_gap -= sp
            remaining_weight -= gap_w
            line.append(" " * sp)
    return line


def _build_fire_art(w: int) -> _Text:
    """Generate fireplace ASCII art at outer width *w*."""
    iw = w - 2  # inner width between │ walls

    result = _Text()

    def _nl() -> None:
        result.append("\n")

    def _full(char: str) -> None:
        result.append(char * w, style="dim")
        _nl()

    def _border(left: str, fill: str, right: str) -> None:
        result.append(left + fill * iw + right, style="dim")
        _nl()

    def _row(content: _Text | None = None, vis_len: int = 0) -> None:
        result.append("│", style="dim")
        if content is not None:
            result.append_text(content)
        result.append(" " * max(iw - vis_len, 0))
        result.append("│", style="dim")
        _nl()

    # ── mantel ──
    _full("═")
    # ── firebox top ──
    _border("┌", "─", "┐")
    # blank
    _row()

    # ── flame rows ──
    for body_frac, atoms in _FLAME_DEFS:
        min_w = sum(len(a[0]) for a in atoms) + len(atoms) - 1
        body_w = max(int(iw * body_frac), min_w)
        lead = (iw - body_w) // 2
        flame = _Text(" " * lead)
        flame.append_text(_expand_flame(atoms, body_w))
        _row(flame, lead + body_w)

    # ── coal bed ──
    coal_w = max(int(iw * _COAL_FRAC), 10)
    coal_lead = (iw - coal_w) // 2
    coal = _Text(" " * coal_lead)
    coal.append("▓" * coal_w, style="dim")
    _row(coal, coal_lead + coal_w)

    # blank
    _row()
    # ── firebox bottom ──
    _border("└", "─", "┘")
    # hearth slab
    _full("█")
    # base mantel
    result.append("═" * w, style="dim")  # no trailing newline

    return result


class FireplaceVisual(Static):
    """Dynamically sized ASCII-art fireplace visual."""

    def render(self) -> _Text:
        """Render fireplace art scaled to the widget's content width."""
        w = self.content_region.width
        if w < 20:
            w = 48
        return _build_fire_art(w)


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
