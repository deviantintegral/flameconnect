"""Command-line interface for flameconnect."""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import logging
import sys
import webbrowser
from dataclasses import replace
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

from flameconnect.auth import MsalAuth
from flameconnect.client import FlameConnectClient
from flameconnect.const import (
    DEFAULT_TARGET_TEMPERATURE,
    MAX_BOOST_DURATION,
    MAX_FLAME_SPEED,
    MAX_TEMP_CELSIUS,
    MAX_TEMP_FAHRENHEIT,
    MAX_TIMER_DURATION,
    MIN_BOOST_DURATION,
    MIN_FLAME_SPEED,
    MIN_TEMP_CELSIUS,
    MIN_TEMP_FAHRENHEIT,
)
from flameconnect.models import (
    NAMED_COLORS,
    Brightness,
    ErrorParam,
    FireFeatures,
    FireMode,
    FlameColor,
    FlameEffect,
    FlameEffectParam,
    HeatMode,
    HeatModeParam,
    HeatParam,
    HeatStatus,
    LightStatus,
    LogEffectParam,
    MediaTheme,
    ModeParam,
    Parameter,
    PulsatingEffect,
    RGBWColor,
    SoftwareVersionParam,
    SoundParam,
    TempUnit,
    TempUnitParam,
    TimerParam,
    TimerStatus,
    convert_from_display,
    convert_temp,
    display_name,
    kebab_name,
    temp_suffix,
)

# Mapping from CLI heat-mode string to HeatMode enum value
_HEAT_MODE_LOOKUP: dict[str, HeatMode] = {
    kebab_name(m): m for m in (HeatMode.NORMAL, HeatMode.BOOST, HeatMode.ECO)
}

_PULSATING_LOOKUP: dict[str, PulsatingEffect] = {
    kebab_name(m): m for m in PulsatingEffect
}

_FLAME_COLOR_LOOKUP: dict[str, FlameColor] = {kebab_name(m): m for m in FlameColor}

_MEDIA_THEME_LOOKUP: dict[str, MediaTheme] = {kebab_name(m): m for m in MediaTheme}

_TEMP_UNIT_LOOKUP: dict[str, TempUnit] = {kebab_name(m): m for m in TempUnit}


class _FlameEffectSetter(NamedTuple):
    field: str
    lookup: dict[str, object]
    label: str


_SET_PARAM_NAMES = (
    "mode, flame-speed, brightness, pulsating, flame-color,"
    " media-theme, heat-status, heat-mode, heat-temp, timer,"
    " temp-unit, flame-effect, media-light, media-color,"
    " overhead-light, overhead-color, ambient-sensor"
)


def _format_rgbw(color: RGBWColor) -> str:
    """Format an RGBWColor for display."""
    return f"RGBW({color.red}, {color.green}, {color.blue}, {color.white})"


# ---------------------------------------------------------------------------
# Generic parameter finder
# ---------------------------------------------------------------------------


def _find_param[T](parameters: list[Parameter], param_type: type[T]) -> T | None:
    """Find the first parameter of a given type in a list."""
    for p in parameters:
        if isinstance(p, param_type):
            return p
    return None


# ---------------------------------------------------------------------------
# Status display formatting
# ---------------------------------------------------------------------------


def _display_mode(
    param: ModeParam,
    temp_unit: TempUnitParam | None = None,
) -> None:
    """Display Mode parameter."""
    unit = temp_unit.unit if temp_unit else TempUnit.CELSIUS
    unit_suffix = ("C" if unit == TempUnit.CELSIUS else "F") if temp_unit else ""
    display_temp = convert_temp(param.target_temperature, unit)
    print("\n  [321] Mode")
    print(f"  {'─' * 40}")
    mode = display_name(param.mode)
    print(f"    Mode:           {mode}")
    print(f"    Target Temp:    {display_temp}\u00b0{unit_suffix}")


