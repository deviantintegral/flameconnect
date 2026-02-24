"""Tests for the wire protocol encoding and decoding."""

from __future__ import annotations

import base64
import struct

import pytest

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
    RGBWColor,
    SoftwareVersionParam,
    SoundParam,
    TempUnit,
    TempUnitParam,
    TimerParam,
    TimerStatus,
)
from flameconnect.protocol import decode_parameter, encode_parameter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_header(param_id: int, payload_size: int) -> bytes:
    """Build a 3-byte wire header."""
    return struct.pack("<HB", param_id, payload_size)


def _roundtrip(param, param_id: int):
    """Encode a param to base64, decode back, and return the decoded param."""
    b64 = encode_parameter(param)
    raw = base64.b64decode(b64)
    return decode_parameter(param_id, raw)


# ---------------------------------------------------------------------------
# Round-trip tests for each parameter type
# ---------------------------------------------------------------------------


class TestModeParamRoundTrip:
    """Round-trip tests for ModeParam (321)."""

    def test_manual_mode(self):
        original = ModeParam(mode=FireMode.MANUAL, temperature=22.5)
        decoded = _roundtrip(original, ParameterId.MODE)
        assert decoded == original

    def test_standby_mode(self):
        original = ModeParam(mode=FireMode.STANDBY, temperature=0.0)
        decoded = _roundtrip(original, ParameterId.MODE)
        assert decoded == original


class TestFlameEffectParamRoundTrip:
    """Round-trip tests for FlameEffectParam (322)."""

    def test_full_flame_effect(self):
        original = FlameEffectParam(
            flame_effect=FlameEffect.ON,
            flame_speed=3,
            brightness=200,
            media_theme=MediaTheme.KALEIDOSCOPE,
            media_light=LightStatus.ON,
            media_color=RGBWColor(red=100, green=75, blue=50, white=25),
            overhead_light=LightStatus.ON,
            overhead_color=RGBWColor(red=200, green=175, blue=150, white=125),
            light_status=LightStatus.ON,
            flame_color=FlameColor.ALL,
            ambient_sensor=LightStatus.OFF,
        )
        decoded = _roundtrip(original, ParameterId.FLAME_EFFECT)
        assert decoded == original

    def test_flame_off(self):
        original = FlameEffectParam(
            flame_effect=FlameEffect.OFF,
            flame_speed=1,
            brightness=0,
            media_theme=MediaTheme.USER_DEFINED,
            media_light=LightStatus.OFF,
            media_color=RGBWColor(red=0, green=0, blue=0, white=0),
            overhead_light=LightStatus.OFF,
            overhead_color=RGBWColor(red=0, green=0, blue=0, white=0),
            light_status=LightStatus.OFF,
            flame_color=FlameColor.ALL,
            ambient_sensor=LightStatus.OFF,
        )
        decoded = _roundtrip(original, ParameterId.FLAME_EFFECT)
        assert decoded == original


class TestHeatParamRoundTrip:
    """Round-trip tests for HeatParam (323)."""

    def test_heat_on_normal(self):
        original = HeatParam(
            heat_status=HeatStatus.ON,
            heat_mode=HeatMode.NORMAL,
            setpoint_temperature=22.0,
            boost_duration=1,
        )
        decoded = _roundtrip(original, ParameterId.HEAT_SETTINGS)
        assert decoded == original

    def test_heat_boost(self):
        original = HeatParam(
            heat_status=HeatStatus.ON,
            heat_mode=HeatMode.BOOST,
            setpoint_temperature=25.5,
            boost_duration=300,
        )
        decoded = _roundtrip(original, ParameterId.HEAT_SETTINGS)
        assert decoded == original


