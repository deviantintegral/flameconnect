"""Tests for TUI keybinding action methods in FlameConnectApp."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from flameconnect.models import (
    Brightness,
    ConnectionState,
    Fire,
    FlameColor,
    FlameEffect,
    FlameEffectParam,
    HeatMode,
    HeatParam,
    HeatStatus,
    LightStatus,
    MediaTheme,
    PulsatingEffect,
    RGBWColor,
    TempUnit,
    TempUnitParam,
    TimerParam,
    TimerStatus,
)
from textual.app import App

from flameconnect.tui.app import FlameConnectApp
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