def _display_flame_effect(param: FlameEffectParam) -> None:
    """Display FlameEffect parameter."""
    print("\n  [322] Flame Effect")
    print(f"  {'─' * 40}")
    flame = display_name(param.flame_effect)
    print(f"    Flame:          {flame}")
    print(f"    Flame Speed:    {param.flame_speed} / {MAX_FLAME_SPEED}")
    brightness = display_name(param.brightness)
    print(f"    Brightness:     {brightness}")
    color = display_name(param.flame_color)
    print(f"    Flame Color:    {color}")
    theme = display_name(param.media_theme)
    rgbw = _format_rgbw(param.media_color)
    print(f"    Media Light:    {theme} | {rgbw}")
    light = display_name(param.light_status)
    pulsating = display_name(param.pulsating_effect)
    print(f"    Overhead Light: {light}")
    print(f"    Overhead Pulsating: {pulsating}")
    print(f"    Overhead Color: {_format_rgbw(param.overhead_color)}")
    ambient = display_name(param.ambient_sensor)
    print(f"    Ambient Sensor: {ambient}")


def _display_heat(
    param: HeatParam,
    temp_unit: TempUnitParam | None = None,
) -> None:
    """Display HeatSettings parameter."""
    unit = temp_unit.unit if temp_unit else TempUnit.CELSIUS
    unit_suffix = ("C" if unit == TempUnit.CELSIUS else "F") if temp_unit else ""
    display_temp = convert_temp(param.setpoint_temperature, unit)
    print("\n  [323] Heat Settings")
    print(f"  {'─' * 40}")
    status = display_name(param.heat_status)
    print(f"    Heat:           {status}")
    mode = display_name(param.heat_mode)
    print(f"    Heat Mode:      {mode}")
    print(f"    Setpoint Temp:  {display_temp}\u00b0{unit_suffix}")
    print(f"    Boost Duration: {param.boost_duration}")


def _display_heat_mode(param: HeatModeParam) -> None:
    """Display HeatMode parameter."""
    print("\n  [325] Heat Mode")
    print(f"  {'─' * 40}")
    ctrl = display_name(param.heat_control)
    print(f"    Heat Control:   {ctrl}")


def _display_timer(param: TimerParam) -> None:
    """Display Timer parameter."""
    from datetime import datetime, timedelta

    dur = param.duration
    print("\n  [326] Timer Mode")
    print(f"  {'─' * 40}")
    ts = display_name(param.timer_status)
    print(f"    Timer:          {ts}")
    print(f"    Duration:       {dur} min ({dur // 60}h {dur % 60}m)")
    if param.timer_status == 1 and dur > 0:
        off_time = datetime.now() + timedelta(minutes=dur)
        print(f"    Off at:         {off_time.strftime('%H:%M')}")


def _display_software_version(param: SoftwareVersionParam) -> None:
    """Display SoftwareVersion parameter."""
    ui = f"{param.ui_major}.{param.ui_minor}.{param.ui_test}"
    ctrl = f"{param.control_major}.{param.control_minor}.{param.control_test}"
    relay = f"{param.relay_major}.{param.relay_minor}.{param.relay_test}"
    print("\n  [327] Software Version")
    print(f"  {'─' * 40}")
    print(f"    UI Version:      {ui}")
    print(f"    Control Version: {ctrl}")
    print(f"    Relay Version:   {relay}")


def _display_error(param: ErrorParam) -> None:
    """Display Error parameter."""
    print("\n  [329] Error")
    print(f"  {'─' * 40}")
    for i, val in enumerate(
        [
            param.error_byte1,
            param.error_byte2,
            param.error_byte3,
            param.error_byte4,
        ],
        start=1,
    ):
        print(f"    Error Byte {i}:   0x{val:02X} ({val:08b})")
    has_errors = (
        param.error_byte1 | param.error_byte2 | param.error_byte3 | param.error_byte4
    )
    if has_errors:
        print("    Active Faults:  Yes")
    else:
        print("    Active Faults:  None")