class TestHeatModeParamRoundTrip:
    """Round-trip tests for HeatModeParam (325)."""

    def test_enabled(self):
        original = HeatModeParam(heat_control=HeatControl.ENABLED)
        decoded = _roundtrip(original, ParameterId.HEAT_MODE)
        assert decoded == original

    def test_software_disabled(self):
        original = HeatModeParam(heat_control=HeatControl.SOFTWARE_DISABLED)
        decoded = _roundtrip(original, ParameterId.HEAT_MODE)
        assert decoded == original


class TestTimerParamRoundTrip:
    """Round-trip tests for TimerParam (326)."""

    def test_disabled(self):
        original = TimerParam(timer_status=TimerStatus.DISABLED, duration=0)
        decoded = _roundtrip(original, ParameterId.TIMER)
        assert decoded == original

    def test_enabled_with_duration(self):
        original = TimerParam(timer_status=TimerStatus.ENABLED, duration=120)
        decoded = _roundtrip(original, ParameterId.TIMER)
        assert decoded == original

    def test_large_duration(self):
        """Test a duration that needs both bytes of the 16-bit LE encoding."""
        original = TimerParam(timer_status=TimerStatus.ENABLED, duration=1000)
        decoded = _roundtrip(original, ParameterId.TIMER)
        assert decoded == original


class TestTempUnitParamRoundTrip:
    """Round-trip tests for TempUnitParam (236)."""

    def test_celsius(self):
        original = TempUnitParam(unit=TempUnit.CELSIUS)
        decoded = _roundtrip(original, ParameterId.TEMPERATURE_UNIT)
        assert decoded == original

    def test_fahrenheit(self):
        original = TempUnitParam(unit=TempUnit.FAHRENHEIT)
        decoded = _roundtrip(original, ParameterId.TEMPERATURE_UNIT)
        assert decoded == original


class TestSoundParamRoundTrip:
    """Round-trip tests for SoundParam (369)."""

    def test_sound(self):
        original = SoundParam(volume=128, sound_file=1)
        decoded = _roundtrip(original, ParameterId.SOUND)
        assert decoded == original

    def test_muted(self):
        original = SoundParam(volume=0, sound_file=0)
        decoded = _roundtrip(original, ParameterId.SOUND)
        assert decoded == original


class TestLogEffectParamRoundTrip:
    """Round-trip tests for LogEffectParam (370)."""

    def test_log_effect_on(self):
        original = LogEffectParam(
            log_effect=LogEffect.ON,
            color=RGBWColor(red=255, green=64, blue=128, white=32),
            pattern=1,
        )
        decoded = _roundtrip(original, ParameterId.LOG_EFFECT)
        assert decoded == original

    def test_log_effect_off(self):
        original = LogEffectParam(
            log_effect=LogEffect.OFF,
            color=RGBWColor(red=0, green=0, blue=0, white=0),
            pattern=0,
        )
        decoded = _roundtrip(original, ParameterId.LOG_EFFECT)
        assert decoded == original


class TestSoftwareVersionDecode:
    """Decode-only tests for SoftwareVersionParam (327) — read-only."""

    def test_decode(self):
        raw = _make_header(327, 9) + bytes([1, 2, 3, 4, 5, 6, 7, 8, 9])
        result = decode_parameter(ParameterId.SOFTWARE_VERSION, raw)
        assert isinstance(result, SoftwareVersionParam)
        assert result.ui_major == 1
        assert result.ui_minor == 2
        assert result.ui_test == 3
        assert result.control_major == 4
        assert result.control_minor == 5
        assert result.control_test == 6
        assert result.relay_major == 7
        assert result.relay_minor == 8
        assert result.relay_test == 9


class TestErrorDecode:
    """Decode-only tests for ErrorParam (329) — read-only."""

    def test_decode_all_zeros(self):
        raw = _make_header(329, 4) + bytes([0, 0, 0, 0])
        result = decode_parameter(ParameterId.ERROR, raw)
        assert isinstance(result, ErrorParam)
        assert result.error_byte1 == 0
        assert result.error_byte2 == 0
        assert result.error_byte3 == 0
        assert result.error_byte4 == 0

    def test_decode_with_errors(self):
        raw = _make_header(329, 4) + bytes([0xFF, 0x01, 0x80, 0x42])
        result = decode_parameter(ParameterId.ERROR, raw)
        assert isinstance(result, ErrorParam)
        assert result.error_byte1 == 0xFF
        assert result.error_byte2 == 0x01
        assert result.error_byte3 == 0x80
        assert result.error_byte4 == 0x42


