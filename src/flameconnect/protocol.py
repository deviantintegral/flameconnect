"""Binary wire protocol encoding and decoding for fireplace parameters."""

from __future__ import annotations

import base64
import logging
import struct

from flameconnect.const import ParameterId
from flameconnect.exceptions import ProtocolError
from flameconnect.models import (
    ErrorParam,
    FireMode,
    FlameColor,
    FlameEffect,
    FlameEffectParam,
    HeatControl,
    HeatMode,
    HeatModeParam,
    HeatParam,
    HeatStatus,
    LightStatus,
    LogEffect,
    LogEffectParam,
    MediaTheme,
    ModeParam,
    Parameter,
    RGBWColor,
    SoftwareVersionParam,
    SoundParam,
    TempUnit,
    TempUnitParam,
    TimerParam,
    TimerStatus,
)

_LOGGER = logging.getLogger(__name__)

# Header size: 2 bytes LE param ID + 1 byte payload size
_HEADER_SIZE = 3


# ---------------------------------------------------------------------------
# Temperature helpers
# ---------------------------------------------------------------------------


def _decode_temperature(raw: bytes, offset: int) -> float:
    """Decode a two-byte temperature value into a float."""
    return float(raw[offset]) + float(raw[offset + 1]) / 10.0


def _encode_temperature(temp: float) -> bytes:
    """Encode a float temperature as two bytes: [integer, decimal_tenth]."""
    return bytes([int(temp), int((temp % 1) * 10)])


# ---------------------------------------------------------------------------
# Wire header helpers
# ---------------------------------------------------------------------------


def _make_header(parameter_id: int, payload_size: int) -> bytes:
    """Build a 3-byte wire header: 2-byte LE param ID + 1-byte payload size."""
    return struct.pack("<HB", parameter_id, payload_size)


def _check_length(raw: bytes, expected: int, name: str) -> None:
    """Raise ProtocolError if *raw* is shorter than *expected*."""
    if len(raw) < expected:
        msg = f"Insufficient data for {name}: expected {expected} bytes, got {len(raw)}"
        raise ProtocolError(msg)


# ---------------------------------------------------------------------------
# Individual decoders
# ---------------------------------------------------------------------------


def _decode_temp_unit(raw: bytes) -> TempUnitParam:
    """Decode TempUnit (236): 4 bytes total."""
    _check_length(raw, 4, "TempUnit")
    unit = TempUnit(raw[3])
    _LOGGER.debug("Decoded TempUnit: %s", unit)
    return TempUnitParam(unit=unit)


def _decode_mode(raw: bytes) -> ModeParam:
    """Decode Mode (321): 6 bytes total."""
    _check_length(raw, 6, "Mode")
    mode = FireMode(raw[3])
    temperature = _decode_temperature(raw, 4)
    _LOGGER.debug("Decoded Mode: mode=%s temperature=%.1f", mode, temperature)
    return ModeParam(mode=mode, temperature=temperature)


def _decode_flame_effect(raw: bytes) -> FlameEffectParam:
    """Decode FlameEffect (322): 23 bytes total."""
    _check_length(raw, 23, "FlameEffect")
    flame_effect = FlameEffect(raw[3])
    flame_speed = raw[4] + 1  # wire is 0-indexed, model is 1-indexed
    brightness = raw[5]
    media_theme = MediaTheme(raw[6])
    media_light = LightStatus(raw[7])
    # Wire byte order: Red, Blue, Green, White
    media_color = RGBWColor(red=raw[8], blue=raw[9], green=raw[10], white=raw[11])
    # raw[12] is padding
    overhead_light = LightStatus(raw[13])
    overhead_color = RGBWColor(red=raw[14], blue=raw[15], green=raw[16], white=raw[17])
    light_status = LightStatus(raw[18])
    flame_color = FlameColor(raw[19])
    # raw[20], raw[21] are padding
    ambient_sensor = LightStatus(raw[22])
    _LOGGER.debug(
        "Decoded FlameEffect: effect=%s speed=%d brightness=%d",
        flame_effect,
        flame_speed,
        brightness,
    )
    return FlameEffectParam(
        flame_effect=flame_effect,
        flame_speed=flame_speed,
        brightness=brightness,
        media_theme=media_theme,
        media_light=media_light,
        media_color=media_color,
        overhead_light=overhead_light,
        overhead_color=overhead_color,
        light_status=light_status,
        flame_color=flame_color,
        ambient_sensor=ambient_sensor,
    )