def _display_temp_unit(param: TempUnitParam) -> None:
    """Display TempUnit parameter."""
    print("\n  [236] Temperature Unit")
    print(f"  {'─' * 40}")
    unit = display_name(param.unit)
    print(f"    Unit:           {unit}")


def _display_sound(param: SoundParam) -> None:
    """Display Sound parameter."""
    print("\n  [369] Sound")
    print(f"  {'─' * 40}")
    print(f"    Volume:         {param.volume} / 255")
    print(f"    Sound File:     {param.sound_file}")


def _display_log_effect(param: LogEffectParam) -> None:
    """Display LogEffect parameter."""
    print("\n  [370] Log Effect")
    print(f"  {'─' * 40}")
    effect = display_name(param.log_effect)
    print(f"    Log Effect:     {effect}")
    print(f"    Colors:         {_format_rgbw(param.color)}")
    print(f"    Pattern:        {param.pattern}")


_FEATURE_LABELS: list[tuple[str, str]] = [
    ("sound", "Sound"),
    ("simple_heat", "Simple Heat"),
    ("advanced_heat", "Advanced Heat"),
    ("seven_day_timer", "7-Day Timer"),
    ("count_down_timer", "Countdown Timer"),
    ("moods", "Moods"),
    ("flame_height", "Flame Height"),
    ("rgb_flame_accent", "RGB Flame Accent"),
    ("flame_dimming", "Flame Dimming"),
    ("rgb_fuel_bed", "RGB Fuel Bed"),
    ("fuel_bed_dimming", "Fuel Bed Dimming"),
    ("flame_fan_speed", "Flame Fan Speed"),
    ("rgb_back_light", "RGB Back Light"),
    ("front_light_amber", "Front Light Amber"),
    ("pir_toggle_smart_sense", "PIR Smart Sense"),
    ("lgt1_to_5", "LGT 1-5"),
    ("requires_warm_up", "Requires Warm Up"),
    ("apply_flame_only_first", "Apply Flame Only First"),
    ("flame_amber", "Flame Amber"),
    ("check_if_remote_was_used", "Check If Remote Was Used"),
    ("media_accent", "Media Accent"),
    ("power_boost", "Power Boost"),
    ("fan_only", "Fan Only"),
    ("rgb_log_effect", "RGB Log Effect"),
]

assert {fn for fn, _ in _FEATURE_LABELS} == {
    f.name for f in dataclasses.fields(FireFeatures)
}, "_FEATURE_LABELS field names do not match FireFeatures fields"


def _display_features(features: FireFeatures) -> None:
    """Display supported feature flags."""
    print("\n  Supported Features")
    print(f"  {'─' * 40}")
    for field_name, label in _FEATURE_LABELS:
        value = "Yes" if getattr(features, field_name) else "No"
        print(f"    {label + ':':<28s}{value}")


def _display_parameter(
    param: Parameter,
    temp_unit: TempUnitParam | None = None,
) -> None:
    """Display a single parameter in human-readable form."""
    if isinstance(param, ModeParam):
        _display_mode(param, temp_unit)
    elif isinstance(param, FlameEffectParam):
        _display_flame_effect(param)
    elif isinstance(param, HeatParam):
        _display_heat(param, temp_unit)
    elif isinstance(param, HeatModeParam):
        _display_heat_mode(param)
    elif isinstance(param, TimerParam):
        _display_timer(param)
    elif isinstance(param, SoftwareVersionParam):
        _display_software_version(param)
    elif isinstance(param, ErrorParam):
        _display_error(param)
    elif isinstance(param, TempUnitParam):
        _display_temp_unit(param)
    elif isinstance(param, SoundParam):
        _display_sound(param)
    elif isinstance(param, LogEffectParam):
        _display_log_effect(param)


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------