# ---------------------------------------------------------------------------
# FlameEffect RGBW byte order tests
# ---------------------------------------------------------------------------


class TestFlameEffectRGBWByteOrder:
    """Verify the R,B,G,W wire order maps to R,G,B,W in the model."""

    def test_media_color_byte_order(self):
        """Wire bytes: R=10, B=20, G=30, W=40 should decode to model RGBW."""
        raw = _make_header(322, 20) + bytes(
            [
                1,  # flame_effect
                0,  # flame_speed (wire)
                100,  # brightness
                0,  # media_theme
                0,  # media_light
                10,  # wire Red
                20,  # wire Blue
                30,  # wire Green
                40,  # wire White
                0,  # padding
                0,  # overhead_light
                0,  # overhead Red
                0,  # overhead Blue
                0,  # overhead Green
                0,  # overhead White
                0,  # light_status
                0,  # flame_color
                0,  # padding
                0,  # padding
                0,  # ambient_sensor
            ]
        )
        result = decode_parameter(ParameterId.FLAME_EFFECT, raw)
        assert isinstance(result, FlameEffectParam)
        # Wire R,B,G,W → model R,G,B,W
        assert result.media_color.red == 10
        assert result.media_color.blue == 20
        assert result.media_color.green == 30
        assert result.media_color.white == 40

    def test_overhead_color_byte_order(self):
        """Wire overhead bytes: R=50, B=60, G=70, W=80."""
        raw = _make_header(322, 20) + bytes(
            [
                0,  # flame_effect
                0,  # flame_speed
                0,  # brightness
                0,  # media_theme
                0,  # media_light
                0,
                0,
                0,
                0,  # media color RBGW
                0,  # padding
                0,  # overhead_light
                50,  # overhead Red
                60,  # overhead Blue
                70,  # overhead Green
                80,  # overhead White
                0,  # light_status
                0,  # flame_color
                0,
                0,
                0,  # ambient_sensor
            ]
        )
        result = decode_parameter(ParameterId.FLAME_EFFECT, raw)
        assert isinstance(result, FlameEffectParam)
        assert result.overhead_color.red == 50
        assert result.overhead_color.blue == 60
        assert result.overhead_color.green == 70
        assert result.overhead_color.white == 80

    def test_log_effect_color_byte_order(self):
        """Wire log effect bytes: R=100, B=200, G=150, W=50."""
        raw = _make_header(370, 8) + bytes(
            [
                1,  # log_effect
                0,  # theme
                100,  # Red
                200,  # Blue
                150,  # Green
                50,  # White
                1,  # pattern
                0,  # padding
            ]
        )
        result = decode_parameter(ParameterId.LOG_EFFECT, raw)
        assert isinstance(result, LogEffectParam)
        assert result.color.red == 100
        assert result.color.blue == 200
        assert result.color.green == 150
        assert result.color.white == 50


# ---------------------------------------------------------------------------
# FlameSpeed offset tests
# ---------------------------------------------------------------------------