def _decode_heat_settings(raw: bytes) -> HeatParam:
    """Decode HeatSettings (323): 10 bytes total."""
    _check_length(raw, 10, "HeatSettings")
    heat_status = HeatStatus(raw[3])
    heat_mode = HeatMode(raw[4])
    setpoint = _decode_temperature(raw, 5)
    boost_duration = raw[7] | (raw[8] << 8)
    _LOGGER.debug(
        "Decoded HeatSettings: status=%s mode=%s temp=%.1f boost=%d",
        heat_status,
        heat_mode,
        setpoint,
        boost_duration,
    )
    return HeatParam(
        heat_status=heat_status,
        heat_mode=heat_mode,
        setpoint_temperature=setpoint,
        boost_duration=boost_duration,
    )


def _decode_heat_mode(raw: bytes) -> HeatModeParam:
    """Decode HeatMode (325): 4 bytes total."""
    _check_length(raw, 4, "HeatMode")
    heat_control = HeatControl(raw[3])
    _LOGGER.debug("Decoded HeatMode: %s", heat_control)
    return HeatModeParam(heat_control=heat_control)


def _decode_timer(raw: bytes) -> TimerParam:
    """Decode Timer (326): 6 bytes total."""
    _check_length(raw, 6, "Timer")
    timer_status = TimerStatus(raw[3])
    duration = raw[4] | (raw[5] << 8)
    _LOGGER.debug("Decoded Timer: status=%s duration=%d", timer_status, duration)
    return TimerParam(timer_status=timer_status, duration=duration)


def _decode_software_version(raw: bytes) -> SoftwareVersionParam:
    """Decode SoftwareVersion (327): 12 bytes total."""
    _check_length(raw, 12, "SoftwareVersion")
    result = SoftwareVersionParam(
        ui_major=raw[3],
        ui_minor=raw[4],
        ui_test=raw[5],
        control_major=raw[6],
        control_minor=raw[7],
        control_test=raw[8],
        relay_major=raw[9],
        relay_minor=raw[10],
        relay_test=raw[11],
    )
    _LOGGER.debug(
        "Decoded SoftwareVersion: UI=%d.%d.%d Control=%d.%d.%d Relay=%d.%d.%d",
        result.ui_major,
        result.ui_minor,
        result.ui_test,
        result.control_major,
        result.control_minor,
        result.control_test,
        result.relay_major,
        result.relay_minor,
        result.relay_test,
    )
    return result


def _decode_error(raw: bytes) -> ErrorParam:
    """Decode Error (329): 7 bytes total."""
    _check_length(raw, 7, "Error")
    result = ErrorParam(
        error_byte1=raw[3],
        error_byte2=raw[4],
        error_byte3=raw[5],
        error_byte4=raw[6],
    )
    _LOGGER.debug(
        "Decoded Error: 0x%02X 0x%02X 0x%02X 0x%02X",
        result.error_byte1,
        result.error_byte2,
        result.error_byte3,
        result.error_byte4,
    )
    return result


def _decode_sound(raw: bytes) -> SoundParam:
    """Decode Sound (369): 5 bytes total."""
    _check_length(raw, 5, "Sound")
    volume = raw[3]
    sound_file = raw[4]
    _LOGGER.debug("Decoded Sound: volume=%d sound_file=%d", volume, sound_file)
    return SoundParam(volume=volume, sound_file=sound_file)