async def cmd_list(client: FlameConnectClient) -> None:
    """List all registered fireplaces."""
    fires = await client.get_fires()
    if not fires:
        print("No fireplaces registered to this account.")
        return
    print(f"Found {len(fires)} fireplace(s):\n")
    for i, fire in enumerate(fires):
        print(f"{'─' * 60}")
        print(f"Fireplace #{i + 1}")
        print(f"{'─' * 60}")
        print(f"  Name:        {fire.friendly_name}")
        print(f"  Fire ID:     {fire.fire_id}")
        state = display_name(fire.connection_state)
        print(f"  Connection:  {state}")


async def cmd_status(client: FlameConnectClient, fire_id: str) -> None:
    """Display the current status of a fireplace."""
    overview = await client.get_fire_overview(fire_id)
    fire = overview.fire
    print(f"Fireplace: {fire.friendly_name} ({fire.fire_id})")
    state = display_name(fire.connection_state)
    print(f"Connection: {state}")
    _display_features(fire.features)

    if not overview.parameters:
        print("\nNo parameters returned (fireplace may be offline).")
        return

    count = len(overview.parameters)
    temp_unit = _find_param(overview.parameters, TempUnitParam)
    print(f"\n{count} parameter(s) reported:")
    for param in overview.parameters:
        _display_parameter(param, temp_unit)


_FLAME_EFFECT_SETTERS: dict[str, _FlameEffectSetter] = {
    "brightness": _FlameEffectSetter(
        "brightness",
        {"low": Brightness.LOW, "high": Brightness.HIGH},
        "Brightness",
    ),
    "pulsating": _FlameEffectSetter(
        "pulsating_effect",
        dict[str, object](_PULSATING_LOOKUP),
        "Pulsating overhead light effect",
    ),
    "flame-color": _FlameEffectSetter(
        "flame_color",
        dict[str, object](_FLAME_COLOR_LOOKUP),
        "Flame color",
    ),
    "media-theme": _FlameEffectSetter(
        "media_theme",
        dict[str, object](_MEDIA_THEME_LOOKUP),
        "Media theme",
    ),
    "flame-effect": _FlameEffectSetter(
        "flame_effect",
        {"on": FlameEffect.ON, "off": FlameEffect.OFF},
        "Flame effect",
    ),
    "media-light": _FlameEffectSetter(
        "media_light",
        {"on": LightStatus.ON, "off": LightStatus.OFF},
        "Media light",
    ),
    "overhead-light": _FlameEffectSetter(
        "light_status",
        {"on": LightStatus.ON, "off": LightStatus.OFF},
        "Overhead light",
    ),
    "ambient-sensor": _FlameEffectSetter(
        "ambient_sensor",
        {"on": LightStatus.ON, "off": LightStatus.OFF},
        "Ambient sensor",
    ),
}

assert all(
    setter.field in {f.name for f in dataclasses.fields(FlameEffectParam)}
    for setter in _FLAME_EFFECT_SETTERS.values()
), "_FLAME_EFFECT_SETTERS contains invalid FlameEffectParam field names"


async def cmd_on(client: FlameConnectClient, fire_id: str) -> None:
    """Turn on a fireplace."""
    await client.turn_on(fire_id)
    print(f"Turn-on command sent to {fire_id}.")


async def cmd_off(client: FlameConnectClient, fire_id: str) -> None:
    """Turn off a fireplace."""
    await client.turn_off(fire_id)
    print(f"Turn-off command sent to {fire_id}.")


async def cmd_set(
    client: FlameConnectClient,
    fire_id: str,
    param: str,
    value: str,
) -> None:
    """Set a specific parameter on a fireplace."""
    if param in _SET_HANDLERS:
        await _SET_HANDLERS[param](client, fire_id, value)
    elif param in _FLAME_EFFECT_SETTERS:
        field, lookup, label = _FLAME_EFFECT_SETTERS[param]
        await _set_flame_effect_field(
            client, fire_id, value, field=field, lookup=lookup, label=label
        )
    else:
        print(f"Error: unknown parameter '{param}'. Valid: {_SET_PARAM_NAMES}.")
        sys.exit(1)


