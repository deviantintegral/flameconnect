"""Tests for TUI keybinding action methods in FlameConnectApp."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest
from textual.app import App

from flameconnect.models import (
    Brightness,
    ConnectionState,
    Fire,
    FireMode,
    FlameColor,
    FlameEffect,
    FlameEffectParam,
    HeatMode,
    HeatParam,
    HeatStatus,
    LightStatus,
    MediaTheme,
    ModeParam,
    PulsatingEffect,
    RGBWColor,
    TempUnit,
    TempUnitParam,
    TimerParam,
    TimerStatus,
)
from flameconnect.tui.app import FlameConnectApp, _resolve_version
from flameconnect.tui.screens import DashboardScreen

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_DEFAULT_FLAME_EFFECT = FlameEffectParam(
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

_DEFAULT_HEAT = HeatParam(
    heat_status=HeatStatus.ON,
    heat_mode=HeatMode.NORMAL,
    setpoint_temperature=22.0,
    boost_duration=1,
)

_DEFAULT_TIMER = TimerParam(
    timer_status=TimerStatus.DISABLED,
    duration=0,
)

_DEFAULT_TEMP_UNIT = TempUnitParam(unit=TempUnit.CELSIUS)

_TEST_FIRE = Fire(
    fire_id="test-fire-001",
    friendly_name="Test Fire",
    brand="TestBrand",
    product_type="Electric",
    product_model="TM-100",
    item_code="TB-001",
    connection_state=ConnectionState.CONNECTED,
    with_heat=True,
    is_iot_fire=True,
)

_TEST_FIRE_2 = Fire(
    fire_id="test-fire-002",
    friendly_name="Second Fire",
    brand="TestBrand",
    product_type="Electric",
    product_model="TM-200",
    item_code="TB-002",
    connection_state=ConnectionState.CONNECTED,
    with_heat=True,
    is_iot_fire=True,
)


@pytest.fixture
def mock_client():
    """Return an AsyncMock client with write_parameters stubbed."""
    client = AsyncMock()
    client.write_parameters = AsyncMock()
    return client


@pytest.fixture
def mock_dashboard():
    """Return a mock DashboardScreen with current_parameters and helpers."""
    screen = MagicMock(spec=DashboardScreen)
    screen.log_message = MagicMock()
    screen.refresh_state = AsyncMock()
    screen.current_parameters = {
        FlameEffectParam: _DEFAULT_FLAME_EFFECT,
        HeatParam: _DEFAULT_HEAT,
        TimerParam: _DEFAULT_TIMER,
        TempUnitParam: _DEFAULT_TEMP_UNIT,
    }
    return screen


def _make_app(mock_client, mock_dashboard):
    """Create a FlameConnectApp wired to the mock client and dashboard.

    We avoid actually running the Textual app; instead we set up the
    instance fields that the action methods rely on and patch
    ``app.screen`` to return the mock dashboard.

    ``run_worker`` is mocked to capture the worker coroutine.
    Use ``await _run_workers(app)`` to execute captured workers.
    """
    app = FlameConnectApp.__new__(FlameConnectApp)
    app.client = mock_client
    app.fire_id = "test-fire-001"
    app._write_in_progress = False
    app._captured_workers: list = []

    def _capture_worker(coro, **kwargs):
        app._captured_workers.append(coro)
        return MagicMock()

    app.run_worker = _capture_worker
    return app


async def _run_workers(app):
    """Execute all captured workers from _run_command calls."""
    for coro in app._captured_workers:
        await coro
    app._captured_workers.clear()


# ---------------------------------------------------------------------------
# _apply_flame_speed (called via FlameSpeedScreen dialog)
# ---------------------------------------------------------------------------


class TestApplyFlameSpeed:
    """Tests for FlameConnectApp._apply_flame_speed."""

    async def test_sets_speed_to_4(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app._apply_flame_speed(4)
            await _run_workers(app)

        mock_client.write_parameters.assert_awaited_once()
        call_args = mock_client.write_parameters.call_args
        assert call_args[0][0] == "test-fire-001"
        written_param = call_args[0][1][0]
        assert isinstance(written_param, FlameEffectParam)
        assert written_param.flame_speed == 4

    async def test_sets_speed_to_1(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app._apply_flame_speed(1)
            await _run_workers(app)

        written_param = mock_client.write_parameters.call_args[0][1][0]
        assert written_param.flame_speed == 1

    async def test_no_op_when_no_fire_id(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.fire_id = None

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app._apply_flame_speed(3)
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_no_op_when_write_in_progress(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app._write_in_progress = True

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app._apply_flame_speed(3)
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_no_op_when_no_flame_param(self, mock_client, mock_dashboard):
        del mock_dashboard.current_parameters[FlameEffectParam]
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app._apply_flame_speed(3)
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()


# ---------------------------------------------------------------------------
# action_toggle_brightness
# ---------------------------------------------------------------------------


class TestToggleBrightness:
    """Tests for FlameConnectApp.action_toggle_brightness."""

    async def test_toggles_low_to_high(self, mock_client, mock_dashboard):
        # Default fixture has brightness LOW
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_brightness()
            await _run_workers(app)

        written_param = mock_client.write_parameters.call_args[0][1][0]
        assert isinstance(written_param, FlameEffectParam)
        assert written_param.brightness == Brightness.HIGH

    async def test_toggles_high_to_low(self, mock_client, mock_dashboard):
        mock_dashboard.current_parameters[FlameEffectParam] = FlameEffectParam(
            flame_effect=FlameEffect.ON,
            flame_speed=3,
            brightness=Brightness.HIGH,
            pulsating_effect=PulsatingEffect.OFF,
            media_theme=MediaTheme.KALEIDOSCOPE,
            media_light=LightStatus.ON,
            media_color=RGBWColor(red=0, green=0, blue=0, white=0),
            overhead_light=LightStatus.OFF,
            overhead_color=RGBWColor(red=0, green=0, blue=0, white=0),
            light_status=LightStatus.OFF,
            flame_color=FlameColor.ALL,
            ambient_sensor=LightStatus.OFF,
        )
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_brightness()
            await _run_workers(app)

        written_param = mock_client.write_parameters.call_args[0][1][0]
        assert written_param.brightness == Brightness.LOW

    async def test_refreshes_after_write(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_brightness()
            await _run_workers(app)

        mock_dashboard.refresh_state.assert_awaited_once()

    async def test_clears_write_flag_on_success(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_brightness()
            await _run_workers(app)

        assert app._write_in_progress is False


# ---------------------------------------------------------------------------
# _apply_heat_mode
# ---------------------------------------------------------------------------


class TestApplyHeatMode:
    """Tests for FlameConnectApp._apply_heat_mode."""

    async def test_sets_normal_mode(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app._apply_heat_mode(HeatMode.NORMAL, None)
            await _run_workers(app)

        written_param = mock_client.write_parameters.call_args[0][1][0]
        assert isinstance(written_param, HeatParam)
        assert written_param.heat_mode == HeatMode.NORMAL

    async def test_sets_eco_mode(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app._apply_heat_mode(HeatMode.ECO, None)
            await _run_workers(app)

        written_param = mock_client.write_parameters.call_args[0][1][0]
        assert isinstance(written_param, HeatParam)
        assert written_param.heat_mode == HeatMode.ECO

    async def test_sets_boost_with_duration(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app._apply_heat_mode(HeatMode.BOOST, 15)
            await _run_workers(app)

        written_param = mock_client.write_parameters.call_args[0][1][0]
        assert isinstance(written_param, HeatParam)
        assert written_param.heat_mode == HeatMode.BOOST
        assert written_param.boost_duration == 15

    async def test_no_op_when_no_heat_param(self, mock_client, mock_dashboard):
        del mock_dashboard.current_parameters[HeatParam]
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app._apply_heat_mode(HeatMode.NORMAL, None)
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_no_op_when_no_fire_id(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.fire_id = None

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app._apply_heat_mode(HeatMode.ECO, None)
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_no_op_when_write_in_progress(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app._write_in_progress = True

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app._apply_heat_mode(HeatMode.ECO, None)
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()


# ---------------------------------------------------------------------------
# action_toggle_timer
# ---------------------------------------------------------------------------


class TestToggleTimer:
    """Tests for FlameConnectApp.action_toggle_timer."""

    async def test_enables_timer_when_disabled(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_timer()
            await _run_workers(app)

        written_param = mock_client.write_parameters.call_args[0][1][0]
        assert isinstance(written_param, TimerParam)
        assert written_param.timer_status == TimerStatus.ENABLED
        assert written_param.duration == 60

    async def test_disables_timer_when_enabled(self, mock_client, mock_dashboard):
        mock_dashboard.current_parameters[TimerParam] = TimerParam(
            timer_status=TimerStatus.ENABLED,
            duration=120,
        )
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_timer()
            await _run_workers(app)

        written_param = mock_client.write_parameters.call_args[0][1][0]
        assert written_param.timer_status == TimerStatus.DISABLED
        assert written_param.duration == 0

    async def test_logs_disable_message(self, mock_client, mock_dashboard):
        mock_dashboard.current_parameters[TimerParam] = TimerParam(
            timer_status=TimerStatus.ENABLED,
            duration=60,
        )
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_timer()
            await _run_workers(app)

        mock_dashboard.log_message.assert_any_call("Disabling timer...")

    async def test_logs_enable_message(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_timer()
            await _run_workers(app)

        mock_dashboard.log_message.assert_any_call("Enabling timer (60 min)...")


# ---------------------------------------------------------------------------
# action_toggle_temp_unit
# ---------------------------------------------------------------------------


class TestToggleTempUnit:
    """Tests for FlameConnectApp.action_toggle_temp_unit."""

    async def test_toggles_celsius_to_fahrenheit(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_temp_unit()
            await _run_workers(app)

        written_param = mock_client.write_parameters.call_args[0][1][0]
        assert isinstance(written_param, TempUnitParam)
        assert written_param.unit == TempUnit.FAHRENHEIT

    async def test_toggles_fahrenheit_to_celsius(self, mock_client, mock_dashboard):
        mock_dashboard.current_parameters[TempUnitParam] = TempUnitParam(
            unit=TempUnit.FAHRENHEIT,
        )
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_temp_unit()
            await _run_workers(app)

        written_param = mock_client.write_parameters.call_args[0][1][0]
        assert written_param.unit == TempUnit.CELSIUS

    async def test_refreshes_and_clears_flag(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_temp_unit()
            await _run_workers(app)

        mock_dashboard.refresh_state.assert_awaited_once()
        assert app._write_in_progress is False

    async def test_logs_unit_message(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_temp_unit()
            await _run_workers(app)

        mock_dashboard.log_message.assert_any_call(
            "Setting temperature unit to Fahrenheit..."
        )

    async def test_no_op_when_no_temp_unit_param(self, mock_client, mock_dashboard):
        del mock_dashboard.current_parameters[TempUnitParam]
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_temp_unit()
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()


# ---------------------------------------------------------------------------
# action_toggle_flame_effect
# ---------------------------------------------------------------------------


class TestToggleFlameEffect:
    """Tests for FlameConnectApp.action_toggle_flame_effect."""

    async def test_toggles_on_to_off(self, mock_client, mock_dashboard):
        # Default fixture has flame_effect ON
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_flame_effect()
            await _run_workers(app)

        written_param = mock_client.write_parameters.call_args[0][1][0]
        assert isinstance(written_param, FlameEffectParam)
        assert written_param.flame_effect == FlameEffect.OFF

    async def test_no_op_when_write_in_progress(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app._write_in_progress = True

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_flame_effect()
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()


# ---------------------------------------------------------------------------
# action_toggle_pulsating
# ---------------------------------------------------------------------------


class TestTogglePulsating:
    """Tests for FlameConnectApp.action_toggle_pulsating."""

    async def test_toggles_off_to_on(self, mock_client, mock_dashboard):
        # Default fixture has pulsating_effect OFF
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_pulsating()
            await _run_workers(app)

        written_param = mock_client.write_parameters.call_args[0][1][0]
        assert isinstance(written_param, FlameEffectParam)
        assert written_param.pulsating_effect == PulsatingEffect.ON

    async def test_no_op_when_write_in_progress(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app._write_in_progress = True

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_pulsating()
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()


# ---------------------------------------------------------------------------
# action_toggle_media_light
# ---------------------------------------------------------------------------


class TestToggleMediaLight:
    """Tests for FlameConnectApp.action_toggle_media_light."""

    async def test_toggles_on_to_off(self, mock_client, mock_dashboard):
        # Default fixture has media_light ON
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_media_light()
            await _run_workers(app)

        written_param = mock_client.write_parameters.call_args[0][1][0]
        assert isinstance(written_param, FlameEffectParam)
        assert written_param.media_light == LightStatus.OFF

    async def test_no_op_when_write_in_progress(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app._write_in_progress = True

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_media_light()
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()


# ---------------------------------------------------------------------------
# action_toggle_overhead_light
# ---------------------------------------------------------------------------


class TestToggleOverheadLight:
    """Tests for FlameConnectApp.action_toggle_overhead_light."""

    async def test_toggles_on_to_off(self, mock_client, mock_dashboard):
        # Default fixture has overhead_light ON
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_overhead_light()
            await _run_workers(app)

        written_param = mock_client.write_parameters.call_args[0][1][0]
        assert isinstance(written_param, FlameEffectParam)
        assert written_param.light_status == LightStatus.OFF

    async def test_no_op_when_write_in_progress(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app._write_in_progress = True

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_overhead_light()
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()


# ---------------------------------------------------------------------------
# action_toggle_ambient_sensor
# ---------------------------------------------------------------------------


class TestToggleAmbientSensor:
    """Tests for FlameConnectApp.action_toggle_ambient_sensor."""

    async def test_toggles_off_to_on(self, mock_client, mock_dashboard):
        # Default fixture has ambient_sensor OFF
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_ambient_sensor()
            await _run_workers(app)

        written_param = mock_client.write_parameters.call_args[0][1][0]
        assert isinstance(written_param, FlameEffectParam)
        assert written_param.ambient_sensor == LightStatus.ON

    async def test_no_op_when_write_in_progress(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app._write_in_progress = True

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_ambient_sensor()
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()


# ---------------------------------------------------------------------------
# _apply_flame_color
# ---------------------------------------------------------------------------


class TestApplyFlameColor:
    """Tests for FlameConnectApp._apply_flame_color."""

    async def test_sets_flame_color(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app._apply_flame_color(FlameColor.BLUE)
            await _run_workers(app)

        written_param = mock_client.write_parameters.call_args[0][1][0]
        assert isinstance(written_param, FlameEffectParam)
        assert written_param.flame_color == FlameColor.BLUE

    async def test_no_op_when_write_in_progress(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app._write_in_progress = True

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app._apply_flame_color(FlameColor.BLUE)
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()


# ---------------------------------------------------------------------------
# _apply_media_theme
# ---------------------------------------------------------------------------


class TestApplyMediaTheme:
    """Tests for FlameConnectApp._apply_media_theme."""

    async def test_sets_media_theme(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app._apply_media_theme(MediaTheme.BLUE)
            await _run_workers(app)

        written_param = mock_client.write_parameters.call_args[0][1][0]
        assert isinstance(written_param, FlameEffectParam)
        assert written_param.media_theme == MediaTheme.BLUE

    async def test_no_op_when_write_in_progress(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app._write_in_progress = True

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app._apply_media_theme(MediaTheme.BLUE)
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()


# ---------------------------------------------------------------------------
# _apply_media_color
# ---------------------------------------------------------------------------


class TestApplyMediaColor:
    """Tests for FlameConnectApp._apply_media_color."""

    async def test_sets_media_color(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        color = RGBWColor(red=255, green=0, blue=0, white=0)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app._apply_media_color(color)
            await _run_workers(app)

        written_param = mock_client.write_parameters.call_args[0][1][0]
        assert isinstance(written_param, FlameEffectParam)
        assert written_param.media_color == RGBWColor(red=255, green=0, blue=0, white=0)

    async def test_no_op_when_write_in_progress(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app._write_in_progress = True

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app._apply_media_color(RGBWColor(red=255, green=0, blue=0, white=0))
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()


# ---------------------------------------------------------------------------
# _apply_overhead_color
# ---------------------------------------------------------------------------


class TestApplyOverheadColor:
    """Tests for FlameConnectApp._apply_overhead_color."""

    async def test_sets_overhead_color(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        color = RGBWColor(red=0, green=0, blue=255, white=80)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app._apply_overhead_color(color)
            await _run_workers(app)

        written_param = mock_client.write_parameters.call_args[0][1][0]
        assert isinstance(written_param, FlameEffectParam)
        assert written_param.overhead_color == RGBWColor(
            red=0, green=0, blue=255, white=80
        )

    async def test_no_op_when_write_in_progress(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app._write_in_progress = True

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app._apply_overhead_color(
                RGBWColor(red=0, green=0, blue=255, white=80)
            )
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestActionErrorHandling:
    """Test that action methods handle exceptions gracefully."""

    async def test_flame_speed_error_logs_and_clears_flag(
        self, mock_client, mock_dashboard
    ):
        mock_client.write_parameters.side_effect = Exception("API failure")
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app._apply_flame_speed(4)
            await _run_workers(app)

        assert app._write_in_progress is False
        # Check that an error was logged
        mock_dashboard.log_message.assert_called()
        log_call_args = [
            call.args[0] for call in mock_dashboard.log_message.call_args_list
        ]
        assert any("failed" in msg.lower() for msg in log_call_args)

    async def test_brightness_error_logs_and_clears_flag(
        self, mock_client, mock_dashboard
    ):
        mock_client.write_parameters.side_effect = Exception("network error")
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_brightness()
            await _run_workers(app)

        assert app._write_in_progress is False

    async def test_timer_error_logs_and_clears_flag(
        self, mock_client, mock_dashboard
    ):
        mock_client.write_parameters.side_effect = Exception("timeout")
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_timer()
            await _run_workers(app)

        assert app._write_in_progress is False

    async def test_temp_unit_error_logs_and_clears_flag(
        self, mock_client, mock_dashboard
    ):
        mock_client.write_parameters.side_effect = Exception("server error")
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_temp_unit()
            await _run_workers(app)

        assert app._write_in_progress is False


# ---------------------------------------------------------------------------
# DashboardScreen.current_parameters property
# ---------------------------------------------------------------------------


class TestDashboardCurrentParameters:
    """Test the current_parameters property on DashboardScreen."""

    def test_returns_copy_of_previous_params(self):
        screen = DashboardScreen.__new__(DashboardScreen)
        screen._previous_params = {
            FlameEffectParam: _DEFAULT_FLAME_EFFECT,
            HeatParam: _DEFAULT_HEAT,
        }
        result = screen.current_parameters
        assert result == screen._previous_params
        # Must be a copy, not the same dict
        assert result is not screen._previous_params

    def test_returns_empty_dict_when_no_params(self):
        screen = DashboardScreen.__new__(DashboardScreen)
        screen._previous_params = {}
        assert screen.current_parameters == {}


# ---------------------------------------------------------------------------
# action_set_heat_mode (dialog open)
# ---------------------------------------------------------------------------


class TestSetHeatModeDialog:
    """Tests for FlameConnectApp.action_set_heat_mode opening HeatModeScreen."""

    async def test_opens_heat_mode_screen(self, mock_client, mock_dashboard):
        """action_set_heat_mode pushes HeatModeScreen with current mode/boost."""
        from flameconnect.tui.heat_mode_screen import HeatModeScreen

        app = _make_app(mock_client, mock_dashboard)
        app.push_screen = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_set_heat_mode()

        app.push_screen.assert_called_once()
        call_args = app.push_screen.call_args
        screen_arg = call_args[0][0]
        assert isinstance(screen_arg, HeatModeScreen)
        # Verify callback was passed
        assert call_args[1].get("callback") is not None or len(call_args[0]) > 1

    async def test_no_op_when_no_heat_param(self, mock_client, mock_dashboard):
        """action_set_heat_mode does nothing if no HeatParam in parameters."""
        del mock_dashboard.current_parameters[HeatParam]
        app = _make_app(mock_client, mock_dashboard)
        app.push_screen = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_set_heat_mode()

        app.push_screen.assert_not_called()

    async def test_no_op_when_no_fire_id(self, mock_client, mock_dashboard):
        """action_set_heat_mode does nothing if no fire_id set."""
        app = _make_app(mock_client, mock_dashboard)
        app.fire_id = None
        app.push_screen = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_set_heat_mode()

        app.push_screen.assert_not_called()

    async def test_callback_defers_via_call_later(self, mock_client, mock_dashboard):
        """Dismiss callback uses call_later so _apply_heat_mode runs after modal pop."""
        app = _make_app(mock_client, mock_dashboard)
        app.push_screen = MagicMock()
        app.call_later = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_set_heat_mode()

        # Extract the callback passed to push_screen
        call_args = app.push_screen.call_args
        callback = call_args[1].get("callback") or call_args[0][1]

        # Simulate the dismiss callback with a NORMAL selection
        callback((HeatMode.NORMAL, None))

        # _apply_heat_mode should have been deferred via call_later
        app.call_later.assert_called_once_with(
            app._apply_heat_mode, HeatMode.NORMAL, None
        )


# ---------------------------------------------------------------------------
# action_switch_fire
# ---------------------------------------------------------------------------


class TestSwitchFire:
    """Tests for FlameConnectApp.action_switch_fire."""

    async def test_refetches_fires_and_opens_dialog(self, mock_client, mock_dashboard):
        """action_switch_fire calls get_fires and opens FireSelectScreen."""
        from flameconnect.tui.fire_select_screen import FireSelectScreen

        mock_client.get_fires = AsyncMock(
            return_value=[_TEST_FIRE, _TEST_FIRE_2],
        )
        app = _make_app(mock_client, mock_dashboard)
        app.fires = [_TEST_FIRE]
        app.push_screen = MagicMock()
        app.notify = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            await app.action_switch_fire()

        # Verify get_fires was called to refresh the list
        mock_client.get_fires.assert_awaited_once()
        # Verify the fire list was updated
        assert len(app.fires) == 2
        # Verify push_screen was called with FireSelectScreen
        app.push_screen.assert_called_once()
        call_args = app.push_screen.call_args
        screen_arg = call_args[0][0]
        assert isinstance(screen_arg, FireSelectScreen)

    async def test_single_fire_guard_notifies(self, mock_client, mock_dashboard):
        """action_switch_fire notifies user when only one fire available."""
        mock_client.get_fires = AsyncMock(return_value=[_TEST_FIRE])
        app = _make_app(mock_client, mock_dashboard)
        app.fires = [_TEST_FIRE]
        app.push_screen = MagicMock()
        app.notify = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            await app.action_switch_fire()

        # Verify notify was called with appropriate message
        app.notify.assert_called_once_with("Only one fireplace available")
        # Verify push_screen was NOT called (no dialog)
        app.push_screen.assert_not_called()

    async def test_no_fires_guard_notifies(self, mock_client, mock_dashboard):
        """action_switch_fire notifies user when no fires available."""
        mock_client.get_fires = AsyncMock(return_value=[])
        app = _make_app(mock_client, mock_dashboard)
        app.fires = []
        app.push_screen = MagicMock()
        app.notify = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            await app.action_switch_fire()

        # Verify notify was called
        app.notify.assert_called_once_with("Only one fireplace available")
        # Verify push_screen was NOT called
        app.push_screen.assert_not_called()

    async def test_get_fires_error_notifies(self, mock_client, mock_dashboard):
        """action_switch_fire handles get_fires failure gracefully."""
        mock_client.get_fires = AsyncMock(
            side_effect=Exception("network error"),
        )
        app = _make_app(mock_client, mock_dashboard)
        app.fires = [_TEST_FIRE]
        app.push_screen = MagicMock()
        app.notify = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            await app.action_switch_fire()

        # Verify error notification
        app.notify.assert_called_once()
        call_args = app.notify.call_args
        assert "Failed to load fireplaces" in call_args[0][0]
        # Verify push_screen was NOT called
        app.push_screen.assert_not_called()


# ---------------------------------------------------------------------------
# action_screenshot – ensures the Downloads directory is created
# ---------------------------------------------------------------------------


class TestDeliverScreenshot:
    """Tests for FlameConnectApp.deliver_screenshot."""

    def test_creates_downloads_dir_before_delivery(
        self, mock_client, mock_dashboard, tmp_path
    ):
        app = _make_app(mock_client, mock_dashboard)

        target = tmp_path / "nonexistent" / "downloads"
        with (
            patch(
                "platformdirs.user_downloads_path", return_value=target
            ),
            patch.object(
                App, "deliver_screenshot", return_value=None
            ) as super_deliver,
        ):
            app.deliver_screenshot()

        assert target.is_dir()
        super_deliver.assert_called_once_with(None, str(target), None)

    def test_explicit_path_is_created(self, mock_client, mock_dashboard, tmp_path):
        app = _make_app(mock_client, mock_dashboard)

        target = tmp_path / "custom" / "dir"
        with patch.object(
            App, "deliver_screenshot", return_value=None
        ) as super_deliver:
            app.deliver_screenshot(path=str(target))

        assert target.is_dir()
        super_deliver.assert_called_once_with(None, str(target), None)


# ---------------------------------------------------------------------------
# _resolve_version
# ---------------------------------------------------------------------------


class TestResolveVersion:
    """Tests for the _resolve_version helper function."""

    def test_returns_version_when_tag_matches(self):
        """When git tag matches __version__, return v{version}."""
        from flameconnect import __version__

        tag_result = MagicMock(returncode=0, stdout=f"v{__version__}\n")
        with patch("flameconnect.tui.app.subprocess.run", return_value=tag_result):
            result = _resolve_version()
        assert result == f"v{__version__}"

    def test_returns_short_hash_when_no_tag(self):
        """When no matching tag, return the short git hash."""
        tag_result = MagicMock(returncode=128, stdout="")
        hash_result = MagicMock(returncode=0, stdout="abc1234\n")
        status_result = MagicMock(returncode=0, stdout="")

        with patch(
            "flameconnect.tui.app.subprocess.run",
            side_effect=[tag_result, hash_result, status_result],
        ):
            result = _resolve_version()
        assert result == "abc1234"

    def test_returns_dirty_hash_when_uncommitted(self):
        """When working tree is dirty, append -dirty to the hash."""
        tag_result = MagicMock(returncode=128, stdout="")
        hash_result = MagicMock(returncode=0, stdout="abc1234\n")
        status_result = MagicMock(returncode=0, stdout="M some_file.py\n")

        with patch(
            "flameconnect.tui.app.subprocess.run",
            side_effect=[tag_result, hash_result, status_result],
        ):
            result = _resolve_version()
        assert result == "abc1234-dirty"

    def test_returns_version_when_hash_fails(self):
        """When git rev-parse fails, fall back to v{version}."""
        from flameconnect import __version__

        tag_result = MagicMock(returncode=128, stdout="")
        hash_result = MagicMock(returncode=128, stdout="")

        with patch(
            "flameconnect.tui.app.subprocess.run",
            side_effect=[tag_result, hash_result],
        ):
            result = _resolve_version()
        assert result == f"v{__version__}"

    def test_returns_version_on_exception(self):
        """When subprocess raises, fall back to v{version}."""
        from flameconnect import __version__

        with patch(
            "flameconnect.tui.app.subprocess.run",
            side_effect=FileNotFoundError("git not found"),
        ):
            result = _resolve_version()
        assert result == f"v{__version__}"


# ---------------------------------------------------------------------------
# FireplaceCommandsProvider
# ---------------------------------------------------------------------------


class TestFireplaceCommandsProvider:
    """Tests for the command palette provider."""

    async def test_search_yields_matching_commands(self):
        """search yields Hit objects for commands that match the query."""
        from flameconnect.tui.app import FireplaceCommandsProvider

        provider = FireplaceCommandsProvider.__new__(FireplaceCommandsProvider)

        # Mock the matcher method
        mock_matcher = MagicMock()
        mock_matcher.match = MagicMock(
            side_effect=lambda name: 80 if "Power" in name else 0
        )
        mock_matcher.highlight = MagicMock(return_value="Power On/Off")
        provider.matcher = MagicMock(return_value=mock_matcher)

        # app is a read-only property on Provider, so patch it
        with patch.object(type(provider), "app", new_callable=PropertyMock) as app_prop:
            app_prop.return_value = MagicMock()

            hits = []
            async for hit in provider.search("Power"):
                hits.append(hit)

        assert len(hits) == 1
        assert hits[0].score == 80

    async def test_search_yields_nothing_for_no_match(self):
        """search yields no hits when nothing matches."""
        from flameconnect.tui.app import FireplaceCommandsProvider

        provider = FireplaceCommandsProvider.__new__(FireplaceCommandsProvider)

        mock_matcher = MagicMock()
        mock_matcher.match = MagicMock(return_value=0)
        provider.matcher = MagicMock(return_value=mock_matcher)

        with patch.object(type(provider), "app", new_callable=PropertyMock) as app_prop:
            app_prop.return_value = MagicMock()

            hits = []
            async for hit in provider.search("zzzznonexistent"):
                hits.append(hit)

        assert len(hits) == 0

    def test_get_fireplace_commands_returns_provider(self):
        """_get_fireplace_commands returns the provider class."""
        from flameconnect.tui.app import (
            FireplaceCommandsProvider,
            _get_fireplace_commands,
        )

        assert _get_fireplace_commands() is FireplaceCommandsProvider


# ---------------------------------------------------------------------------
# FlameConnectApp.__init__
# ---------------------------------------------------------------------------


class TestFlameConnectAppInit:
    """Tests for FlameConnectApp constructor."""

    def test_init_sets_fields(self, mock_client):
        app = FlameConnectApp.__new__(FlameConnectApp)
        # Manually call __init__ with mocked super
        with patch.object(App, "__init__", return_value=None):
            app.__init__(mock_client)

        assert app.client is mock_client
        assert app.fire_id is None
        assert app.fires == []
        assert app._write_in_progress is False
        assert app._help_visible is False


# ---------------------------------------------------------------------------
# action_refresh
# ---------------------------------------------------------------------------


class TestActionRefresh:
    """Tests for FlameConnectApp.action_refresh."""

    async def test_refreshes_dashboard(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            await app.action_refresh()

        mock_dashboard.log_message.assert_any_call("Refreshing...")
        mock_dashboard.refresh_state.assert_awaited_once()
        mock_dashboard.log_message.assert_any_call("Refresh complete")

    async def test_no_op_when_not_dashboard(self, mock_client):
        """action_refresh does nothing when screen is not DashboardScreen."""
        app = _make_app(mock_client, MagicMock())
        non_dashboard = MagicMock(spec=[])  # no DashboardScreen spec

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = non_dashboard
            await app.action_refresh()

        # Should not have raised; log_message never called


# ---------------------------------------------------------------------------
# action_toggle_help
# ---------------------------------------------------------------------------


class TestActionToggleHelp:
    """Tests for FlameConnectApp.action_toggle_help."""

    def test_shows_help_when_hidden(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app._help_visible = False
        app.action_show_help_panel = MagicMock()
        app.action_hide_help_panel = MagicMock()

        app.action_toggle_help()

        app.action_show_help_panel.assert_called_once()
        app.action_hide_help_panel.assert_not_called()
        assert app._help_visible is True

    def test_hides_help_when_visible(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app._help_visible = True
        app.action_show_help_panel = MagicMock()
        app.action_hide_help_panel = MagicMock()

        app.action_toggle_help()

        app.action_hide_help_panel.assert_called_once()
        app.action_show_help_panel.assert_not_called()
        assert app._help_visible is False


# ---------------------------------------------------------------------------
# action_toggle_power
# ---------------------------------------------------------------------------


class TestActionTogglePower:
    """Tests for FlameConnectApp.action_toggle_power."""

    async def test_turns_off_when_manual(self, mock_client, mock_dashboard):
        """When current mode is MANUAL, should call turn_off."""
        mock_dashboard.current_mode = ModeParam(
            mode=FireMode.MANUAL, target_temperature=22.0
        )
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_power()
            await _run_workers(app)

        mock_client.turn_off.assert_awaited_once_with("test-fire-001")

    async def test_turns_on_when_standby(self, mock_client, mock_dashboard):
        """When current mode is STANDBY, should call turn_on."""
        mock_dashboard.current_mode = ModeParam(
            mode=FireMode.STANDBY, target_temperature=22.0
        )
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_power()
            await _run_workers(app)

        mock_client.turn_on.assert_awaited_once_with("test-fire-001")

    async def test_turns_on_when_mode_is_none(self, mock_client, mock_dashboard):
        """When current_mode is None, should call turn_on."""
        mock_dashboard.current_mode = None
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_power()
            await _run_workers(app)

        mock_client.turn_on.assert_awaited_once_with("test-fire-001")

    async def test_no_op_when_no_fire_id(self, mock_client, mock_dashboard):
        mock_dashboard.current_mode = None
        app = _make_app(mock_client, mock_dashboard)
        app.fire_id = None

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_power()
            await _run_workers(app)

        mock_client.turn_on.assert_not_awaited()
        mock_client.turn_off.assert_not_awaited()
        mock_dashboard.log_message.assert_called()

    async def test_no_op_when_write_in_progress(self, mock_client, mock_dashboard):
        mock_dashboard.current_mode = None
        app = _make_app(mock_client, mock_dashboard)
        app._write_in_progress = True

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_power()
            await _run_workers(app)

        mock_client.turn_on.assert_not_awaited()
        mock_client.turn_off.assert_not_awaited()

    async def test_no_op_when_not_dashboard(self, mock_client):
        non_dashboard = MagicMock(spec=[])
        app = _make_app(mock_client, non_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = non_dashboard
            app.action_toggle_power()
            await _run_workers(app)

        mock_client.turn_on.assert_not_awaited()
        mock_client.turn_off.assert_not_awaited()


# ---------------------------------------------------------------------------
# action_toggle_heat
# ---------------------------------------------------------------------------


class TestActionToggleHeat:
    """Tests for FlameConnectApp.action_toggle_heat."""

    async def test_toggles_on_to_off(self, mock_client, mock_dashboard):
        """When heat is ON, should toggle to OFF."""
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_heat()
            await _run_workers(app)

        written_param = mock_client.write_parameters.call_args[0][1][0]
        assert isinstance(written_param, HeatParam)
        assert written_param.heat_status == HeatStatus.OFF

    async def test_toggles_off_to_on(self, mock_client, mock_dashboard):
        """When heat is OFF, should toggle to ON."""
        mock_dashboard.current_parameters[HeatParam] = HeatParam(
            heat_status=HeatStatus.OFF,
            heat_mode=HeatMode.NORMAL,
            setpoint_temperature=22.0,
            boost_duration=1,
        )
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_heat()
            await _run_workers(app)

        written_param = mock_client.write_parameters.call_args[0][1][0]
        assert written_param.heat_status == HeatStatus.ON

    async def test_no_op_when_no_fire_id(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.fire_id = None

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_heat()
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_no_op_when_write_in_progress(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app._write_in_progress = True

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_heat()
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_no_op_when_no_heat_param(self, mock_client, mock_dashboard):
        del mock_dashboard.current_parameters[HeatParam]
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_heat()
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_no_op_when_not_dashboard(self, mock_client):
        non_dashboard = MagicMock(spec=[])
        app = _make_app(mock_client, non_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = non_dashboard
            app.action_toggle_heat()
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()


# ---------------------------------------------------------------------------
# action_set_flame_speed (dialog opening)
# ---------------------------------------------------------------------------


class TestSetFlameSpeedDialog:
    """Tests for FlameConnectApp.action_set_flame_speed opening FlameSpeedScreen."""

    async def test_opens_flame_speed_screen(self, mock_client, mock_dashboard):
        from flameconnect.tui.flame_speed_screen import FlameSpeedScreen

        app = _make_app(mock_client, mock_dashboard)
        app.push_screen = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_set_flame_speed()

        app.push_screen.assert_called_once()
        call_args = app.push_screen.call_args
        screen_arg = call_args[0][0]
        assert isinstance(screen_arg, FlameSpeedScreen)

    async def test_no_op_when_no_fire_id(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.fire_id = None
        app.push_screen = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_set_flame_speed()

        app.push_screen.assert_not_called()

    async def test_no_op_when_not_dashboard(self, mock_client):
        non_dashboard = MagicMock(spec=[])
        app = _make_app(mock_client, non_dashboard)
        app.push_screen = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = non_dashboard
            app.action_set_flame_speed()

        app.push_screen.assert_not_called()

    async def test_no_op_when_no_flame_param(self, mock_client, mock_dashboard):
        del mock_dashboard.current_parameters[FlameEffectParam]
        app = _make_app(mock_client, mock_dashboard)
        app.push_screen = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_set_flame_speed()

        app.push_screen.assert_not_called()

    async def test_callback_defers_via_call_later(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.push_screen = MagicMock()
        app.call_later = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_set_flame_speed()

        call_args = app.push_screen.call_args
        callback = call_args[1].get("callback") or call_args[0][1]

        # Simulate user selecting speed 5
        callback(5)

        app.call_later.assert_called_once_with(app._apply_flame_speed, 5)

    async def test_callback_no_op_on_none(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.push_screen = MagicMock()
        app.call_later = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_set_flame_speed()

        call_args = app.push_screen.call_args
        callback = call_args[1].get("callback") or call_args[0][1]

        # Simulate user dismissing without selecting
        callback(None)

        app.call_later.assert_not_called()

    async def test_callback_no_op_on_same_speed(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.push_screen = MagicMock()
        app.call_later = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_set_flame_speed()

        call_args = app.push_screen.call_args
        callback = call_args[1].get("callback") or call_args[0][1]

        # Simulate user selecting the same speed (3 is default)
        callback(3)

        app.call_later.assert_not_called()


# ---------------------------------------------------------------------------
# action_set_flame_color (dialog opening)
# ---------------------------------------------------------------------------


class TestSetFlameColorDialog:
    """Tests for FlameConnectApp.action_set_flame_color opening FlameColorScreen."""

    async def test_opens_flame_color_screen(self, mock_client, mock_dashboard):
        from flameconnect.tui.flame_color_screen import FlameColorScreen

        app = _make_app(mock_client, mock_dashboard)
        app.push_screen = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_set_flame_color()

        app.push_screen.assert_called_once()
        call_args = app.push_screen.call_args
        screen_arg = call_args[0][0]
        assert isinstance(screen_arg, FlameColorScreen)

    async def test_no_op_when_no_fire_id(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.fire_id = None
        app.push_screen = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_set_flame_color()

        app.push_screen.assert_not_called()

    async def test_no_op_when_not_dashboard(self, mock_client):
        non_dashboard = MagicMock(spec=[])
        app = _make_app(mock_client, non_dashboard)
        app.push_screen = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = non_dashboard
            app.action_set_flame_color()

        app.push_screen.assert_not_called()

    async def test_no_op_when_no_flame_param(self, mock_client, mock_dashboard):
        del mock_dashboard.current_parameters[FlameEffectParam]
        app = _make_app(mock_client, mock_dashboard)
        app.push_screen = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_set_flame_color()

        app.push_screen.assert_not_called()

    async def test_callback_defers_via_call_later(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.push_screen = MagicMock()
        app.call_later = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_set_flame_color()

        call_args = app.push_screen.call_args
        callback = call_args[1].get("callback") or call_args[0][1]

        callback(FlameColor.BLUE)

        app.call_later.assert_called_once_with(app._apply_flame_color, FlameColor.BLUE)

    async def test_callback_no_op_on_none(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.push_screen = MagicMock()
        app.call_later = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_set_flame_color()

        call_args = app.push_screen.call_args
        callback = call_args[1].get("callback") or call_args[0][1]

        callback(None)

        app.call_later.assert_not_called()

    async def test_callback_no_op_on_same_color(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.push_screen = MagicMock()
        app.call_later = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_set_flame_color()

        call_args = app.push_screen.call_args
        callback = call_args[1].get("callback") or call_args[0][1]

        # Default is FlameColor.ALL
        callback(FlameColor.ALL)

        app.call_later.assert_not_called()


# ---------------------------------------------------------------------------
# action_set_media_theme (dialog opening)
# ---------------------------------------------------------------------------


class TestSetMediaThemeDialog:
    """Tests for FlameConnectApp.action_set_media_theme opening MediaThemeScreen."""

    async def test_opens_media_theme_screen(self, mock_client, mock_dashboard):
        from flameconnect.tui.media_theme_screen import MediaThemeScreen

        app = _make_app(mock_client, mock_dashboard)
        app.push_screen = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_set_media_theme()

        app.push_screen.assert_called_once()
        call_args = app.push_screen.call_args
        screen_arg = call_args[0][0]
        assert isinstance(screen_arg, MediaThemeScreen)

    async def test_no_op_when_no_fire_id(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.fire_id = None
        app.push_screen = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_set_media_theme()

        app.push_screen.assert_not_called()

    async def test_no_op_when_not_dashboard(self, mock_client):
        non_dashboard = MagicMock(spec=[])
        app = _make_app(mock_client, non_dashboard)
        app.push_screen = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = non_dashboard
            app.action_set_media_theme()

        app.push_screen.assert_not_called()

    async def test_no_op_when_no_flame_param(self, mock_client, mock_dashboard):
        del mock_dashboard.current_parameters[FlameEffectParam]
        app = _make_app(mock_client, mock_dashboard)
        app.push_screen = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_set_media_theme()

        app.push_screen.assert_not_called()

    async def test_callback_defers_via_call_later(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.push_screen = MagicMock()
        app.call_later = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_set_media_theme()

        call_args = app.push_screen.call_args
        callback = call_args[1].get("callback") or call_args[0][1]

        callback(MediaTheme.BLUE)

        app.call_later.assert_called_once_with(app._apply_media_theme, MediaTheme.BLUE)

    async def test_callback_no_op_on_none(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.push_screen = MagicMock()
        app.call_later = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_set_media_theme()

        call_args = app.push_screen.call_args
        callback = call_args[1].get("callback") or call_args[0][1]

        callback(None)

        app.call_later.assert_not_called()

    async def test_callback_no_op_on_same_theme(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.push_screen = MagicMock()
        app.call_later = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_set_media_theme()

        call_args = app.push_screen.call_args
        callback = call_args[1].get("callback") or call_args[0][1]

        # Default is MediaTheme.KALEIDOSCOPE
        callback(MediaTheme.KALEIDOSCOPE)

        app.call_later.assert_not_called()


# ---------------------------------------------------------------------------
# action_set_media_color (dialog opening)
# ---------------------------------------------------------------------------


class TestSetMediaColorDialog:
    """Tests for FlameConnectApp.action_set_media_color opening ColorScreen."""

    async def test_opens_color_screen(self, mock_client, mock_dashboard):
        from flameconnect.tui.color_screen import ColorScreen

        app = _make_app(mock_client, mock_dashboard)
        app.push_screen = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_set_media_color()

        app.push_screen.assert_called_once()
        call_args = app.push_screen.call_args
        screen_arg = call_args[0][0]
        assert isinstance(screen_arg, ColorScreen)

    async def test_no_op_when_no_fire_id(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.fire_id = None
        app.push_screen = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_set_media_color()

        app.push_screen.assert_not_called()

    async def test_no_op_when_not_dashboard(self, mock_client):
        non_dashboard = MagicMock(spec=[])
        app = _make_app(mock_client, non_dashboard)
        app.push_screen = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = non_dashboard
            app.action_set_media_color()

        app.push_screen.assert_not_called()

    async def test_no_op_when_no_flame_param(self, mock_client, mock_dashboard):
        del mock_dashboard.current_parameters[FlameEffectParam]
        app = _make_app(mock_client, mock_dashboard)
        app.push_screen = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_set_media_color()

        app.push_screen.assert_not_called()

    async def test_callback_defers_via_call_later(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.push_screen = MagicMock()
        app.call_later = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_set_media_color()

        call_args = app.push_screen.call_args
        callback = call_args[1].get("callback") or call_args[0][1]

        color = RGBWColor(red=255, green=0, blue=0, white=0)
        callback(color)

        app.call_later.assert_called_once_with(app._apply_media_color, color)

    async def test_callback_no_op_on_none(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.push_screen = MagicMock()
        app.call_later = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_set_media_color()

        call_args = app.push_screen.call_args
        callback = call_args[1].get("callback") or call_args[0][1]

        callback(None)

        app.call_later.assert_not_called()


# ---------------------------------------------------------------------------
# action_set_overhead_color (dialog opening)
# ---------------------------------------------------------------------------


class TestSetOverheadColorDialog:
    """Tests for FlameConnectApp.action_set_overhead_color opening ColorScreen."""

    async def test_opens_color_screen(self, mock_client, mock_dashboard):
        from flameconnect.tui.color_screen import ColorScreen

        app = _make_app(mock_client, mock_dashboard)
        app.push_screen = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_set_overhead_color()

        app.push_screen.assert_called_once()
        call_args = app.push_screen.call_args
        screen_arg = call_args[0][0]
        assert isinstance(screen_arg, ColorScreen)

    async def test_no_op_when_no_fire_id(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.fire_id = None
        app.push_screen = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_set_overhead_color()

        app.push_screen.assert_not_called()

    async def test_no_op_when_not_dashboard(self, mock_client):
        non_dashboard = MagicMock(spec=[])
        app = _make_app(mock_client, non_dashboard)
        app.push_screen = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = non_dashboard
            app.action_set_overhead_color()

        app.push_screen.assert_not_called()

    async def test_no_op_when_no_flame_param(self, mock_client, mock_dashboard):
        del mock_dashboard.current_parameters[FlameEffectParam]
        app = _make_app(mock_client, mock_dashboard)
        app.push_screen = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_set_overhead_color()

        app.push_screen.assert_not_called()

    async def test_callback_defers_via_call_later(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.push_screen = MagicMock()
        app.call_later = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_set_overhead_color()

        call_args = app.push_screen.call_args
        callback = call_args[1].get("callback") or call_args[0][1]

        color = RGBWColor(red=0, green=255, blue=0, white=50)
        callback(color)

        app.call_later.assert_called_once_with(app._apply_overhead_color, color)

    async def test_callback_no_op_on_none(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.push_screen = MagicMock()
        app.call_later = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_set_overhead_color()

        call_args = app.push_screen.call_args
        callback = call_args[1].get("callback") or call_args[0][1]

        callback(None)

        app.call_later.assert_not_called()


# ---------------------------------------------------------------------------
# action_set_temperature (dialog opening)
# ---------------------------------------------------------------------------


class TestSetTemperatureDialog:
    """Tests for FlameConnectApp.action_set_temperature opening TemperatureScreen."""

    async def test_opens_temperature_screen(self, mock_client, mock_dashboard):
        from flameconnect.tui.temperature_screen import TemperatureScreen

        app = _make_app(mock_client, mock_dashboard)
        app.push_screen = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_set_temperature()

        app.push_screen.assert_called_once()
        call_args = app.push_screen.call_args
        screen_arg = call_args[0][0]
        assert isinstance(screen_arg, TemperatureScreen)

    async def test_no_op_when_no_fire_id(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.fire_id = None
        app.push_screen = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_set_temperature()

        app.push_screen.assert_not_called()

    async def test_no_op_when_not_dashboard(self, mock_client):
        non_dashboard = MagicMock(spec=[])
        app = _make_app(mock_client, non_dashboard)
        app.push_screen = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = non_dashboard
            app.action_set_temperature()

        app.push_screen.assert_not_called()

    async def test_no_op_when_no_heat_param(self, mock_client, mock_dashboard):
        del mock_dashboard.current_parameters[HeatParam]
        app = _make_app(mock_client, mock_dashboard)
        app.push_screen = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_set_temperature()

        app.push_screen.assert_not_called()

    async def test_no_op_when_no_temp_unit_param(self, mock_client, mock_dashboard):
        del mock_dashboard.current_parameters[TempUnitParam]
        app = _make_app(mock_client, mock_dashboard)
        app.push_screen = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_set_temperature()

        app.push_screen.assert_not_called()

    async def test_callback_defers_via_call_later(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.push_screen = MagicMock()
        app.call_later = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_set_temperature()

        call_args = app.push_screen.call_args
        callback = call_args[1].get("callback") or call_args[0][1]

        callback(25.0)

        app.call_later.assert_called_once_with(app._apply_temperature, 25.0)

    async def test_callback_no_op_on_none(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.push_screen = MagicMock()
        app.call_later = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_set_temperature()

        call_args = app.push_screen.call_args
        callback = call_args[1].get("callback") or call_args[0][1]

        callback(None)

        app.call_later.assert_not_called()

    async def test_callback_no_op_on_same_temperature(
        self, mock_client, mock_dashboard
    ):
        app = _make_app(mock_client, mock_dashboard)
        app.push_screen = MagicMock()
        app.call_later = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_set_temperature()

        call_args = app.push_screen.call_args
        callback = call_args[1].get("callback") or call_args[0][1]

        # Default is 22.0
        callback(22.0)

        app.call_later.assert_not_called()


# ---------------------------------------------------------------------------
# _apply_temperature
# ---------------------------------------------------------------------------


class TestApplyTemperature:
    """Tests for FlameConnectApp._apply_temperature."""

    async def test_sets_temperature(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app._apply_temperature(25.0)
            await _run_workers(app)

        written_param = mock_client.write_parameters.call_args[0][1][0]
        assert isinstance(written_param, HeatParam)
        assert written_param.setpoint_temperature == 25.0

    async def test_no_op_when_no_fire_id(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.fire_id = None

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app._apply_temperature(25.0)
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_no_op_when_write_in_progress(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app._write_in_progress = True

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app._apply_temperature(25.0)
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_no_op_when_no_heat_param(self, mock_client, mock_dashboard):
        del mock_dashboard.current_parameters[HeatParam]
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app._apply_temperature(25.0)
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_no_op_when_not_dashboard(self, mock_client):
        non_dashboard = MagicMock(spec=[])
        app = _make_app(mock_client, non_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = non_dashboard
            app._apply_temperature(25.0)
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_logs_feedback_message(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app._apply_temperature(25.0)
            await _run_workers(app)

        mock_dashboard.log_message.assert_any_call("Setting temperature to 25.0...")


# ---------------------------------------------------------------------------
# _run_command (direct testing of the orchestrator)
# ---------------------------------------------------------------------------


class TestRunCommand:
    """Tests for FlameConnectApp._run_command."""

    async def test_no_op_when_not_dashboard(self, mock_client):
        non_dashboard = MagicMock(spec=[])
        app = _make_app(mock_client, non_dashboard)

        coro = AsyncMock()()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = non_dashboard
            app._run_command(coro, "test...", "test failed")

        # run_worker should not have been called
        assert len(app._captured_workers) == 0

    async def test_sets_write_in_progress(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        coro = AsyncMock()()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app._run_command(coro, "test...", "test failed")

        assert app._write_in_progress is True
        mock_dashboard.log_message.assert_any_call("test...")

    async def test_worker_clears_flag_on_success(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        coro = AsyncMock()()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app._run_command(coro, "test...", "test failed")
            await _run_workers(app)

        assert app._write_in_progress is False

    async def test_worker_clears_flag_on_error(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)

        async def _failing():
            raise RuntimeError("boom")

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app._run_command(_failing(), "test...", "test failed")
            await _run_workers(app)

        assert app._write_in_progress is False
        # Error message logged
        log_calls = [c.args[0] for c in mock_dashboard.log_message.call_args_list]
        assert any("test failed" in msg for msg in log_calls)


# ---------------------------------------------------------------------------
# _load_fires
# ---------------------------------------------------------------------------


class TestLoadFires:
    """Tests for FlameConnectApp._load_fires."""

    async def test_single_fire_auto_selects(self, mock_client, mock_dashboard):
        """When only one fire, auto-select and push dashboard."""
        mock_client.get_fires = AsyncMock(return_value=[_TEST_FIRE])
        app = _make_app(mock_client, mock_dashboard)
        app._push_dashboard = MagicMock()

        # Mock the query_one to return a Static widget
        mock_loading = MagicMock()
        app.query_one = MagicMock(return_value=mock_loading)

        await app._load_fires()

        assert app.fire_id == "test-fire-001"
        mock_loading.remove.assert_called_once()
        app._push_dashboard.assert_called_once_with(_TEST_FIRE)

    async def test_no_fires_shows_error(self, mock_client, mock_dashboard):
        """When no fires found, update loading label with error."""
        mock_client.get_fires = AsyncMock(return_value=[])
        app = _make_app(mock_client, mock_dashboard)

        mock_loading = MagicMock()
        app.query_one = MagicMock(return_value=mock_loading)

        await app._load_fires()

        mock_loading.update.assert_called_once_with(
            "[bold red]No fireplaces found.[/bold red]"
        )

    async def test_multiple_fires_shows_selector(self, mock_client, mock_dashboard):
        """When multiple fires, show selection list."""
        mock_client.get_fires = AsyncMock(
            return_value=[_TEST_FIRE, _TEST_FIRE_2]
        )
        app = _make_app(mock_client, mock_dashboard)
        app.mount = AsyncMock()

        mock_loading = MagicMock()
        app.query_one = MagicMock(return_value=mock_loading)

        await app._load_fires()

        mock_loading.update.assert_called_once_with(
            "[bold]Select a fireplace:[/bold]"
        )
        app.mount.assert_awaited_once()

    async def test_get_fires_exception_notifies(self, mock_client, mock_dashboard):
        """When get_fires raises, notify the user."""
        mock_client.get_fires = AsyncMock(
            side_effect=Exception("connection refused")
        )
        app = _make_app(mock_client, mock_dashboard)
        app.notify = MagicMock()

        await app._load_fires()

        app.notify.assert_called_once()
        call_args = app.notify.call_args
        assert "Failed to load fireplaces" in call_args[0][0]


# ---------------------------------------------------------------------------
# on_option_list_option_selected
# ---------------------------------------------------------------------------


class TestOnOptionListOptionSelected:
    """Tests for FlameConnectApp.on_option_list_option_selected."""

    def test_selects_fire_and_pushes_dashboard(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.fires = [_TEST_FIRE, _TEST_FIRE_2]
        app._push_dashboard = MagicMock()

        # Create a mock event
        mock_event = MagicMock()
        mock_option = MagicMock()
        mock_option.id = "test-fire-002"
        mock_event.option = mock_option

        app.on_option_list_option_selected(mock_event)

        assert app.fire_id == "test-fire-002"
        app._push_dashboard.assert_called_once_with(_TEST_FIRE_2)

    def test_no_op_when_option_id_is_none(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.fires = [_TEST_FIRE]
        app._push_dashboard = MagicMock()

        mock_event = MagicMock()
        mock_option = MagicMock()
        mock_option.id = None
        mock_event.option = mock_option

        app.on_option_list_option_selected(mock_event)

        app._push_dashboard.assert_not_called()

    def test_no_op_when_fire_not_found(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.fires = [_TEST_FIRE]
        app._push_dashboard = MagicMock()

        mock_event = MagicMock()
        mock_option = MagicMock()
        mock_option.id = "nonexistent-fire"
        mock_event.option = mock_option

        app.on_option_list_option_selected(mock_event)

        app._push_dashboard.assert_not_called()


# ---------------------------------------------------------------------------
# show_auth_screen
# ---------------------------------------------------------------------------


class TestShowAuthScreen:
    """Tests for FlameConnectApp.show_auth_screen."""

    def test_pushes_auth_screen(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.push_screen = MagicMock()

        loop = asyncio.new_event_loop()
        future = loop.create_future()

        app.show_auth_screen(
            "https://auth.example.com",
            "https://redirect.example.com",
            future,
        )

        app.push_screen.assert_called_once()
        call_args = app.push_screen.call_args
        from flameconnect.tui.auth_screen import AuthScreen

        screen_arg = call_args[0][0]
        assert isinstance(screen_arg, AuthScreen)
        loop.close()

    def test_dismiss_callback_sets_result(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.push_screen = MagicMock()

        loop = asyncio.new_event_loop()
        future = loop.create_future()

        app.show_auth_screen(
            "https://auth.example.com",
            "https://redirect.example.com",
            future,
        )

        call_args = app.push_screen.call_args
        callback = call_args[1].get("callback") or call_args[0][1]

        # Simulate successful auth
        callback("auth-code-123")

        assert future.done()
        assert future.result() == "auth-code-123"
        loop.close()

    def test_dismiss_callback_sets_exception_on_none(self, mock_client, mock_dashboard):
        from flameconnect.exceptions import AuthenticationError

        app = _make_app(mock_client, mock_dashboard)
        app.push_screen = MagicMock()

        loop = asyncio.new_event_loop()
        future = loop.create_future()

        app.show_auth_screen(
            "https://auth.example.com",
            "https://redirect.example.com",
            future,
        )

        call_args = app.push_screen.call_args
        callback = call_args[1].get("callback") or call_args[0][1]

        # Simulate cancelled auth
        callback(None)

        assert future.done()
        with pytest.raises(AuthenticationError):
            future.result()
        loop.close()

    def test_dismiss_callback_no_op_when_future_done(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.push_screen = MagicMock()

        loop = asyncio.new_event_loop()
        future = loop.create_future()
        future.set_result("already-done")

        app.show_auth_screen(
            "https://auth.example.com",
            "https://redirect.example.com",
            future,
        )

        call_args = app.push_screen.call_args
        callback = call_args[1].get("callback") or call_args[0][1]

        # Should not raise even though future is already done
        callback("new-code")

        assert future.result() == "already-done"
        loop.close()


# ---------------------------------------------------------------------------
# _push_dashboard
# ---------------------------------------------------------------------------


class TestPushDashboard:
    """Tests for FlameConnectApp._push_dashboard."""

    def test_pushes_dashboard_screen(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.push_screen = MagicMock()

        app._push_dashboard(_TEST_FIRE)

        app.push_screen.assert_called_once()
        call_args = app.push_screen.call_args
        screen_arg = call_args[0][0]
        assert isinstance(screen_arg, DashboardScreen)


# ---------------------------------------------------------------------------
# action_switch_fire callback detail
# ---------------------------------------------------------------------------


class TestSwitchFireCallback:
    """Tests for the switch_fire callback behavior."""

    async def test_callback_pops_and_pushes_on_selection(
        self, mock_client, mock_dashboard
    ):
        """Callback pops current screen and pushes new dashboard."""
        mock_client.get_fires = AsyncMock(
            return_value=[_TEST_FIRE, _TEST_FIRE_2],
        )
        app = _make_app(mock_client, mock_dashboard)
        app.fires = [_TEST_FIRE]
        app.push_screen = MagicMock()
        app.pop_screen = MagicMock()
        app.call_later = MagicMock()
        app.notify = MagicMock()
        app._push_dashboard = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            await app.action_switch_fire()

        # Extract the callback
        call_args = app.push_screen.call_args
        callback = call_args[1].get("callback") or call_args[0][1]

        # Simulate user selecting the second fire
        callback(_TEST_FIRE_2)

        # call_later should have been called with the _switch function
        app.call_later.assert_called_once()

    async def test_callback_no_op_on_none_selection(self, mock_client, mock_dashboard):
        """When user dismisses without selecting, callback does nothing."""
        mock_client.get_fires = AsyncMock(
            return_value=[_TEST_FIRE, _TEST_FIRE_2],
        )
        app = _make_app(mock_client, mock_dashboard)
        app.fires = [_TEST_FIRE]
        app.push_screen = MagicMock()
        app.call_later = MagicMock()
        app.notify = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            await app.action_switch_fire()

        call_args = app.push_screen.call_args
        callback = call_args[1].get("callback") or call_args[0][1]

        callback(None)

        app.call_later.assert_not_called()

    async def test_no_op_when_no_fire_id(self, mock_client, mock_dashboard):
        """action_switch_fire returns early when fire_id is None and multiple fires."""
        mock_client.get_fires = AsyncMock(
            return_value=[_TEST_FIRE, _TEST_FIRE_2],
        )
        app = _make_app(mock_client, mock_dashboard)
        app.fire_id = None
        app.push_screen = MagicMock()
        app.notify = MagicMock()

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            await app.action_switch_fire()

        app.push_screen.assert_not_called()


# ---------------------------------------------------------------------------
# _apply_media_theme error handling (custom worker)
# ---------------------------------------------------------------------------


class TestApplyMediaThemeWorker:
    """Tests for _apply_media_theme's custom worker logic."""

    async def test_worker_error_logs_and_clears_flag(self, mock_client, mock_dashboard):
        """_apply_media_theme worker logs error and clears write flag on failure."""
        mock_client.write_parameters = AsyncMock(
            side_effect=Exception("API failure")
        )
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app._apply_media_theme(MediaTheme.BLUE)
            await _run_workers(app)

        assert app._write_in_progress is False
        log_calls = [c.args[0] for c in mock_dashboard.log_message.call_args_list]
        assert any("failed" in msg.lower() for msg in log_calls)

    async def test_no_op_when_no_flame_param(self, mock_client, mock_dashboard):
        del mock_dashboard.current_parameters[FlameEffectParam]
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app._apply_media_theme(MediaTheme.BLUE)
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_no_op_when_no_fire_id(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.fire_id = None

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app._apply_media_theme(MediaTheme.BLUE)
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_no_op_when_not_dashboard(self, mock_client):
        non_dashboard = MagicMock(spec=[])
        app = _make_app(mock_client, non_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = non_dashboard
            app._apply_media_theme(MediaTheme.BLUE)
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()


# ---------------------------------------------------------------------------
# Additional guard-clause tests for existing _apply methods
# (covering not-dashboard branches)
# ---------------------------------------------------------------------------


class TestApplyMethodsNotDashboard:
    """Test that all _apply methods no-op when screen is not DashboardScreen."""

    async def test_apply_flame_speed_not_dashboard(self, mock_client):
        non_dashboard = MagicMock(spec=[])
        app = _make_app(mock_client, non_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = non_dashboard
            app._apply_flame_speed(4)
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_apply_flame_color_not_dashboard(self, mock_client):
        non_dashboard = MagicMock(spec=[])
        app = _make_app(mock_client, non_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = non_dashboard
            app._apply_flame_color(FlameColor.BLUE)
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_apply_media_color_not_dashboard(self, mock_client):
        non_dashboard = MagicMock(spec=[])
        app = _make_app(mock_client, non_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = non_dashboard
            app._apply_media_color(RGBWColor(red=0, green=0, blue=0, white=0))
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_apply_overhead_color_not_dashboard(self, mock_client):
        non_dashboard = MagicMock(spec=[])
        app = _make_app(mock_client, non_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = non_dashboard
            app._apply_overhead_color(RGBWColor(red=0, green=0, blue=0, white=0))
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_apply_heat_mode_not_dashboard(self, mock_client):
        non_dashboard = MagicMock(spec=[])
        app = _make_app(mock_client, non_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = non_dashboard
            app._apply_heat_mode(HeatMode.NORMAL, None)
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_apply_temperature_not_dashboard(self, mock_client):
        non_dashboard = MagicMock(spec=[])
        app = _make_app(mock_client, non_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = non_dashboard
            app._apply_temperature(25.0)
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()


# ---------------------------------------------------------------------------
# Additional guard-clause tests for toggle actions (no-fire-id, no-param)
# ---------------------------------------------------------------------------


class TestToggleActionsGuardClauses:
    """Additional guard clause tests for toggle actions."""

    async def test_toggle_brightness_no_fire_id(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.fire_id = None

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_brightness()
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_toggle_brightness_no_flame_param(self, mock_client, mock_dashboard):
        del mock_dashboard.current_parameters[FlameEffectParam]
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_brightness()
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_toggle_flame_effect_no_fire_id(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.fire_id = None

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_flame_effect()
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_toggle_flame_effect_no_flame_param(
        self, mock_client, mock_dashboard
    ):
        del mock_dashboard.current_parameters[FlameEffectParam]
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_flame_effect()
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_toggle_pulsating_no_fire_id(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.fire_id = None

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_pulsating()
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_toggle_pulsating_no_flame_param(self, mock_client, mock_dashboard):
        del mock_dashboard.current_parameters[FlameEffectParam]
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_pulsating()
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_toggle_media_light_no_fire_id(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.fire_id = None

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_media_light()
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_toggle_media_light_no_flame_param(self, mock_client, mock_dashboard):
        del mock_dashboard.current_parameters[FlameEffectParam]
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_media_light()
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_toggle_overhead_light_no_fire_id(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.fire_id = None

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_overhead_light()
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_toggle_overhead_light_no_flame_param(
        self, mock_client, mock_dashboard
    ):
        del mock_dashboard.current_parameters[FlameEffectParam]
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_overhead_light()
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_toggle_ambient_sensor_no_fire_id(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.fire_id = None

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_ambient_sensor()
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_toggle_ambient_sensor_no_flame_param(
        self, mock_client, mock_dashboard
    ):
        del mock_dashboard.current_parameters[FlameEffectParam]
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_ambient_sensor()
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_toggle_timer_no_fire_id(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.fire_id = None

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_timer()
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_toggle_timer_no_timer_param(self, mock_client, mock_dashboard):
        del mock_dashboard.current_parameters[TimerParam]
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_timer()
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_toggle_timer_write_in_progress(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app._write_in_progress = True

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_timer()
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_toggle_temp_unit_no_fire_id(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.fire_id = None

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_temp_unit()
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_toggle_temp_unit_write_in_progress(
        self, mock_client, mock_dashboard
    ):
        app = _make_app(mock_client, mock_dashboard)
        app._write_in_progress = True

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_temp_unit()
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_toggle_heat_logs_feedback(self, mock_client, mock_dashboard):
        """Toggle heat logs the correct feedback message."""
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_heat()
            await _run_workers(app)

        mock_dashboard.log_message.assert_any_call("Setting heat to Off...")


# ---------------------------------------------------------------------------
# Reverse toggle tests (other direction)
# ---------------------------------------------------------------------------


class TestReverseToggles:
    """Test the reverse direction of toggles not covered in the original tests."""

    async def test_toggle_flame_effect_off_to_on(self, mock_client, mock_dashboard):
        """When flame effect is OFF, should toggle to ON."""
        mock_dashboard.current_parameters[FlameEffectParam] = FlameEffectParam(
            flame_effect=FlameEffect.OFF,
            flame_speed=3,
            brightness=Brightness.LOW,
            pulsating_effect=PulsatingEffect.OFF,
            media_theme=MediaTheme.KALEIDOSCOPE,
            media_light=LightStatus.ON,
            media_color=RGBWColor(red=0, green=0, blue=0, white=0),
            overhead_light=LightStatus.OFF,
            overhead_color=RGBWColor(red=0, green=0, blue=0, white=0),
            light_status=LightStatus.OFF,
            flame_color=FlameColor.ALL,
            ambient_sensor=LightStatus.OFF,
        )
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_flame_effect()
            await _run_workers(app)

        written_param = mock_client.write_parameters.call_args[0][1][0]
        assert written_param.flame_effect == FlameEffect.ON

    async def test_toggle_pulsating_on_to_off(self, mock_client, mock_dashboard):
        """When pulsating is ON, should toggle to OFF."""
        mock_dashboard.current_parameters[FlameEffectParam] = FlameEffectParam(
            flame_effect=FlameEffect.ON,
            flame_speed=3,
            brightness=Brightness.LOW,
            pulsating_effect=PulsatingEffect.ON,
            media_theme=MediaTheme.KALEIDOSCOPE,
            media_light=LightStatus.ON,
            media_color=RGBWColor(red=0, green=0, blue=0, white=0),
            overhead_light=LightStatus.OFF,
            overhead_color=RGBWColor(red=0, green=0, blue=0, white=0),
            light_status=LightStatus.OFF,
            flame_color=FlameColor.ALL,
            ambient_sensor=LightStatus.OFF,
        )
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_pulsating()
            await _run_workers(app)

        written_param = mock_client.write_parameters.call_args[0][1][0]
        assert written_param.pulsating_effect == PulsatingEffect.OFF

    async def test_toggle_media_light_off_to_on(self, mock_client, mock_dashboard):
        """When media light is OFF, should toggle to ON."""
        mock_dashboard.current_parameters[FlameEffectParam] = FlameEffectParam(
            flame_effect=FlameEffect.ON,
            flame_speed=3,
            brightness=Brightness.LOW,
            pulsating_effect=PulsatingEffect.OFF,
            media_theme=MediaTheme.KALEIDOSCOPE,
            media_light=LightStatus.OFF,
            media_color=RGBWColor(red=0, green=0, blue=0, white=0),
            overhead_light=LightStatus.OFF,
            overhead_color=RGBWColor(red=0, green=0, blue=0, white=0),
            light_status=LightStatus.OFF,
            flame_color=FlameColor.ALL,
            ambient_sensor=LightStatus.OFF,
        )
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_media_light()
            await _run_workers(app)

        written_param = mock_client.write_parameters.call_args[0][1][0]
        assert written_param.media_light == LightStatus.ON

    async def test_toggle_overhead_light_off_to_on(self, mock_client, mock_dashboard):
        """When overhead light is OFF, should toggle to ON."""
        mock_dashboard.current_parameters[FlameEffectParam] = FlameEffectParam(
            flame_effect=FlameEffect.ON,
            flame_speed=3,
            brightness=Brightness.LOW,
            pulsating_effect=PulsatingEffect.OFF,
            media_theme=MediaTheme.KALEIDOSCOPE,
            media_light=LightStatus.ON,
            media_color=RGBWColor(red=0, green=0, blue=0, white=0),
            overhead_light=LightStatus.OFF,
            overhead_color=RGBWColor(red=0, green=0, blue=0, white=0),
            light_status=LightStatus.OFF,
            flame_color=FlameColor.ALL,
            ambient_sensor=LightStatus.OFF,
        )
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_overhead_light()
            await _run_workers(app)

        written_param = mock_client.write_parameters.call_args[0][1][0]
        assert written_param.light_status == LightStatus.ON

    async def test_toggle_ambient_sensor_on_to_off(self, mock_client, mock_dashboard):
        """When ambient sensor is ON, should toggle to OFF."""
        mock_dashboard.current_parameters[FlameEffectParam] = FlameEffectParam(
            flame_effect=FlameEffect.ON,
            flame_speed=3,
            brightness=Brightness.LOW,
            pulsating_effect=PulsatingEffect.OFF,
            media_theme=MediaTheme.KALEIDOSCOPE,
            media_light=LightStatus.ON,
            media_color=RGBWColor(red=0, green=0, blue=0, white=0),
            overhead_light=LightStatus.OFF,
            overhead_color=RGBWColor(red=0, green=0, blue=0, white=0),
            light_status=LightStatus.OFF,
            flame_color=FlameColor.ALL,
            ambient_sensor=LightStatus.ON,
        )
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app.action_toggle_ambient_sensor()
            await _run_workers(app)

        written_param = mock_client.write_parameters.call_args[0][1][0]
        assert written_param.ambient_sensor == LightStatus.OFF


# ---------------------------------------------------------------------------
# Not-dashboard guards for all toggle actions
# ---------------------------------------------------------------------------


class TestToggleActionsNotDashboard:
    """Test that all toggle actions no-op when screen is not DashboardScreen."""

    async def test_toggle_brightness_not_dashboard(self, mock_client):
        non_dashboard = MagicMock(spec=[])
        app = _make_app(mock_client, non_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = non_dashboard
            app.action_toggle_brightness()
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_toggle_flame_effect_not_dashboard(self, mock_client):
        non_dashboard = MagicMock(spec=[])
        app = _make_app(mock_client, non_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = non_dashboard
            app.action_toggle_flame_effect()
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_toggle_pulsating_not_dashboard(self, mock_client):
        non_dashboard = MagicMock(spec=[])
        app = _make_app(mock_client, non_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = non_dashboard
            app.action_toggle_pulsating()
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_toggle_media_light_not_dashboard(self, mock_client):
        non_dashboard = MagicMock(spec=[])
        app = _make_app(mock_client, non_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = non_dashboard
            app.action_toggle_media_light()
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_toggle_overhead_light_not_dashboard(self, mock_client):
        non_dashboard = MagicMock(spec=[])
        app = _make_app(mock_client, non_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = non_dashboard
            app.action_toggle_overhead_light()
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_toggle_ambient_sensor_not_dashboard(self, mock_client):
        non_dashboard = MagicMock(spec=[])
        app = _make_app(mock_client, non_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = non_dashboard
            app.action_toggle_ambient_sensor()
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_toggle_heat_not_dashboard(self, mock_client):
        non_dashboard = MagicMock(spec=[])
        app = _make_app(mock_client, non_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = non_dashboard
            app.action_toggle_heat()
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_toggle_timer_not_dashboard(self, mock_client):
        non_dashboard = MagicMock(spec=[])
        app = _make_app(mock_client, non_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = non_dashboard
            app.action_toggle_timer()
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_toggle_temp_unit_not_dashboard(self, mock_client):
        non_dashboard = MagicMock(spec=[])
        app = _make_app(mock_client, non_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = non_dashboard
            app.action_toggle_temp_unit()
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()


# ---------------------------------------------------------------------------
# _apply_flame_color no-param guard
# ---------------------------------------------------------------------------


class TestApplyFlameColorGuards:
    """Additional guard tests for _apply_flame_color."""

    async def test_no_op_when_no_fire_id(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.fire_id = None

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app._apply_flame_color(FlameColor.BLUE)
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_no_op_when_no_flame_param(self, mock_client, mock_dashboard):
        del mock_dashboard.current_parameters[FlameEffectParam]
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app._apply_flame_color(FlameColor.BLUE)
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()


# ---------------------------------------------------------------------------
# _apply_media_color guard
# ---------------------------------------------------------------------------


class TestApplyMediaColorGuards:
    """Additional guard tests for _apply_media_color."""

    async def test_no_op_when_no_fire_id(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.fire_id = None

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app._apply_media_color(RGBWColor(red=0, green=0, blue=0, white=0))
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_no_op_when_no_flame_param(self, mock_client, mock_dashboard):
        del mock_dashboard.current_parameters[FlameEffectParam]
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app._apply_media_color(RGBWColor(red=0, green=0, blue=0, white=0))
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()


# ---------------------------------------------------------------------------
# _apply_overhead_color guard
# ---------------------------------------------------------------------------


class TestApplyOverheadColorGuards:
    """Additional guard tests for _apply_overhead_color."""

    async def test_no_op_when_no_fire_id(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app.fire_id = None

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app._apply_overhead_color(RGBWColor(red=0, green=0, blue=0, white=0))
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()

    async def test_no_op_when_no_flame_param(self, mock_client, mock_dashboard):
        del mock_dashboard.current_parameters[FlameEffectParam]
        app = _make_app(mock_client, mock_dashboard)

        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            app._apply_overhead_color(RGBWColor(red=0, green=0, blue=0, white=0))
            await _run_workers(app)

        mock_client.write_parameters.assert_not_awaited()