def _decode_log_effect(raw: bytes) -> LogEffectParam:
    """Decode LogEffect (370): 11 bytes total."""
    _check_length(raw, 11, "LogEffect")
    log_effect = LogEffect(raw[3])
    # raw[4] is theme — not stored in the dataclass (pattern serves as the field)
    # Wire byte order: Red, Blue, Green, White
    color = RGBWColor(red=raw[5], blue=raw[6], green=raw[7], white=raw[8])
    pattern = raw[9]
    # raw[10] is padding
    _LOGGER.debug("Decoded LogEffect: effect=%s pattern=%d", log_effect, pattern)
    return LogEffectParam(log_effect=log_effect, color=color, pattern=pattern)


# ---------------------------------------------------------------------------
# Individual encoders
# ---------------------------------------------------------------------------


def _encode_temp_unit(param: TempUnitParam) -> bytes:
    """Encode TempUnit (236): 3-byte header + 1 byte payload."""
    _LOGGER.debug("Encoding TempUnit: %s", param.unit)
    return _make_header(ParameterId.TEMPERATURE_UNIT, 1) + bytes([param.unit])


def _encode_mode(param: ModeParam) -> bytes:
    """Encode Mode (321): 3-byte header + 3 bytes payload."""
    _LOGGER.debug(
        "Encoding Mode: mode=%s temperature=%.1f",
        param.mode,
        param.temperature,
    )
    return (
        _make_header(ParameterId.MODE, 3)
        + bytes([param.mode])
        + _encode_temperature(param.temperature)
    )


def _encode_flame_effect(param: FlameEffectParam) -> bytes:
    """Encode FlameEffect (322): 3-byte header + 20 bytes payload."""
    _LOGGER.debug(
        "Encoding FlameEffect: effect=%s speed=%d",
        param.flame_effect,
        param.flame_speed,
    )
    payload = bytes(
        [
            param.flame_effect,
            max(0, param.flame_speed - 1),  # model is 1-indexed, wire is 0-indexed
            param.brightness,
            param.media_theme,
            param.media_light,
            # Wire byte order: Red, Blue, Green, White
            param.media_color.red,
            param.media_color.blue,
            param.media_color.green,
            param.media_color.white,
            0x00,  # padding
            param.overhead_light,
            param.overhead_color.red,
            param.overhead_color.blue,
            param.overhead_color.green,
            param.overhead_color.white,
            param.light_status,
            param.flame_color,
            0x00,  # padding
            0x00,  # padding
            param.ambient_sensor,
        ]
    )
    return _make_header(ParameterId.FLAME_EFFECT, 20) + payload


def _encode_heat_settings(param: HeatParam) -> bytes:
    """Encode HeatSettings (323): 3-byte header + 7 bytes payload."""
    _LOGGER.debug(
        "Encoding HeatSettings: status=%s mode=%s temp=%.1f boost=%d",
        param.heat_status,
        param.heat_mode,
        param.setpoint_temperature,
        param.boost_duration,
    )
    boost_lo = param.boost_duration & 0xFF
    boost_hi = (param.boost_duration >> 8) & 0xFF
    payload = (
        bytes([param.heat_status, param.heat_mode])
        + _encode_temperature(param.setpoint_temperature)
        + bytes([boost_lo, boost_hi])
    )
    return _make_header(ParameterId.HEAT_SETTINGS, len(payload)) + payload


def _encode_heat_mode(param: HeatModeParam) -> bytes:
    """Encode HeatMode (325): 3-byte header + 1 byte payload."""
    _LOGGER.debug("Encoding HeatMode: %s", param.heat_control)
    return _make_header(ParameterId.HEAT_MODE, 1) + bytes([param.heat_control])


def _encode_timer(param: TimerParam) -> bytes:
    """Encode Timer (326): 3-byte header + 3 bytes payload."""
    _LOGGER.debug(
        "Encoding Timer: status=%s duration=%d",
        param.timer_status,
        param.duration,
    )
    dur_lo = param.duration & 0xFF
    dur_hi = (param.duration >> 8) & 0xFF
    return _make_header(ParameterId.TIMER, 3) + bytes(
        [param.timer_status, dur_lo, dur_hi]
    )