def _parse_color(value: str) -> RGBWColor | None:
    """Parse a color value as either R,G,B,W integers or a named preset."""
    if value in NAMED_COLORS:
        return NAMED_COLORS[value]
    parts = value.split(",")
    if len(parts) == 4:
        try:
            r, g, b, w = (int(p) for p in parts)
        except ValueError:
            return None
        if all(0 <= v <= 255 for v in (r, g, b, w)):
            return RGBWColor(red=r, green=g, blue=b, white=w)
    return None


async def _set_mode(client: FlameConnectClient, fire_id: str, value: str) -> None:
    """Set the fireplace mode, preserving current temperature."""
    if value not in ("standby", "manual"):
        print("Error: mode must be 'standby' or 'manual'.")
        sys.exit(1)

    overview = await client.get_fire_overview(fire_id)
    current_mode: ModeParam | None = None
    for param in overview.parameters:
        if isinstance(param, ModeParam):
            current_mode = param
            break

    temperature = (
        current_mode.target_temperature if current_mode else DEFAULT_TARGET_TEMPERATURE
    )
    mode = FireMode.STANDBY if value == "standby" else FireMode.MANUAL
    mode_param = ModeParam(mode=mode, target_temperature=temperature)
    await client.write_parameters(fire_id, [mode_param])
    print(f"Mode set to {value}.")


async def _set_flame_speed(
    client: FlameConnectClient, fire_id: str, value: str
) -> None:
    """Set flame speed (1-5)."""
    speed = int(value)
    if speed < MIN_FLAME_SPEED or speed > MAX_FLAME_SPEED:
        print(
            f"Error: flame-speed must be between"
            f" {MIN_FLAME_SPEED} and {MAX_FLAME_SPEED}."
        )
        sys.exit(1)
    overview = await client.get_fire_overview(fire_id)
    current = _find_param(overview.parameters, FlameEffectParam)
    if current is None:
        print("Error: no FlameEffect parameter found.")
        sys.exit(1)
    new_param = replace(current, flame_speed=speed)
    await client.write_parameters(fire_id, [new_param])
    print(f"Flame speed set to {speed}.")


async def _set_flame_effect_field(
    client: FlameConnectClient,
    fire_id: str,
    value: str,
    *,
    field: str,
    lookup: dict[str, object],
    label: str,
) -> None:
    """Validate, fetch, replace a single FlameEffectParam field, and write."""
    if value not in lookup:
        valid = ", ".join(lookup)
        print(f"Error: {label} must be one of: {valid}.")
        sys.exit(1)
    overview = await client.get_fire_overview(fire_id)
    current = _find_param(overview.parameters, FlameEffectParam)
    if current is None:
        print("Error: no FlameEffect parameter found.")
        sys.exit(1)
    new_param = replace(current, **{field: lookup[value]})  # type: ignore[arg-type]
    await client.write_parameters(fire_id, [new_param])
    print(f"{label} set to {value}.")


async def _set_heat_mode(client: FlameConnectClient, fire_id: str, value: str) -> None:
    """Set the heater mode.

    Supports ``normal``, ``eco``, ``boost``, and ``boost:<minutes>``
    where minutes is 1-20.
    """
    boost_minutes: int | None = None

    if value.startswith("boost:"):
        try:
            boost_minutes = int(value.split(":")[1])
        except (ValueError, IndexError):
            print("Error: boost format is boost:<minutes> (e.g., boost:15).")
            sys.exit(1)
        if not MIN_BOOST_DURATION <= boost_minutes <= MAX_BOOST_DURATION:
            print(
                f"Error: boost duration must be"
                f" {MIN_BOOST_DURATION}-{MAX_BOOST_DURATION}"
                " minutes."
            )
            sys.exit(1)
        heat_mode = HeatMode.BOOST
    elif value in _HEAT_MODE_LOOKUP:
        heat_mode = _HEAT_MODE_LOOKUP[value]
    else:
        valid = ", ".join([*_HEAT_MODE_LOOKUP, "boost:<minutes>"])
        print(f"Error: heat-mode must be one of: {valid}.")
        sys.exit(1)

    overview = await client.get_fire_overview(fire_id)
    current = _find_param(overview.parameters, HeatParam)
    if current is None:
        print("Error: no HeatSettings parameter found.")
        sys.exit(1)
    if boost_minutes is not None:
        new_param = replace(current, heat_mode=heat_mode, boost_duration=boost_minutes)
    else:
        new_param = replace(current, heat_mode=heat_mode)
    await client.write_parameters(fire_id, [new_param])
    print(f"Heat mode set to {value}.")


