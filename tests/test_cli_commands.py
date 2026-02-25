"""Tests for CLI helper functions, display functions, commands, and entry points."""

from __future__ import annotations

import argparse
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from flameconnect.cli import (
    _convert_temp,
    _display_error,
    _display_flame_effect,
    _display_heat,
    _display_heat_mode,
    _display_log_effect,
    _display_mode,
    _display_parameter,
    _display_software_version,
    _display_sound,
    _display_temp_unit,
    _display_timer,
    _enum_name,
    _find_param,
    _find_temp_unit,
    _format_rgbw,
    _temp_suffix,
    async_main,
    build_parser,
    cmd_list,
    cmd_off,
    cmd_on,
    cmd_set,
    cmd_status,
    main,
)
from flameconnect.models import (
    Brightness,
    ConnectionState,
    ErrorParam,
    Fire,
    FireMode,
    FireOverview,
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
    PulsatingEffect,
    RGBWColor,
    SoftwareVersionParam,
    SoundParam,
    TempUnit,
    TempUnitParam,
    TimerParam,
    TimerStatus,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

FIRE_ID = "test-fire-001"

_DEFAULT_RGBW = RGBWColor(red=0, green=0, blue=0, white=0)


def _make_flame_effect_param(**overrides) -> FlameEffectParam:
    """Create a FlameEffectParam with sensible defaults."""
    defaults = dict(
        flame_effect=FlameEffect.ON,
        flame_speed=3,
        brightness=Brightness.HIGH,
        pulsating_effect=PulsatingEffect.OFF,
        media_theme=MediaTheme.USER_DEFINED,
        media_light=LightStatus.OFF,
        media_color=_DEFAULT_RGBW,
        overhead_light=LightStatus.OFF,
        overhead_color=_DEFAULT_RGBW,
        light_status=LightStatus.OFF,
        flame_color=FlameColor.ALL,
        ambient_sensor=LightStatus.OFF,
    )
    defaults.update(overrides)
    return FlameEffectParam(**defaults)


def _make_heat_param(**overrides) -> HeatParam:
    defaults = dict(
        heat_status=HeatStatus.ON,
        heat_mode=HeatMode.NORMAL,
        setpoint_temperature=22.0,
        boost_duration=0,
    )
    defaults.update(overrides)
    return HeatParam(**defaults)


def _make_mode_param(**overrides) -> ModeParam:
    defaults = dict(mode=FireMode.MANUAL, target_temperature=22.0)
    defaults.update(overrides)
    return ModeParam(**defaults)


def _make_fire(**overrides) -> Fire:
    defaults = dict(
        fire_id=FIRE_ID,
        friendly_name="Living Room",
        brand="Dimplex",
        product_type="Bold Ignite XL",
        product_model="BIX-50",
        item_code="ABC123",
        connection_state=ConnectionState.CONNECTED,
        with_heat=True,
        is_iot_fire=True,
    )
    defaults.update(overrides)
    return Fire(**defaults)


# ===================================================================
# Helper function tests
# ===================================================================


class TestEnumName:
    """Tests for _enum_name()."""

    def test_known_value(self):
        mapping = {0: "Off", 1: "On"}
        assert _enum_name(mapping, 0) == "Off"
        assert _enum_name(mapping, 1) == "On"

    def test_unknown_value(self):
        mapping = {0: "Off", 1: "On"}
        assert _enum_name(mapping, 99) == "Unknown(99)"

    def test_empty_mapping(self):
        assert _enum_name({}, 5) == "Unknown(5)"


class TestFormatRGBW:
    """Tests for _format_rgbw()."""

    def test_all_zeros(self):
        c = RGBWColor(red=0, green=0, blue=0, white=0)
        assert _format_rgbw(c) == "RGBW(0, 0, 0, 0)"

    def test_mixed_values(self):
        c = RGBWColor(red=255, green=128, blue=64, white=32)
        assert _format_rgbw(c) == "RGBW(255, 128, 64, 32)"


class TestFindTempUnit:
    """Tests for _find_temp_unit()."""

    def test_found(self):
        tu = TempUnitParam(unit=TempUnit.CELSIUS)
        result = _find_temp_unit([_make_mode_param(), tu])
        assert result is tu

    def test_not_found(self):
        result = _find_temp_unit([_make_mode_param()])
        assert result is None

    def test_empty_list(self):
        assert _find_temp_unit([]) is None


class TestTempSuffix:
    """Tests for _temp_suffix()."""

    def test_celsius(self):
        params: list[Parameter] = [TempUnitParam(unit=TempUnit.CELSIUS)]
        assert _temp_suffix(params) == "C"

    def test_fahrenheit(self):
        params: list[Parameter] = [TempUnitParam(unit=TempUnit.FAHRENHEIT)]
        assert _temp_suffix(params) == "F"

    def test_missing(self):
        assert _temp_suffix([]) == ""


class TestConvertTemp:
    """Tests for _convert_temp()."""

    def test_celsius_passthrough(self):
        assert _convert_temp(22.0, TempUnit.CELSIUS) == 22.0

    def test_fahrenheit_conversion(self):
        assert _convert_temp(0.0, TempUnit.FAHRENHEIT) == 32.0

    def test_fahrenheit_100(self):
        assert _convert_temp(100.0, TempUnit.FAHRENHEIT) == 212.0

    def test_fahrenheit_negative(self):
        # -40 C == -40 F
        assert _convert_temp(-40.0, TempUnit.FAHRENHEIT) == -40.0


class TestFindParam:
    """Tests for _find_param()."""

    def test_find_flame_effect(self):
        fep = _make_flame_effect_param()
        result = _find_param([_make_mode_param(), fep], FlameEffectParam)
        assert result is fep

    def test_find_heat(self):
        hp = _make_heat_param()
        result = _find_param([_make_mode_param(), hp], HeatParam)
        assert result is hp

    def test_not_found(self):
        result = _find_param([_make_mode_param()], FlameEffectParam)
        assert result is None

    def test_empty_list(self):
        result = _find_param([], HeatParam)
        assert result is None


# ===================================================================
# Display function tests
# ===================================================================


class TestDisplayMode:
    """Tests for _display_mode()."""

    def test_standby_no_temp_unit(self, capsys):
        param = _make_mode_param(mode=FireMode.STANDBY, target_temperature=20.0)
        _display_mode(param)
        out = capsys.readouterr().out
        assert "[321] Mode" in out
        assert "Standby" in out
        assert "20.0" in out
        # No unit suffix when temp_unit is None
        assert "\u00b0" in out

    def test_manual_with_celsius(self, capsys):
        param = _make_mode_param(mode=FireMode.MANUAL, target_temperature=22.0)
        tu = TempUnitParam(unit=TempUnit.CELSIUS)
        _display_mode(param, tu)
        out = capsys.readouterr().out
        assert "On" in out
        assert "22.0" in out
        assert "\u00b0C" in out

    def test_manual_with_fahrenheit(self, capsys):
        param = _make_mode_param(mode=FireMode.MANUAL, target_temperature=22.0)
        tu = TempUnitParam(unit=TempUnit.FAHRENHEIT)
        _display_mode(param, tu)
        out = capsys.readouterr().out
        assert "71.6" in out
        assert "\u00b0F" in out


class TestDisplayFlameEffect:
    """Tests for _display_flame_effect()."""

    def test_all_fields_displayed(self, capsys):
        param = _make_flame_effect_param(
            flame_effect=FlameEffect.ON,
            flame_speed=4,
            brightness=Brightness.LOW,
            pulsating_effect=PulsatingEffect.ON,
            flame_color=FlameColor.BLUE,
            media_theme=MediaTheme.PRISM,
            media_color=RGBWColor(red=10, green=20, blue=30, white=40),
            light_status=LightStatus.ON,
            overhead_color=RGBWColor(red=50, green=60, blue=70, white=80),
            ambient_sensor=LightStatus.ON,
        )
        _display_flame_effect(param)
        out = capsys.readouterr().out
        assert "[322] Flame Effect" in out
        assert "Flame:          On" in out
        assert "4 / 5" in out
        assert "Low" in out
        assert "Pulsating:      On" in out
        assert "Blue" in out
        assert "Prism" in out
        assert "RGBW(10, 20, 30, 40)" in out
        assert "Overhead Light: On" in out
        assert "RGBW(50, 60, 70, 80)" in out
        assert "Ambient Sensor: On" in out

    def test_flame_off(self, capsys):
        param = _make_flame_effect_param(flame_effect=FlameEffect.OFF)
        _display_flame_effect(param)
        out = capsys.readouterr().out
        assert "Flame:          Off" in out


class TestDisplayHeat:
    """Tests for _display_heat()."""

    def test_heat_on_no_temp_unit(self, capsys):
        param = _make_heat_param(
            heat_status=HeatStatus.ON,
            heat_mode=HeatMode.BOOST,
            setpoint_temperature=25.0,
            boost_duration=15,
        )
        _display_heat(param)
        out = capsys.readouterr().out
        assert "[323] Heat Settings" in out
        assert "On" in out
        assert "Boost" in out
        assert "25.0" in out
        assert "15" in out

    def test_heat_with_celsius(self, capsys):
        param = _make_heat_param(setpoint_temperature=22.0)
        tu = TempUnitParam(unit=TempUnit.CELSIUS)
        _display_heat(param, tu)
        out = capsys.readouterr().out
        assert "22.0\u00b0C" in out

    def test_heat_with_fahrenheit(self, capsys):
        param = _make_heat_param(setpoint_temperature=22.0)
        tu = TempUnitParam(unit=TempUnit.FAHRENHEIT)
        _display_heat(param, tu)
        out = capsys.readouterr().out
        assert "71.6\u00b0F" in out

    def test_heat_off(self, capsys):
        param = _make_heat_param(heat_status=HeatStatus.OFF)
        _display_heat(param)
        out = capsys.readouterr().out
        assert "Off" in out


class TestDisplayHeatMode:
    """Tests for _display_heat_mode()."""

    def test_enabled(self, capsys):
        param = HeatModeParam(heat_control=HeatControl.ENABLED)
        _display_heat_mode(param)
        out = capsys.readouterr().out
        assert "[325] Heat Mode" in out
        assert "Enabled" in out

    def test_software_disabled(self, capsys):
        param = HeatModeParam(heat_control=HeatControl.SOFTWARE_DISABLED)
        _display_heat_mode(param)
        out = capsys.readouterr().out
        assert "Software Disabled" in out

    def test_hardware_disabled(self, capsys):
        param = HeatModeParam(heat_control=HeatControl.HARDWARE_DISABLED)
        _display_heat_mode(param)
        out = capsys.readouterr().out
        assert "Hardware Disabled" in out


class TestDisplayTimer:
    """Tests for _display_timer()."""

    def test_timer_disabled(self, capsys):
        param = TimerParam(timer_status=TimerStatus.DISABLED, duration=0)
        _display_timer(param)
        out = capsys.readouterr().out
        assert "[326] Timer Mode" in out
        assert "Disabled" in out
        assert "0 min (0h 0m)" in out
        # Should NOT show "Off at:" when disabled
        assert "Off at:" not in out

    def test_timer_enabled_with_duration(self, capsys):
        param = TimerParam(timer_status=TimerStatus.ENABLED, duration=90)
        _display_timer(param)
        out = capsys.readouterr().out
        assert "Enabled" in out
        assert "90 min (1h 30m)" in out
        assert "Off at:" in out

    def test_timer_enabled_zero_duration(self, capsys):
        # Enabled but 0 duration: no "Off at:" line
        param = TimerParam(timer_status=TimerStatus.ENABLED, duration=0)
        _display_timer(param)
        out = capsys.readouterr().out
        assert "Enabled" in out
        assert "Off at:" not in out


class TestDisplaySoftwareVersion:
    """Tests for _display_software_version()."""

    def test_version_display(self, capsys):
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
        _display_software_version(param)
        out = capsys.readouterr().out
        assert "[327] Software Version" in out
        assert "1.2.3" in out
        assert "4.5.6" in out
        assert "7.8.9" in out


class TestDisplayError:
    """Tests for _display_error()."""

    def test_no_errors(self, capsys):
        param = ErrorParam(error_byte1=0, error_byte2=0, error_byte3=0, error_byte4=0)
        _display_error(param)
        out = capsys.readouterr().out
        assert "[329] Error" in out
        assert "None" in out
        assert "Active Faults:  None" in out

    def test_with_errors(self, capsys):
        param = ErrorParam(
            error_byte1=0xFF, error_byte2=0, error_byte3=0, error_byte4=0
        )
        _display_error(param)
        out = capsys.readouterr().out
        assert "Active Faults:  Yes" in out
        assert "0xFF" in out

    def test_error_bytes_formatted(self, capsys):
        param = ErrorParam(error_byte1=1, error_byte2=2, error_byte3=4, error_byte4=8)
        _display_error(param)
        out = capsys.readouterr().out
        assert "Error Byte 1:" in out
        assert "Error Byte 2:" in out
        assert "Error Byte 3:" in out
        assert "Error Byte 4:" in out
        assert "Active Faults:  Yes" in out


class TestDisplayTempUnit:
    """Tests for _display_temp_unit()."""

    def test_celsius(self, capsys):
        param = TempUnitParam(unit=TempUnit.CELSIUS)
        _display_temp_unit(param)
        out = capsys.readouterr().out
        assert "[236] Temperature Unit" in out
        assert "Celsius" in out

    def test_fahrenheit(self, capsys):
        param = TempUnitParam(unit=TempUnit.FAHRENHEIT)
        _display_temp_unit(param)
        out = capsys.readouterr().out
        assert "Fahrenheit" in out


class TestDisplaySound:
    """Tests for _display_sound()."""

    def test_display(self, capsys):
        param = SoundParam(volume=128, sound_file=3)
        _display_sound(param)
        out = capsys.readouterr().out
        assert "[369] Sound" in out
        assert "128 / 255" in out
        assert "3" in out


class TestDisplayLogEffect:
    """Tests for _display_log_effect()."""

    def test_on(self, capsys):
        param = LogEffectParam(
            log_effect=LogEffect.ON,
            color=RGBWColor(red=1, green=0, blue=255, white=128),
            pattern=5,
        )
        _display_log_effect(param)
        out = capsys.readouterr().out
        assert "[370] Log Effect" in out
        assert "On" in out
        assert "RGBW(1, 0, 255, 128)" in out
        assert "5" in out

    def test_off(self, capsys):
        param = LogEffectParam(
            log_effect=LogEffect.OFF,
            color=_DEFAULT_RGBW,
            pattern=0,
        )
        _display_log_effect(param)
        out = capsys.readouterr().out
        assert "Off" in out


# ===================================================================
# _display_parameter dispatcher tests
# ===================================================================


class TestDisplayParameter:
    """Tests for the _display_parameter() dispatcher."""

    def test_dispatches_mode(self, capsys):
        param = _make_mode_param()
        _display_parameter(param)
        assert "[321] Mode" in capsys.readouterr().out

    def test_dispatches_mode_with_temp_unit(self, capsys):
        param = _make_mode_param()
        tu = TempUnitParam(unit=TempUnit.CELSIUS)
        _display_parameter(param, tu)
        out = capsys.readouterr().out
        assert "[321] Mode" in out
        assert "\u00b0C" in out

    def test_dispatches_flame_effect(self, capsys):
        param = _make_flame_effect_param()
        _display_parameter(param)
        assert "[322] Flame Effect" in capsys.readouterr().out

    def test_dispatches_heat(self, capsys):
        param = _make_heat_param()
        _display_parameter(param)
        assert "[323] Heat Settings" in capsys.readouterr().out

    def test_dispatches_heat_with_temp_unit(self, capsys):
        param = _make_heat_param()
        tu = TempUnitParam(unit=TempUnit.FAHRENHEIT)
        _display_parameter(param, tu)
        out = capsys.readouterr().out
        assert "[323] Heat Settings" in out
        assert "\u00b0F" in out

    def test_dispatches_heat_mode(self, capsys):
        param = HeatModeParam(heat_control=HeatControl.ENABLED)
        _display_parameter(param)
        assert "[325] Heat Mode" in capsys.readouterr().out

    def test_dispatches_timer(self, capsys):
        param = TimerParam(timer_status=TimerStatus.DISABLED, duration=0)
        _display_parameter(param)
        assert "[326] Timer Mode" in capsys.readouterr().out

    def test_dispatches_software_version(self, capsys):
        param = SoftwareVersionParam(
            ui_major=1, ui_minor=0, ui_test=0,
            control_major=1, control_minor=0, control_test=0,
            relay_major=1, relay_minor=0, relay_test=0,
        )
        _display_parameter(param)
        assert "[327] Software Version" in capsys.readouterr().out

    def test_dispatches_error(self, capsys):
        param = ErrorParam(error_byte1=0, error_byte2=0, error_byte3=0, error_byte4=0)
        _display_parameter(param)
        assert "[329] Error" in capsys.readouterr().out

    def test_dispatches_temp_unit(self, capsys):
        param = TempUnitParam(unit=TempUnit.CELSIUS)
        _display_parameter(param)
        assert "[236] Temperature Unit" in capsys.readouterr().out

    def test_dispatches_sound(self, capsys):
        param = SoundParam(volume=100, sound_file=1)
        _display_parameter(param)
        assert "[369] Sound" in capsys.readouterr().out

    def test_dispatches_log_effect(self, capsys):
        param = LogEffectParam(log_effect=LogEffect.OFF, color=_DEFAULT_RGBW, pattern=0)
        _display_parameter(param)
        assert "[370] Log Effect" in capsys.readouterr().out


# ===================================================================
# Command tests (cmd_list, cmd_status, cmd_on, cmd_off, cmd_set)
# ===================================================================


class TestCmdList:
    """Tests for cmd_list()."""

    async def test_no_fires(self, capsys):
        client = AsyncMock()
        client.get_fires.return_value = []
        await cmd_list(client)
        out = capsys.readouterr().out
        assert "No fireplaces registered" in out

    async def test_one_fire(self, capsys):
        client = AsyncMock()
        fire = _make_fire()
        client.get_fires.return_value = [fire]
        await cmd_list(client)
        out = capsys.readouterr().out
        assert "1 fireplace(s)" in out
        assert "Living Room" in out
        assert FIRE_ID in out
        assert "Connected" in out

    async def test_multiple_fires(self, capsys):
        client = AsyncMock()
        fire1 = _make_fire(fire_id="fire-1", friendly_name="Room A")
        fire2 = _make_fire(
            fire_id="fire-2",
            friendly_name="Room B",
            connection_state=ConnectionState.NOT_CONNECTED,
        )
        client.get_fires.return_value = [fire1, fire2]
        await cmd_list(client)
        out = capsys.readouterr().out
        assert "2 fireplace(s)" in out
        assert "Room A" in out
        assert "Room B" in out
        assert "Not Connected" in out


class TestCmdStatus:
    """Tests for cmd_status()."""

    async def test_with_parameters(self, capsys):
        client = AsyncMock()
        params: list[Parameter] = [
            _make_mode_param(),
            _make_flame_effect_param(),
            _make_heat_param(),
            TempUnitParam(unit=TempUnit.CELSIUS),
        ]
        overview = FireOverview(fire=_make_fire(), parameters=params)
        client.get_fire_overview.return_value = overview
        await cmd_status(client, FIRE_ID)
        out = capsys.readouterr().out
        assert "Living Room" in out
        assert "4 parameter(s)" in out
        assert "[321] Mode" in out
        assert "[322] Flame Effect" in out
        assert "[323] Heat Settings" in out
        assert "[236] Temperature Unit" in out

    async def test_no_parameters(self, capsys):
        client = AsyncMock()
        overview = FireOverview(fire=_make_fire(), parameters=[])
        client.get_fire_overview.return_value = overview
        await cmd_status(client, FIRE_ID)
        out = capsys.readouterr().out
        assert "No parameters returned" in out

    async def test_connection_state_displayed(self, capsys):
        client = AsyncMock()
        fire = _make_fire(connection_state=ConnectionState.UPDATING_FIRMWARE)
        overview = FireOverview(fire=fire, parameters=[])
        client.get_fire_overview.return_value = overview
        await cmd_status(client, FIRE_ID)
        out = capsys.readouterr().out
        assert "Updating Firmware" in out


class TestCmdOn:
    """Tests for cmd_on()."""

    async def test_turn_on(self, capsys):
        client = AsyncMock()
        await cmd_on(client, FIRE_ID)
        client.turn_on.assert_awaited_once_with(FIRE_ID)
        out = capsys.readouterr().out
        assert "Turn-on command sent" in out
        assert FIRE_ID in out


class TestCmdOff:
    """Tests for cmd_off()."""

    async def test_turn_off(self, capsys):
        client = AsyncMock()
        await cmd_off(client, FIRE_ID)
        client.turn_off.assert_awaited_once_with(FIRE_ID)
        out = capsys.readouterr().out
        assert "Turn-off command sent" in out
        assert FIRE_ID in out


class TestCmdSet:
    """Tests for cmd_set() dispatch to all parameter setters."""

    async def test_dispatch_mode(self, capsys):
        client = AsyncMock()
        overview = FireOverview(
            fire=_make_fire(), parameters=[_make_mode_param()]
        )
        client.get_fire_overview.return_value = overview
        await cmd_set(client, FIRE_ID, "mode", "standby")
        out = capsys.readouterr().out
        assert "Mode set to standby" in out

    async def test_dispatch_flame_speed(self, capsys):
        client = AsyncMock()
        overview = FireOverview(
            fire=_make_fire(), parameters=[_make_flame_effect_param()]
        )
        client.get_fire_overview.return_value = overview
        await cmd_set(client, FIRE_ID, "flame-speed", "3")
        out = capsys.readouterr().out
        assert "Flame speed set to 3" in out

    async def test_dispatch_brightness(self, capsys):
        client = AsyncMock()
        overview = FireOverview(
            fire=_make_fire(), parameters=[_make_flame_effect_param()]
        )
        client.get_fire_overview.return_value = overview
        await cmd_set(client, FIRE_ID, "brightness", "low")
        out = capsys.readouterr().out
        assert "Brightness set to low" in out

    async def test_dispatch_pulsating(self, capsys):
        client = AsyncMock()
        overview = FireOverview(
            fire=_make_fire(), parameters=[_make_flame_effect_param()]
        )
        client.get_fire_overview.return_value = overview
        await cmd_set(client, FIRE_ID, "pulsating", "on")
        out = capsys.readouterr().out
        assert "Pulsating effect set to on" in out

    async def test_dispatch_flame_color(self, capsys):
        client = AsyncMock()
        overview = FireOverview(
            fire=_make_fire(), parameters=[_make_flame_effect_param()]
        )
        client.get_fire_overview.return_value = overview
        await cmd_set(client, FIRE_ID, "flame-color", "blue")
        out = capsys.readouterr().out
        assert "Flame color set to blue" in out

    async def test_dispatch_media_theme(self, capsys):
        client = AsyncMock()
        overview = FireOverview(
            fire=_make_fire(), parameters=[_make_flame_effect_param()]
        )
        client.get_fire_overview.return_value = overview
        await cmd_set(client, FIRE_ID, "media-theme", "prism")
        out = capsys.readouterr().out
        assert "Media theme set to prism" in out

    async def test_dispatch_heat_mode(self, capsys):
        client = AsyncMock()
        overview = FireOverview(
            fire=_make_fire(), parameters=[_make_heat_param()]
        )
        client.get_fire_overview.return_value = overview
        await cmd_set(client, FIRE_ID, "heat-mode", "eco")
        out = capsys.readouterr().out
        assert "Heat mode set to eco" in out

    async def test_dispatch_heat_temp(self, capsys):
        client = AsyncMock()
        overview = FireOverview(
            fire=_make_fire(), parameters=[_make_heat_param()]
        )
        client.get_fire_overview.return_value = overview
        await cmd_set(client, FIRE_ID, "heat-temp", "25.0")
        out = capsys.readouterr().out
        assert "Heat temperature set to 25.0" in out

    async def test_dispatch_timer(self, capsys):
        client = AsyncMock()
        await cmd_set(client, FIRE_ID, "timer", "60")
        out = capsys.readouterr().out
        assert "Timer set to 60 minutes" in out

    async def test_dispatch_temp_unit(self, capsys):
        client = AsyncMock()
        await cmd_set(client, FIRE_ID, "temp-unit", "celsius")
        out = capsys.readouterr().out
        assert "Temperature unit set to celsius" in out

    async def test_dispatch_flame_effect(self, capsys):
        client = AsyncMock()
        overview = FireOverview(
            fire=_make_fire(), parameters=[_make_flame_effect_param()]
        )
        client.get_fire_overview.return_value = overview
        await cmd_set(client, FIRE_ID, "flame-effect", "on")
        out = capsys.readouterr().out
        assert "Flame effect set to on" in out

    async def test_dispatch_media_light(self, capsys):
        client = AsyncMock()
        overview = FireOverview(
            fire=_make_fire(), parameters=[_make_flame_effect_param()]
        )
        client.get_fire_overview.return_value = overview
        await cmd_set(client, FIRE_ID, "media-light", "on")
        out = capsys.readouterr().out
        assert "Media light set to on" in out

    async def test_dispatch_media_color(self, capsys):
        client = AsyncMock()
        overview = FireOverview(
            fire=_make_fire(), parameters=[_make_flame_effect_param()]
        )
        client.get_fire_overview.return_value = overview
        await cmd_set(client, FIRE_ID, "media-color", "255,0,0,0")
        out = capsys.readouterr().out
        assert "Media color set to 255,0,0,0" in out

    async def test_dispatch_overhead_light(self, capsys):
        client = AsyncMock()
        overview = FireOverview(
            fire=_make_fire(), parameters=[_make_flame_effect_param()]
        )
        client.get_fire_overview.return_value = overview
        await cmd_set(client, FIRE_ID, "overhead-light", "on")
        out = capsys.readouterr().out
        assert "Overhead light set to on" in out

    async def test_dispatch_overhead_color(self, capsys):
        client = AsyncMock()
        overview = FireOverview(
            fire=_make_fire(), parameters=[_make_flame_effect_param()]
        )
        client.get_fire_overview.return_value = overview
        await cmd_set(client, FIRE_ID, "overhead-color", "0,0,180,0")
        out = capsys.readouterr().out
        assert "Overhead color set to 0,0,180,0" in out

    async def test_dispatch_ambient_sensor(self, capsys):
        client = AsyncMock()
        overview = FireOverview(
            fire=_make_fire(), parameters=[_make_flame_effect_param()]
        )
        client.get_fire_overview.return_value = overview
        await cmd_set(client, FIRE_ID, "ambient-sensor", "on")
        out = capsys.readouterr().out
        assert "Ambient sensor set to on" in out

    async def test_dispatch_unknown_param(self, capsys):
        client = AsyncMock()
        with pytest.raises(SystemExit):
            await cmd_set(client, FIRE_ID, "bogus-param", "value")
        out = capsys.readouterr().out
        assert "Error" in out
        assert "bogus-param" in out


# ===================================================================
# cmd_set edge cases: missing FlameEffectParam / HeatParam
# ===================================================================


class TestCmdSetMissingParams:
    """Tests for cmd_set when current parameter is missing from the overview."""

    async def test_flame_speed_no_flame_param(self, capsys):
        client = AsyncMock()
        overview = FireOverview(fire=_make_fire(), parameters=[])
        client.get_fire_overview.return_value = overview
        with pytest.raises(SystemExit):
            await cmd_set(client, FIRE_ID, "flame-speed", "3")
        out = capsys.readouterr().out
        assert "no FlameEffect parameter" in out

    async def test_brightness_no_flame_param(self, capsys):
        client = AsyncMock()
        overview = FireOverview(fire=_make_fire(), parameters=[])
        client.get_fire_overview.return_value = overview
        with pytest.raises(SystemExit):
            await cmd_set(client, FIRE_ID, "brightness", "low")
        out = capsys.readouterr().out
        assert "no FlameEffect parameter" in out

    async def test_heat_mode_no_heat_param(self, capsys):
        client = AsyncMock()
        overview = FireOverview(fire=_make_fire(), parameters=[])
        client.get_fire_overview.return_value = overview
        with pytest.raises(SystemExit):
            await cmd_set(client, FIRE_ID, "heat-mode", "eco")
        out = capsys.readouterr().out
        assert "no HeatSettings parameter" in out

    async def test_heat_temp_no_heat_param(self, capsys):
        client = AsyncMock()
        overview = FireOverview(fire=_make_fire(), parameters=[])
        client.get_fire_overview.return_value = overview
        with pytest.raises(SystemExit):
            await cmd_set(client, FIRE_ID, "heat-temp", "25.0")
        out = capsys.readouterr().out
        assert "no HeatSettings parameter" in out

    async def test_flame_effect_no_flame_param(self, capsys):
        client = AsyncMock()
        overview = FireOverview(fire=_make_fire(), parameters=[])
        client.get_fire_overview.return_value = overview
        with pytest.raises(SystemExit):
            await cmd_set(client, FIRE_ID, "flame-effect", "on")
        out = capsys.readouterr().out
        assert "no FlameEffect parameter" in out

    async def test_media_light_no_flame_param(self, capsys):
        client = AsyncMock()
        overview = FireOverview(fire=_make_fire(), parameters=[])
        client.get_fire_overview.return_value = overview
        with pytest.raises(SystemExit):
            await cmd_set(client, FIRE_ID, "media-light", "on")
        out = capsys.readouterr().out
        assert "no FlameEffect parameter" in out

    async def test_media_color_no_flame_param(self, capsys):
        client = AsyncMock()
        overview = FireOverview(fire=_make_fire(), parameters=[])
        client.get_fire_overview.return_value = overview
        with pytest.raises(SystemExit):
            await cmd_set(client, FIRE_ID, "media-color", "255,0,0,0")
        out = capsys.readouterr().out
        assert "no FlameEffect parameter" in out

    async def test_overhead_light_no_flame_param(self, capsys):
        client = AsyncMock()
        overview = FireOverview(fire=_make_fire(), parameters=[])
        client.get_fire_overview.return_value = overview
        with pytest.raises(SystemExit):
            await cmd_set(client, FIRE_ID, "overhead-light", "on")
        out = capsys.readouterr().out
        assert "no FlameEffect parameter" in out

    async def test_overhead_color_no_flame_param(self, capsys):
        client = AsyncMock()
        overview = FireOverview(fire=_make_fire(), parameters=[])
        client.get_fire_overview.return_value = overview
        with pytest.raises(SystemExit):
            await cmd_set(client, FIRE_ID, "overhead-color", "0,0,180,0")
        out = capsys.readouterr().out
        assert "no FlameEffect parameter" in out

    async def test_ambient_sensor_no_flame_param(self, capsys):
        client = AsyncMock()
        overview = FireOverview(fire=_make_fire(), parameters=[])
        client.get_fire_overview.return_value = overview
        with pytest.raises(SystemExit):
            await cmd_set(client, FIRE_ID, "ambient-sensor", "on")
        out = capsys.readouterr().out
        assert "no FlameEffect parameter" in out


# ===================================================================
# cmd_set invalid values
# ===================================================================


class TestCmdSetInvalidValues:
    """Tests for cmd_set with invalid values that trigger validation errors."""

    async def test_mode_invalid(self, capsys):
        client = AsyncMock()
        with pytest.raises(SystemExit):
            await cmd_set(client, FIRE_ID, "mode", "turbo")
        out = capsys.readouterr().out
        assert "Error" in out

    async def test_flame_speed_too_high(self, capsys):
        client = AsyncMock()
        overview = FireOverview(
            fire=_make_fire(), parameters=[_make_flame_effect_param()]
        )
        client.get_fire_overview.return_value = overview
        with pytest.raises(SystemExit):
            await cmd_set(client, FIRE_ID, "flame-speed", "6")
        out = capsys.readouterr().out
        assert "Error" in out

    async def test_brightness_invalid(self, capsys):
        client = AsyncMock()
        with pytest.raises(SystemExit):
            await cmd_set(client, FIRE_ID, "brightness", "medium")
        out = capsys.readouterr().out
        assert "Error" in out

    async def test_pulsating_invalid(self, capsys):
        client = AsyncMock()
        with pytest.raises(SystemExit):
            await cmd_set(client, FIRE_ID, "pulsating", "maybe")
        out = capsys.readouterr().out
        assert "Error" in out

    async def test_flame_color_invalid(self, capsys):
        client = AsyncMock()
        with pytest.raises(SystemExit):
            await cmd_set(client, FIRE_ID, "flame-color", "rainbow")
        out = capsys.readouterr().out
        assert "Error" in out

    async def test_media_theme_invalid(self, capsys):
        client = AsyncMock()
        with pytest.raises(SystemExit):
            await cmd_set(client, FIRE_ID, "media-theme", "neon")
        out = capsys.readouterr().out
        assert "Error" in out

    async def test_heat_mode_invalid(self, capsys):
        client = AsyncMock()
        with pytest.raises(SystemExit):
            await cmd_set(client, FIRE_ID, "heat-mode", "turbo")
        out = capsys.readouterr().out
        assert "Error" in out

    async def test_temp_unit_invalid(self, capsys):
        client = AsyncMock()
        with pytest.raises(SystemExit):
            await cmd_set(client, FIRE_ID, "temp-unit", "kelvin")
        out = capsys.readouterr().out
        assert "Error" in out

    async def test_timer_negative(self, capsys):
        client = AsyncMock()
        with pytest.raises(SystemExit):
            await cmd_set(client, FIRE_ID, "timer", "-5")
        out = capsys.readouterr().out
        assert "Error" in out

    async def test_flame_effect_invalid(self, capsys):
        client = AsyncMock()
        with pytest.raises(SystemExit):
            await cmd_set(client, FIRE_ID, "flame-effect", "maybe")
        out = capsys.readouterr().out
        assert "Error" in out

    async def test_media_light_invalid(self, capsys):
        client = AsyncMock()
        with pytest.raises(SystemExit):
            await cmd_set(client, FIRE_ID, "media-light", "maybe")
        out = capsys.readouterr().out
        assert "Error" in out

    async def test_media_color_invalid(self, capsys):
        client = AsyncMock()
        with pytest.raises(SystemExit):
            await cmd_set(client, FIRE_ID, "media-color", "not-a-color")
        out = capsys.readouterr().out
        assert "Error" in out

    async def test_overhead_light_invalid(self, capsys):
        client = AsyncMock()
        with pytest.raises(SystemExit):
            await cmd_set(client, FIRE_ID, "overhead-light", "maybe")
        out = capsys.readouterr().out
        assert "Error" in out

    async def test_overhead_color_invalid(self, capsys):
        client = AsyncMock()
        with pytest.raises(SystemExit):
            await cmd_set(client, FIRE_ID, "overhead-color", "not-a-color")
        out = capsys.readouterr().out
        assert "Error" in out

    async def test_ambient_sensor_invalid(self, capsys):
        client = AsyncMock()
        with pytest.raises(SystemExit):
            await cmd_set(client, FIRE_ID, "ambient-sensor", "maybe")
        out = capsys.readouterr().out
        assert "Error" in out


# ===================================================================
# _set_mode edge cases
# ===================================================================


class TestSetModeEdgeCases:
    """Tests for _set_mode when no ModeParam exists (uses default temp)."""

    async def test_mode_manual_no_existing_mode(self, capsys):
        """When no ModeParam exists, default temperature 22.0 is used."""
        client = AsyncMock()
        overview = FireOverview(fire=_make_fire(), parameters=[])
        client.get_fire_overview.return_value = overview
        await cmd_set(client, FIRE_ID, "mode", "manual")
        out = capsys.readouterr().out
        assert "Mode set to manual" in out
        # write_parameters should have been called
        client.write_parameters.assert_awaited_once()


# ===================================================================
# _set_heat_mode edge cases
# ===================================================================


class TestSetHeatModeEdgeCases:
    """Tests for _set_heat_mode special cases."""

    async def test_boost_with_duration(self, capsys):
        client = AsyncMock()
        overview = FireOverview(
            fire=_make_fire(), parameters=[_make_heat_param()]
        )
        client.get_fire_overview.return_value = overview
        await cmd_set(client, FIRE_ID, "heat-mode", "boost:15")
        out = capsys.readouterr().out
        assert "Heat mode set to boost:15" in out

    async def test_boost_duration_too_high(self, capsys):
        client = AsyncMock()
        with pytest.raises(SystemExit):
            await cmd_set(client, FIRE_ID, "heat-mode", "boost:21")
        out = capsys.readouterr().out
        assert "Error" in out

    async def test_boost_duration_too_low(self, capsys):
        client = AsyncMock()
        with pytest.raises(SystemExit):
            await cmd_set(client, FIRE_ID, "heat-mode", "boost:0")
        out = capsys.readouterr().out
        assert "Error" in out

    async def test_boost_duration_bad_format(self, capsys):
        client = AsyncMock()
        with pytest.raises(SystemExit):
            await cmd_set(client, FIRE_ID, "heat-mode", "boost:abc")
        out = capsys.readouterr().out
        assert "Error" in out


# ===================================================================
# _set_timer edge cases
# ===================================================================


class TestSetTimerEdgeCases:
    """Tests for _set_timer disable flow."""

    async def test_timer_disable(self, capsys):
        client = AsyncMock()
        await cmd_set(client, FIRE_ID, "timer", "0")
        out = capsys.readouterr().out
        assert "Timer disabled" in out


# ===================================================================
# _set_heat_temp with temp suffix
# ===================================================================


class TestSetHeatTempSuffix:
    """Tests for _set_heat_temp displaying correct temp suffix."""

    async def test_heat_temp_with_celsius_suffix(self, capsys):
        client = AsyncMock()
        overview = FireOverview(
            fire=_make_fire(),
            parameters=[
                _make_heat_param(),
                TempUnitParam(unit=TempUnit.CELSIUS),
            ],
        )
        client.get_fire_overview.return_value = overview
        await cmd_set(client, FIRE_ID, "heat-temp", "25.0")
        out = capsys.readouterr().out
        assert "25.0\u00b0C" in out

    async def test_heat_temp_with_fahrenheit_suffix(self, capsys):
        client = AsyncMock()
        overview = FireOverview(
            fire=_make_fire(),
            parameters=[
                _make_heat_param(),
                TempUnitParam(unit=TempUnit.FAHRENHEIT),
            ],
        )
        client.get_fire_overview.return_value = overview
        await cmd_set(client, FIRE_ID, "heat-temp", "25.0")
        out = capsys.readouterr().out
        assert "25.0\u00b0F" in out


# ===================================================================
# build_parser tests
# ===================================================================


class TestBuildParser:
    """Tests for build_parser()."""

    def test_parser_created(self):
        parser = build_parser()
        assert parser.prog == "flameconnect"

    def test_parse_list(self):
        parser = build_parser()
        args = parser.parse_args(["list"])
        assert args.command == "list"

    def test_parse_status(self):
        parser = build_parser()
        args = parser.parse_args(["status", "my-fire"])
        assert args.command == "status"
        assert args.fire_id == "my-fire"

    def test_parse_on(self):
        parser = build_parser()
        args = parser.parse_args(["on", "my-fire"])
        assert args.command == "on"
        assert args.fire_id == "my-fire"

    def test_parse_off(self):
        parser = build_parser()
        args = parser.parse_args(["off", "my-fire"])
        assert args.command == "off"
        assert args.fire_id == "my-fire"

    def test_parse_set(self):
        parser = build_parser()
        args = parser.parse_args(["set", "my-fire", "mode", "manual"])
        assert args.command == "set"
        assert args.fire_id == "my-fire"
        assert args.param == "mode"
        assert args.value == "manual"

    def test_parse_tui(self):
        parser = build_parser()
        args = parser.parse_args(["tui"])
        assert args.command == "tui"

    def test_parse_verbose(self):
        parser = build_parser()
        args = parser.parse_args(["-v", "list"])
        assert args.verbose is True

    def test_parse_no_verbose(self):
        parser = build_parser()
        args = parser.parse_args(["list"])
        assert args.verbose is False

    def test_no_command(self):
        parser = build_parser()
        args = parser.parse_args([])
        assert args.command is None


# ===================================================================
# async_main tests
# ===================================================================


class TestAsyncMain:
    """Tests for async_main() dispatch."""

    async def test_tui_command(self):
        args = argparse.Namespace(command="tui", verbose=False)
        with patch("flameconnect.cli.cmd_tui", new_callable=AsyncMock) as mock_tui:
            await async_main(args)
            mock_tui.assert_awaited_once_with(verbose=False)

    async def test_none_command_runs_tui(self):
        args = argparse.Namespace(command=None, verbose=False)
        with patch("flameconnect.cli.cmd_tui", new_callable=AsyncMock) as mock_tui:
            await async_main(args)
            mock_tui.assert_awaited_once_with(verbose=False)

    async def test_list_command(self):
        args = argparse.Namespace(command="list", verbose=False)
        mock_client = AsyncMock()
        mock_client.get_fires.return_value = []
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("flameconnect.cli.MsalAuth"), \
             patch("flameconnect.cli.FlameConnectClient", return_value=mock_client):
            await async_main(args)
        mock_client.get_fires.assert_awaited_once()

    async def test_status_command(self):
        args = argparse.Namespace(command="status", fire_id=FIRE_ID, verbose=False)
        mock_client = AsyncMock()
        overview = FireOverview(fire=_make_fire(), parameters=[])
        mock_client.get_fire_overview.return_value = overview
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("flameconnect.cli.MsalAuth"), \
             patch("flameconnect.cli.FlameConnectClient", return_value=mock_client):
            await async_main(args)
        mock_client.get_fire_overview.assert_awaited_once_with(FIRE_ID)

    async def test_on_command(self):
        args = argparse.Namespace(command="on", fire_id=FIRE_ID, verbose=False)
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("flameconnect.cli.MsalAuth"), \
             patch("flameconnect.cli.FlameConnectClient", return_value=mock_client):
            await async_main(args)
        mock_client.turn_on.assert_awaited_once_with(FIRE_ID)

    async def test_off_command(self):
        args = argparse.Namespace(command="off", fire_id=FIRE_ID, verbose=False)
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("flameconnect.cli.MsalAuth"), \
             patch("flameconnect.cli.FlameConnectClient", return_value=mock_client):
            await async_main(args)
        mock_client.turn_off.assert_awaited_once_with(FIRE_ID)

    async def test_set_command(self):
        args = argparse.Namespace(
            command="set",
            fire_id=FIRE_ID,
            param="temp-unit",
            value="celsius",
            verbose=False,
        )
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("flameconnect.cli.MsalAuth"), \
             patch("flameconnect.cli.FlameConnectClient", return_value=mock_client):
            await async_main(args)
        mock_client.write_parameters.assert_awaited_once()

    async def test_tui_verbose(self):
        args = argparse.Namespace(command="tui", verbose=True)
        with patch("flameconnect.cli.cmd_tui", new_callable=AsyncMock) as mock_tui:
            await async_main(args)
            mock_tui.assert_awaited_once_with(verbose=True)


# ===================================================================
# main() entry point tests
# ===================================================================


class TestMain:
    """Tests for the synchronous main() entry point."""

    def test_main_calls_async_main(self):
        with patch("flameconnect.cli.build_parser") as mock_parser_fn, \
             patch("flameconnect.cli.asyncio") as mock_asyncio:
            mock_parser = MagicMock()
            mock_args = argparse.Namespace(command="list", verbose=False)
            mock_parser.parse_args.return_value = mock_args
            mock_parser_fn.return_value = mock_parser

            main()

            mock_asyncio.run.assert_called_once()

    def test_main_verbose_logging(self):
        with patch("flameconnect.cli.build_parser") as mock_parser_fn, \
             patch("flameconnect.cli.asyncio"), \
             patch("flameconnect.cli.logging") as mock_logging:
            import logging as real_logging

            mock_parser = MagicMock()
            mock_args = argparse.Namespace(command="list", verbose=True)
            mock_parser.parse_args.return_value = mock_args
            mock_parser_fn.return_value = mock_parser
            mock_logging.DEBUG = real_logging.DEBUG
            mock_logging.WARNING = real_logging.WARNING

            main()

            mock_logging.basicConfig.assert_called_once_with(
                level=real_logging.DEBUG
            )

    def test_main_no_verbose_logging(self):
        with patch("flameconnect.cli.build_parser") as mock_parser_fn, \
             patch("flameconnect.cli.asyncio"), \
             patch("flameconnect.cli.logging") as mock_logging:
            import logging as real_logging

            mock_parser = MagicMock()
            mock_args = argparse.Namespace(command="list", verbose=False)
            mock_parser.parse_args.return_value = mock_args
            mock_parser_fn.return_value = mock_parser
            mock_logging.DEBUG = real_logging.DEBUG
            mock_logging.WARNING = real_logging.WARNING

            main()

            mock_logging.basicConfig.assert_called_once_with(
                level=real_logging.WARNING
            )


# ===================================================================
# cmd_tui tests
# ===================================================================


class TestCmdTui:
    """Tests for cmd_tui()."""

    async def test_tui_import_error(self, capsys):
        from flameconnect.cli import cmd_tui

        with (
            patch.dict("sys.modules", {"flameconnect.tui": None}),
            patch("builtins.__import__", side_effect=ImportError("no tui")),
            pytest.raises(SystemExit),
        ):
            await cmd_tui()

    async def test_tui_runs(self):
        from flameconnect.cli import cmd_tui

        mock_run_tui = AsyncMock()
        mock_module = MagicMock()
        mock_module.run_tui = mock_run_tui

        with patch.dict("sys.modules", {"flameconnect.tui": mock_module}):
            await cmd_tui(verbose=True)
        mock_run_tui.assert_awaited_once_with(verbose=True)


# ===================================================================
# _masked_input tests
# ===================================================================


class TestMaskedInput:
    """Tests for _masked_input() terminal password reading.

    termios and tty are imported *inside* _masked_input, so we need to
    patch them in the modules dict before calling the function.
    """

    @staticmethod
    def _run_masked(chars: list[str], prompt: str = "Password: ") -> str:
        """Helper to run _masked_input with mocked terminal I/O."""
        from flameconnect.cli import _masked_input

        mock_stdin = MagicMock()
        mock_stdout = MagicMock()
        mock_stdin.read.side_effect = chars
        mock_stdin.fileno.return_value = 0

        mock_termios = MagicMock()
        mock_termios.tcgetattr.return_value = []
        mock_termios.TCSADRAIN = 1
        mock_tty = MagicMock()

        with patch("sys.stdin", mock_stdin), \
             patch("sys.stdout", mock_stdout), \
             patch.dict("sys.modules", {"termios": mock_termios, "tty": mock_tty}):
            return _masked_input(prompt)

    def test_basic_input(self):
        assert self._run_masked(["a", "b", "c", "\n"]) == "abc"

    def test_backspace(self):
        assert self._run_masked(["a", "b", "\x7f", "c", "\n"]) == "ac"

    def test_backspace_on_empty(self):
        assert self._run_masked(["\x7f", "a", "\n"]) == "a"

    def test_ctrl_c(self):
        from flameconnect.cli import _masked_input

        mock_stdin = MagicMock()
        mock_stdout = MagicMock()
        mock_stdin.read.side_effect = ["\x03"]
        mock_stdin.fileno.return_value = 0

        mock_termios = MagicMock()
        mock_termios.tcgetattr.return_value = []
        mock_termios.TCSADRAIN = 1
        mock_tty = MagicMock()

        with (
            patch("sys.stdin", mock_stdin),
            patch("sys.stdout", mock_stdout),
            patch.dict("sys.modules", {"termios": mock_termios, "tty": mock_tty}),
            pytest.raises(KeyboardInterrupt),
        ):
            _masked_input()

    def test_carriage_return(self):
        assert self._run_masked(["x", "\r"]) == "x"

    def test_delete_char(self):
        # \x08 is the other backspace/delete code
        assert self._run_masked(["a", "b", "\x08", "c", "\n"]) == "ac"


# ===================================================================
# _cli_auth_prompt tests
# ===================================================================


class TestCliAuthPrompt:
    """Tests for _cli_auth_prompt().

    b2c_login_with_credentials is imported inside the function from
    flameconnect.b2c_login, so we patch it there.
    """

    async def test_successful_direct_login(self, capsys):
        from flameconnect.cli import _cli_auth_prompt

        with (
            patch(
                "flameconnect.cli.asyncio.to_thread",
                new_callable=AsyncMock,
            ) as mock_thread,
            patch(
                "flameconnect.b2c_login.b2c_login_with_credentials",
                new_callable=AsyncMock,
            ) as mock_b2c,
        ):
            # First call: email input, second call: password input
            mock_thread.side_effect = ["user@test.com", "secret123"]
            mock_b2c.return_value = "https://redirect.example.com/?code=ABC123"

            result = await _cli_auth_prompt(
                "https://auth.example.com", "https://redirect.example.com"
            )

        assert result == "https://redirect.example.com/?code=ABC123"
        out = capsys.readouterr().out
        assert "Login successful" in out

    async def test_fallback_to_browser(self, capsys):
        from flameconnect.cli import _cli_auth_prompt
        from flameconnect.exceptions import AuthenticationError

        with (
            patch(
                "flameconnect.cli.asyncio.to_thread",
                new_callable=AsyncMock,
            ) as mock_thread,
            patch(
                "flameconnect.b2c_login.b2c_login_with_credentials",
                new_callable=AsyncMock,
            ) as mock_b2c,
            patch("flameconnect.cli.webbrowser.open") as mock_open,
        ):
            # input calls: email, password, then final paste URL
            mock_thread.side_effect = [
                "user@test.com",
                "wrong_password",
                "https://redirect.example.com/?code=XYZ",
            ]
            mock_b2c.side_effect = AuthenticationError("bad credentials")

            result = await _cli_auth_prompt(
                "https://auth.example.com", "https://redirect.example.com"
            )

        assert result == "https://redirect.example.com/?code=XYZ"
        mock_open.assert_called_once_with("https://auth.example.com")
        out = capsys.readouterr().out
        assert "Direct login failed" in out
        assert "browser" in out.lower()


# ===================================================================
# _parse_color edge cases (supplementary to test_cli_set.py)
# ===================================================================


class TestParseColorExtra:
    """Additional edge cases for _parse_color."""

    def test_non_numeric_rgbw(self):
        from flameconnect.cli import _parse_color

        assert _parse_color("a,b,c,d") is None

    def test_negative_values(self):
        from flameconnect.cli import _parse_color

        assert _parse_color("-1,0,0,0") is None

    def test_five_components(self):
        from flameconnect.cli import _parse_color

        assert _parse_color("1,2,3,4,5") is None

    def test_valid_boundary(self):
        from flameconnect.cli import _parse_color

        result = _parse_color("0,0,0,0")
        assert result == RGBWColor(red=0, green=0, blue=0, white=0)

    def test_max_boundary(self):
        from flameconnect.cli import _parse_color

        result = _parse_color("255,255,255,255")
        assert result == RGBWColor(red=255, green=255, blue=255, white=255)


# ===================================================================
# cmd_status with various parameter types
# ===================================================================


class TestCmdStatusAllParams:
    """Test cmd_status with all parameter types to ensure full display coverage."""

    async def test_all_parameter_types(self, capsys):
        """Ensure cmd_status displays all parameter types correctly."""
        client = AsyncMock()
        params: list[Parameter] = [
            _make_mode_param(),
            _make_flame_effect_param(),
            _make_heat_param(),
            HeatModeParam(heat_control=HeatControl.ENABLED),
            TimerParam(timer_status=TimerStatus.ENABLED, duration=60),
            SoftwareVersionParam(
                ui_major=1, ui_minor=0, ui_test=0,
                control_major=2, control_minor=0, control_test=0,
                relay_major=3, relay_minor=0, relay_test=0,
            ),
            ErrorParam(error_byte1=0, error_byte2=0, error_byte3=0, error_byte4=0),
            TempUnitParam(unit=TempUnit.CELSIUS),
            SoundParam(volume=100, sound_file=1),
            LogEffectParam(log_effect=LogEffect.ON, color=_DEFAULT_RGBW, pattern=2),
        ]
        overview = FireOverview(fire=_make_fire(), parameters=params)
        client.get_fire_overview.return_value = overview

        await cmd_status(client, FIRE_ID)
        out = capsys.readouterr().out

        assert "10 parameter(s)" in out
        assert "[321] Mode" in out
        assert "[322] Flame Effect" in out
        assert "[323] Heat Settings" in out
        assert "[325] Heat Mode" in out
        assert "[326] Timer Mode" in out
        assert "[327] Software Version" in out
        assert "[329] Error" in out
        assert "[236] Temperature Unit" in out
        assert "[369] Sound" in out
        assert "[370] Log Effect" in out