class TestFlameSpeedOffset:
    """Model value N maps to wire value N-1 and decodes back to N."""

    def test_speed_3_wire_2(self):
        """Model flame_speed=3 should produce wire byte 2, decode back to 3."""
        param = FlameEffectParam(
            flame_effect=FlameEffect.ON,
            flame_speed=3,
            brightness=200,
            media_theme=MediaTheme.USER_DEFINED,
            media_light=LightStatus.OFF,
            media_color=RGBWColor(red=0, green=0, blue=0, white=0),
            overhead_light=LightStatus.OFF,
            overhead_color=RGBWColor(red=0, green=0, blue=0, white=0),
            light_status=LightStatus.OFF,
            flame_color=FlameColor.ALL,
            ambient_sensor=LightStatus.OFF,
        )
        b64 = encode_parameter(param)
        raw = base64.b64decode(b64)
        # Wire byte at index 4 (after 3-byte header + 1 flame_effect byte)
        assert raw[4] == 2, "wire flame_speed should be model-1"
        decoded = decode_parameter(ParameterId.FLAME_EFFECT, raw)
        assert isinstance(decoded, FlameEffectParam)
        assert decoded.flame_speed == 3

    def test_speed_1_wire_0(self):
        """Model flame_speed=1 should produce wire byte 0."""
        param = FlameEffectParam(
            flame_effect=FlameEffect.ON,
            flame_speed=1,
            brightness=100,
            media_theme=MediaTheme.USER_DEFINED,
            media_light=LightStatus.OFF,
            media_color=RGBWColor(red=0, green=0, blue=0, white=0),
            overhead_light=LightStatus.OFF,
            overhead_color=RGBWColor(red=0, green=0, blue=0, white=0),
            light_status=LightStatus.OFF,
            flame_color=FlameColor.ALL,
            ambient_sensor=LightStatus.OFF,
        )
        b64 = encode_parameter(param)
        raw = base64.b64decode(b64)
        assert raw[4] == 0
        decoded = decode_parameter(ParameterId.FLAME_EFFECT, raw)
        assert isinstance(decoded, FlameEffectParam)
        assert decoded.flame_speed == 1

    def test_speed_5_wire_4(self):
        """Model flame_speed=5 should produce wire byte 4."""
        param = FlameEffectParam(
            flame_effect=FlameEffect.ON,
            flame_speed=5,
            brightness=255,
            media_theme=MediaTheme.USER_DEFINED,
            media_light=LightStatus.OFF,
            media_color=RGBWColor(red=0, green=0, blue=0, white=0),
            overhead_light=LightStatus.OFF,
            overhead_color=RGBWColor(red=0, green=0, blue=0, white=0),
            light_status=LightStatus.OFF,
            flame_color=FlameColor.ALL,
            ambient_sensor=LightStatus.OFF,
        )
        b64 = encode_parameter(param)
        raw = base64.b64decode(b64)
        assert raw[4] == 4
        decoded = decode_parameter(ParameterId.FLAME_EFFECT, raw)
        assert isinstance(decoded, FlameEffectParam)
        assert decoded.flame_speed == 5


# ---------------------------------------------------------------------------
# Temperature encoding tests
# ---------------------------------------------------------------------------


class TestTemperatureEncoding:
    """Test temperature encode/decode for various values."""

    @pytest.mark.parametrize(
        "temp",
        [0.0, 7.0, 22.5, 37.5],
    )
    def test_temperature_roundtrip(self, temp: float):
        """Temperature should survive an encode/decode cycle."""
        original = ModeParam(mode=FireMode.MANUAL, temperature=temp)
        decoded = _roundtrip(original, ParameterId.MODE)
        assert decoded.temperature == pytest.approx(temp)

    def test_zero_temperature(self):
        original = ModeParam(mode=FireMode.STANDBY, temperature=0.0)
        decoded = _roundtrip(original, ParameterId.MODE)
        assert decoded.temperature == 0.0

    def test_heat_temperature_roundtrip(self):
        """Temperature in HeatParam should also round-trip correctly."""
        original = HeatParam(
            heat_status=HeatStatus.ON,
            heat_mode=HeatMode.NORMAL,
            setpoint_temperature=37.5,
            boost_duration=0,
        )
        decoded = _roundtrip(original, ParameterId.HEAT_SETTINGS)
        assert decoded.setpoint_temperature == pytest.approx(37.5)


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