async def _set_heat_temp(client: FlameConnectClient, fire_id: str, value: str) -> None:
    """Set the heater setpoint temperature."""
    temp = float(value)
    overview = await client.get_fire_overview(fire_id)
    temp_unit_param = _find_param(overview.parameters, TempUnitParam)
    unit = temp_unit_param.unit if temp_unit_param else TempUnit.CELSIUS
    if unit == TempUnit.FAHRENHEIT:
        min_temp, max_temp = MIN_TEMP_FAHRENHEIT, MAX_TEMP_FAHRENHEIT
    else:
        min_temp, max_temp = MIN_TEMP_CELSIUS, MAX_TEMP_CELSIUS
    if not (min_temp <= temp <= max_temp):
        unit_suffix = temp_suffix(temp_unit_param)
        print(
            f"Error: heat-temp must be between"
            f" {min_temp} and {max_temp}\u00b0{unit_suffix}."
        )
        sys.exit(1)
    current = _find_param(overview.parameters, HeatParam)
    if current is None:
        print("Error: no HeatSettings parameter found.")
        sys.exit(1)
    unit_suffix = temp_suffix(temp_unit_param)
    # The wire always stores Celsius; convert the entered display value first.
    setpoint_celsius = convert_from_display(temp, unit)
    new_param = replace(current, setpoint_temperature=setpoint_celsius)
    await client.write_parameters(fire_id, [new_param])
    print(f"Heat temperature set to {temp}\u00b0{unit_suffix}.")


async def _set_timer(client: FlameConnectClient, fire_id: str, value: str) -> None:
    """Set or disable the timer."""
    minutes = int(value)
    if minutes < 0:
        print("Error: timer must be non-negative (0 to disable).")
        sys.exit(1)
    if minutes > MAX_TIMER_DURATION:
        print(f"Error: timer must not exceed {MAX_TIMER_DURATION} minutes.")
        sys.exit(1)
    timer_status = TimerStatus.ENABLED if minutes > 0 else TimerStatus.DISABLED
    timer_param = TimerParam(timer_status=timer_status, duration=minutes)
    await client.write_parameters(fire_id, [timer_param])
    if minutes > 0:
        print(f"Timer set to {minutes} minutes.")
    else:
        print("Timer disabled.")


async def _set_temp_unit(client: FlameConnectClient, fire_id: str, value: str) -> None:
    """Set the temperature display unit."""
    if value not in _TEMP_UNIT_LOOKUP:
        valid = ", ".join(_TEMP_UNIT_LOOKUP)
        print(f"Error: temp-unit must be one of: {valid}.")
        sys.exit(1)
    unit = _TEMP_UNIT_LOOKUP[value]
    temp_unit_param = TempUnitParam(unit=unit)
    await client.write_parameters(fire_id, [temp_unit_param])
    print(f"Temperature unit set to {value}.")


async def _set_media_color(
    client: FlameConnectClient, fire_id: str, value: str
) -> None:
    """Set the media color."""
    color = _parse_color(value)
    if color is None:
        names = ", ".join(NAMED_COLORS)
        print(f"Error: media-color must be R,G,B,W (0-255) or a preset: {names}.")
        sys.exit(1)
    overview = await client.get_fire_overview(fire_id)
    current = _find_param(overview.parameters, FlameEffectParam)
    if current is None:
        print("Error: no FlameEffect parameter found.")
        sys.exit(1)
    new_param = replace(current, media_color=color)
    await client.write_parameters(fire_id, [new_param])
    print(f"Media color set to {value}.")


