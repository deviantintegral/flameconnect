"""Command-line interface for flameconnect."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import webbrowser
from typing import overload

from flameconnect.auth import MsalAuth
from flameconnect.client import FlameConnectClient
from flameconnect.models import (
    ErrorParam,
    FireMode,
    FlameEffectParam,
    HeatMode,
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
    TimerStatus,
)

# ---------------------------------------------------------------------------
# Enum display name lookups
# ---------------------------------------------------------------------------

_FIRE_MODE_NAMES: dict[int, str] = {0: "Standby", 1: "On"}
_BRIGHTNESS_NAMES: dict[int, str] = {0: "High", 1: "Low"}
_PULSATING_NAMES: dict[int, str] = {0: "Off", 1: "On"}
_FLAME_EFFECT_NAMES: dict[int, str] = {0: "Off", 1: "On"}
_HEAT_STATUS_NAMES: dict[int, str] = {0: "Off", 1: "On"}
_HEAT_MODE_NAMES: dict[int, str] = {
    0: "Normal",
    1: "Boost",
    2: "Eco",
    3: "Fan Only",
    4: "Schedule",
}
_HEAT_CONTROL_NAMES: dict[int, str] = {
    0: "Software Disabled",
    1: "Hardware Disabled",
    2: "Enabled",
}
_FLAME_COLOR_NAMES: dict[int, str] = {
    0: "All",
    1: "Yellow/Red",
    2: "Yellow/Blue",
    3: "Blue",
    4: "Red",
    5: "Yellow",
    6: "Blue/Red",
}
_LIGHT_STATUS_NAMES: dict[int, str] = {0: "Off", 1: "On"}
_TIMER_STATUS_NAMES: dict[int, str] = {0: "Disabled", 1: "Enabled"}
_TEMP_UNIT_NAMES: dict[int, str] = {0: "Fahrenheit", 1: "Celsius"}
_LOG_EFFECT_NAMES: dict[int, str] = {0: "Off", 1: "On"}
_MEDIA_THEME_NAMES: dict[int, str] = {
    0: "User Defined",
    1: "White",
    2: "Blue",
    3: "Purple",
    4: "Red",
    5: "Green",
    6: "Prism",
    7: "Kaleidoscope",
    8: "Midnight",
}
_CONNECTION_STATE_NAMES: dict[int, str] = {
    0: "Unknown",
    1: "Not Connected",
    2: "Connected",
    3: "Updating Firmware",
}

# Mapping from CLI heat-mode string to HeatMode enum value
_HEAT_MODE_LOOKUP: dict[str, HeatMode] = {
    "normal": HeatMode.NORMAL,
    "boost": HeatMode.BOOST,
    "eco": HeatMode.ECO,
    "fan-only": HeatMode.FAN_ONLY,
}

_SET_PARAM_NAMES = "mode, flame-speed, brightness, heat-mode, heat-temp, timer"


def _enum_name(mapping: dict[int, str], value: int) -> str:
    """Look up a human-readable name for an enum value."""
    return mapping.get(value, f"Unknown({value})")


def _format_rgbw(color: RGBWColor) -> str:
    """Format an RGBWColor for display."""
    return f"RGBW({color.red}, {color.green}, {color.blue}, {color.white})"


# ---------------------------------------------------------------------------
# Generic parameter finder (with overloads for type safety)
# ---------------------------------------------------------------------------


@overload
def _find_param(
    parameters: list[Parameter], param_type: type[FlameEffectParam]
) -> FlameEffectParam | None: ...


@overload
def _find_param(
    parameters: list[Parameter], param_type: type[HeatParam]
) -> HeatParam | None: ...


def _find_param[T](parameters: list[Parameter], param_type: type[T]) -> T | None:
    """Find the first parameter of a given type in a list."""
    for p in parameters:
        if isinstance(p, param_type):
            return p
    return None


# ---------------------------------------------------------------------------
# Status display formatting
# ---------------------------------------------------------------------------


def _display_mode(param: ModeParam) -> None:
    """Display Mode parameter."""
    print("\n  [321] Mode")
    print(f"  {'─' * 40}")
    mode = _enum_name(_FIRE_MODE_NAMES, param.mode)
    print(f"    Mode:           {mode}")
    print(f"    Temperature:    {param.temperature}\u00b0")


def _display_flame_effect(param: FlameEffectParam) -> None:
    """Display FlameEffect parameter."""
    print("\n  [322] Flame Effect")
    print(f"  {'─' * 40}")
    flame = _enum_name(_FLAME_EFFECT_NAMES, param.flame_effect)
    print(f"    Flame:          {flame}")
    print(f"    Flame Speed:    {param.flame_speed} / 5")
    brightness = _enum_name(_BRIGHTNESS_NAMES, param.brightness)
    pulsating = _enum_name(_PULSATING_NAMES, param.pulsating_effect)
    print(f"    Brightness:     {brightness}")
    print(f"    Pulsating:      {pulsating}")
    color = _enum_name(_FLAME_COLOR_NAMES, param.flame_color)
    print(f"    Flame Color:    {color}")
    theme = _enum_name(_MEDIA_THEME_NAMES, param.media_theme)
    rgbw = _format_rgbw(param.media_color)
    print(f"    Fuel Bed Light: {theme} | {rgbw}")
    print(f"    Overhead Light: {_format_rgbw(param.overhead_color)}")
    light = _enum_name(_LIGHT_STATUS_NAMES, param.light_status)
    print(f"    Light Status:   {light}")
    ambient = _enum_name(_LIGHT_STATUS_NAMES, param.ambient_sensor)
    print(f"    Ambient Sensor: {ambient}")


def _display_heat(param: HeatParam) -> None:
    """Display HeatSettings parameter."""
    print("\n  [323] Heat Settings")
    print(f"  {'─' * 40}")
    status = _enum_name(_HEAT_STATUS_NAMES, param.heat_status)
    print(f"    Heat:           {status}")
    mode = _enum_name(_HEAT_MODE_NAMES, param.heat_mode)
    print(f"    Heat Mode:      {mode}")
    print(f"    Setpoint Temp:  {param.setpoint_temperature}\u00b0")
    print(f"    Boost Duration: {param.boost_duration}")


def _display_heat_mode(param: HeatModeParam) -> None:
    """Display HeatMode parameter."""
    print("\n  [325] Heat Mode")
    print(f"  {'─' * 40}")
    ctrl = _enum_name(_HEAT_CONTROL_NAMES, param.heat_control)
    print(f"    Heat Control:   {ctrl}")


def _display_timer(param: TimerParam) -> None:
    """Display Timer parameter."""
    from datetime import datetime, timedelta

    dur = param.duration
    print("\n  [326] Timer Mode")
    print(f"  {'─' * 40}")
    ts = _enum_name(_TIMER_STATUS_NAMES, param.timer_status)
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
    unit = _enum_name(_TEMP_UNIT_NAMES, param.unit)
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
    effect = _enum_name(_LOG_EFFECT_NAMES, param.log_effect)
    print(f"    Log Effect:     {effect}")
    print(f"    Colors:         {_format_rgbw(param.color)}")
    print(f"    Pattern:        {param.pattern}")


def _display_parameter(param: Parameter) -> None:
    """Display a single parameter in human-readable form."""
    if isinstance(param, ModeParam):
        _display_mode(param)
    elif isinstance(param, FlameEffectParam):
        _display_flame_effect(param)
    elif isinstance(param, HeatParam):
        _display_heat(param)
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
        state = _enum_name(_CONNECTION_STATE_NAMES, fire.connection_state)
        print(f"  Connection:  {state}")


async def cmd_status(client: FlameConnectClient, fire_id: str) -> None:
    """Display the current status of a fireplace."""
    overview = await client.get_fire_overview(fire_id)
    fire = overview.fire
    print(f"Fireplace: {fire.friendly_name} ({fire.fire_id})")
    state = _enum_name(_CONNECTION_STATE_NAMES, fire.connection_state)
    print(f"Connection: {state}")

    if not overview.parameters:
        print("\nNo parameters returned (fireplace may be offline).")
        return

    count = len(overview.parameters)
    print(f"\n{count} parameter(s) reported:")
    for param in overview.parameters:
        _display_parameter(param)


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
    if param == "mode":
        await _set_mode(client, fire_id, value)
        return
    if param == "flame-speed":
        await _set_flame_speed(client, fire_id, value)
        return
    if param == "brightness":
        await _set_brightness(client, fire_id, value)
        return
    if param == "heat-mode":
        await _set_heat_mode(client, fire_id, value)
        return
    if param == "heat-temp":
        await _set_heat_temp(client, fire_id, value)
        return
    if param == "timer":
        await _set_timer(client, fire_id, value)
        return

    print(f"Error: unknown parameter '{param}'. Valid: {_SET_PARAM_NAMES}.")
    sys.exit(1)


async def _set_mode(client: FlameConnectClient, fire_id: str, value: str) -> None:
    """Set the fireplace mode."""
    if value not in ("standby", "manual"):
        print("Error: mode must be 'standby' or 'manual'.")
        sys.exit(1)
    mode = FireMode.STANDBY if value == "standby" else FireMode.MANUAL
    mode_param = ModeParam(mode=mode, temperature=22.0)
    await client.write_parameters(fire_id, [mode_param])
    print(f"Mode set to {value}.")


async def _set_flame_speed(
    client: FlameConnectClient, fire_id: str, value: str
) -> None:
    """Set flame speed (1-5)."""
    speed = int(value)
    if speed < 1 or speed > 5:
        print("Error: flame-speed must be between 1 and 5.")
        sys.exit(1)
    overview = await client.get_fire_overview(fire_id)
    current = _find_param(overview.parameters, FlameEffectParam)
    if current is None:
        print("Error: no FlameEffect parameter found.")
        sys.exit(1)
    new_param = FlameEffectParam(
        flame_effect=current.flame_effect,
        flame_speed=speed,
        brightness=current.brightness,
        pulsating_effect=current.pulsating_effect,
        media_theme=current.media_theme,
        media_light=current.media_light,
        media_color=current.media_color,
        overhead_light=current.overhead_light,
        overhead_color=current.overhead_color,
        light_status=current.light_status,
        flame_color=current.flame_color,
        ambient_sensor=current.ambient_sensor,
    )
    await client.write_parameters(fire_id, [new_param])
    print(f"Flame speed set to {speed}.")


async def _set_brightness(client: FlameConnectClient, fire_id: str, value: str) -> None:
    """Set brightness (low or high)."""
    from flameconnect.models import Brightness

    lookup = {"low": Brightness.LOW, "high": Brightness.HIGH}
    if value not in lookup:
        print("Error: brightness must be 'low' or 'high'.")
        sys.exit(1)
    brightness = lookup[value]
    overview = await client.get_fire_overview(fire_id)
    current = _find_param(overview.parameters, FlameEffectParam)
    if current is None:
        print("Error: no FlameEffect parameter found.")
        sys.exit(1)
    new_param = FlameEffectParam(
        flame_effect=current.flame_effect,
        flame_speed=current.flame_speed,
        brightness=brightness,
        pulsating_effect=current.pulsating_effect,
        media_theme=current.media_theme,
        media_light=current.media_light,
        media_color=current.media_color,
        overhead_light=current.overhead_light,
        overhead_color=current.overhead_color,
        light_status=current.light_status,
        flame_color=current.flame_color,
        ambient_sensor=current.ambient_sensor,
    )
    await client.write_parameters(fire_id, [new_param])
    print(f"Brightness set to {value}.")


async def _set_heat_mode(client: FlameConnectClient, fire_id: str, value: str) -> None:
    """Set the heater mode."""
    if value not in _HEAT_MODE_LOOKUP:
        valid = ", ".join(_HEAT_MODE_LOOKUP)
        print(f"Error: heat-mode must be one of: {valid}.")
        sys.exit(1)
    heat_mode = _HEAT_MODE_LOOKUP[value]
    overview = await client.get_fire_overview(fire_id)
    current = _find_param(overview.parameters, HeatParam)
    if current is None:
        print("Error: no HeatSettings parameter found.")
        sys.exit(1)
    new_param = HeatParam(
        heat_status=current.heat_status,
        heat_mode=heat_mode,
        setpoint_temperature=current.setpoint_temperature,
        boost_duration=current.boost_duration,
    )
    await client.write_parameters(fire_id, [new_param])
    print(f"Heat mode set to {value}.")


async def _set_heat_temp(client: FlameConnectClient, fire_id: str, value: str) -> None:
    """Set the heater setpoint temperature."""
    temp = float(value)
    overview = await client.get_fire_overview(fire_id)
    current = _find_param(overview.parameters, HeatParam)
    if current is None:
        print("Error: no HeatSettings parameter found.")
        sys.exit(1)
    new_param = HeatParam(
        heat_status=current.heat_status,
        heat_mode=current.heat_mode,
        setpoint_temperature=temp,
        boost_duration=current.boost_duration,
    )
    await client.write_parameters(fire_id, [new_param])
    print(f"Heat temperature set to {temp}\u00b0.")


async def _set_timer(client: FlameConnectClient, fire_id: str, value: str) -> None:
    """Set or disable the timer."""
    minutes = int(value)
    if minutes < 0:
        print("Error: timer must be non-negative (0 to disable).")
        sys.exit(1)
    timer_status = TimerStatus.ENABLED if minutes > 0 else TimerStatus.DISABLED
    timer_param = TimerParam(timer_status=timer_status, duration=minutes)
    await client.write_parameters(fire_id, [timer_param])
    if minutes > 0:
        print(f"Timer set to {minutes} minutes.")
    else:
        print("Timer disabled.")


async def cmd_tui(*, verbose: bool = False) -> None:
    """Launch the TUI, showing install message if missing."""
    try:
        from flameconnect.tui import run_tui
    except ImportError:
        print("The TUI requires the 'tui' extra. Install with:")
        print("  pip install flameconnect[tui]")
        print("  # or: uv add flameconnect[tui]")
        sys.exit(1)
    await run_tui(verbose=verbose)


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argparse parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="flameconnect",
        description=("Control Dimplex fireplaces via the Flame Connect cloud API"),
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
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
            "Parameter name: mode, flame-speed, brightness, heat-mode, heat-temp, timer"
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
    if args.command in (None, "tui"):
        await cmd_tui(verbose=args.verbose)
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
        level=logging.DEBUG if args.verbose else logging.WARNING,
    )
    asyncio.run(async_main(args))
