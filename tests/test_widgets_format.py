"""Tests for widget format functions and the format_parameters dispatcher.

Covers:
- _display_name helper
- _format_rgbw helper
- _temp_suffix / _convert_temp helpers
- _format_mode
- _format_flame_effect
- _format_heat
- _format_heat_mode
- _format_timer
- _format_software_version
- _format_error
- _format_temp_unit
- _format_sound
- _format_log_effect
- _format_connection_state
- format_parameters dispatcher (all param types + ordering + empty)
- ArrowNavMixin
- _ClickableValue / ClickableParam
- _rotate_palette
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from flameconnect.models import (
    Brightness,
    ConnectionState,
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
from flameconnect.tui.widgets import (
    _convert_temp,
    _display_name,
    _format_connection_state,
    _format_error,
    _format_flame_effect,
    _format_heat,
    _format_heat_mode,
    _format_log_effect,
    _format_mode,
    _format_rgbw,
    _format_software_version,
    _format_sound,
    _format_temp_unit,
    _format_timer,
    _rotate_palette,
    _temp_suffix,
    format_parameters,
)

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _white() -> RGBWColor:
    return RGBWColor(red=255, green=255, blue=255, white=0)


def _black() -> RGBWColor:
    return RGBWColor(red=0, green=0, blue=0, white=0)


def _sample_flame_effect(**overrides) -> FlameEffectParam:
    """Build a FlameEffectParam with sensible defaults, overridable."""
    defaults = dict(
        flame_effect=FlameEffect.ON,
        flame_speed=3,
        brightness=Brightness.HIGH,
        pulsating_effect=PulsatingEffect.OFF,
        media_theme=MediaTheme.WHITE,
        media_light=LightStatus.ON,
        media_color=_white(),
        overhead_light=LightStatus.ON,
        overhead_color=_white(),
        light_status=LightStatus.ON,
        flame_color=FlameColor.ALL,
        ambient_sensor=LightStatus.OFF,
    )
    defaults.update(overrides)
    return FlameEffectParam(**defaults)


# ---------------------------------------------------------------------------
# _display_name
# ---------------------------------------------------------------------------


class TestDisplayName:
    """Tests for _display_name enum-to-title conversion."""

    def test_single_word(self):
        assert _display_name(FireMode.STANDBY) == "Standby"

    def test_single_word_manual(self):
        assert _display_name(FireMode.MANUAL) == "Manual"

    def test_multi_word_underscore(self):
        assert _display_name(HeatMode.FAN_ONLY) == "Fan Only"

    def test_multi_word_software_disabled(self):
        assert _display_name(HeatControl.SOFTWARE_DISABLED) == "Software Disabled"

    def test_multi_word_hardware_disabled(self):
        assert _display_name(HeatControl.HARDWARE_DISABLED) == "Hardware Disabled"

    def test_enum_on_off(self):
        assert _display_name(FlameEffect.ON) == "On"
        assert _display_name(FlameEffect.OFF) == "Off"

    def test_connection_states(self):
        assert _display_name(ConnectionState.CONNECTED) == "Connected"
        assert _display_name(ConnectionState.NOT_CONNECTED) == "Not Connected"
        assert _display_name(ConnectionState.UPDATING_FIRMWARE) == "Updating Firmware"
        assert _display_name(ConnectionState.UNKNOWN) == "Unknown"

    def test_temp_unit(self):
        assert _display_name(TempUnit.CELSIUS) == "Celsius"
        assert _display_name(TempUnit.FAHRENHEIT) == "Fahrenheit"

    def test_media_theme_user_defined(self):
        assert _display_name(MediaTheme.USER_DEFINED) == "User Defined"

    def test_yellow_red(self):
        assert _display_name(FlameColor.YELLOW_RED) == "Yellow Red"

    def test_yellow_blue(self):
        assert _display_name(FlameColor.YELLOW_BLUE) == "Yellow Blue"

    def test_blue_red(self):
        assert _display_name(FlameColor.BLUE_RED) == "Blue Red"


# ---------------------------------------------------------------------------
# _format_rgbw
# ---------------------------------------------------------------------------


class TestFormatRGBW:
    """Tests for _format_rgbw."""

    def test_basic_color(self):
        color = RGBWColor(red=100, green=200, blue=50, white=30)
        assert _format_rgbw(color) == "R:100 G:200 B:50 W:30"

    def test_all_zeros(self):
        color = RGBWColor(red=0, green=0, blue=0, white=0)
        assert _format_rgbw(color) == "R:0 G:0 B:0 W:0"

    def test_max_values(self):
        color = RGBWColor(red=255, green=255, blue=255, white=255)
        assert _format_rgbw(color) == "R:255 G:255 B:255 W:255"


# ---------------------------------------------------------------------------
# _temp_suffix / _convert_temp
# ---------------------------------------------------------------------------


class TestTempSuffix:
    """Tests for _temp_suffix helper."""

    def test_none_returns_empty(self):
        assert _temp_suffix(None) == ""

    def test_celsius(self):
        assert _temp_suffix(TempUnitParam(unit=TempUnit.CELSIUS)) == "C"

    def test_fahrenheit(self):
        assert _temp_suffix(TempUnitParam(unit=TempUnit.FAHRENHEIT)) == "F"


class TestConvertTemp:
    """Tests for _convert_temp helper."""

    def test_celsius_passthrough(self):
        assert _convert_temp(22.0, TempUnit.CELSIUS) == 22.0

    def test_fahrenheit_conversion(self):
        # 22 C => 71.6 F
        assert _convert_temp(22.0, TempUnit.FAHRENHEIT) == 71.6

    def test_zero_celsius_to_fahrenheit(self):
        # 0 C => 32 F
        assert _convert_temp(0.0, TempUnit.FAHRENHEIT) == 32.0

    def test_100_celsius_to_fahrenheit(self):
        # 100 C => 212.0 F
        assert _convert_temp(100.0, TempUnit.FAHRENHEIT) == 212.0


# ---------------------------------------------------------------------------
# _format_mode
# ---------------------------------------------------------------------------


class TestFormatMode:
    """Tests for _format_mode."""

    def test_standby_no_unit(self):
        param = ModeParam(mode=FireMode.STANDBY, target_temperature=20.0)
        result = _format_mode(param)
        assert len(result) == 2
        label, value, action = result[0]
        assert "Mode" in label
        assert value == "Standby"
        assert action == "toggle_power"
        # Temperature with no unit suffix
        label_t, value_t, action_t = result[1]
        assert "Target Temp" in label_t
        assert "20.0\u00b0" in value_t
        assert action_t == "set_temperature"

    def test_manual_mode_display(self):
        param = ModeParam(mode=FireMode.MANUAL, target_temperature=25.0)
        result = _format_mode(param)
        assert result[0][1] == "On"

    def test_with_celsius_unit(self):
        param = ModeParam(mode=FireMode.MANUAL, target_temperature=22.0)
        tu = TempUnitParam(unit=TempUnit.CELSIUS)
        result = _format_mode(param, temp_unit=tu)
        assert "22.0\u00b0C" in result[1][1]

    def test_with_fahrenheit_unit(self):
        param = ModeParam(mode=FireMode.MANUAL, target_temperature=22.0)
        tu = TempUnitParam(unit=TempUnit.FAHRENHEIT)
        result = _format_mode(param, temp_unit=tu)
        assert "71.6\u00b0F" in result[1][1]


# ---------------------------------------------------------------------------
# _format_flame_effect
# ---------------------------------------------------------------------------


class TestFormatFlameEffect:
    """Tests for _format_flame_effect."""

    def test_basic_flame_effect(self):
        param = _sample_flame_effect()
        result = _format_flame_effect(param)
        # Should have 11 tuples (flame_effect + color + speed + brightness
        #   + pulsating + media_theme + media_light + media_color
        #   + overhead_light + overhead_color + ambient_sensor)
        assert len(result) == 11

    def test_flame_effect_labels_and_actions(self):
        param = _sample_flame_effect()
        result = _format_flame_effect(param)
        labels_and_actions = [(r[0], r[2]) for r in result]
        assert "Flame Effect" in labels_and_actions[0][0]
        assert labels_and_actions[0][1] == "toggle_flame_effect"
        assert labels_and_actions[1][1] == "set_flame_color"
        assert labels_and_actions[2][1] == "set_flame_speed"
        assert labels_and_actions[3][1] == "toggle_brightness"
        assert labels_and_actions[4][1] == "toggle_pulsating"
        assert labels_and_actions[5][1] == "set_media_theme"
        assert labels_and_actions[6][1] == "toggle_media_light"
        assert labels_and_actions[7][1] == "set_media_color"
        assert labels_and_actions[8][1] == "toggle_overhead_light"
        assert labels_and_actions[9][1] == "set_overhead_color"
        assert labels_and_actions[10][1] == "toggle_ambient_sensor"

    def test_flame_effect_values(self):
        param = _sample_flame_effect(
            flame_effect=FlameEffect.OFF,
            flame_speed=5,
            brightness=Brightness.LOW,
            pulsating_effect=PulsatingEffect.ON,
            media_theme=MediaTheme.PRISM,
            media_light=LightStatus.OFF,
            flame_color=FlameColor.BLUE,
            ambient_sensor=LightStatus.ON,
        )
        result = _format_flame_effect(param)
        assert result[0][1] == "Off"  # FlameEffect.OFF
        assert result[1][1] == "Blue"  # FlameColor.BLUE
        assert result[2][1] == "5/5"  # flame_speed
        assert result[3][1] == "Low"  # Brightness.LOW
        assert result[4][1] == "On"  # PulsatingEffect.ON
        assert result[5][1] == "Prism"  # MediaTheme.PRISM
        assert result[6][1] == "Off"  # media_light OFF
        assert result[10][1] == "On"  # ambient_sensor ON

    def test_flame_effect_media_color_format(self):
        color = RGBWColor(red=10, green=20, blue=30, white=40)
        param = _sample_flame_effect(media_color=color)
        result = _format_flame_effect(param)
        assert result[7][1] == "R:10 G:20 B:30 W:40"

    def test_flame_effect_overhead_color_format(self):
        color = RGBWColor(red=50, green=60, blue=70, white=80)
        param = _sample_flame_effect(overhead_color=color)
        result = _format_flame_effect(param)
        assert result[9][1] == "R:50 G:60 B:70 W:80"

    def test_overhead_light_status_display(self):
        param = _sample_flame_effect(light_status=LightStatus.OFF)
        result = _format_flame_effect(param)
        assert result[8][1] == "Off"  # Overhead Light uses light_status


# ---------------------------------------------------------------------------
# _format_heat
# ---------------------------------------------------------------------------


class TestFormatHeat:
    """Tests for _format_heat."""

    def test_normal_mode_no_unit(self):
        param = HeatParam(
            heat_status=HeatStatus.ON,
            heat_mode=HeatMode.NORMAL,
            setpoint_temperature=22.0,
            boost_duration=30,
        )
        result = _format_heat(param)
        assert len(result) == 4
        assert result[0][1] == "On"
        assert result[0][2] == "toggle_heat"
        assert result[1][1] == "Normal"
        assert result[1][2] == "set_heat_mode"
        assert "22.0\u00b0" in result[2][1]
        assert result[3][1] == "Off"  # Boost off when not BOOST mode

    def test_boost_mode(self):
        param = HeatParam(
            heat_status=HeatStatus.ON,
            heat_mode=HeatMode.BOOST,
            setpoint_temperature=25.0,
            boost_duration=15,
        )
        result = _format_heat(param)
        assert result[3][1] == "15min"

    def test_heat_off_status(self):
        param = HeatParam(
            heat_status=HeatStatus.OFF,
            heat_mode=HeatMode.ECO,
            setpoint_temperature=18.0,
            boost_duration=0,
        )
        result = _format_heat(param)
        assert result[0][1] == "Off"
        assert result[1][1] == "Eco"

    def test_heat_with_celsius(self):
        param = HeatParam(
            heat_status=HeatStatus.ON,
            heat_mode=HeatMode.NORMAL,
            setpoint_temperature=22.0,
            boost_duration=0,
        )
        tu = TempUnitParam(unit=TempUnit.CELSIUS)
        result = _format_heat(param, temp_unit=tu)
        assert "22.0\u00b0C" in result[2][1]

    def test_heat_with_fahrenheit(self):
        param = HeatParam(
            heat_status=HeatStatus.ON,
            heat_mode=HeatMode.NORMAL,
            setpoint_temperature=22.0,
            boost_duration=0,
        )
        tu = TempUnitParam(unit=TempUnit.FAHRENHEIT)
        result = _format_heat(param, temp_unit=tu)
        assert "71.6\u00b0F" in result[2][1]

    def test_fan_only_mode(self):
        param = HeatParam(
            heat_status=HeatStatus.ON,
            heat_mode=HeatMode.FAN_ONLY,
            setpoint_temperature=20.0,
            boost_duration=0,
        )
        result = _format_heat(param)
        assert result[1][1] == "Fan Only"

    def test_schedule_mode(self):
        param = HeatParam(
            heat_status=HeatStatus.ON,
            heat_mode=HeatMode.SCHEDULE,
            setpoint_temperature=20.0,
            boost_duration=0,
        )
        result = _format_heat(param)
        assert result[1][1] == "Schedule"


# ---------------------------------------------------------------------------
# _format_heat_mode
# ---------------------------------------------------------------------------


class TestFormatHeatMode:
    """Tests for _format_heat_mode."""

    def test_enabled(self):
        param = HeatModeParam(heat_control=HeatControl.ENABLED)
        result = _format_heat_mode(param)
        assert len(result) == 1
        assert "Heat Control" in result[0][0]
        assert result[0][1] == "Enabled"
        assert result[0][2] is None

    def test_software_disabled(self):
        param = HeatModeParam(heat_control=HeatControl.SOFTWARE_DISABLED)
        result = _format_heat_mode(param)
        assert result[0][1] == "Software Disabled"

    def test_hardware_disabled(self):
        param = HeatModeParam(heat_control=HeatControl.HARDWARE_DISABLED)
        result = _format_heat_mode(param)
        assert result[0][1] == "Hardware Disabled"


# ---------------------------------------------------------------------------
# _format_timer
# ---------------------------------------------------------------------------


class TestFormatTimer:
    """Tests for _format_timer."""

    def test_disabled_timer(self):
        param = TimerParam(timer_status=TimerStatus.DISABLED, duration=0)
        result = _format_timer(param)
        assert len(result) == 1
        assert "Timer" in result[0][0]
        assert "Disabled" in result[0][1]
        assert "Duration: 0min" in result[0][1]
        assert result[0][2] == "toggle_timer"

    def test_enabled_timer_with_duration(self):
        param = TimerParam(timer_status=TimerStatus.ENABLED, duration=30)
        result = _format_timer(param)
        assert "Enabled" in result[0][1]
        assert "Duration: 30min" in result[0][1]
        # Should include "Off at HH:MM"
        assert "Off at" in result[0][1]

    def test_enabled_timer_zero_duration(self):
        """Enabled timer with 0 duration should not show off-at time."""
        param = TimerParam(timer_status=TimerStatus.ENABLED, duration=0)
        result = _format_timer(param)
        assert "Enabled" in result[0][1]
        assert "Off at" not in result[0][1]

    def test_disabled_timer_nonzero_duration(self):
        """Disabled timer with leftover duration should not show off-at."""
        param = TimerParam(timer_status=TimerStatus.DISABLED, duration=45)
        result = _format_timer(param)
        assert "Disabled" in result[0][1]
        assert "Duration: 45min" in result[0][1]
        assert "Off at" not in result[0][1]


# ---------------------------------------------------------------------------
# _format_software_version
# ---------------------------------------------------------------------------


class TestFormatSoftwareVersion:
    """Tests for _format_software_version."""

    def test_basic_version(self):
        param = SoftwareVersionParam(
            ui_major=1,
            ui_minor=2,
            ui_test=3,
            control_major=4,
            control_minor=5,
            control_test=6,
            relay_major=7,
            relay_minor=8,
            relay_test=9,
        )
        result = _format_software_version(param)
        assert len(result) == 1
        assert "Software" in result[0][0]
        assert "UI 1.2.3" in result[0][1]
        assert "Control 4.5.6" in result[0][1]
        assert "Relay 7.8.9" in result[0][1]
        assert result[0][2] is None

    def test_zero_version(self):
        param = SoftwareVersionParam(
            ui_major=0,
            ui_minor=0,
            ui_test=0,
            control_major=0,
            control_minor=0,
            control_test=0,
            relay_major=0,
            relay_minor=0,
            relay_test=0,
        )
        result = _format_software_version(param)
        assert "UI 0.0.0" in result[0][1]
        assert "Control 0.0.0" in result[0][1]
        assert "Relay 0.0.0" in result[0][1]


# ---------------------------------------------------------------------------
# _format_error
# ---------------------------------------------------------------------------


class TestFormatError:
    """Tests for _format_error."""

    def test_no_errors(self):
        param = ErrorParam(error_byte1=0, error_byte2=0, error_byte3=0, error_byte4=0)
        result = _format_error(param)
        assert len(result) == 1
        assert "No Errors Recorded" in result[0][1]
        assert result[0][2] is None

    def test_has_error_byte1(self):
        param = ErrorParam(
            error_byte1=0xFF, error_byte2=0, error_byte3=0, error_byte4=0
        )
        result = _format_error(param)
        assert len(result) == 1
        assert "Error" in result[0][0]
        assert "0xFF" in result[0][1]
        assert "0x00" in result[0][1]

    def test_has_error_all_bytes(self):
        param = ErrorParam(
            error_byte1=0x12,
            error_byte2=0x34,
            error_byte3=0x56,
            error_byte4=0x78,
        )
        result = _format_error(param)
        assert "0x12" in result[0][1]
        assert "0x34" in result[0][1]
        assert "0x56" in result[0][1]
        assert "0x78" in result[0][1]

    def test_error_only_byte4(self):
        param = ErrorParam(error_byte1=0, error_byte2=0, error_byte3=0, error_byte4=1)
        result = _format_error(param)
        # Any non-zero byte should flag an error
        assert "Error" in result[0][0]

    def test_no_error_label_bold(self):
        param = ErrorParam(error_byte1=0, error_byte2=0, error_byte3=0, error_byte4=0)
        result = _format_error(param)
        assert "[bold]Errors:[/bold]" in result[0][0]

    def test_error_label_bold_red(self):
        param = ErrorParam(error_byte1=1, error_byte2=0, error_byte3=0, error_byte4=0)
        result = _format_error(param)
        assert "bold red" in result[0][0]


# ---------------------------------------------------------------------------
# _format_temp_unit
# ---------------------------------------------------------------------------


class TestFormatTempUnit:
    """Tests for _format_temp_unit."""

    def test_celsius(self):
        param = TempUnitParam(unit=TempUnit.CELSIUS)
        result = _format_temp_unit(param)
        assert len(result) == 1
        assert "Temp Unit" in result[0][0]
        assert result[0][1] == "Celsius"
        assert result[0][2] == "toggle_temp_unit"

    def test_fahrenheit(self):
        param = TempUnitParam(unit=TempUnit.FAHRENHEIT)
        result = _format_temp_unit(param)
        assert result[0][1] == "Fahrenheit"


# ---------------------------------------------------------------------------
# _format_sound
# ---------------------------------------------------------------------------


class TestFormatSound:
    """Tests for _format_sound."""

    def test_basic(self):
        param = SoundParam(volume=5, sound_file=3)
        result = _format_sound(param)
        assert len(result) == 1
        assert "Sound" in result[0][0]
        assert "Volume 5" in result[0][1]
        assert "File: 3" in result[0][1]
        assert result[0][2] is None

    def test_zero_volume(self):
        param = SoundParam(volume=0, sound_file=0)
        result = _format_sound(param)
        assert "Volume 0" in result[0][1]
        assert "File: 0" in result[0][1]


# ---------------------------------------------------------------------------
# _format_log_effect
# ---------------------------------------------------------------------------


class TestFormatLogEffect:
    """Tests for _format_log_effect."""

    def test_basic(self):
        color = RGBWColor(red=128, green=64, blue=32, white=16)
        param = LogEffectParam(log_effect=LogEffect.ON, color=color, pattern=2)
        result = _format_log_effect(param)
        assert len(result) == 1
        assert "Log Effect" in result[0][0]
        assert "On" in result[0][1]
        assert "R:128 G:64 B:32 W:16" in result[0][1]
        assert "Pattern: 2" in result[0][1]
        assert result[0][2] is None

    def test_off(self):
        color = _black()
        param = LogEffectParam(log_effect=LogEffect.OFF, color=color, pattern=0)
        result = _format_log_effect(param)
        assert "Off" in result[0][1]


# ---------------------------------------------------------------------------
# _format_connection_state
# ---------------------------------------------------------------------------


class TestFormatConnectionState:
    """Tests for _format_connection_state."""

    def test_connected(self):
        result = _format_connection_state(ConnectionState.CONNECTED)
        assert "green" in result
        assert "Connected" in result

    def test_not_connected(self):
        result = _format_connection_state(ConnectionState.NOT_CONNECTED)
        assert "red" in result
        assert "Not Connected" in result

    def test_updating_firmware(self):
        result = _format_connection_state(ConnectionState.UPDATING_FIRMWARE)
        assert "yellow" in result
        assert "Updating Firmware" in result

    def test_unknown(self):
        result = _format_connection_state(ConnectionState.UNKNOWN)
        assert "dim" in result
        assert "Unknown" in result


# ---------------------------------------------------------------------------
# _rotate_palette
# ---------------------------------------------------------------------------


class TestRotatePalette:
    """Tests for _rotate_palette."""

    def test_frame_0(self):
        palette = ("a", "b", "c")
        assert _rotate_palette(palette, 0) == ("a", "b", "c")

    def test_frame_1(self):
        palette = ("a", "b", "c")
        assert _rotate_palette(palette, 1) == ("b", "c", "a")

    def test_frame_2(self):
        palette = ("a", "b", "c")
        assert _rotate_palette(palette, 2) == ("c", "a", "b")

    def test_frame_wraps(self):
        palette = ("a", "b", "c")
        assert _rotate_palette(palette, 3) == ("a", "b", "c")
        assert _rotate_palette(palette, 4) == ("b", "c", "a")
        assert _rotate_palette(palette, 5) == ("c", "a", "b")


# ---------------------------------------------------------------------------
# format_parameters dispatcher
# ---------------------------------------------------------------------------


class TestFormatParameters:
    """Tests for the format_parameters dispatcher function."""

    def test_empty_params(self):
        result = format_parameters([])
        assert len(result) == 1
        assert "No parameters available" in result[0][0]

    def test_single_mode_param(self):
        params = [ModeParam(mode=FireMode.MANUAL, target_temperature=22.0)]
        result = format_parameters(params)
        assert len(result) == 2  # mode + target_temp
        assert "Mode" in result[0][0]
        assert result[0][1] == "On"

    def test_single_heat_param(self):
        params = [
            HeatParam(
                heat_status=HeatStatus.ON,
                heat_mode=HeatMode.NORMAL,
                setpoint_temperature=22.0,
                boost_duration=0,
            )
        ]
        result = format_parameters(params)
        assert any("Heat" in r[0] for r in result)

    def test_single_heat_mode_param(self):
        params = [HeatModeParam(heat_control=HeatControl.ENABLED)]
        result = format_parameters(params)
        assert any("Heat Control" in r[0] for r in result)

    def test_single_flame_effect_param(self):
        params = [_sample_flame_effect()]
        result = format_parameters(params)
        assert any("Flame Effect" in r[0] for r in result)

    def test_single_timer_param(self):
        params = [TimerParam(timer_status=TimerStatus.DISABLED, duration=0)]
        result = format_parameters(params)
        assert any("Timer" in r[0] for r in result)

    def test_single_software_version_param(self):
        params = [
            SoftwareVersionParam(
                ui_major=1,
                ui_minor=0,
                ui_test=0,
                control_major=2,
                control_minor=0,
                control_test=0,
                relay_major=3,
                relay_minor=0,
                relay_test=0,
            )
        ]
        result = format_parameters(params)
        assert any("Software" in r[0] for r in result)

    def test_single_error_param(self):
        params = [
            ErrorParam(error_byte1=0, error_byte2=0, error_byte3=0, error_byte4=0)
        ]
        result = format_parameters(params)
        assert any("No Errors Recorded" in r[1] for r in result)

    def test_single_temp_unit_param(self):
        params = [TempUnitParam(unit=TempUnit.CELSIUS)]
        result = format_parameters(params)
        assert any("Temp Unit" in r[0] for r in result)
        assert any("Celsius" in r[1] for r in result)

    def test_single_sound_param(self):
        params = [SoundParam(volume=3, sound_file=1)]
        result = format_parameters(params)
        assert any("Sound" in r[0] for r in result)

    def test_single_log_effect_param(self):
        params = [LogEffectParam(log_effect=LogEffect.ON, color=_black(), pattern=0)]
        result = format_parameters(params)
        assert any("Log Effect" in r[0] for r in result)

    def test_temp_unit_applied_to_mode(self):
        """When TempUnitParam is present, mode temp should use it."""
        params = [
            TempUnitParam(unit=TempUnit.FAHRENHEIT),
            ModeParam(mode=FireMode.MANUAL, target_temperature=22.0),
        ]
        result = format_parameters(params)
        # 22C -> 71.6F
        temp_row = [r for r in result if "Target Temp" in r[0]][0]
        assert "71.6\u00b0F" in temp_row[1]

    def test_temp_unit_applied_to_heat(self):
        """When TempUnitParam is present, heat temp should use it."""
        params = [
            TempUnitParam(unit=TempUnit.FAHRENHEIT),
            HeatParam(
                heat_status=HeatStatus.ON,
                heat_mode=HeatMode.NORMAL,
                setpoint_temperature=22.0,
                boost_duration=0,
            ),
        ]
        result = format_parameters(params)
        setpoint_row = [r for r in result if "Setpoint" in r[0]][0]
        assert "71.6\u00b0F" in setpoint_row[1]

    def test_display_order(self):
        """Parameters are returned in the defined display order."""
        params = [
            ErrorParam(error_byte1=0, error_byte2=0, error_byte3=0, error_byte4=0),
            ModeParam(mode=FireMode.MANUAL, target_temperature=22.0),
            TempUnitParam(unit=TempUnit.CELSIUS),
        ]
        result = format_parameters(params)
        # Mode should come before TempUnit, which should come before Error
        labels = [r[0] for r in result]
        mode_idx = next(i for i, lbl in enumerate(labels) if "Mode" in lbl)
        temp_idx = next(i for i, lbl in enumerate(labels) if "Temp Unit" in lbl)
        error_idx = next(i for i, lbl in enumerate(labels) if "Errors" in lbl)
        assert mode_idx < temp_idx < error_idx

    def test_all_param_types_together(self):
        """All parameter types together produce correctly ordered results."""
        params = [
            ModeParam(mode=FireMode.MANUAL, target_temperature=22.0),
            HeatParam(
                heat_status=HeatStatus.ON,
                heat_mode=HeatMode.NORMAL,
                setpoint_temperature=22.0,
                boost_duration=0,
            ),
            HeatModeParam(heat_control=HeatControl.ENABLED),
            _sample_flame_effect(),
            TimerParam(timer_status=TimerStatus.DISABLED, duration=0),
            SoftwareVersionParam(
                ui_major=1,
                ui_minor=0,
                ui_test=0,
                control_major=2,
                control_minor=0,
                control_test=0,
                relay_major=3,
                relay_minor=0,
                relay_test=0,
            ),
            TempUnitParam(unit=TempUnit.CELSIUS),
            SoundParam(volume=5, sound_file=1),
            LogEffectParam(log_effect=LogEffect.ON, color=_black(), pattern=0),
            ErrorParam(error_byte1=0, error_byte2=0, error_byte3=0, error_byte4=0),
        ]
        result = format_parameters(params)
        # Should have results for all types; at minimum > 20 rows
        assert len(result) > 20

        # Verify display order: Mode before Heat before HeatMode
        # before FlameEffect before Timer before Software before
        # TempUnit before Sound before LogEffect before Error
        labels = [r[0] for r in result]
        first_mode = next(i for i, lbl in enumerate(labels) if "Mode" in lbl)
        first_heat = next(
            i
            for i, lbl in enumerate(labels)
            if "Heat" in lbl and "Control" not in lbl and "Mode" not in lbl
        )
        first_flame = next(i for i, lbl in enumerate(labels) if "Flame Effect" in lbl)
        first_timer = next(i for i, lbl in enumerate(labels) if "Timer" in lbl)
        first_sw = next(i for i, lbl in enumerate(labels) if "Software" in lbl)
        first_temp_unit = next(i for i, lbl in enumerate(labels) if "Temp Unit" in lbl)
        first_sound = next(i for i, lbl in enumerate(labels) if "Sound" in lbl)
        first_log = next(i for i, lbl in enumerate(labels) if "Log Effect" in lbl)
        first_error = next(
            i for i, lbl in enumerate(labels) if "Errors" in lbl or "Error" in lbl
        )
        assert (
            first_mode
            < first_heat
            < first_flame
            < first_timer
            < first_sw
            < first_temp_unit
            < first_sound
            < first_log
            < first_error
        )

    def test_error_with_nonzero_bytes(self):
        """Error param with non-zero bytes shows hex codes."""
        params = [
            ErrorParam(
                error_byte1=0xAB,
                error_byte2=0xCD,
                error_byte3=0xEF,
                error_byte4=0x01,
            )
        ]
        result = format_parameters(params)
        error_row = result[0]
        assert "0xAB" in error_row[1]
        assert "0xCD" in error_row[1]
        assert "0xEF" in error_row[1]
        assert "0x01" in error_row[1]


# ---------------------------------------------------------------------------
# ArrowNavMixin
# ---------------------------------------------------------------------------


class TestArrowNavMixin:
    """Tests for ArrowNavMixin.on_key method."""

    def test_left_key_focuses_previous(self):
        from flameconnect.tui.widgets import ArrowNavMixin

        mixin = ArrowNavMixin()
        mixin.focused = MagicMock()
        mixin.focus_previous = MagicMock()
        mixin.focus_next = MagicMock()

        # Patch the isinstance checks
        event = MagicMock()
        event.key = "left"

        with patch(
            "flameconnect.tui.widgets.ArrowNavMixin.on_key.__module__",
            create=True,
        ):
            # We need to make isinstance checks work
            from textual import events
            from textual.widgets import Button

            # Make focused look like a Button
            mixin.focused = MagicMock(spec=Button)
            real_event = MagicMock(spec=events.Key)
            real_event.key = "left"
            real_event.prevent_default = MagicMock()
            real_event.stop = MagicMock()

            mixin.on_key(real_event)
            mixin.focus_previous.assert_called_once()
            real_event.prevent_default.assert_called_once()
            real_event.stop.assert_called_once()

    def test_right_key_focuses_next(self):
        from flameconnect.tui.widgets import ArrowNavMixin

        mixin = ArrowNavMixin()
        mixin.focus_next = MagicMock()
        mixin.focus_previous = MagicMock()

        from textual import events
        from textual.widgets import Button

        mixin.focused = MagicMock(spec=Button)
        real_event = MagicMock(spec=events.Key)
        real_event.key = "right"
        real_event.prevent_default = MagicMock()
        real_event.stop = MagicMock()

        mixin.on_key(real_event)
        mixin.focus_next.assert_called_once()
        real_event.prevent_default.assert_called_once()
        real_event.stop.assert_called_once()

    def test_up_key_focuses_previous(self):
        from flameconnect.tui.widgets import ArrowNavMixin

        mixin = ArrowNavMixin()
        mixin.focus_previous = MagicMock()
        mixin.focus_next = MagicMock()

        from textual import events
        from textual.widgets import Button

        mixin.focused = MagicMock(spec=Button)
        real_event = MagicMock(spec=events.Key)
        real_event.key = "up"
        real_event.prevent_default = MagicMock()
        real_event.stop = MagicMock()

        mixin.on_key(real_event)
        mixin.focus_previous.assert_called_once()

    def test_down_key_focuses_next(self):
        from flameconnect.tui.widgets import ArrowNavMixin

        mixin = ArrowNavMixin()
        mixin.focus_next = MagicMock()
        mixin.focus_previous = MagicMock()

        from textual import events
        from textual.widgets import Button

        mixin.focused = MagicMock(spec=Button)
        real_event = MagicMock(spec=events.Key)
        real_event.key = "down"
        real_event.prevent_default = MagicMock()
        real_event.stop = MagicMock()

        mixin.on_key(real_event)
        mixin.focus_next.assert_called_once()

    def test_non_button_focused_does_nothing(self):
        from flameconnect.tui.widgets import ArrowNavMixin

        mixin = ArrowNavMixin()
        mixin.focus_previous = MagicMock()
        mixin.focus_next = MagicMock()

        from textual import events

        # focused is NOT a Button
        mixin.focused = MagicMock()  # plain mock, not spec=Button
        real_event = MagicMock(spec=events.Key)
        real_event.key = "left"
        real_event.prevent_default = MagicMock()
        real_event.stop = MagicMock()

        mixin.on_key(real_event)
        mixin.focus_previous.assert_not_called()
        mixin.focus_next.assert_not_called()

    def test_non_event_key_does_nothing(self):
        from flameconnect.tui.widgets import ArrowNavMixin

        mixin = ArrowNavMixin()
        mixin.focus_previous = MagicMock()
        mixin.focus_next = MagicMock()

        # Pass something that is NOT events.Key
        mixin.on_key("not an event")
        mixin.focus_previous.assert_not_called()
        mixin.focus_next.assert_not_called()

    def test_other_key_does_nothing(self):
        """Non-arrow keys on a focused button should not trigger navigation."""
        from flameconnect.tui.widgets import ArrowNavMixin

        mixin = ArrowNavMixin()
        mixin.focus_previous = MagicMock()
        mixin.focus_next = MagicMock()

        from textual import events
        from textual.widgets import Button

        mixin.focused = MagicMock(spec=Button)
        real_event = MagicMock(spec=events.Key)
        real_event.key = "enter"
        real_event.prevent_default = MagicMock()
        real_event.stop = MagicMock()

        mixin.on_key(real_event)
        mixin.focus_previous.assert_not_called()
        mixin.focus_next.assert_not_called()
        real_event.prevent_default.assert_not_called()


# ---------------------------------------------------------------------------
# _ClickableValue
# ---------------------------------------------------------------------------


class TestClickableValue:
    """Tests for _ClickableValue widget construction."""

    def test_with_action(self):
        from flameconnect.tui.widgets import _ClickableValue

        widget = _ClickableValue("hello", action="do_something")
        assert widget._action == "do_something"
        assert "clickable" in widget.classes

    def test_without_action(self):
        from flameconnect.tui.widgets import _ClickableValue

        widget = _ClickableValue("hello", action=None)
        assert widget._action is None
        assert "clickable" not in widget.classes

    def test_no_action_default(self):
        from flameconnect.tui.widgets import _ClickableValue

        widget = _ClickableValue("hello")
        assert widget._action is None


# ---------------------------------------------------------------------------
# ClickableParam
# ---------------------------------------------------------------------------


class TestClickableParam:
    """Tests for ClickableParam widget construction."""

    def test_construction(self):
        from flameconnect.tui.widgets import ClickableParam

        widget = ClickableParam("Label: ", "Value", action="some_action")
        assert widget._label == "Label: "
        assert widget._value == "Value"
        assert widget._action == "some_action"

    def test_construction_no_action(self):
        from flameconnect.tui.widgets import ClickableParam

        widget = ClickableParam("Label: ", "Value")
        assert widget._action is None