class TestProtocolErrors:
    """Test error handling in decode/encode."""

    def test_truncated_mode_raises_protocol_error(self):
        """Truncated Mode data (too few bytes) should raise ProtocolError."""
        raw = _make_header(321, 3) + bytes([1])  # Only 4 bytes, need 6
        with pytest.raises(ProtocolError, match="Insufficient data"):
            decode_parameter(ParameterId.MODE, raw)

    def test_truncated_flame_effect_raises_protocol_error(self):
        """Truncated FlameEffect should raise ProtocolError."""
        raw = _make_header(322, 20) + bytes([0] * 5)  # Only 8 bytes, need 23
        with pytest.raises(ProtocolError, match="Insufficient data"):
            decode_parameter(ParameterId.FLAME_EFFECT, raw)

    def test_truncated_heat_settings_raises_protocol_error(self):
        raw = _make_header(323, 7) + bytes([0])  # Only 4 bytes, need 10
        with pytest.raises(ProtocolError, match="Insufficient data"):
            decode_parameter(ParameterId.HEAT_SETTINGS, raw)

    def test_truncated_software_version_raises_protocol_error(self):
        raw = _make_header(327, 9) + bytes([0] * 3)  # Only 6 bytes, need 12
        with pytest.raises(ProtocolError, match="Insufficient data"):
            decode_parameter(ParameterId.SOFTWARE_VERSION, raw)

    def test_truncated_error_param_raises_protocol_error(self):
        raw = _make_header(329, 4) + bytes([0])  # Only 4 bytes, need 7
        with pytest.raises(ProtocolError, match="Insufficient data"):
            decode_parameter(ParameterId.ERROR, raw)

    def test_truncated_timer_raises_protocol_error(self):
        raw = _make_header(326, 3) + bytes([0])  # Only 4 bytes, need 6
        with pytest.raises(ProtocolError, match="Insufficient data"):
            decode_parameter(ParameterId.TIMER, raw)

    def test_truncated_temp_unit_raises_protocol_error(self):
        raw = _make_header(236, 1)  # Only 3 bytes, need 4
        with pytest.raises(ProtocolError, match="Insufficient data"):
            decode_parameter(ParameterId.TEMPERATURE_UNIT, raw)

    def test_truncated_sound_raises_protocol_error(self):
        raw = _make_header(369, 2) + bytes([0])  # Only 4 bytes, need 5
        with pytest.raises(ProtocolError, match="Insufficient data"):
            decode_parameter(ParameterId.SOUND, raw)

    def test_truncated_log_effect_raises_protocol_error(self):
        raw = _make_header(370, 8) + bytes([0] * 3)  # Only 6 bytes, need 11
        with pytest.raises(ProtocolError, match="Insufficient data"):
            decode_parameter(ParameterId.LOG_EFFECT, raw)

    def test_unknown_parameter_id_raises_protocol_error(self):
        """An unrecognized parameter ID should raise ProtocolError."""
        raw = _make_header(999, 1) + bytes([0])
        with pytest.raises(ProtocolError, match="Unknown parameter ID"):
            decode_parameter(999, raw)

    def test_encode_software_version_raises_protocol_error(self):
        """SoftwareVersionParam is read-only; encoding should raise."""
        param = SoftwareVersionParam(
            ui_major=1,
            ui_minor=0,
            ui_test=0,
            control_major=1,
            control_minor=0,
            control_test=0,
            relay_major=1,
            relay_minor=0,
            relay_test=0,
        )
        with pytest.raises(ProtocolError, match="read-only"):
            encode_parameter(param)

    def test_encode_error_param_raises_protocol_error(self):
        """ErrorParam is read-only; encoding should raise."""
        param = ErrorParam(
            error_byte1=0,
            error_byte2=0,
            error_byte3=0,
            error_byte4=0,
        )
        with pytest.raises(ProtocolError, match="read-only"):
            encode_parameter(param)
