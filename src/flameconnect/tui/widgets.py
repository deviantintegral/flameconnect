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
    from textual.timer import Timer

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


class ArrowNavMixin:
    """Mixin for arrow key navigation between buttons in dialog screens."""

    def on_key(self, event: object) -> None:
        from textual import events
        from textual.widgets import Button

        if not isinstance(event, events.Key):
            return
        if isinstance(self.focused, Button):  # type: ignore[attr-defined]
            if event.key in ("left", "up"):
                self.focus_previous()  # type: ignore[attr-defined]
                event.prevent_default()
                event.stop()
            elif event.key in ("right", "down"):
                self.focus_next()  # type: ignore[attr-defined]
                event.prevent_default()
                event.stop()


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


def _temp_suffix(temp_unit: TempUnitParam | None) -> str:
    """Return the temperature unit suffix (e.g. 'C' or 'F'), or empty."""
    if temp_unit is None:
        return ""
    from flameconnect.models import TempUnit

    return "C" if temp_unit.unit == TempUnit.CELSIUS else "F"


def _format_mode(
    param: ModeParam,
    temp_unit: TempUnitParam | None = None,
) -> str:
    """Format the mode parameter for display."""
    mode_label = _MODE_DISPLAY.get(
        param.mode, _display_name(param.mode)
    )
    suffix = _temp_suffix(temp_unit)
    return (
        f"[bold]Mode:[/bold] {mode_label}  |  "
        f"[bold]Target Temp:[/bold] "
        f"{param.target_temperature}\u00b0{suffix}"
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
            f"Overhead Light: {_display_name(param.light_status)}"
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


def _format_heat(
    param: HeatParam,
    temp_unit: TempUnitParam | None = None,
) -> str:
    """Format the heat settings parameter for display."""
    from flameconnect.models import HeatMode

    boost_text = (
        f"Boost: {param.boost_duration}min"
        if param.heat_mode == HeatMode.BOOST
        else "Boost: Off"
    )
    suffix = _temp_suffix(temp_unit)
    return (
        f"[bold]Heat:[/bold] "
        f"{_display_name(param.heat_status)}  |  "
        f"Mode: {_display_name(param.heat_mode)}  |  "
        f"Setpoint: {param.setpoint_temperature}\u00b0{suffix}"
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

    # Extract the temperature unit (if present) for use in formatters.
    temp_unit: TempUnitParam | None = None
    for param in params:
        if isinstance(param, TempUnitParam):
            temp_unit = param
            break

    # Collect formatted lines keyed by type.
    formatted: dict[type, str] = {}
    for param in params:
        if isinstance(param, ModeParam):
            formatted[ModeParam] = _format_mode(
                param, temp_unit
            )
        elif isinstance(param, HeatParam):
            formatted[HeatParam] = _format_heat(
                param, temp_unit
            )
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

# Animation speed mapping: flame_speed (1-5) -> interval in seconds
_FLAME_SPEED_INTERVALS: dict[int, float] = {
    1: 0.6,
    2: 0.45,
    3: 0.3,
    4: 0.2,
    5: 0.15,
}

# Number of heat indicator rows rendered above the flames
_HEAT_ROWS = 2

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


def _rotate_palette(
    palette: tuple[str, str, str],
    frame: int,
) -> tuple[str, str, str]:
    """Rotate a (tip, mid, base) palette by *frame* positions.

    Frame 0: (tip, mid, base) -- original
    Frame 1: (base, tip, mid)
    Frame 2: (mid, base, tip)
    """
    idx = frame % 3
    if idx == 0:
        return palette
    if idx == 1:
        return (palette[2], palette[0], palette[1])
    return (palette[1], palette[2], palette[0])


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
    anim_frame: int = 0,
    heat_on: bool = False,
) -> _Text:
    """Generate fireplace ASCII art at outer width *w* and height *h*.

    Parameters
    ----------
    anim_frame:
        Animation frame index (0-2) used to rotate the flame palette
        colors, creating a cycling colour animation.
    heat_on:
        When ``True``, render wavy heat-indicator rows above the flame
        zone (reducing the flame row budget to keep total height
        constant).
    """
    ow = w - 2   # fill width between outer frame borders
    iw = w - 4   # content width between inner frame borders

    # Rotate palette for animation
    palette = _rotate_palette(flame_palette, anim_frame)

    result = _Text()

    def _nl() -> None:
        result.append("\n")

    # -- top edge --
    result.append("\u2581" * w, style="dim")
    _nl()

    # -- outer frame top --
    result.append("\u250c" + "\u2500" * ow + "\u2510", style="dim")
    _nl()

    # -- inner frame top --
    result.append("\u2502", style="dim")
    result.append("\u250c" + "\u2500" * (ow - 2) + "\u2510", style="dim")
    result.append("\u2502", style="dim")
    _nl()

    # -- LED strip --
    result.append("\u2502\u2502", style="dim")
    result.append("\u2591" * iw, style=led_style)
    result.append("\u2502\u2502", style="dim")
    _nl()

    # -- flame zone --
    flame_rows = max(h - _FIXED_ROWS, _MIN_FLAME_ROWS)

    # Reserve rows for heat indicators (reduce flame budget)
    heat_row_count = _HEAT_ROWS if heat_on else 0
    flame_rows_effective = max(
        flame_rows - heat_row_count, _MIN_FLAME_ROWS
    )

    num_defs = len(_FLAME_DEFS)
    if flame_rows_effective >= num_defs:
        blank_above = flame_rows_effective - num_defs
        defs_to_render = _FLAME_DEFS
    else:
        blank_above = 0
        defs_to_render = _FLAME_DEFS[
            num_defs - flame_rows_effective:
        ]

    # -- heat indicator rows --
    if heat_on:
        # Alternate two wave patterns for visual variety
        wave_chars = [
            "\u2248" * iw,   # (approx-equal signs)
            "~" * iw,        # (tildes)
        ]
        actual_heat_rows = flame_rows - flame_rows_effective
        for i in range(actual_heat_rows):
            result.append("\u2502\u2502", style="dim")
            result.append(
                wave_chars[i % len(wave_chars)],
                style="bright_red",
            )
            result.append("\u2502\u2502", style="dim")
            _nl()

    # Blank rows above flames
    for _ in range(blank_above):
        result.append("\u2502\u2502", style="dim")
        result.append(" " * iw)
        result.append("\u2502\u2502", style="dim")
        _nl()

    # Flame rows (or blank if standby)
    for body_frac, zone, atoms in defs_to_render:
        result.append("\u2502\u2502", style="dim")
        if fire_on:
            min_w = sum(len(a[0]) for a in atoms) + len(atoms) - 1
            body_w = max(int(iw * body_frac), min_w)
            lead = (iw - body_w) // 2
            style = palette[zone]
            flame_line = _Text(" " * lead)
            flame_line.append_text(_expand_flame(atoms, body_w, style))
            result.append_text(flame_line)
            result.append(" " * max(iw - lead - body_w, 0))
        else:
            result.append(" " * iw)
        result.append("\u2502\u2502", style="dim")
        _nl()

    # -- inner media bed --
    result.append("\u2502\u2502", style="dim")
    result.append("\u2593" * iw, style=media_style)
    result.append("\u2502\u2502", style="dim")
    _nl()

    # -- inner frame bottom --
    result.append("\u2502", style="dim")
    result.append("\u2514" + "\u2500" * (ow - 2) + "\u2518", style="dim")
    result.append("\u2502", style="dim")
    _nl()

    # -- outer hearth (fixed dim) --
    result.append("\u2502", style="dim")
    result.append("\u2593" * ow, style="dim")
    result.append("\u2502", style="dim")
    _nl()

    # -- outer frame bottom --
    bottom = "\u2514" + "\u2500" * ow + "\u2518"
    result.append(bottom, style="dim")  # no trailing newline

    return result


class FireplaceVisual(Static):
    """Dynamically sized ASCII-art fireplace visual."""

    _anim_frame: int = 0
    _anim_timer: Timer | None = None
    _flame_speed: int = 3
    _heat_on: bool = False

    def _advance_frame(self) -> None:
        """Advance the animation frame and trigger a repaint."""
        self._anim_frame = (self._anim_frame + 1) % 3
        self.refresh()

    def update_state(
        self,
        mode: ModeParam | None,
        flame_effect: FlameEffectParam | None,
        heat_param: HeatParam | None = None,
    ) -> None:
        """Update the visual with new fireplace state."""
        self._mode = mode
        self._flame_effect = flame_effect

        # Determine heat-on state
        if heat_param is not None:
            from flameconnect.models import HeatStatus

            self._heat_on = (
                heat_param.heat_status == HeatStatus.ON
            )
        else:
            self._heat_on = False

        # Determine fire-on state
        fire_on = True
        if mode is not None:
            fire_on = mode.mode == FireMode.MANUAL

        # Determine desired flame speed
        new_speed = 3
        if flame_effect is not None:
            new_speed = flame_effect.flame_speed

        # Manage animation timer
        if fire_on:
            speed_changed = new_speed != self._flame_speed
            self._flame_speed = new_speed
            if (
                self._anim_timer is None
                or speed_changed
            ):
                # Cancel existing timer if any
                if self._anim_timer is not None:
                    self._anim_timer.stop()
                    self._anim_timer = None
                interval = _FLAME_SPEED_INTERVALS.get(
                    self._flame_speed, 0.3
                )
                self._anim_timer = self.set_interval(
                    interval, self._advance_frame
                )
        else:
            # Fire is off -- stop animation
            if self._anim_timer is not None:
                self._anim_timer.stop()
                self._anim_timer = None
            self._anim_frame = 0

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
        media_style = "dim"

        if mode is not None:
            fire_on = mode.mode == FireMode.MANUAL

        if fire_on and flame_effect is not None:
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
            anim_frame=self._anim_frame,
            heat_on=self._heat_on,
        )