async def _set_overhead_color(
    client: FlameConnectClient, fire_id: str, value: str
) -> None:
    """Set the overhead color."""
    color = _parse_color(value)
    if color is None:
        names = ", ".join(NAMED_COLORS)
        print(f"Error: overhead-color must be R,G,B,W (0-255) or a preset: {names}.")
        sys.exit(1)
    overview = await client.get_fire_overview(fire_id)
    current = _find_param(overview.parameters, FlameEffectParam)
    if current is None:
        print("Error: no FlameEffect parameter found.")
        sys.exit(1)
    new_param = replace(current, overhead_color=color)
    await client.write_parameters(fire_id, [new_param])
    print(f"Overhead color set to {value}.")


async def _set_heat_status(
    client: FlameConnectClient, fire_id: str, value: str
) -> None:
    """Set the heater on or off."""
    lookup: dict[str, HeatStatus] = {"on": HeatStatus.ON, "off": HeatStatus.OFF}
    if value not in lookup:
        valid = ", ".join(lookup)
        print(f"Error: heat-status must be one of: {valid}.")
        sys.exit(1)
    heat_status = lookup[value]
    overview = await client.get_fire_overview(fire_id)
    current = _find_param(overview.parameters, HeatParam)
    if current is None:
        print("Error: no HeatSettings parameter found.")
        sys.exit(1)
    new_param = replace(current, heat_status=heat_status)
    await client.write_parameters(fire_id, [new_param])
    print(f"Heat status set to {value}.")


_SET_HANDLERS: dict[str, Callable[..., Awaitable[None]]] = {
    "mode": _set_mode,
    "flame-speed": _set_flame_speed,
    "heat-mode": _set_heat_mode,
    "heat-temp": _set_heat_temp,
    "heat-status": _set_heat_status,
    "timer": _set_timer,
    "temp-unit": _set_temp_unit,
    "media-color": _set_media_color,
    "overhead-color": _set_overhead_color,
}


async def cmd_tui(*, log_level: int = logging.WARNING) -> None:
    """Launch the TUI, showing install message if missing."""
    try:
        from flameconnect.tui import run_tui
    except ImportError:
        print("The TUI requires the 'tui' extra. Run with:")
        print("  uv tool run flameconnect[tui]")
        sys.exit(1)
    await run_tui(log_level=log_level)


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argparse parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="flameconnect",
        description=(
            "Control Dimplex, Faber, and Real Flame fireplaces"
            " via the Flame Connect cloud API"
        ),
    )
    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    verbosity.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose logging including HTTP requests and responses",
    )

    subparsers = parser.add_subparsers(dest="command")

    # list
    subparsers.add_parser("list", help="List registered fireplaces")

    # status
    sp_status = subparsers.add_parser("status", help="Show current fireplace status")
    sp_status.add_argument("fire_id", help="Fireplace ID")

    # on
    sp_on = subparsers.add_parser("on", help="Turn on a fireplace")
    sp_on.add_argument("fire_id", help="Fireplace ID")

    # off
    sp_off = subparsers.add_parser("off", help="Turn off a fireplace")
    sp_off.add_argument("fire_id", help="Fireplace ID")

    # set
    sp_set = subparsers.add_parser("set", help="Set a fireplace parameter")
    sp_set.add_argument("fire_id", help="Fireplace ID")
    sp_set.add_argument(
        "param",
        help=(
            "Parameter name: mode, flame-speed, brightness, pulsating,"
            " flame-color, media-theme, heat-status, heat-mode,"
            " heat-temp, timer, temp-unit, flame-effect, media-light,"
            " media-color, overhead-light, overhead-color,"
            " ambient-sensor"
        ),
    )
    sp_set.add_argument("value", help="Value to set")

    # tui
    subparsers.add_parser("tui", help="Launch the interactive TUI")

    return parser


