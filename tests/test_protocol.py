"""Tests for the wire protocol encoding and decoding."""

from __future__ import annotations

import base64
import logging
import struct

import pytest

from flameconnect.const import ParameterId
from flameconnect.exceptions import ProtocolError
from flameconnect.models import (
    Brightness,
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
    PulsatingEffect,
    RGBWColor,
    SoftwareVersionParam,
    SoundParam,
    TempUnit,
    TempUnitParam,
    TimerParam,
    TimerStatus,
)
from flameconnect.protocol import _make_header as _protocol_make_header
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
        original = ModeParam(mode=FireMode.MANUAL, target_temperature=22.5)
        decoded = _roundtrip(original, ParameterId.MODE)
        assert decoded == original

    def test_standby_mode(self):
        original = ModeParam(mode=FireMode.STANDBY, target_temperature=0.0)
        decoded = _roundtrip(original, ParameterId.MODE)
        assert decoded == original


class TestFlameEffectParamRoundTrip:
    """Round-trip tests for FlameEffectParam (322)."""

    def test_full_flame_effect(self):
        original = FlameEffectParam(
            flame_effect=FlameEffect.ON,
            flame_speed=3,
            brightness=Brightness.LOW,
            pulsating_effect=PulsatingEffect.OFF,
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
            brightness=Brightness.HIGH,
            pulsating_effect=PulsatingEffect.OFF,
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
            boost_duration=15,
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
                1,  # brightness (HIGH)
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
                0,  # brightness (LOW)
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
            brightness=Brightness.LOW,
            pulsating_effect=PulsatingEffect.OFF,
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
            brightness=Brightness.LOW,
            pulsating_effect=PulsatingEffect.OFF,
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
            brightness=Brightness.LOW,
            pulsating_effect=PulsatingEffect.OFF,
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
        original = ModeParam(mode=FireMode.MANUAL, target_temperature=temp)
        decoded = _roundtrip(original, ParameterId.MODE)
        assert decoded.target_temperature == pytest.approx(temp)

    def test_zero_temperature(self):
        original = ModeParam(mode=FireMode.STANDBY, target_temperature=0.0)
        decoded = _roundtrip(original, ParameterId.MODE)
        assert decoded.target_temperature == 0.0

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

    def test_encode_unknown_param_type_raises_protocol_error(self):
        """An object that is not a known parameter type should raise."""
        # Pass an arbitrary object that doesn't match any isinstance check
        not_a_param = "this is not a parameter"
        with pytest.raises(ProtocolError, match="Unknown parameter type"):
            encode_parameter(not_a_param)


# ---------------------------------------------------------------------------
# Exact error message text in _check_length (kills name string mutants)
# ---------------------------------------------------------------------------


class TestCheckLengthErrorMessages:
    """Verify exact parameter name in ProtocolError messages."""

    def test_mode_error_says_mode(self):
        raw = _make_header(321, 3) + bytes([1])
        with pytest.raises(ProtocolError, match=r"for Mode:"):
            decode_parameter(ParameterId.MODE, raw)

    def test_flame_effect_error_says_flame_effect(self):
        raw = _make_header(322, 20) + bytes([0] * 5)
        with pytest.raises(ProtocolError, match=r"for FlameEffect:"):
            decode_parameter(ParameterId.FLAME_EFFECT, raw)

    def test_heat_settings_error_says_heat_settings(self):
        raw = _make_header(323, 7) + bytes([0])
        with pytest.raises(ProtocolError, match=r"for HeatSettings:"):
            decode_parameter(ParameterId.HEAT_SETTINGS, raw)

    def test_heat_mode_error_says_heat_mode(self):
        raw = _make_header(325, 1)
        with pytest.raises(ProtocolError, match=r"for HeatMode:"):
            decode_parameter(ParameterId.HEAT_MODE, raw)

    def test_timer_error_says_timer(self):
        raw = _make_header(326, 3) + bytes([0])
        with pytest.raises(ProtocolError, match=r"for Timer:"):
            decode_parameter(ParameterId.TIMER, raw)

    def test_software_version_error(self):
        raw = _make_header(327, 9) + bytes([0] * 3)
        with pytest.raises(
            ProtocolError,
            match=r"for SoftwareVersion:",
        ):
            decode_parameter(ParameterId.SOFTWARE_VERSION, raw)

    def test_error_param_error_says_error(self):
        raw = _make_header(329, 4) + bytes([0])
        with pytest.raises(ProtocolError, match=r"for Error:"):
            decode_parameter(ParameterId.ERROR, raw)

    def test_temp_unit_error_says_temp_unit(self):
        raw = _make_header(236, 1)
        with pytest.raises(ProtocolError, match=r"for TempUnit:"):
            decode_parameter(ParameterId.TEMPERATURE_UNIT, raw)

    def test_sound_error_says_sound(self):
        raw = _make_header(369, 2) + bytes([0])
        with pytest.raises(ProtocolError, match=r"for Sound:"):
            decode_parameter(ParameterId.SOUND, raw)

    def test_log_effect_error_says_log_effect(self):
        raw = _make_header(370, 8) + bytes([0] * 3)
        with pytest.raises(ProtocolError, match=r"for LogEffect:"):
            decode_parameter(ParameterId.LOG_EFFECT, raw)

    def test_error_includes_expected_and_got(self):
        """Verify error has expected/got byte counts."""
        raw = _make_header(321, 3) + bytes([1])
        with pytest.raises(
            ProtocolError,
            match=r"expected 6 bytes, got 4",
        ):
            decode_parameter(ParameterId.MODE, raw)


# ---------------------------------------------------------------------------
# Exact error message text in encode_parameter (kills error msg mutants)
# ---------------------------------------------------------------------------


class TestEncodeErrorMessages:
    """Verify exact error message text for read-only params."""

    def test_software_version_error_text(self):
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
        with pytest.raises(ProtocolError) as exc_info:
            encode_parameter(param)
        msg = str(exc_info.value)
        assert msg.startswith("SoftwareVersionParam")
        assert "read-only" in msg

    def test_error_param_error_text(self):
        param = ErrorParam(
            error_byte1=0,
            error_byte2=0,
            error_byte3=0,
            error_byte4=0,
        )
        with pytest.raises(ProtocolError) as exc_info:
            encode_parameter(param)
        msg = str(exc_info.value)
        assert msg.startswith("ErrorParam")
        assert "read-only" in msg

    def test_unknown_param_error_text(self):
        with pytest.raises(
            ProtocolError,
            match="Unknown parameter type: str",
        ):
            encode_parameter("not a param")


# ---------------------------------------------------------------------------
# Exact encoded byte verification (kills payload size + padding mutants)
# ---------------------------------------------------------------------------


class TestExactEncodedBytes:
    """Verify exact byte content of encoded parameters."""

    def test_temp_unit_encoded_bytes(self):
        param = TempUnitParam(unit=TempUnit.CELSIUS)
        b64 = encode_parameter(param)
        raw = base64.b64decode(b64)
        assert len(raw) == 4
        # Header: param_id=236 LE (0xEC, 0x00), payload_size=1
        assert raw[0:2] == struct.pack("<H", 236)
        assert raw[2] == 1  # payload size byte
        assert raw[3] == 1  # CELSIUS = 1

    def test_mode_encoded_bytes(self):
        param = ModeParam(mode=FireMode.MANUAL, target_temperature=22.5)
        b64 = encode_parameter(param)
        raw = base64.b64decode(b64)
        assert len(raw) == 6
        assert raw[0:2] == struct.pack("<H", 321)
        assert raw[2] == 3  # payload size
        assert raw[3] == 1  # MANUAL = 1
        assert raw[4] == 22  # integer part of temp
        assert raw[5] == 5  # decimal tenth (0.5 * 10)

    def test_heat_mode_encoded_bytes(self):
        param = HeatModeParam(heat_control=HeatControl.ENABLED)
        b64 = encode_parameter(param)
        raw = base64.b64decode(b64)
        assert len(raw) == 4
        assert raw[0:2] == struct.pack("<H", 325)
        assert raw[2] == 1  # payload size
        assert raw[3] == 2  # ENABLED = 2

    def test_timer_encoded_bytes(self):
        param = TimerParam(timer_status=TimerStatus.ENABLED, duration=300)
        b64 = encode_parameter(param)
        raw = base64.b64decode(b64)
        assert len(raw) == 6
        assert raw[0:2] == struct.pack("<H", 326)
        assert raw[2] == 3  # payload size
        assert raw[3] == 1  # ENABLED = 1
        # 300 = 0x012C -> lo=0x2C, hi=0x01
        assert raw[4] == 0x2C
        assert raw[5] == 0x01

    def test_sound_encoded_bytes(self):
        param = SoundParam(volume=128, sound_file=3)
        b64 = encode_parameter(param)
        raw = base64.b64decode(b64)
        assert len(raw) == 5
        assert raw[0:2] == struct.pack("<H", 369)
        assert raw[2] == 2  # payload size
        assert raw[3] == 128
        assert raw[4] == 3

    def test_log_effect_encoded_bytes(self):
        param = LogEffectParam(
            log_effect=LogEffect.ON,
            color=RGBWColor(red=10, green=20, blue=30, white=40),
            pattern=5,
        )
        b64 = encode_parameter(param)
        raw = base64.b64decode(b64)
        assert len(raw) == 11
        assert raw[0:2] == struct.pack("<H", 370)
        assert raw[2] == 8  # payload size
        assert raw[3] == 1  # ON
        assert raw[4] == 0  # theme placeholder
        # Wire: R, B, G, W
        assert raw[5] == 10  # red
        assert raw[6] == 30  # blue
        assert raw[7] == 20  # green
        assert raw[8] == 40  # white
        assert raw[9] == 5  # pattern
        assert raw[10] == 0  # padding

    def test_heat_settings_encoded_bytes(self):
        param = HeatParam(
            heat_status=HeatStatus.ON,
            heat_mode=HeatMode.BOOST,
            setpoint_temperature=25.5,
            boost_duration=10,
        )
        b64 = encode_parameter(param)
        raw = base64.b64decode(b64)
        # 3 header + 5 payload
        assert len(raw) == 8
        assert raw[0:2] == struct.pack("<H", 323)
        assert raw[2] == 5  # payload size
        assert raw[3] == 1  # ON
        assert raw[4] == 1  # BOOST
        assert raw[5] == 25  # integer temp
        assert raw[6] == 5  # decimal tenth
        # boost: model 10 -> wire 9
        assert raw[7] == 9

    def test_flame_effect_encoded_bytes(self):
        param = FlameEffectParam(
            flame_effect=FlameEffect.ON,
            flame_speed=3,
            brightness=Brightness.LOW,
            pulsating_effect=PulsatingEffect.ON,
            media_theme=MediaTheme.BLUE,
            media_light=LightStatus.ON,
            media_color=RGBWColor(red=10, green=20, blue=30, white=40),
            overhead_light=LightStatus.ON,
            overhead_color=RGBWColor(red=50, green=60, blue=70, white=80),
            light_status=LightStatus.ON,
            flame_color=FlameColor.YELLOW_RED,
            ambient_sensor=LightStatus.ON,
        )
        b64 = encode_parameter(param)
        raw = base64.b64decode(b64)
        assert len(raw) == 23
        assert raw[0:2] == struct.pack("<H", 322)
        assert raw[2] == 20  # payload size
        assert raw[3] == 1  # ON
        assert raw[4] == 2  # speed 3 -> wire 2
        # brightness=1(LOW) | pulsating=1<<1 = 0b11 = 3
        assert raw[5] == 3
        assert raw[6] == 2  # BLUE theme
        assert raw[7] == 1  # media_light ON
        # media color wire: R, B, G, W
        assert raw[8] == 10  # red
        assert raw[9] == 30  # blue
        assert raw[10] == 20  # green
        assert raw[11] == 40  # white
        assert raw[12] == 0  # padding
        assert raw[13] == 1  # overhead_light ON
        # overhead wire: R, B, G, W
        assert raw[14] == 50
        assert raw[15] == 70  # blue
        assert raw[16] == 60  # green
        assert raw[17] == 80
        assert raw[18] == 1  # light_status ON
        assert raw[19] == 1  # YELLOW_RED
        assert raw[20] == 0  # padding
        assert raw[21] == 0  # padding
        assert raw[22] == 1  # ambient_sensor ON


# ---------------------------------------------------------------------------
# _make_header format string test (signed vs unsigned)
# ---------------------------------------------------------------------------


class TestMakeHeaderFormat:
    """Verify _make_header uses unsigned format."""

    def test_large_param_id_unsigned(self):
        """Parameter IDs > 127 must use unsigned packing."""
        param = TempUnitParam(unit=TempUnit.FAHRENHEIT)
        b64 = encode_parameter(param)
        raw = base64.b64decode(b64)
        # ParameterId.TEMPERATURE_UNIT = 236
        # Unsigned LE: 0xEC, 0x00
        assert raw[0] == 0xEC
        assert raw[1] == 0x00

    def test_payload_size_above_signed_byte_range(self):
        """payload_size >= 128 requires unsigned byte format <HB, not signed <hb.

        struct.pack('<hb', ..., 128) raises struct.error because 128 is out of
        range for a signed byte.  Kills _make_header__mutmut_8 which changes
        the format string from '<HB' to '<hb'.
        """
        header = _protocol_make_header(100, 128)
        assert len(header) == 3
        assert header[2] == 128


# ---------------------------------------------------------------------------
# Temperature encoding multiplier (kills *10 -> *11)
# ---------------------------------------------------------------------------


class TestTemperatureEncodingExact:
    """Verify exact byte values for temperature encoding."""

    def test_temp_22_5_encodes_to_22_and_5(self):
        param = ModeParam(mode=FireMode.MANUAL, target_temperature=22.5)
        b64 = encode_parameter(param)
        raw = base64.b64decode(b64)
        assert raw[4] == 22  # integer
        assert raw[5] == 5  # 0.5 * 10 = 5

    def test_temp_18_5_encodes_to_18_and_5(self):
        param = ModeParam(mode=FireMode.MANUAL, target_temperature=18.5)
        b64 = encode_parameter(param)
        raw = base64.b64decode(b64)
        assert raw[4] == 18
        assert raw[5] == 5  # 0.5 * 10 = 5, not 0.5 * 11

    def test_temp_decode_exact(self):
        """Decode raw bytes and check exact temperature."""
        raw = _make_header(321, 3) + bytes([1, 22, 5])
        result = decode_parameter(ParameterId.MODE, raw)
        assert result.target_temperature == 22.5

    def test_temp_22_91_encodes_decimal_as_9(self):
        """Decimal tenth uses multiplier 10, not 11.

        int(0.91 * 10) == 9, but int(0.91 * 11) == 10.
        Kills _encode_temperature__mutmut_7 which changes * 10 to * 11.
        """
        param = ModeParam(mode=FireMode.MANUAL, target_temperature=22.91)
        b64 = encode_parameter(param)
        raw = base64.b64decode(b64)
        assert raw[4] == 22
        assert raw[5] == 9  # int(0.91 * 10) = 9, not int(0.91 * 11) = 10


# ---------------------------------------------------------------------------
# Pulsating/brightness bitfield mutations (shift direction/amount)
# ---------------------------------------------------------------------------


class TestBrightnessPulsatingBitfield:
    """Test brightness and pulsating bitfield encode/decode."""

    def test_pulsating_on_decodes_from_bit1(self):
        """brightness_byte=0b10 -> brightness=LOW(0), pulsating=ON."""
        raw = _make_header(322, 20) + bytes(
            [
                1,
                0,
                0b10,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
            ]
        )
        result = decode_parameter(ParameterId.FLAME_EFFECT, raw)
        assert result.brightness == Brightness.HIGH
        assert result.pulsating_effect == PulsatingEffect.ON

    def test_both_on_decodes_from_0b11(self):
        """brightness_byte=0b11 -> brightness=LOW(1), pulsating=ON."""
        raw = _make_header(322, 20) + bytes(
            [
                1,
                0,
                0b11,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
            ]
        )
        result = decode_parameter(ParameterId.FLAME_EFFECT, raw)
        assert result.brightness == Brightness.LOW
        assert result.pulsating_effect == PulsatingEffect.ON

    def test_pulsating_on_encodes_to_bit1(self):
        """Pulsating ON should set bit 1 in encoded byte."""
        param = FlameEffectParam(
            flame_effect=FlameEffect.ON,
            flame_speed=1,
            brightness=Brightness.HIGH,
            pulsating_effect=PulsatingEffect.ON,
            media_theme=MediaTheme.USER_DEFINED,
            media_light=LightStatus.OFF,
            media_color=RGBWColor(0, 0, 0, 0),
            overhead_light=LightStatus.OFF,
            overhead_color=RGBWColor(0, 0, 0, 0),
            light_status=LightStatus.OFF,
            flame_color=FlameColor.ALL,
            ambient_sensor=LightStatus.OFF,
        )
        b64 = encode_parameter(param)
        raw = base64.b64decode(b64)
        assert raw[5] == 0b10  # HIGH(0) | ON(1)<<1 = 2


# ---------------------------------------------------------------------------
# Flame color index test (raw[19] vs raw[20])
# ---------------------------------------------------------------------------


class TestFlameColorIndex:
    """Verify flame_color reads from raw[19], not raw[20]."""

    def test_flame_color_from_index_19(self):
        raw = _make_header(322, 20) + bytes(
            [
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                3,  # raw[19] = BLUE(3)
                99,  # raw[20] = padding (different)
                99,  # raw[21] = padding
                0,  # raw[22]
            ]
        )
        result = decode_parameter(ParameterId.FLAME_EFFECT, raw)
        assert result.flame_color == FlameColor.BLUE


# ---------------------------------------------------------------------------
# Heat settings boost duration boundary conditions
# ---------------------------------------------------------------------------


class TestHeatSettingsBoostBoundary:
    """Test boost duration decode with varying payload lengths."""

    def test_exactly_7_bytes_boost_defaults_zero(self):
        """With exactly 7 bytes, boost_lo defaults to 0."""
        raw = _make_header(323, 4) + bytes([1, 0, 22, 0])  # 7 bytes total
        result = decode_parameter(ParameterId.HEAT_SETTINGS, raw)
        # boost_lo=0, boost_hi=0 => duration=(0|0)+1=1
        assert result.boost_duration == 1

    def test_exactly_8_bytes_boost_lo_read(self):
        """With 8 bytes, boost_lo is read from raw[7]."""
        raw = _make_header(323, 5) + bytes([1, 0, 22, 0, 5])  # 8 bytes
        result = decode_parameter(ParameterId.HEAT_SETTINGS, raw)
        # boost_lo=5, boost_hi=0 => (5|0)+1=6
        assert result.boost_duration == 6

    def test_exactly_9_bytes_boost_hi_read(self):
        """With 9 bytes, boost_hi is read from raw[8]."""
        raw = _make_header(323, 6) + bytes([1, 0, 22, 0, 5, 2])  # 9 bytes
        result = decode_parameter(ParameterId.HEAT_SETTINGS, raw)
        # boost_lo=5, boost_hi=2 => (5|(2<<8))+1 = (5|512)+1=518
        assert result.boost_duration == 518

    def test_boost_hi_shift_amount(self):
        """Verify boost_hi is shifted left by 8 (not 9)."""
        raw = _make_header(323, 6) + bytes([1, 0, 22, 0, 0, 1])  # 9 bytes
        result = decode_parameter(ParameterId.HEAT_SETTINGS, raw)
        # boost_lo=0, boost_hi=1 => (0|(1<<8))+1 = 257
        assert result.boost_duration == 257

    def test_boost_duration_7_bytes_fallback(self):
        """With 7 bytes, len(raw) > 7 is False so boost_lo=0."""
        raw = bytes(7)
        raw = _make_header(323, 4) + bytes([0, 0, 20, 0])
        assert len(raw) == 7
        result = decode_parameter(ParameterId.HEAT_SETTINGS, raw)
        assert result.boost_duration == 1

    def test_check_length_mutant_7_vs_8(self):
        """_check_length is called with 7 (not 8)."""
        # Exactly 7 bytes should NOT raise
        raw = _make_header(323, 4) + bytes([0, 0, 20, 0])
        result = decode_parameter(ParameterId.HEAT_SETTINGS, raw)
        assert isinstance(result, HeatParam)


# ---------------------------------------------------------------------------
# Logging output tests (kills _LOGGER.debug mutations)
# ---------------------------------------------------------------------------


def _assert_no_xx(text: str) -> None:
    """Assert no 'XX' mutation markers appear in log text."""
    assert "XX" not in text, f"Found 'XX' in: {text}"


def _assert_no_none(text: str) -> None:
    """Assert 'None' does not appear in log text."""
    assert "None" not in text, f"Found 'None' in: {text}"


class TestDecoderLogging:
    """Verify debug logging in decode functions."""

    def test_decode_temp_unit_logs(self, caplog):
        raw = _make_header(236, 1) + bytes([1])
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            decode_parameter(ParameterId.TEMPERATURE_UNIT, raw)
        _assert_no_xx(caplog.text)
        _assert_no_none(caplog.text)
        assert "Decoded TempUnit" in caplog.text
        assert "%s" not in caplog.text

    def test_decode_mode_logs(self, caplog):
        raw = _make_header(321, 3) + bytes([1, 22, 5])
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            decode_parameter(ParameterId.MODE, raw)
        _assert_no_xx(caplog.text)
        _assert_no_none(caplog.text)
        assert "Decoded Mode" in caplog.text
        assert "22.5" in caplog.text

    def test_decode_flame_effect_logs(self, caplog):
        raw = _make_header(322, 20) + bytes(
            [1, 2, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        )
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            decode_parameter(ParameterId.FLAME_EFFECT, raw)
        _assert_no_xx(caplog.text)
        _assert_no_none(caplog.text)
        assert "Decoded FlameEffect" in caplog.text

    def test_decode_heat_settings_logs(self, caplog):
        raw = _make_header(323, 7) + bytes([1, 0, 22, 0, 0, 0, 0])
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            decode_parameter(ParameterId.HEAT_SETTINGS, raw)
        _assert_no_xx(caplog.text)
        _assert_no_none(caplog.text)
        assert "Decoded HeatSettings" in caplog.text

    def test_decode_heat_mode_logs(self, caplog):
        raw = _make_header(325, 1) + bytes([2])
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            decode_parameter(ParameterId.HEAT_MODE, raw)
        _assert_no_xx(caplog.text)
        _assert_no_none(caplog.text)
        assert "Decoded HeatMode" in caplog.text
        assert "%s" not in caplog.text

    def test_decode_timer_logs(self, caplog):
        raw = _make_header(326, 3) + bytes([1, 120, 0])
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            decode_parameter(ParameterId.TIMER, raw)
        _assert_no_xx(caplog.text)
        _assert_no_none(caplog.text)
        assert "Decoded Timer" in caplog.text

    def test_decode_software_version_logs(self, caplog):
        raw = _make_header(327, 9) + bytes([1, 2, 3, 4, 5, 6, 7, 8, 9])
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            decode_parameter(ParameterId.SOFTWARE_VERSION, raw)
        _assert_no_xx(caplog.text)
        _assert_no_none(caplog.text)
        assert "Decoded SoftwareVersion" in caplog.text

    def test_decode_error_logs(self, caplog):
        raw = _make_header(329, 4) + bytes([0xFF, 1, 0x80, 0x42])
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            decode_parameter(ParameterId.ERROR, raw)
        _assert_no_xx(caplog.text)
        _assert_no_none(caplog.text)
        assert "Decoded Error" in caplog.text

    def test_decode_sound_logs(self, caplog):
        raw = _make_header(369, 2) + bytes([128, 3])
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            decode_parameter(ParameterId.SOUND, raw)
        _assert_no_xx(caplog.text)
        _assert_no_none(caplog.text)
        assert "Decoded Sound" in caplog.text

    def test_decode_log_effect_logs(self, caplog):
        raw = _make_header(370, 8) + bytes([1, 0, 100, 200, 150, 50, 1, 0])
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            decode_parameter(ParameterId.LOG_EFFECT, raw)
        _assert_no_xx(caplog.text)
        _assert_no_none(caplog.text)
        assert "Decoded LogEffect" in caplog.text

    def test_decode_parameter_entry_logs(self, caplog):
        raw = _make_header(236, 1) + bytes([1])
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            decode_parameter(ParameterId.TEMPERATURE_UNIT, raw)
        _assert_no_xx(caplog.text)
        _assert_no_none(caplog.text)
        assert "Decoding parameter" in caplog.text


class TestEncoderLogging:
    """Verify debug logging in encode functions."""

    def test_encode_temp_unit_logs(self, caplog):
        param = TempUnitParam(unit=TempUnit.CELSIUS)
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            encode_parameter(param)
        _assert_no_xx(caplog.text)
        _assert_no_none(caplog.text)
        assert "Encoding TempUnit" in caplog.text

    def test_encode_mode_logs(self, caplog):
        param = ModeParam(mode=FireMode.MANUAL, target_temperature=22.5)
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            encode_parameter(param)
        _assert_no_xx(caplog.text)
        _assert_no_none(caplog.text)
        assert "Encoding Mode" in caplog.text

    def test_encode_flame_effect_logs(self, caplog):
        param = FlameEffectParam(
            flame_effect=FlameEffect.ON,
            flame_speed=3,
            brightness=Brightness.LOW,
            pulsating_effect=PulsatingEffect.OFF,
            media_theme=MediaTheme.USER_DEFINED,
            media_light=LightStatus.OFF,
            media_color=RGBWColor(0, 0, 0, 0),
            overhead_light=LightStatus.OFF,
            overhead_color=RGBWColor(0, 0, 0, 0),
            light_status=LightStatus.OFF,
            flame_color=FlameColor.ALL,
            ambient_sensor=LightStatus.OFF,
        )
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            encode_parameter(param)
        _assert_no_xx(caplog.text)
        _assert_no_none(caplog.text)
        assert "Encoding FlameEffect" in caplog.text

    def test_encode_heat_settings_logs(self, caplog):
        param = HeatParam(
            heat_status=HeatStatus.ON,
            heat_mode=HeatMode.NORMAL,
            setpoint_temperature=22.0,
            boost_duration=1,
        )
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            encode_parameter(param)
        _assert_no_xx(caplog.text)
        _assert_no_none(caplog.text)
        assert "Encoding HeatSettings" in caplog.text

    def test_encode_heat_mode_logs(self, caplog):
        param = HeatModeParam(heat_control=HeatControl.ENABLED)
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            encode_parameter(param)
        _assert_no_xx(caplog.text)
        _assert_no_none(caplog.text)
        assert "Encoding HeatMode" in caplog.text
        assert "%s" not in caplog.text

    def test_encode_timer_logs(self, caplog):
        param = TimerParam(timer_status=TimerStatus.ENABLED, duration=120)
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            encode_parameter(param)
        _assert_no_xx(caplog.text)
        _assert_no_none(caplog.text)
        assert "Encoding Timer" in caplog.text

    def test_encode_sound_logs(self, caplog):
        param = SoundParam(volume=128, sound_file=1)
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            encode_parameter(param)
        _assert_no_xx(caplog.text)
        _assert_no_none(caplog.text)
        assert "Encoding Sound" in caplog.text

    def test_encode_log_effect_logs(self, caplog):
        param = LogEffectParam(
            log_effect=LogEffect.ON,
            color=RGBWColor(255, 64, 128, 32),
            pattern=1,
        )
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            encode_parameter(param)
        _assert_no_xx(caplog.text)
        _assert_no_none(caplog.text)
        assert "Encoding LogEffect" in caplog.text


# ---------------------------------------------------------------------------
# Detailed logging argument tests (kills argument mutation)
# ---------------------------------------------------------------------------


class TestDecoderLoggingArgs:
    """Verify log messages include the actual field values."""

    def test_temp_unit_log_value(self, caplog):
        raw = _make_header(236, 1) + bytes([0])
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            decode_parameter(ParameterId.TEMPERATURE_UNIT, raw)
        _assert_no_xx(caplog.text)
        _assert_no_none(caplog.text)
        assert "TempUnit" in caplog.text
        assert "0" in caplog.text

    def test_mode_log_values(self, caplog):
        raw = _make_header(321, 3) + bytes([0, 25, 3])
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            decode_parameter(ParameterId.MODE, raw)
        _assert_no_xx(caplog.text)
        _assert_no_none(caplog.text)
        assert "mode" in caplog.text.lower()
        assert "25.3" in caplog.text

    def test_flame_effect_log_values(self, caplog):
        """Verify log has speed, brightness, pulsating."""
        raw = _make_header(322, 20) + bytes(
            [1, 4, 0b11, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        )
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            decode_parameter(ParameterId.FLAME_EFFECT, raw)
        _assert_no_xx(caplog.text)
        _assert_no_none(caplog.text)
        assert "5" in caplog.text
        assert "LOW" in caplog.text
        assert "ON" in caplog.text

    def test_heat_settings_log_values(self, caplog):
        raw = _make_header(323, 7) + bytes([1, 1, 25, 5, 14, 0, 0])
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            decode_parameter(ParameterId.HEAT_SETTINGS, raw)
        _assert_no_xx(caplog.text)
        _assert_no_none(caplog.text)
        assert "25.5" in caplog.text
        assert "15" in caplog.text

    def test_heat_mode_log_value(self, caplog):
        raw = _make_header(325, 1) + bytes([2])
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            decode_parameter(ParameterId.HEAT_MODE, raw)
        _assert_no_xx(caplog.text)
        _assert_no_none(caplog.text)
        assert "HeatMode" in caplog.text
        assert "2" in caplog.text

    def test_timer_log_values(self, caplog):
        raw = _make_header(326, 3) + bytes([1, 0x78, 0])
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            decode_parameter(ParameterId.TIMER, raw)
        _assert_no_xx(caplog.text)
        _assert_no_none(caplog.text)
        assert "120" in caplog.text
        assert "1" in caplog.text

    def test_software_version_log_values(self, caplog):
        raw = _make_header(327, 9) + bytes([2, 3, 4, 5, 6, 7, 8, 9, 10])
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            decode_parameter(ParameterId.SOFTWARE_VERSION, raw)
        _assert_no_xx(caplog.text)
        _assert_no_none(caplog.text)
        for n in [2, 3, 4, 5, 6, 7, 8, 9, 10]:
            assert str(n) in caplog.text

    def test_error_log_values(self, caplog):
        raw = _make_header(329, 4) + bytes([0xAA, 0xBB, 0xCC, 0xDD])
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            decode_parameter(ParameterId.ERROR, raw)
        _assert_no_xx(caplog.text)
        _assert_no_none(caplog.text)
        text = caplog.text.upper()
        assert "AA" in text
        assert "BB" in text
        assert "CC" in text
        assert "DD" in text

    def test_sound_log_values(self, caplog):
        raw = _make_header(369, 2) + bytes([200, 7])
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            decode_parameter(ParameterId.SOUND, raw)
        _assert_no_xx(caplog.text)
        _assert_no_none(caplog.text)
        assert "200" in caplog.text
        assert "7" in caplog.text

    def test_log_effect_log_values(self, caplog):
        raw = _make_header(370, 8) + bytes([1, 0, 10, 20, 30, 40, 3, 0])
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            decode_parameter(ParameterId.LOG_EFFECT, raw)
        _assert_no_xx(caplog.text)
        _assert_no_none(caplog.text)
        assert "3" in caplog.text

    def test_decode_parameter_logs_id_and_len(self, caplog):
        raw = _make_header(236, 1) + bytes([1])
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            decode_parameter(ParameterId.TEMPERATURE_UNIT, raw)
        _assert_no_xx(caplog.text)
        _assert_no_none(caplog.text)
        assert "236" in caplog.text
        assert "4" in caplog.text


class TestEncoderLoggingArgs:
    """Verify encoder log messages include actual values."""

    def test_encode_temp_unit_log_value(self, caplog):
        param = TempUnitParam(unit=TempUnit.FAHRENHEIT)
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            encode_parameter(param)
        _assert_no_xx(caplog.text)
        _assert_no_none(caplog.text)
        assert "TempUnit" in caplog.text
        assert "0" in caplog.text

    def test_encode_mode_log_values(self, caplog):
        param = ModeParam(mode=FireMode.MANUAL, target_temperature=22.5)
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            encode_parameter(param)
        _assert_no_xx(caplog.text)
        _assert_no_none(caplog.text)
        assert "Mode" in caplog.text
        assert "22.5" in caplog.text

    def test_encode_flame_effect_log_values(self, caplog):
        param = FlameEffectParam(
            flame_effect=FlameEffect.ON,
            flame_speed=5,
            brightness=Brightness.LOW,
            pulsating_effect=PulsatingEffect.OFF,
            media_theme=MediaTheme.USER_DEFINED,
            media_light=LightStatus.OFF,
            media_color=RGBWColor(0, 0, 0, 0),
            overhead_light=LightStatus.OFF,
            overhead_color=RGBWColor(0, 0, 0, 0),
            light_status=LightStatus.OFF,
            flame_color=FlameColor.ALL,
            ambient_sensor=LightStatus.OFF,
        )
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            encode_parameter(param)
        _assert_no_xx(caplog.text)
        _assert_no_none(caplog.text)
        assert "5" in caplog.text

    def test_encode_heat_settings_log_values(self, caplog):
        param = HeatParam(
            heat_status=HeatStatus.ON,
            heat_mode=HeatMode.BOOST,
            setpoint_temperature=25.5,
            boost_duration=15,
        )
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            encode_parameter(param)
        _assert_no_xx(caplog.text)
        _assert_no_none(caplog.text)
        assert "25.5" in caplog.text
        assert "15" in caplog.text

    def test_encode_heat_mode_log_value(self, caplog):
        param = HeatModeParam(heat_control=HeatControl.SOFTWARE_DISABLED)
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            encode_parameter(param)
        _assert_no_xx(caplog.text)
        _assert_no_none(caplog.text)
        assert "HeatMode" in caplog.text
        assert "0" in caplog.text

    def test_encode_timer_log_values(self, caplog):
        param = TimerParam(timer_status=TimerStatus.ENABLED, duration=300)
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            encode_parameter(param)
        _assert_no_xx(caplog.text)
        _assert_no_none(caplog.text)
        assert "300" in caplog.text
        assert "1" in caplog.text

    def test_encode_sound_log_values(self, caplog):
        param = SoundParam(volume=200, sound_file=7)
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            encode_parameter(param)
        _assert_no_xx(caplog.text)
        _assert_no_none(caplog.text)
        assert "200" in caplog.text
        assert "7" in caplog.text

    def test_encode_log_effect_log_values(self, caplog):
        param = LogEffectParam(
            log_effect=LogEffect.ON,
            color=RGBWColor(10, 20, 30, 40),
            pattern=5,
        )
        with caplog.at_level(logging.DEBUG, "flameconnect"):
            encode_parameter(param)
        _assert_no_xx(caplog.text)
        _assert_no_none(caplog.text)
        assert "5" in caplog.text


# ---------------------------------------------------------------------------
# Detailed decode field verification (kills index mutations)
# ---------------------------------------------------------------------------


class TestDecodeFieldValues:
    """Verify individual decoded field values from raw bytes."""

    def test_mode_fields(self):
        raw = _make_header(321, 3) + bytes([1, 30, 7])
        result = decode_parameter(ParameterId.MODE, raw)
        assert result.mode == FireMode.MANUAL
        assert result.target_temperature == 30.7

    def test_heat_settings_fields(self):
        raw = _make_header(323, 7) + bytes([1, 2, 20, 5, 10, 1, 0])
        result = decode_parameter(ParameterId.HEAT_SETTINGS, raw)
        assert result.heat_status == HeatStatus.ON
        assert result.heat_mode == HeatMode.ECO
        assert result.setpoint_temperature == 20.5
        # boost: lo=10, hi=1 => (10 | (1<<8))+1 = 267
        assert result.boost_duration == 267

    def test_heat_mode_field(self):
        raw = _make_header(325, 1) + bytes([0])
        result = decode_parameter(ParameterId.HEAT_MODE, raw)
        assert result.heat_control == HeatControl.SOFTWARE_DISABLED

    def test_timer_fields(self):
        raw = _make_header(326, 3) + bytes([1, 0xE8, 0x03])
        result = decode_parameter(ParameterId.TIMER, raw)
        assert result.timer_status == TimerStatus.ENABLED
        assert result.duration == 1000

    def test_sound_fields(self):
        raw = _make_header(369, 2) + bytes([200, 7])
        result = decode_parameter(ParameterId.SOUND, raw)
        assert result.volume == 200
        assert result.sound_file == 7

    def test_log_effect_fields(self):
        raw = _make_header(370, 8) + bytes([1, 0, 10, 20, 30, 40, 5, 0])
        result = decode_parameter(ParameterId.LOG_EFFECT, raw)
        assert result.log_effect == LogEffect.ON
        assert result.color.red == 10
        assert result.color.blue == 20
        assert result.color.green == 30
        assert result.color.white == 40
        assert result.pattern == 5

    def test_flame_effect_all_fields(self):
        """Verify every field in a flame effect decode."""
        raw = _make_header(322, 20) + bytes(
            [
                1,  # flame_effect ON
                4,  # wire speed -> model 5
                0b11,  # brightness LOW, pulsating ON
                7,  # media_theme KALEIDOSCOPE
                1,  # media_light ON
                10,
                20,
                30,
                40,  # media RBGW
                0,  # padding
                1,  # overhead_light ON
                50,
                60,
                70,
                80,  # overhead RBGW
                1,  # light_status ON
                5,  # flame_color YELLOW
                0,
                0,  # padding
                1,  # ambient_sensor ON
            ]
        )
        r = decode_parameter(ParameterId.FLAME_EFFECT, raw)
        assert r.flame_effect == FlameEffect.ON
        assert r.flame_speed == 5
        assert r.brightness == Brightness.LOW
        assert r.pulsating_effect == PulsatingEffect.ON
        assert r.media_theme == MediaTheme.KALEIDOSCOPE
        assert r.media_light == LightStatus.ON
        assert r.media_color == RGBWColor(red=10, blue=20, green=30, white=40)
        assert r.overhead_light == LightStatus.ON
        assert r.overhead_color == RGBWColor(red=50, blue=60, green=70, white=80)
        assert r.light_status == LightStatus.ON
        assert r.flame_color == FlameColor.YELLOW
        assert r.ambient_sensor == LightStatus.ON