def _expand_piped_line(line: str, width: int = 0) -> str:
    """Expand every ``  |  `` separator into a new indented line.

    When *width* > 0, segments are wrapped using the same greedy
    algorithm as :func:`_wrap_piped_line` after expansion so that
    lines exceeding the panel width are broken correctly.
    """
    sep = "  |  "
    segments = line.split(sep)
    if len(segments) <= 1:
        return line

    if width > 0:
        rows: list[str] = []
        current = segments[0]
        for seg in segments[1:]:
            candidate = current + sep + seg
            if _Text.from_markup(candidate).cell_len > width:
                rows.append(current)
                current = "  " + seg
            else:
                current = candidate
        rows.append(current)
        return "\n".join(rows)

    return "\n".join(
        [segments[0], *(f"  {seg}" for seg in segments[1:])]
    )


def _expand_piped_text(text: str, width: int = 0) -> str:
    """Expand all pipe separators in *text* to separate lines.

    When *width* > 0, each line is wrapped to fit within *width*
    columns instead of unconditionally splitting every separator.
    """
    return "\n".join(
        _expand_piped_line(line, width) for line in text.split("\n")
    )


def _wrap_piped_line(line: str, width: int) -> str:
    """Wrap a pipe-separated line to fit within *width* columns.

    Segments are split on ``  |  `` and accumulated greedily.
    When the next segment would overflow, it starts a new line
    with a 2-space indent.
    """
    sep = "  |  "
    segments = line.split(sep)
    if len(segments) <= 1:
        return line

    rows: list[str] = []
    current = segments[0]
    for seg in segments[1:]:
        candidate = current + sep + seg
        if _Text.from_markup(candidate).cell_len > width:
            rows.append(current)
            current = "  " + seg
        else:
            current = candidate
    rows.append(current)
    return "\n".join(rows)


def _wrap_piped_text(text: str, width: int) -> str:
    """Apply pipe-aware wrapping to every line of *text*."""
    return "\n".join(
        _wrap_piped_line(line, width) for line in text.split("\n")
    )


class ParameterPanel(Static):
    """Widget displaying decoded parameters in a panel."""

    content_text: reactive[str] = reactive(
        "[dim]Loading...[/dim]"
    )

    def render(self) -> str:
        """Render the parameter panel content."""
        width = self.content_region.width
        if self.has_class("compact"):
            if width > 0:
                return _wrap_piped_text(
                    self.content_text, width
                )
            return self.content_text
        return _expand_piped_text(self.content_text, width)

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