def _encode_sound(param: SoundParam) -> bytes:
    """Encode Sound (369): 3-byte header + 2 bytes payload."""
    _LOGGER.debug(
        "Encoding Sound: volume=%d sound_file=%d",
        param.volume,
        param.sound_file,
    )
    return _make_header(ParameterId.SOUND, 2) + bytes([param.volume, param.sound_file])


def _encode_log_effect(param: LogEffectParam) -> bytes:
    """Encode LogEffect (370): 3-byte header + 8 bytes payload."""
    _LOGGER.debug(
        "Encoding LogEffect: effect=%s pattern=%d",
        param.log_effect,
        param.pattern,
    )
    payload = bytes(
        [
            param.log_effect,
            0x00,  # theme byte (placeholder)
            # Wire byte order: Red, Blue, Green, White
            param.color.red,
            param.color.blue,
            param.color.green,
            param.color.white,
            param.pattern,
            0x00,  # padding
        ]
    )
    return _make_header(ParameterId.LOG_EFFECT, 8) + payload


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def decode_parameter(parameter_id: int, data: bytes) -> Parameter:
    """Decode raw wire bytes into a typed parameter dataclass.

    Args:
        parameter_id: The ParameterId integer value.
        data: The full base64-decoded payload (including the 3-byte header).

    Returns:
        A typed parameter dataclass.

    Raises:
        ProtocolError: If the parameter ID is unknown or data is too short.
    """
    _LOGGER.debug("Decoding parameter %d (%d bytes)", parameter_id, len(data))

    if parameter_id == ParameterId.TEMPERATURE_UNIT:
        return _decode_temp_unit(data)
    if parameter_id == ParameterId.MODE:
        return _decode_mode(data)
    if parameter_id == ParameterId.FLAME_EFFECT:
        return _decode_flame_effect(data)
    if parameter_id == ParameterId.HEAT_SETTINGS:
        return _decode_heat_settings(data)
    if parameter_id == ParameterId.HEAT_MODE:
        return _decode_heat_mode(data)
    if parameter_id == ParameterId.TIMER:
        return _decode_timer(data)
    if parameter_id == ParameterId.SOFTWARE_VERSION:
        return _decode_software_version(data)
    if parameter_id == ParameterId.ERROR:
        return _decode_error(data)
    if parameter_id == ParameterId.SOUND:
        return _decode_sound(data)
    if parameter_id == ParameterId.LOG_EFFECT:
        return _decode_log_effect(data)

    msg = f"Unknown parameter ID: {parameter_id}"
    raise ProtocolError(msg)


def encode_parameter(param: Parameter) -> str:
    """Encode a parameter dataclass into a base64 string for the API.

    Args:
        param: A typed parameter dataclass.

    Returns:
        A base64-encoded ASCII string.

    Raises:
        ProtocolError: If the parameter type is read-only or unknown.
    """
    raw: bytes

    if isinstance(param, TempUnitParam):
        raw = _encode_temp_unit(param)
    elif isinstance(param, ModeParam):
        raw = _encode_mode(param)
    elif isinstance(param, FlameEffectParam):
        raw = _encode_flame_effect(param)
    elif isinstance(param, HeatParam):
        raw = _encode_heat_settings(param)
    elif isinstance(param, HeatModeParam):
        raw = _encode_heat_mode(param)
    elif isinstance(param, TimerParam):
        raw = _encode_timer(param)
    elif isinstance(param, SoundParam):
        raw = _encode_sound(param)
    elif isinstance(param, LogEffectParam):
        raw = _encode_log_effect(param)
    elif isinstance(param, SoftwareVersionParam):
        msg = "SoftwareVersionParam is read-only and cannot be encoded"
        raise ProtocolError(msg)
    elif isinstance(param, ErrorParam):
        msg = "ErrorParam is read-only and cannot be encoded"
        raise ProtocolError(msg)
    else:
        msg = f"Unknown parameter type: {type(param).__name__}"
        raise ProtocolError(msg)

    return base64.b64encode(raw).decode("ascii")