# ---------------------------------------------------------------------------
# Async entry point
# ---------------------------------------------------------------------------


def _masked_input(prompt: str = "Password: ") -> str:
    """Read a password from stdin, printing * for each character."""
    import termios
    import tty

    sys.stdout.write(prompt)
    sys.stdout.flush()
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    chars: list[str] = []
    try:
        tty.setraw(fd)
        while True:
            ch = sys.stdin.read(1)
            if ch in ("\r", "\n"):
                break
            if ch in ("\x7f", "\x08"):  # backspace / delete
                if chars:
                    chars.pop()
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
                continue
            if ch == "\x03":  # Ctrl-C
                raise KeyboardInterrupt
            chars.append(ch)
            sys.stdout.write("*")
            sys.stdout.flush()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    sys.stdout.write("\n")
    sys.stdout.flush()
    return "".join(chars)


async def _cli_auth_prompt(auth_uri: str, redirect_uri: str) -> str:
    """Prompt the user to complete login.

    Asks for email + password and tries direct B2C credential submission.
    Falls back to the manual browser flow if that fails.
    """
    from flameconnect.b2c_login import b2c_login_with_credentials
    from flameconnect.exceptions import AuthenticationError

    print()
    print("=" * 60)
    print("AUTHENTICATION REQUIRED")
    print("=" * 60)
    print()
    email: str = await asyncio.to_thread(input, "Email: ")
    password: str = await asyncio.to_thread(_masked_input, "Password: ")

    try:
        redirect_url = await b2c_login_with_credentials(auth_uri, email, password)
        print("Login successful.")
        return redirect_url
    except AuthenticationError as exc:
        print(f"\nDirect login failed: {exc}")
        print("Falling back to browser login.\n")

    webbrowser.open(auth_uri)
    print("A browser window has been opened. Log in with your account.")
    print()
    print(f"After login, the browser will redirect to {redirect_uri}?code=...")
    print("The page won't load — that's expected.")
    print()
    print("Copy the FULL URL from your browser's address bar and paste it below.")
    print("If the URL has '...' in the middle, it was truncated.")
    print("Use F12 > Console > copy(location.href) to get the full URL.")
    print()
    print("=" * 60)
    result: str = await asyncio.to_thread(input, "\nPaste the redirect URL here: ")
    return result


async def async_main(args: argparse.Namespace) -> None:
    """Run the appropriate subcommand."""
    log_level = (
        logging.DEBUG
        if args.debug
        else logging.INFO
        if args.verbose
        else logging.WARNING
    )
    if args.command is None:
        try:
            from flameconnect.tui import run_tui
        except ImportError:
            build_parser().print_help()
            return
        await run_tui(log_level=log_level)
        return

    if args.command == "tui":
        await cmd_tui(log_level=log_level)
        return

    auth = MsalAuth(prompt_callback=_cli_auth_prompt)
    async with FlameConnectClient(auth=auth) as client:
        if args.command == "list":
            await cmd_list(client)
        elif args.command == "status":
            fire_id: str = args.fire_id
            await cmd_status(client, fire_id)
        elif args.command == "on":
            await cmd_on(client, str(args.fire_id))
        elif args.command == "off":
            await cmd_off(client, str(args.fire_id))
        elif args.command == "set":
            await cmd_set(
                client,
                str(args.fire_id),
                str(args.param),
                str(args.value),
            )


# ---------------------------------------------------------------------------
# Synchronous entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point for the flameconnect CLI."""
    parser = build_parser()
    args = parser.parse_args()
    logging.basicConfig(
        level=(
            logging.DEBUG
            if args.debug
            else logging.INFO
            if args.verbose
            else logging.WARNING
        ),
    )
    asyncio.run(async_main(args))
