"""Custom Textual widgets for the FlameConnect TUI."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.text import Text as _Text
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import Static

from flameconnect.models import FireMode, FlameColor, LightStatus

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
# The fireplace has three state-driven zones:
#   1. Upper LED strip (overhead_color / overhead_light)
#   2. Flames (flame_color + fire mode)
#   3. Inner media bed (media_color)
# The outer hearth row is fixed dim grey.
#
# Flames scale vertically to fill available height by trimming
# the topmost (sparsest) rows first.

# Number of fixed structural rows (everything except flame zone)
_FIXED_ROWS = 8
_MIN_FLAME_ROWS = 2
_DEFAULT_HEIGHT = 20


def _rgbw_to_style(color: RGBWColor) -> str:
    """Convert an RGBW color to a Rich ``rgb(r,g,b)`` style string."""
    r = min(color.red + color.white, 255)
    g = min(color.green + color.white, 255)
    b = min(color.blue + color.white, 255)
    return f"rgb({r},{g},{b})"


# Flame color palettes: (tip, mid, base) Rich style strings
_FLAME_PALETTES: dict[FlameColor, tuple[str, str, str]] = {
    FlameColor.ALL: ("yellow", "bright_green", "bright_magenta"),
    FlameColor.YELLOW_RED: ("yellow", "bright_red", "red"),
    FlameColor.YELLOW_BLUE: ("yellow", "bright_cyan", "blue"),
    FlameColor.BLUE: ("bright_cyan", "bright_blue", "blue"),
    FlameColor.RED: ("bright_yellow", "bright_red", "red"),
    FlameColor.YELLOW: ("bright_yellow", "yellow", "bright_red"),
    FlameColor.BLUE_RED: ("bright_cyan", "bright_blue", "red"),
}
_DEFAULT_PALETTE: tuple[str, str, str] = ("yellow", "bright_red", "red")

# Flame row definitions: (body_width_fraction, zone_index, atoms)
# zone_index: 0=tip, 1=mid, 2=base (indexes into palette tuple)
# atoms: (text, trailing_gap_weight)
_FLAME_DEFS: list[tuple[float, int, list[tuple[str, int]]]] = [
    # Row 0: Sparse tips
    (0.95, 0, [
        ("( )", 3), (",", 5), (")", 5),
        (",", 5), ("( )", 3), (",", 5), ("( )", 0),
    ]),
    # Row 1: Forming columns
    (0.95, 0, [
        ("( \\ )", 2), ("( | )", 2), ("(  )", 1),
        ("( \\)", 2), ("( | )", 2),
        ("( | )", 1), ("( )", 0),
    ]),
    # Row 2: Growing
    (0.95, 1, [
        ("( \\ \\ )", 2), ("( | | )", 2), ("( \\ )", 1),
        ("( \\ \\)", 2), ("( / | )", 2),
        ("( / | )", 1), ("( )", 0),
    ]),
    # Row 3: Full width
    (0.95, 1, [
        ("( \\\\ \\)", 2), ("( || |)", 2), ("( \\\\ )", 1),
        ("( \\\\ )", 2), ("( /| |)", 2),
        ("( /| | )", 1), ("( )", 0),
    ]),
    # Row 4: Dense mid
    (0.95, 1, [
        ("( \\\\ )", 2), ("( || )", 2), ("( \\\\ )", 1),
        ("( || )", 2), ("( /| )", 2),
        ("( /| |)", 1), ("( )", 0),
    ]),
    # Row 5: Narrowing
    (0.95, 2, [
        ("( \\\\)", 2), ("( //)", 2), ("( \\\\ )", 1),
        ("( || )", 2), ("( // )", 2),
        ("( // )", 1), ("( )", 0),
    ]),
    # Row 6: Base
    (0.95, 2, [
        ("(\\)", 2), ("(/)", 2), ("(\\)(|)", 3),
        ("(/)", 2), ("(/)", 2), ("()", 0),
    ]),
    # Row 7: Base
    (0.95, 2, [
        ("(\\)", 2), ("(/)", 2), ("(\\|/)", 4),
        ("(/)", 2), ("(/)", 2), ("()", 0),
    ]),
]


def _expand_flame(
    atoms: list[tuple[str, int]],
    body_width: int,
    style: str,
) -> _Text:
    """Build a single flame row, distributing gaps proportionally."""
    chars_w = sum(len(a[0]) for a in atoms)
    total_gap = max(body_width - chars_w, 0)
    total_weight = sum(a[1] for a in atoms) or 1

    line = _Text()
    remaining_gap = total_gap
    remaining_weight = total_weight
    for text, gap_w in atoms:
        line.append(text, style=style)
        if gap_w > 0 and remaining_weight > 0:
            sp = remaining_gap * gap_w // remaining_weight
            remaining_gap -= sp
            remaining_weight -= gap_w
            line.append(" " * sp)
    return line


def _build_fire_art(
    w: int,
    h: int,
    *,
    fire_on: bool = True,
    flame_palette: tuple[str, str, str] = _DEFAULT_PALETTE,
    led_style: str = "dim",
    media_style: str = "red",
) -> _Text:
    """Generate fireplace ASCII art at outer width *w* and height *h*."""
    ow = w - 2   # fill width between outer frame borders
    iw = w - 4   # content width between inner frame borders

    result = _Text()

    def _nl() -> None:
        result.append("\n")

    # ── top edge ──
    result.append("▁" * w, style="dim")
    _nl()

    # ── outer frame top ──
    result.append("┌" + "─" * ow + "┐", style="dim")
    _nl()

    # ── inner frame top ──
    result.append("│", style="dim")
    result.append("┌" + "─" * (ow - 2) + "┐", style="dim")
    result.append("│", style="dim")
    _nl()

    # ── LED strip ──
    result.append("││", style="dim")
    result.append("░" * iw, style=led_style)
    result.append("││", style="dim")
    _nl()

    # ── flame zone ──
    flame_rows = max(h - _FIXED_ROWS, _MIN_FLAME_ROWS)
    num_defs = len(_FLAME_DEFS)
    if flame_rows >= num_defs:
        blank_above = flame_rows - num_defs
        defs_to_render = _FLAME_DEFS
    else:
        blank_above = 0
        defs_to_render = _FLAME_DEFS[num_defs - flame_rows:]

    # Blank rows above flames
    for _ in range(blank_above):
        result.append("││", style="dim")
        result.append(" " * iw)
        result.append("││", style="dim")
        _nl()

    # Flame rows (or blank if standby)
    for body_frac, zone, atoms in defs_to_render:
        result.append("││", style="dim")
        if fire_on:
            min_w = sum(len(a[0]) for a in atoms) + len(atoms) - 1
            body_w = max(int(iw * body_frac), min_w)
            lead = (iw - body_w) // 2
            style = flame_palette[zone]
            flame_line = _Text(" " * lead)
            flame_line.append_text(_expand_flame(atoms, body_w, style))
            result.append_text(flame_line)
            result.append(" " * max(iw - lead - body_w, 0))
        else:
            result.append(" " * iw)
        result.append("││", style="dim")
        _nl()

    # ── inner media bed ──
    result.append("││", style="dim")
    result.append("▓" * iw, style=media_style)
    result.append("││", style="dim")
    _nl()

    # ── inner frame bottom ──
    result.append("│", style="dim")
    result.append("└" + "─" * (ow - 2) + "┘", style="dim")
    result.append("│", style="dim")
    _nl()

    # ── outer hearth (fixed dim) ──
    result.append("│", style="dim")
    result.append("▓" * ow, style="dim")
    result.append("│", style="dim")
    _nl()

    # ── outer frame bottom ──
    result.append("└" + "─" * ow + "┘", style="dim")  # no trailing newline

    return result


class FireplaceVisual(Static):
    """Dynamically sized ASCII-art fireplace visual."""

    def update_state(
        self,
        mode: ModeParam | None,
        flame_effect: FlameEffectParam | None,
    ) -> None:
        """Update the visual with new fireplace state."""
        self._mode = mode
        self._flame_effect = flame_effect
        self.refresh()

    def render(self) -> _Text:
        """Render fireplace art scaled to the widget's content region."""
        w = self.content_region.width
        h = self.content_region.height
        if w < 20:
            w = 48
        if h == 0:
            h = _DEFAULT_HEIGHT

        mode = getattr(self, "_mode", None)
        flame_effect = getattr(self, "_flame_effect", None)

        fire_on = True
        palette = _DEFAULT_PALETTE
        led_style = "dim"
        media_style = "red"

        if mode is not None:
            fire_on = mode.mode == FireMode.MANUAL

        if flame_effect is not None:
            palette = _FLAME_PALETTES.get(
                flame_effect.flame_color, _DEFAULT_PALETTE
            )
            if flame_effect.overhead_light == LightStatus.ON:
                led_style = _rgbw_to_style(
                    flame_effect.overhead_color
                )
            media_style = _rgbw_to_style(
                flame_effect.media_color
            )

        return _build_fire_art(
            w, h,
            fire_on=fire_on,
            flame_palette=palette,
            led_style=led_style,
            media_style=media_style,
        )


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
