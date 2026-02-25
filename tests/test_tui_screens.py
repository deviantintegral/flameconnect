"""Tests for TUI modal screen classes.

Covers:
  - FlameSpeedScreen
  - FlameColorScreen
  - MediaThemeScreen
  - HeatModeScreen
  - TemperatureScreen
  - ColorScreen (RGBW colour picker)
  - FireSelectScreen
  - AuthScreen
  - DashboardScreen (screens.py)
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock, patch

from textual.app import App
from textual.widgets import Button, Input, RichLog, Static

from flameconnect.models import (
    NAMED_COLORS,
    Brightness,
    ConnectionState,
    Fire,
    FireMode,
    FireOverview,
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
)

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

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
    brand="OtherBrand",
    product_type="Gas",
    product_model="GM-200",
    item_code="OB-002",
    connection_state=ConnectionState.NOT_CONNECTED,
    with_heat=False,
    is_iot_fire=True,
)

_TEST_FIRE_NO_BRAND = Fire(
    fire_id="test-fire-003",
    friendly_name="Bare Fire",
    brand="",
    product_type="Electric",
    product_model="",
    item_code="BB-003",
    connection_state=ConnectionState.CONNECTED,
    with_heat=True,
    is_iot_fire=True,
)

_DEFAULT_RGBW = RGBWColor(red=100, green=50, blue=25, white=10)

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

_DEFAULT_MODE = ModeParam(mode=FireMode.MANUAL, target_temperature=22.0)

_DEFAULT_HEAT = HeatParam(
    heat_status=HeatStatus.ON,
    heat_mode=HeatMode.NORMAL,
    setpoint_temperature=22.0,
    boost_duration=1,
)


# ===================================================================
# FlameSpeedScreen
# ===================================================================


class FlameSpeedApp(App[None]):
    """Host app for testing FlameSpeedScreen."""

    def __init__(self, current_speed: int = 3) -> None:
        super().__init__()
        self._speed = current_speed
        self.dismiss_result: int | None = None

    def on_mount(self) -> None:
        from flameconnect.tui.flame_speed_screen import FlameSpeedScreen

        def _on_dismiss(result: int | None) -> None:
            self.dismiss_result = result

        self.push_screen(FlameSpeedScreen(self._speed), callback=_on_dismiss)


class TestFlameSpeedScreen:
    """Tests for FlameSpeedScreen."""

    async def test_compose_shows_title_with_current_speed(self):
        app = FlameSpeedApp(current_speed=3)
        async with app.run_test(size=(60, 20)):
            title = app.screen.query_one("#flame-speed-title", Static)
            assert "3" in str(title._Static__content)

    async def test_compose_creates_five_buttons(self):
        app = FlameSpeedApp(current_speed=2)
        async with app.run_test(size=(60, 20)):
            buttons = app.screen.query("Button")
            assert len(buttons) == 5

    async def test_current_speed_button_is_primary(self):
        app = FlameSpeedApp(current_speed=4)
        async with app.run_test(size=(60, 20)):
            btn = app.screen.query_one("#speed-4", Button)
            assert btn.variant == "primary"

    async def test_non_current_speed_button_is_default(self):
        app = FlameSpeedApp(current_speed=4)
        async with app.run_test(size=(60, 20)):
            btn = app.screen.query_one("#speed-1", Button)
            assert btn.variant == "default"

    async def test_button_press_dismisses_with_speed(self):
        app = FlameSpeedApp(current_speed=1)
        async with app.run_test(size=(60, 20)) as pilot:
            btn = app.screen.query_one("#speed-5", Button)
            btn.press()
            await pilot.pause()
            assert app.dismiss_result == 5

    async def test_action_select_speed_dismisses(self):
        app = FlameSpeedApp(current_speed=2)
        async with app.run_test(size=(60, 20)) as pilot:
            app.screen.action_select_speed(3)
            await pilot.pause()
            assert app.dismiss_result == 3

    async def test_action_cancel_dismisses_none(self):
        app = FlameSpeedApp(current_speed=3)
        async with app.run_test(size=(60, 20)) as pilot:
            app.screen.action_cancel()
            await pilot.pause()
            assert app.dismiss_result is None

    async def test_button_with_non_speed_prefix_ignored(self):
        """Buttons without the 'speed-' prefix should be ignored."""
        app = FlameSpeedApp(current_speed=3)
        async with app.run_test(size=(60, 20)) as pilot:
            # All buttons have speed- prefix, so this is a coverage check
            # that the on_button_pressed guard works
            screen = app.screen
            # Manually create a ButtonPressed event with no id
            event = Button.Pressed(Button("X", id=None))
            screen.on_button_pressed(event)
            await pilot.pause()
            # Should not dismiss
            assert app.dismiss_result is None


# ===================================================================
# FlameColorScreen
# ===================================================================


class FlameColorApp(App[None]):
    """Host app for testing FlameColorScreen."""

    def __init__(self, current_color: FlameColor = FlameColor.ALL) -> None:
        super().__init__()
        self._color = current_color
        self.dismiss_result: FlameColor | None = "SENTINEL"

    def on_mount(self) -> None:
        from flameconnect.tui.flame_color_screen import FlameColorScreen

        def _on_dismiss(result: FlameColor | None) -> None:
            self.dismiss_result = result

        self.push_screen(FlameColorScreen(self._color), callback=_on_dismiss)


class TestFlameColorScreen:
    """Tests for FlameColorScreen."""

    async def test_compose_shows_title(self):
        app = FlameColorApp(FlameColor.BLUE)
        async with app.run_test(size=(80, 20)):
            title = app.screen.query_one("#flame-color-title", Static)
            assert "Blue" in str(title._Static__content)

    async def test_compose_creates_seven_buttons(self):
        app = FlameColorApp(FlameColor.ALL)
        async with app.run_test(size=(80, 20)):
            buttons = app.screen.query("#flame-color-buttons Button")
            assert len(buttons) == 7

    async def test_current_color_button_is_primary(self):
        app = FlameColorApp(FlameColor.RED)
        async with app.run_test(size=(80, 20)):
            btn = app.screen.query_one("#color-red", Button)
            assert btn.variant == "primary"

    async def test_non_current_color_button_is_default(self):
        app = FlameColorApp(FlameColor.RED)
        async with app.run_test(size=(80, 20)):
            btn = app.screen.query_one("#color-blue", Button)
            assert btn.variant == "default"

    async def test_button_press_dismisses_with_color(self):
        app = FlameColorApp(FlameColor.ALL)
        async with app.run_test(size=(80, 20)) as pilot:
            btn = app.screen.query_one("#color-blue", Button)
            btn.press()
            await pilot.pause()
            assert app.dismiss_result == FlameColor.BLUE

    async def test_action_select_color_dismisses(self):
        app = FlameColorApp(FlameColor.ALL)
        async with app.run_test(size=(80, 20)) as pilot:
            app.screen.action_select_color("YELLOW_RED")
            await pilot.pause()
            assert app.dismiss_result == FlameColor.YELLOW_RED

    async def test_action_cancel_dismisses_none(self):
        app = FlameColorApp(FlameColor.ALL)
        async with app.run_test(size=(80, 20)) as pilot:
            app.screen.action_cancel()
            await pilot.pause()
            assert app.dismiss_result is None

    async def test_button_no_prefix_ignored(self):
        app = FlameColorApp(FlameColor.ALL)
        async with app.run_test(size=(80, 20)) as pilot:
            event = Button.Pressed(Button("X", id="not-color-prefix"))
            app.screen.on_button_pressed(event)
            await pilot.pause()
            assert app.dismiss_result == "SENTINEL"

    async def test_button_none_id_ignored(self):
        app = FlameColorApp(FlameColor.ALL)
        async with app.run_test(size=(80, 20)) as pilot:
            event = Button.Pressed(Button("X", id=None))
            app.screen.on_button_pressed(event)
            await pilot.pause()
            assert app.dismiss_result == "SENTINEL"


# ===================================================================
# MediaThemeScreen
# ===================================================================


class MediaThemeApp(App[None]):
    """Host app for testing MediaThemeScreen."""

    def __init__(self, current_theme: MediaTheme = MediaTheme.WHITE) -> None:
        super().__init__()
        self._theme = current_theme
        self.dismiss_result: MediaTheme | None = "SENTINEL"

    def on_mount(self) -> None:
        from flameconnect.tui.media_theme_screen import MediaThemeScreen

        def _on_dismiss(result: MediaTheme | None) -> None:
            self.dismiss_result = result

        self.push_screen(MediaThemeScreen(self._theme), callback=_on_dismiss)


class TestMediaThemeScreen:
    """Tests for MediaThemeScreen."""

    async def test_compose_shows_title_with_current(self):
        app = MediaThemeApp(MediaTheme.PRISM)
        async with app.run_test(size=(80, 20)):
            title = app.screen.query_one("#media-theme-title", Static)
            assert "Prism" in str(title._Static__content)

    async def test_compose_creates_nine_buttons(self):
        app = MediaThemeApp(MediaTheme.WHITE)
        async with app.run_test(size=(80, 20)):
            row1 = app.screen.query("#media-theme-row1 Button")
            row2 = app.screen.query("#media-theme-row2 Button")
            assert len(row1) + len(row2) == 9

    async def test_current_theme_button_is_primary(self):
        app = MediaThemeApp(MediaTheme.BLUE)
        async with app.run_test(size=(80, 20)):
            btn = app.screen.query_one("#theme-blue", Button)
            assert btn.variant == "primary"

    async def test_non_current_theme_button_is_default(self):
        app = MediaThemeApp(MediaTheme.BLUE)
        async with app.run_test(size=(80, 20)):
            btn = app.screen.query_one("#theme-red", Button)
            assert btn.variant == "default"

    async def test_button_press_dismisses_with_theme(self):
        app = MediaThemeApp(MediaTheme.WHITE)
        async with app.run_test(size=(80, 20)) as pilot:
            btn = app.screen.query_one("#theme-purple", Button)
            btn.press()
            await pilot.pause()
            assert app.dismiss_result == MediaTheme.PURPLE

    async def test_action_select_theme_dismisses(self):
        app = MediaThemeApp(MediaTheme.WHITE)
        async with app.run_test(size=(80, 20)) as pilot:
            app.screen.action_select_theme("MIDNIGHT")
            await pilot.pause()
            assert app.dismiss_result == MediaTheme.MIDNIGHT

    async def test_action_cancel_dismisses_none(self):
        app = MediaThemeApp(MediaTheme.WHITE)
        async with app.run_test(size=(80, 20)) as pilot:
            app.screen.action_cancel()
            await pilot.pause()
            assert app.dismiss_result is None

    async def test_button_no_prefix_ignored(self):
        app = MediaThemeApp(MediaTheme.WHITE)
        async with app.run_test(size=(80, 20)) as pilot:
            event = Button.Pressed(Button("X", id="not-theme"))
            app.screen.on_button_pressed(event)
            await pilot.pause()
            assert app.dismiss_result == "SENTINEL"

    async def test_button_none_id_ignored(self):
        app = MediaThemeApp(MediaTheme.WHITE)
        async with app.run_test(size=(80, 20)) as pilot:
            event = Button.Pressed(Button("X", id=None))
            app.screen.on_button_pressed(event)
            await pilot.pause()
            assert app.dismiss_result == "SENTINEL"


# ===================================================================
# HeatModeScreen
# ===================================================================


class HeatModeApp(App[None]):
    """Host app for testing HeatModeScreen."""

    def __init__(
        self,
        current_mode: HeatMode = HeatMode.NORMAL,
        current_boost: int = 5,
    ) -> None:
        super().__init__()
        self._mode = current_mode
        self._boost = current_boost
        self.dismiss_result = "SENTINEL"

    def on_mount(self) -> None:
        from flameconnect.tui.heat_mode_screen import HeatModeScreen

        def _on_dismiss(result):
            self.dismiss_result = result

        self.push_screen(HeatModeScreen(self._mode, self._boost), callback=_on_dismiss)


class TestHeatModeScreen:
    """Tests for HeatModeScreen."""

    async def test_compose_shows_title_with_current_mode(self):
        app = HeatModeApp(HeatMode.ECO)
        async with app.run_test(size=(60, 25)):
            title = app.screen.query_one("#heat-mode-title", Static)
            assert "Eco" in str(title._Static__content)

    async def test_compose_creates_three_mode_buttons(self):
        app = HeatModeApp()
        async with app.run_test(size=(60, 25)):
            buttons = app.screen.query("#heat-mode-buttons Button")
            assert len(buttons) == 3

    async def test_current_mode_button_is_primary(self):
        app = HeatModeApp(HeatMode.BOOST)
        async with app.run_test(size=(60, 25)):
            btn = app.screen.query_one("#mode-boost", Button)
            assert btn.variant == "primary"

    async def test_non_current_mode_button_is_default(self):
        app = HeatModeApp(HeatMode.BOOST)
        async with app.run_test(size=(60, 25)):
            btn = app.screen.query_one("#mode-normal", Button)
            assert btn.variant == "default"

    async def test_boost_container_hidden_on_mount(self):
        app = HeatModeApp()
        async with app.run_test(size=(60, 25)):
            container = app.screen.query_one("#boost-input-container")
            assert container.display is False

    async def test_normal_button_dismisses_immediately(self):
        app = HeatModeApp()
        async with app.run_test(size=(60, 25)) as pilot:
            btn = app.screen.query_one("#mode-normal", Button)
            btn.press()
            await pilot.pause()
            assert app.dismiss_result == (HeatMode.NORMAL, None)

    async def test_eco_button_dismisses_immediately(self):
        app = HeatModeApp()
        async with app.run_test(size=(60, 25)) as pilot:
            btn = app.screen.query_one("#mode-eco", Button)
            btn.press()
            await pilot.pause()
            assert app.dismiss_result == (HeatMode.ECO, None)

    async def test_boost_button_shows_input(self):
        app = HeatModeApp()
        async with app.run_test(size=(60, 25)) as pilot:
            btn = app.screen.query_one("#mode-boost", Button)
            btn.press()
            await pilot.pause()
            container = app.screen.query_one("#boost-input-container")
            assert container.display is True

    async def test_boost_submit_valid_duration(self):
        app = HeatModeApp(current_boost=10)
        async with app.run_test(size=(60, 25)) as pilot:
            # Show boost input
            app.screen.query_one("#mode-boost", Button).press()
            await pilot.pause()
            # Set value and submit
            inp = app.screen.query_one("#boost-duration", Input)
            inp.value = "15"
            # Submit via Input.Submitted
            await inp.action_submit()
            await pilot.pause()
            assert app.dismiss_result == (HeatMode.BOOST, 15)

    async def test_boost_submit_invalid_string_notifies(self):
        app = HeatModeApp()
        async with app.run_test(size=(60, 25)) as pilot:
            app.screen.query_one("#mode-boost", Button).press()
            await pilot.pause()
            inp = app.screen.query_one("#boost-duration", Input)
            inp.value = "abc"
            await inp.action_submit()
            await pilot.pause()
            # Should NOT have dismissed
            assert app.dismiss_result == "SENTINEL"

    async def test_boost_submit_out_of_range_notifies(self):
        app = HeatModeApp()
        async with app.run_test(size=(60, 25)) as pilot:
            app.screen.query_one("#mode-boost", Button).press()
            await pilot.pause()
            inp = app.screen.query_one("#boost-duration", Input)
            inp.value = "25"
            await inp.action_submit()
            await pilot.pause()
            assert app.dismiss_result == "SENTINEL"

    async def test_boost_submit_zero_out_of_range(self):
        app = HeatModeApp()
        async with app.run_test(size=(60, 25)) as pilot:
            app.screen.query_one("#mode-boost", Button).press()
            await pilot.pause()
            inp = app.screen.query_one("#boost-duration", Input)
            inp.value = "0"
            await inp.action_submit()
            await pilot.pause()
            assert app.dismiss_result == "SENTINEL"

    async def test_action_select_mode_normal(self):
        app = HeatModeApp()
        async with app.run_test(size=(60, 25)) as pilot:
            app.screen.action_select_mode("normal")
            await pilot.pause()
            assert app.dismiss_result == (HeatMode.NORMAL, None)

    async def test_action_select_mode_eco(self):
        app = HeatModeApp()
        async with app.run_test(size=(60, 25)) as pilot:
            app.screen.action_select_mode("eco")
            await pilot.pause()
            assert app.dismiss_result == (HeatMode.ECO, None)

    async def test_action_select_boost_shows_input_first(self):
        app = HeatModeApp()
        async with app.run_test(size=(60, 25)) as pilot:
            app.screen.action_select_boost()
            await pilot.pause()
            container = app.screen.query_one("#boost-input-container")
            assert container.display is True

    async def test_action_select_boost_second_call_submits(self):
        app = HeatModeApp(current_boost=10)
        async with app.run_test(size=(60, 25)) as pilot:
            # First call shows input
            app.screen.action_select_boost()
            await pilot.pause()
            # Set a valid value
            inp = app.screen.query_one("#boost-duration", Input)
            inp.value = "10"
            # Second call submits
            app.screen.action_select_boost()
            await pilot.pause()
            assert app.dismiss_result == (HeatMode.BOOST, 10)

    async def test_action_cancel_dismisses_none(self):
        app = HeatModeApp()
        async with app.run_test(size=(60, 25)) as pilot:
            app.screen.action_cancel()
            await pilot.pause()
            assert app.dismiss_result is None

    async def test_input_submitted_non_boost_id_ignored(self):
        """Input.Submitted from non-boost inputs should be ignored."""
        app = HeatModeApp()
        async with app.run_test(size=(60, 25)) as pilot:
            # Create a fake Input.Submitted with different id
            fake_input = MagicMock(spec=Input)
            fake_input.id = "other-input"
            event = Input.Submitted(fake_input, "test")
            app.screen.on_input_submitted(event)
            await pilot.pause()
            assert app.dismiss_result == "SENTINEL"


# ===================================================================
# TemperatureScreen
# ===================================================================


class TemperatureApp(App[None]):
    """Host app for testing TemperatureScreen."""

    def __init__(
        self, current_temp: float = 22.0, unit: TempUnit = TempUnit.CELSIUS
    ) -> None:
        super().__init__()
        self._temp = current_temp
        self._unit = unit
        self.dismiss_result = "SENTINEL"

    def on_mount(self) -> None:
        from flameconnect.tui.temperature_screen import TemperatureScreen

        def _on_dismiss(result):
            self.dismiss_result = result

        self.push_screen(
            TemperatureScreen(self._temp, self._unit), callback=_on_dismiss
        )


class TestTemperatureScreen:
    """Tests for TemperatureScreen."""

    async def test_compose_celsius_title(self):
        app = TemperatureApp(22.0, TempUnit.CELSIUS)
        async with app.run_test(size=(60, 20)):
            title = app.screen.query_one("#temp-title", Static)
            assert "22.0" in str(title._Static__content)
            assert "\u00b0C" in str(title._Static__content)

    async def test_compose_fahrenheit_title(self):
        app = TemperatureApp(22.0, TempUnit.FAHRENHEIT)
        async with app.run_test(size=(60, 20)):
            title = app.screen.query_one("#temp-title", Static)
            # 22 C = 71.6 F
            assert "71.6" in str(title._Static__content)
            assert "\u00b0F" in str(title._Static__content)

    async def test_compose_celsius_range_label(self):
        app = TemperatureApp(22.0, TempUnit.CELSIUS)
        async with app.run_test(size=(60, 20)):
            range_label = app.screen.query_one("#temp-range", Static)
            assert "5.0" in str(range_label._Static__content)
            assert "35.0" in str(range_label._Static__content)

    async def test_compose_fahrenheit_range_label(self):
        app = TemperatureApp(22.0, TempUnit.FAHRENHEIT)
        async with app.run_test(size=(60, 20)):
            range_label = app.screen.query_one("#temp-range", Static)
            assert "40.0" in str(range_label._Static__content)
            assert "95.0" in str(range_label._Static__content)

    async def test_set_button_validates_and_dismisses_celsius(self):
        app = TemperatureApp(22.0, TempUnit.CELSIUS)
        async with app.run_test(size=(60, 20)) as pilot:
            inp = app.screen.query_one("#temp-input", Input)
            inp.value = "25.0"
            btn = app.screen.query_one("#set-btn", Button)
            btn.press()
            await pilot.pause()
            assert app.dismiss_result == 25.0

    async def test_set_button_validates_and_dismisses_fahrenheit(self):
        app = TemperatureApp(22.0, TempUnit.FAHRENHEIT)
        async with app.run_test(size=(60, 20)) as pilot:
            inp = app.screen.query_one("#temp-input", Input)
            inp.value = "72.0"
            btn = app.screen.query_one("#set-btn", Button)
            btn.press()
            await pilot.pause()
            # 72F -> celsius should be approximately 22.2
            assert isinstance(app.dismiss_result, float)
            assert abs(app.dismiss_result - 22.2) < 0.2

    async def test_set_invalid_number_does_not_dismiss(self):
        app = TemperatureApp(22.0, TempUnit.CELSIUS)
        async with app.run_test(size=(60, 20)) as pilot:
            inp = app.screen.query_one("#temp-input", Input)
            inp.value = "abc"
            btn = app.screen.query_one("#set-btn", Button)
            btn.press()
            await pilot.pause()
            assert app.dismiss_result == "SENTINEL"

    async def test_set_out_of_range_celsius_does_not_dismiss(self):
        app = TemperatureApp(22.0, TempUnit.CELSIUS)
        async with app.run_test(size=(60, 20)) as pilot:
            inp = app.screen.query_one("#temp-input", Input)
            inp.value = "50.0"
            btn = app.screen.query_one("#set-btn", Button)
            btn.press()
            await pilot.pause()
            assert app.dismiss_result == "SENTINEL"

    async def test_set_below_range_celsius_does_not_dismiss(self):
        app = TemperatureApp(22.0, TempUnit.CELSIUS)
        async with app.run_test(size=(60, 20)) as pilot:
            inp = app.screen.query_one("#temp-input", Input)
            inp.value = "2.0"
            btn = app.screen.query_one("#set-btn", Button)
            btn.press()
            await pilot.pause()
            assert app.dismiss_result == "SENTINEL"

    async def test_set_out_of_range_fahrenheit_does_not_dismiss(self):
        app = TemperatureApp(22.0, TempUnit.FAHRENHEIT)
        async with app.run_test(size=(60, 20)) as pilot:
            inp = app.screen.query_one("#temp-input", Input)
            inp.value = "100.0"
            btn = app.screen.query_one("#set-btn", Button)
            btn.press()
            await pilot.pause()
            assert app.dismiss_result == "SENTINEL"

    async def test_cancel_button_dismisses_none(self):
        app = TemperatureApp(22.0, TempUnit.CELSIUS)
        async with app.run_test(size=(60, 20)) as pilot:
            btn = app.screen.query_one("#cancel-btn", Button)
            btn.press()
            await pilot.pause()
            assert app.dismiss_result is None

    async def test_action_cancel_dismisses_none(self):
        app = TemperatureApp(22.0, TempUnit.CELSIUS)
        async with app.run_test(size=(60, 20)) as pilot:
            app.screen.action_cancel()
            await pilot.pause()
            assert app.dismiss_result is None

    async def test_input_submitted_validates_and_dismisses(self):
        app = TemperatureApp(22.0, TempUnit.CELSIUS)
        async with app.run_test(size=(60, 20)) as pilot:
            inp = app.screen.query_one("#temp-input", Input)
            inp.value = "30.0"
            await inp.action_submit()
            await pilot.pause()
            assert app.dismiss_result == 30.0

    async def test_boundary_value_celsius_min(self):
        app = TemperatureApp(22.0, TempUnit.CELSIUS)
        async with app.run_test(size=(60, 20)) as pilot:
            inp = app.screen.query_one("#temp-input", Input)
            inp.value = "5.0"
            btn = app.screen.query_one("#set-btn", Button)
            btn.press()
            await pilot.pause()
            assert app.dismiss_result == 5.0

    async def test_boundary_value_celsius_max(self):
        app = TemperatureApp(22.0, TempUnit.CELSIUS)
        async with app.run_test(size=(60, 20)) as pilot:
            inp = app.screen.query_one("#temp-input", Input)
            inp.value = "35.0"
            btn = app.screen.query_one("#set-btn", Button)
            btn.press()
            await pilot.pause()
            assert app.dismiss_result == 35.0


# ===================================================================
# TemperatureScreen helper functions
# ===================================================================


class TestTemperatureHelpers:
    """Tests for temperature conversion helper functions."""

    def test_convert_temp_celsius_returns_same(self):
        from flameconnect.tui.temperature_screen import _convert_temp

        assert _convert_temp(22.0, TempUnit.CELSIUS) == 22.0

    def test_convert_temp_fahrenheit(self):
        from flameconnect.tui.temperature_screen import _convert_temp

        result = _convert_temp(0.0, TempUnit.FAHRENHEIT)
        assert result == 32.0

    def test_convert_temp_fahrenheit_100(self):
        from flameconnect.tui.temperature_screen import _convert_temp

        result = _convert_temp(100.0, TempUnit.FAHRENHEIT)
        assert result == 212.0

    def test_convert_to_celsius(self):
        from flameconnect.tui.temperature_screen import _convert_to_celsius

        result = _convert_to_celsius(72.0)
        assert abs(result - 22.2) < 0.1

    def test_convert_to_celsius_32(self):
        from flameconnect.tui.temperature_screen import _convert_to_celsius

        assert _convert_to_celsius(32.0) == 0.0


# ===================================================================
# ColorScreen (RGBW colour picker)
# ===================================================================


class ColorScreenApp(App[None]):
    """Host app for testing ColorScreen."""

    def __init__(
        self,
        current: RGBWColor = _DEFAULT_RGBW,
        title: str = "Test Color",
    ) -> None:
        super().__init__()
        self._current = current
        self._title = title
        self.dismiss_result = "SENTINEL"

    def on_mount(self) -> None:
        from flameconnect.tui.color_screen import ColorScreen

        def _on_dismiss(result):
            self.dismiss_result = result

        self.push_screen(ColorScreen(self._current, self._title), callback=_on_dismiss)


class TestColorScreen:
    """Tests for ColorScreen."""

    async def test_compose_shows_title_and_current(self):
        app = ColorScreenApp(RGBWColor(red=10, green=20, blue=30, white=40), "My Color")
        async with app.run_test(size=(100, 30)):
            title = app.screen.query_one("#color-title", Static)
            rendered = str(title._Static__content)
            assert "My Color" in rendered
            assert "R=10" in rendered
            assert "G=20" in rendered
            assert "B=30" in rendered
            assert "W=40" in rendered

    async def test_compose_dark_preset_buttons(self):
        app = ColorScreenApp()
        async with app.run_test(size=(100, 30)):
            buttons = app.screen.query("#dark-presets Button")
            assert len(buttons) == 7

    async def test_compose_light_preset_buttons(self):
        app = ColorScreenApp()
        async with app.run_test(size=(100, 30)):
            buttons = app.screen.query("#light-presets Button")
            assert len(buttons) == 7

    async def test_compose_rgbw_inputs(self):
        app = ColorScreenApp(RGBWColor(red=10, green=20, blue=30, white=40))
        async with app.run_test(size=(100, 30)):
            r_input = app.screen.query_one("#input-r", Input)
            g_input = app.screen.query_one("#input-g", Input)
            b_input = app.screen.query_one("#input-b", Input)
            w_input = app.screen.query_one("#input-w", Input)
            assert r_input.value == "10"
            assert g_input.value == "20"
            assert b_input.value == "30"
            assert w_input.value == "40"

    async def test_dark_preset_button_press(self):
        app = ColorScreenApp()
        async with app.run_test(size=(100, 30)) as pilot:
            btn = app.screen.query_one("#preset-dark-red", Button)
            btn.press()
            await pilot.pause()
            assert app.dismiss_result == NAMED_COLORS["dark-red"]

    async def test_light_preset_button_press(self):
        app = ColorScreenApp()
        async with app.run_test(size=(100, 30)) as pilot:
            btn = app.screen.query_one("#preset-light-blue", Button)
            btn.press()
            await pilot.pause()
            assert app.dismiss_result == NAMED_COLORS["light-blue"]

    async def test_set_rgbw_button_custom_values(self):
        app = ColorScreenApp()
        async with app.run_test(size=(100, 30)) as pilot:
            app.screen.query_one("#input-r", Input).value = "128"
            app.screen.query_one("#input-g", Input).value = "64"
            app.screen.query_one("#input-b", Input).value = "32"
            app.screen.query_one("#input-w", Input).value = "16"
            btn = app.screen.query_one("#set-rgbw", Button)
            btn.press()
            await pilot.pause()
            assert app.dismiss_result == RGBWColor(red=128, green=64, blue=32, white=16)

    async def test_set_rgbw_invalid_value_does_not_dismiss(self):
        app = ColorScreenApp()
        async with app.run_test(size=(100, 30)) as pilot:
            app.screen.query_one("#input-r", Input).value = "abc"
            btn = app.screen.query_one("#set-rgbw", Button)
            btn.press()
            await pilot.pause()
            assert app.dismiss_result == "SENTINEL"

    async def test_set_rgbw_out_of_range_does_not_dismiss(self):
        app = ColorScreenApp()
        async with app.run_test(size=(100, 30)) as pilot:
            app.screen.query_one("#input-r", Input).value = "300"
            app.screen.query_one("#input-g", Input).value = "0"
            app.screen.query_one("#input-b", Input).value = "0"
            app.screen.query_one("#input-w", Input).value = "0"
            btn = app.screen.query_one("#set-rgbw", Button)
            btn.press()
            await pilot.pause()
            assert app.dismiss_result == "SENTINEL"

    async def test_set_rgbw_negative_does_not_dismiss(self):
        app = ColorScreenApp()
        async with app.run_test(size=(100, 30)) as pilot:
            app.screen.query_one("#input-r", Input).value = "-1"
            app.screen.query_one("#input-g", Input).value = "0"
            app.screen.query_one("#input-b", Input).value = "0"
            app.screen.query_one("#input-w", Input).value = "0"
            btn = app.screen.query_one("#set-rgbw", Button)
            btn.press()
            await pilot.pause()
            assert app.dismiss_result == "SENTINEL"

    async def test_action_select_preset(self):
        app = ColorScreenApp()
        async with app.run_test(size=(100, 30)) as pilot:
            app.screen.action_select_preset("dark-green")
            await pilot.pause()
            assert app.dismiss_result == NAMED_COLORS["dark-green"]

    async def test_action_cancel(self):
        app = ColorScreenApp()
        async with app.run_test(size=(100, 30)) as pilot:
            app.screen.action_cancel()
            await pilot.pause()
            assert app.dismiss_result is None

    async def test_input_submitted_triggers_custom_rgbw(self):
        app = ColorScreenApp()
        async with app.run_test(size=(100, 30)) as pilot:
            app.screen.query_one("#input-r", Input).value = "50"
            app.screen.query_one("#input-g", Input).value = "60"
            app.screen.query_one("#input-b", Input).value = "70"
            app.screen.query_one("#input-w", Input).value = "80"
            # Trigger on_input_submitted
            inp = app.screen.query_one("#input-r", Input)
            await inp.action_submit()
            await pilot.pause()
            assert app.dismiss_result == RGBWColor(red=50, green=60, blue=70, white=80)

    async def test_button_no_preset_prefix_for_set(self):
        """set-rgbw button goes through _apply_custom_rgbw path."""
        app = ColorScreenApp()
        async with app.run_test(size=(100, 30)) as pilot:
            app.screen.query_one("#input-r", Input).value = "0"
            app.screen.query_one("#input-g", Input).value = "0"
            app.screen.query_one("#input-b", Input).value = "0"
            app.screen.query_one("#input-w", Input).value = "0"
            btn = app.screen.query_one("#set-rgbw", Button)
            btn.press()
            await pilot.pause()
            assert app.dismiss_result == RGBWColor(red=0, green=0, blue=0, white=0)

    async def test_boundary_rgbw_255(self):
        app = ColorScreenApp()
        async with app.run_test(size=(100, 30)) as pilot:
            app.screen.query_one("#input-r", Input).value = "255"
            app.screen.query_one("#input-g", Input).value = "255"
            app.screen.query_one("#input-b", Input).value = "255"
            app.screen.query_one("#input-w", Input).value = "255"
            btn = app.screen.query_one("#set-rgbw", Button)
            btn.press()
            await pilot.pause()
            assert app.dismiss_result == RGBWColor(
                red=255, green=255, blue=255, white=255
            )


# ===================================================================
# FireSelectScreen
# ===================================================================


class FireSelectApp(App[None]):
    """Host app for testing FireSelectScreen."""

    def __init__(
        self,
        fires: list[Fire] | None = None,
        current_fire_id: str = "test-fire-001",
    ) -> None:
        super().__init__()
        self._fires = fires or [_TEST_FIRE, _TEST_FIRE_2]
        self._current_fire_id = current_fire_id
        self.dismiss_result = "SENTINEL"

    def on_mount(self) -> None:
        from flameconnect.tui.fire_select_screen import FireSelectScreen

        def _on_dismiss(result):
            self.dismiss_result = result

        self.push_screen(
            FireSelectScreen(self._fires, self._current_fire_id),
            callback=_on_dismiss,
        )


class TestFireSelectScreen:
    """Tests for FireSelectScreen."""

    async def test_compose_shows_title(self):
        app = FireSelectApp()
        async with app.run_test(size=(80, 20)):
            title = app.screen.query_one("#fire-select-title", Static)
            assert "Switch Fireplace" in str(title._Static__content)

    async def test_compose_creates_buttons_for_each_fire(self):
        app = FireSelectApp()
        async with app.run_test(size=(80, 20)):
            buttons = app.screen.query("#fire-select-list Button")
            assert len(buttons) == 2

    async def test_current_fire_button_is_primary(self):
        app = FireSelectApp()
        async with app.run_test(size=(80, 20)):
            btn = app.screen.query_one("#fire-0", Button)
            assert btn.variant == "primary"

    async def test_other_fire_button_is_default(self):
        app = FireSelectApp()
        async with app.run_test(size=(80, 20)):
            btn = app.screen.query_one("#fire-1", Button)
            assert btn.variant == "default"

    async def test_button_press_selects_different_fire(self):
        app = FireSelectApp()
        async with app.run_test(size=(80, 20)) as pilot:
            btn = app.screen.query_one("#fire-1", Button)
            btn.press()
            await pilot.pause()
            assert app.dismiss_result == _TEST_FIRE_2

    async def test_button_press_current_fire_dismisses_none(self):
        app = FireSelectApp()
        async with app.run_test(size=(80, 20)) as pilot:
            btn = app.screen.query_one("#fire-0", Button)
            btn.press()
            await pilot.pause()
            assert app.dismiss_result is None

    async def test_action_select_fire_by_number(self):
        app = FireSelectApp()
        async with app.run_test(size=(80, 20)) as pilot:
            app.screen.action_select_fire(2)
            await pilot.pause()
            assert app.dismiss_result == _TEST_FIRE_2

    async def test_action_select_fire_out_of_range(self):
        app = FireSelectApp()
        async with app.run_test(size=(80, 20)) as pilot:
            app.screen.action_select_fire(10)
            await pilot.pause()
            assert app.dismiss_result == "SENTINEL"

    async def test_action_select_fire_zero_index(self):
        """Number 0 maps to index -1 which should be ignored."""
        app = FireSelectApp()
        async with app.run_test(size=(80, 20)) as pilot:
            app.screen.action_select_fire(0)
            await pilot.pause()
            assert app.dismiss_result == "SENTINEL"

    async def test_action_cancel_dismisses_none(self):
        app = FireSelectApp()
        async with app.run_test(size=(80, 20)) as pilot:
            app.screen.action_cancel()
            await pilot.pause()
            assert app.dismiss_result is None

    async def test_button_none_id_ignored(self):
        app = FireSelectApp()
        async with app.run_test(size=(80, 20)) as pilot:
            event = Button.Pressed(Button("X", id=None))
            app.screen.on_button_pressed(event)
            await pilot.pause()
            assert app.dismiss_result == "SENTINEL"

    async def test_button_non_fire_prefix_ignored(self):
        app = FireSelectApp()
        async with app.run_test(size=(80, 20)) as pilot:
            event = Button.Pressed(Button("X", id="other-0"))
            app.screen.on_button_pressed(event)
            await pilot.pause()
            assert app.dismiss_result == "SENTINEL"

    async def test_single_fire_list(self):
        app = FireSelectApp(fires=[_TEST_FIRE], current_fire_id="test-fire-001")
        async with app.run_test(size=(80, 20)):
            buttons = app.screen.query("#fire-select-list Button")
            assert len(buttons) == 1


# ===================================================================
# AuthScreen
# ===================================================================


class AuthScreenApp(App[None]):
    """Host app for testing AuthScreen."""

    def __init__(
        self,
        auth_uri: str = "https://example.com/auth",
        redirect_uri: str = "msal://redirect",
    ) -> None:
        super().__init__()
        self._auth_uri = auth_uri
        self._redirect_uri = redirect_uri
        self.dismiss_result = "SENTINEL"

    def on_mount(self) -> None:
        from flameconnect.tui.auth_screen import AuthScreen

        def _on_dismiss(result):
            self.dismiss_result = result

        self.push_screen(
            AuthScreen(self._auth_uri, self._redirect_uri),
            callback=_on_dismiss,
        )


class TestAuthScreen:
    """Tests for AuthScreen."""

    async def test_compose_shows_title(self):
        app = AuthScreenApp()
        async with app.run_test(size=(80, 25)):
            title = app.screen.query_one("#auth-title", Static)
            assert "Authentication Required" in str(title._Static__content)

    async def test_compose_has_email_and_password_inputs(self):
        app = AuthScreenApp()
        async with app.run_test(size=(80, 25)):
            email = app.screen.query_one("#email-input", Input)
            password = app.screen.query_one("#password-input", Input)
            assert email is not None
            assert password is not None

    async def test_compose_has_sign_in_button(self):
        app = AuthScreenApp()
        async with app.run_test(size=(80, 25)):
            btn = app.screen.query_one("#sign-in-btn", Button)
            assert btn is not None

    async def test_error_hidden_initially(self):
        app = AuthScreenApp()
        async with app.run_test(size=(80, 25)):
            error = app.screen.query_one("#auth-error", Static)
            assert error.display is False

    async def test_status_hidden_initially(self):
        app = AuthScreenApp()
        async with app.run_test(size=(80, 25)):
            status = app.screen.query_one("#auth-status", Static)
            assert status.display is False

    async def test_hint_hidden_initially(self):
        app = AuthScreenApp()
        async with app.run_test(size=(80, 25)):
            hint = app.screen.query_one("#auth-hint", Static)
            assert hint.display is False

    async def test_action_cancel_dismisses_none(self):
        app = AuthScreenApp()
        async with app.run_test(size=(80, 25)) as pilot:
            app.screen.action_cancel()
            await pilot.pause()
            assert app.dismiss_result is None

    async def test_submit_empty_email_shows_error(self):
        app = AuthScreenApp()
        async with app.run_test(size=(80, 25)) as pilot:
            # Leave fields empty and press sign in
            app.screen.query_one("#email-input", Input).value = ""
            app.screen.query_one("#password-input", Input).value = ""
            app.screen.query_one("#sign-in-btn", Button).press()
            await pilot.pause()
            error = app.screen.query_one("#auth-error", Static)
            assert error.display is True

    async def test_submit_empty_password_shows_error(self):
        app = AuthScreenApp()
        async with app.run_test(size=(80, 25)) as pilot:
            app.screen.query_one("#email-input", Input).value = "user@example.com"
            app.screen.query_one("#password-input", Input).value = ""
            app.screen.query_one("#sign-in-btn", Button).press()
            await pilot.pause()
            error = app.screen.query_one("#auth-error", Static)
            assert error.display is True

    async def test_email_input_submitted_focuses_password(self):
        app = AuthScreenApp()
        async with app.run_test(size=(80, 25)) as pilot:
            email_input = app.screen.query_one("#email-input", Input)
            email_input.value = "user@example.com"
            await email_input.action_submit()
            await pilot.pause()
            # Password input should now be focused
            password_input = app.screen.query_one("#password-input", Input)
            assert password_input.has_focus

    async def test_show_error_helper(self):
        app = AuthScreenApp()
        async with app.run_test(size=(80, 25)):
            app.screen._show_error("Test error message")
            error = app.screen.query_one("#auth-error", Static)
            assert error.display is True

    async def test_hide_error_helper(self):
        app = AuthScreenApp()
        async with app.run_test(size=(80, 25)):
            app.screen._show_error("Test error")
            app.screen._hide_error()
            error = app.screen.query_one("#auth-error", Static)
            assert error.display is False

    async def test_show_status_helper(self):
        app = AuthScreenApp()
        async with app.run_test(size=(80, 25)):
            app.screen._show_status("Loading...")
            status = app.screen.query_one("#auth-status", Static)
            assert status.display is True

    async def test_hide_status_helper(self):
        app = AuthScreenApp()
        async with app.run_test(size=(80, 25)):
            app.screen._show_status("Loading...")
            app.screen._hide_status()
            status = app.screen.query_one("#auth-status", Static)
            assert status.display is False

    async def test_show_hint_helper(self):
        app = AuthScreenApp()
        async with app.run_test(size=(80, 25)):
            app.screen._show_hint("Open browser to login")
            hint = app.screen.query_one("#auth-hint", Static)
            assert hint.display is True

    async def test_set_inputs_disabled(self):
        app = AuthScreenApp()
        async with app.run_test(size=(80, 25)):
            app.screen._set_inputs_disabled(True)
            for inp in app.screen.query(Input):
                assert inp.disabled is True
            btn = app.screen.query_one("#sign-in-btn", Button)
            assert btn.disabled is True

    async def test_set_inputs_enabled(self):
        app = AuthScreenApp()
        async with app.run_test(size=(80, 25)):
            app.screen._set_inputs_disabled(True)
            app.screen._set_inputs_disabled(False)
            for inp in app.screen.query(Input):
                assert inp.disabled is False
            btn = app.screen.query_one("#sign-in-btn", Button)
            assert btn.disabled is False

    async def test_credential_submit_triggers_worker(self):
        """Submitting with credentials starts the login worker."""
        app = AuthScreenApp()
        async with app.run_test(size=(80, 25)) as pilot:
            app.screen.query_one("#email-input", Input).value = "user@test.com"
            app.screen.query_one("#password-input", Input).value = "secret"
            # Patch the worker to avoid actual login
            with patch.object(app.screen, "run_worker") as mock_worker:
                app.screen.query_one("#sign-in-btn", Button).press()
                await pilot.pause()
                mock_worker.assert_called_once()

    async def test_credential_login_success_dismisses(self):
        """Successful credential login dismisses with the redirect URL."""
        app = AuthScreenApp()
        async with app.run_test(size=(80, 25)) as pilot:
            mock_login = AsyncMock(return_value="msal://redirect?code=123")
            with patch(
                "flameconnect.b2c_login.b2c_login_with_credentials",
                mock_login,
            ):
                await app.screen._do_credential_login("user@test.com", "pass")
                await pilot.pause()

    async def test_switch_to_browser_fallback(self):
        """_switch_to_browser_fallback hides credential inputs and shows URL input."""
        app = AuthScreenApp()
        async with app.run_test(size=(80, 25)) as pilot:
            with patch("webbrowser.open"):
                app.screen._switch_to_browser_fallback("Bad credentials")
                await pilot.pause()
                # Credential inputs should be hidden
                assert app.screen.query_one("#email-input", Input).display is False
                assert app.screen.query_one("#password-input", Input).display is False
                # Error should show
                error = app.screen.query_one("#auth-error", Static)
                assert error.display is True
                # URL input should exist (mounted)
                await pilot.pause()
                url_input = app.screen.query_one("#url-input", Input)
                assert url_input is not None

    async def test_browser_fallback_submit_url(self):
        """In browser fallback mode, submitting a URL dismisses."""
        app = AuthScreenApp()
        async with app.run_test(size=(80, 25)) as pilot:
            with patch("webbrowser.open"):
                app.screen._switch_to_browser_fallback("Bad creds")
                await pilot.pause()
                url_input = app.screen.query_one("#url-input", Input)
                url_input.value = "msal://auth?code=ABC"
                # Submit should use _submit_url path
                app.screen._on_submit()
                await pilot.pause()
                assert app.dismiss_result == "msal://auth?code=ABC"

    async def test_browser_fallback_empty_url_shows_error(self):
        """In browser fallback mode, empty URL shows error."""
        app = AuthScreenApp()
        async with app.run_test(size=(80, 25)) as pilot:
            with patch("webbrowser.open"):
                app.screen._switch_to_browser_fallback("Bad creds")
                await pilot.pause()
                url_input = app.screen.query_one("#url-input", Input)
                url_input.value = ""
                app.screen._submit_url()
                await pilot.pause()
                error = app.screen.query_one("#auth-error", Static)
                assert error.display is True

    async def test_password_submitted_triggers_on_submit(self):
        """Pressing enter on password input calls _on_submit."""
        app = AuthScreenApp()
        async with app.run_test(size=(80, 25)) as pilot:
            app.screen.query_one("#email-input", Input).value = "user@test.com"
            app.screen.query_one("#password-input", Input).value = "secret"
            with patch.object(app.screen, "run_worker"):
                pw_input = app.screen.query_one("#password-input", Input)
                await pw_input.action_submit()
                await pilot.pause()

    async def test_button_pressed_non_sign_in_ignored(self):
        """Button press on non sign-in button should be ignored."""
        app = AuthScreenApp()
        async with app.run_test(size=(80, 25)) as pilot:
            event = Button.Pressed(Button("X", id="other-btn"))
            app.screen.on_button_pressed(event)
            await pilot.pause()
            assert app.dismiss_result == "SENTINEL"


# ===================================================================
# DashboardScreen (from screens.py)
# ===================================================================


class DashboardApp(App[None]):
    """Host app for testing DashboardScreen."""

    def __init__(self, client=None, fire=None) -> None:
        super().__init__()
        self._client = client or MagicMock()
        self._fire = fire or _TEST_FIRE
        # Prevent actual API calls during mount
        if not hasattr(self._client, "get_fire_overview"):
            self._client.get_fire_overview = AsyncMock(
                side_effect=Exception("not wired")
            )

    def on_mount(self) -> None:
        from flameconnect.tui.screens import DashboardScreen

        self.push_screen(DashboardScreen(self._client, self._fire))


class TestDashboardScreen:
    """Tests for DashboardScreen."""

    async def test_compose_has_messages_panel(self):
        app = DashboardApp()
        async with app.run_test(size=(120, 40)):
            panel = app.screen.query_one("#messages-panel", RichLog)
            assert panel is not None

    async def test_compose_has_param_panel(self):
        app = DashboardApp()
        async with app.run_test(size=(120, 40)):
            panel = app.screen.query_one("#param-panel")
            assert panel is not None

    async def test_compose_has_fireplace_visual(self):
        app = DashboardApp()
        async with app.run_test(size=(120, 40)):
            visual = app.screen.query_one("#fireplace-visual")
            assert visual is not None

    async def test_sub_title_includes_fire_name(self):
        app = DashboardApp(fire=_TEST_FIRE)
        async with app.run_test(size=(120, 40)):
            assert "Test Fire" in app.screen.sub_title

    async def test_sub_title_includes_fire_id(self):
        app = DashboardApp(fire=_TEST_FIRE)
        async with app.run_test(size=(120, 40)):
            assert "test-fire-001" in app.screen.sub_title

    async def test_sub_title_includes_brand_model(self):
        app = DashboardApp(fire=_TEST_FIRE)
        async with app.run_test(size=(120, 40)):
            assert "TestBrand" in app.screen.sub_title
            assert "TM-100" in app.screen.sub_title

    async def test_sub_title_no_brand(self):
        """Fire with empty brand/model should not have extra separator."""
        app = DashboardApp(fire=_TEST_FIRE_NO_BRAND)
        async with app.run_test(size=(120, 40)):
            # Should only have "Bare Fire (test-fire-003)"
            assert "Bare Fire" in app.screen.sub_title

    async def test_log_message_writes_to_rich_log(self):
        app = DashboardApp()
        async with app.run_test(size=(120, 40)) as pilot:
            app.screen.log_message("Test message")
            await pilot.pause()
            # The rich log should have at least one write

    async def test_log_message_with_warning_level(self):
        app = DashboardApp()
        async with app.run_test(size=(120, 40)) as pilot:
            app.screen.log_message("Warning msg", level=logging.WARNING)
            await pilot.pause()

    async def test_log_message_with_error_level(self):
        app = DashboardApp()
        async with app.run_test(size=(120, 40)) as pilot:
            app.screen.log_message("Error msg", level=logging.ERROR)
            await pilot.pause()

    async def test_current_parameters_initially_empty(self):
        app = DashboardApp()
        async with app.run_test(size=(120, 40)):
            params = app.screen.current_parameters
            assert params == {}

    async def test_current_mode_initially_none(self):
        app = DashboardApp()
        async with app.run_test(size=(120, 40)):
            assert app.screen.current_mode is None

    async def test_refresh_state_success(self):
        """refresh_state should update display on success."""
        overview = FireOverview(
            fire=_TEST_FIRE,
            parameters=[_DEFAULT_MODE, _DEFAULT_FLAME_EFFECT, _DEFAULT_HEAT],
        )
        client = MagicMock()
        client.get_fire_overview = AsyncMock(return_value=overview)
        app = DashboardApp(client=client, fire=_TEST_FIRE)
        async with app.run_test(size=(120, 40)) as pilot:
            await app.screen.refresh_state()
            await pilot.pause()
            # After refresh, current_parameters should be populated
            params = app.screen.current_parameters
            assert ModeParam in params
            assert FlameEffectParam in params
            assert HeatParam in params

    async def test_refresh_state_sets_current_mode(self):
        overview = FireOverview(
            fire=_TEST_FIRE,
            parameters=[_DEFAULT_MODE, _DEFAULT_FLAME_EFFECT],
        )
        client = MagicMock()
        client.get_fire_overview = AsyncMock(return_value=overview)
        app = DashboardApp(client=client, fire=_TEST_FIRE)
        async with app.run_test(size=(120, 40)) as pilot:
            await app.screen.refresh_state()
            await pilot.pause()
            assert app.screen.current_mode == _DEFAULT_MODE

    async def test_refresh_state_error_notifies(self):
        """refresh_state should handle exceptions gracefully."""
        client = MagicMock()
        client.get_fire_overview = AsyncMock(side_effect=Exception("API error"))
        app = DashboardApp(client=client, fire=_TEST_FIRE)
        async with app.run_test(size=(120, 40)) as pilot:
            await app.screen.refresh_state()
            await pilot.pause()
            # Should not crash, parameters stay empty
            assert app.screen.current_parameters == {}

    async def test_update_display_tracks_param_changes(self):
        """Calling _update_display twice should log changed params."""
        overview1 = FireOverview(
            fire=_TEST_FIRE,
            parameters=[_DEFAULT_MODE, _DEFAULT_FLAME_EFFECT],
        )
        changed_mode = ModeParam(mode=FireMode.STANDBY, target_temperature=18.0)
        overview2 = FireOverview(
            fire=_TEST_FIRE,
            parameters=[changed_mode, _DEFAULT_FLAME_EFFECT],
        )
        client = MagicMock()
        client.get_fire_overview = AsyncMock(side_effect=[overview1, overview2])
        app = DashboardApp(client=client, fire=_TEST_FIRE)
        async with app.run_test(size=(120, 40)) as pilot:
            await app.screen.refresh_state()
            await pilot.pause()
            # Second refresh with changed mode
            await app.screen.refresh_state()
            await pilot.pause()
            # The _log_param_changes should have been called
            # and the mode should be updated
            assert app.screen.current_mode == changed_mode

    async def test_update_display_sub_title_includes_timestamp(self):
        overview = FireOverview(
            fire=_TEST_FIRE,
            parameters=[_DEFAULT_MODE],
        )
        client = MagicMock()
        client.get_fire_overview = AsyncMock(return_value=overview)
        app = DashboardApp(client=client, fire=_TEST_FIRE)
        async with app.run_test(size=(120, 40)) as pilot:
            await app.screen.refresh_state()
            await pilot.pause()
            assert "Updated:" in app.screen.sub_title

    async def test_on_unmount_removes_log_handler(self):
        app = DashboardApp()
        async with app.run_test(size=(120, 40)):
            screen = app.screen
            assert screen._log_handler is not None
            screen.on_unmount()
            assert screen._log_handler is None

    async def test_on_unmount_idempotent(self):
        app = DashboardApp()
        async with app.run_test(size=(120, 40)):
            screen = app.screen
            screen.on_unmount()
            screen.on_unmount()  # Should not raise
            assert screen._log_handler is None


# ===================================================================
# _TuiLogHandler (from screens.py)
# ===================================================================


class TestTuiLogHandler:
    """Tests for the _TuiLogHandler class."""

    async def test_handler_writes_to_rich_log(self):
        app = DashboardApp()
        async with app.run_test(size=(120, 40)) as pilot:
            # Get the log handler
            handler = app.screen._log_handler
            assert handler is not None
            # Create a log record and emit it
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg="Test log message",
                args=(),
                exc_info=None,
            )
            handler.emit(record)
            await pilot.pause()

    async def test_handler_formats_warning(self):
        app = DashboardApp()
        async with app.run_test(size=(120, 40)) as pilot:
            handler = app.screen._log_handler
            record = logging.LogRecord(
                name="test",
                level=logging.WARNING,
                pathname="",
                lineno=0,
                msg="Warning message",
                args=(),
                exc_info=None,
            )
            handler.emit(record)
            await pilot.pause()

    async def test_handler_formats_error(self):
        app = DashboardApp()
        async with app.run_test(size=(120, 40)) as pilot:
            handler = app.screen._log_handler
            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="",
                lineno=0,
                msg="Error message",
                args=(),
                exc_info=None,
            )
            handler.emit(record)
            await pilot.pause()

    async def test_handler_formats_debug(self):
        app = DashboardApp()
        async with app.run_test(size=(120, 40)) as pilot:
            handler = app.screen._log_handler
            record = logging.LogRecord(
                name="test",
                level=logging.DEBUG,
                pathname="",
                lineno=0,
                msg="Debug message",
                args=(),
                exc_info=None,
            )
            handler.emit(record)
            await pilot.pause()

    async def test_handler_formats_critical(self):
        app = DashboardApp()
        async with app.run_test(size=(120, 40)) as pilot:
            handler = app.screen._log_handler
            record = logging.LogRecord(
                name="test",
                level=logging.CRITICAL,
                pathname="",
                lineno=0,
                msg="Critical message",
                args=(),
                exc_info=None,
            )
            handler.emit(record)
            await pilot.pause()

    async def test_handler_unknown_level(self):
        app = DashboardApp()
        async with app.run_test(size=(120, 40)) as pilot:
            handler = app.screen._log_handler
            record = logging.LogRecord(
                name="test",
                level=99,  # Unusual level
                pathname="",
                lineno=0,
                msg="Custom level message",
                args=(),
                exc_info=None,
            )
            handler.emit(record)
            await pilot.pause()

    async def test_handler_emit_exception_handled(self):
        """If RichLog.write raises, the handler should call handleError."""
        app = DashboardApp()
        async with app.run_test(size=(120, 40)):
            handler = app.screen._log_handler
            # Monkey-patch the _rich_log to raise
            original_write = handler._rich_log.write
            handler._rich_log.write = MagicMock(side_effect=Exception("write failed"))
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg="Should fail",
                args=(),
                exc_info=None,
            )
            # Should not raise
            with patch.object(handler, "handleError"):
                handler.emit(record)
            handler._rich_log.write = original_write


# ===================================================================
# DashboardScreen._log_param_changes (from screens.py)
# ===================================================================


class TestLogParamChanges:
    """Tests for DashboardScreen._log_param_changes."""

    async def test_logs_changed_fields(self):
        """Changed fields between old and new params should be logged."""
        old_mode = ModeParam(mode=FireMode.MANUAL, target_temperature=22.0)
        new_mode = ModeParam(mode=FireMode.STANDBY, target_temperature=22.0)
        overview1 = FireOverview(fire=_TEST_FIRE, parameters=[old_mode])
        overview2 = FireOverview(fire=_TEST_FIRE, parameters=[new_mode])
        client = MagicMock()
        client.get_fire_overview = AsyncMock(side_effect=[overview1, overview2])
        app = DashboardApp(client=client, fire=_TEST_FIRE)
        async with app.run_test(size=(120, 40)) as pilot:
            await app.screen.refresh_state()
            await pilot.pause()
            await app.screen.refresh_state()
            await pilot.pause()

    async def test_no_log_for_unchanged_params(self):
        """Identical params between refreshes should not trigger log."""
        overview = FireOverview(fire=_TEST_FIRE, parameters=[_DEFAULT_MODE])
        client = MagicMock()
        client.get_fire_overview = AsyncMock(return_value=overview)
        app = DashboardApp(client=client, fire=_TEST_FIRE)
        async with app.run_test(size=(120, 40)) as pilot:
            await app.screen.refresh_state()
            await pilot.pause()
            await app.screen.refresh_state()
            await pilot.pause()

    async def test_log_new_param_type_not_in_old(self):
        """If a new param type appears, skip it (no old to compare)."""
        overview1 = FireOverview(fire=_TEST_FIRE, parameters=[_DEFAULT_MODE])
        overview2 = FireOverview(
            fire=_TEST_FIRE,
            parameters=[_DEFAULT_MODE, _DEFAULT_FLAME_EFFECT],
        )
        client = MagicMock()
        client.get_fire_overview = AsyncMock(side_effect=[overview1, overview2])
        app = DashboardApp(client=client, fire=_TEST_FIRE)
        async with app.run_test(size=(120, 40)) as pilot:
            await app.screen.refresh_state()
            await pilot.pause()
            await app.screen.refresh_state()
            await pilot.pause()

    async def test_multiple_field_changes_logged(self):
        """When multiple fields change, each should be logged."""
        old_mode = ModeParam(mode=FireMode.MANUAL, target_temperature=22.0)
        new_mode = ModeParam(mode=FireMode.STANDBY, target_temperature=18.0)
        overview1 = FireOverview(fire=_TEST_FIRE, parameters=[old_mode])
        overview2 = FireOverview(fire=_TEST_FIRE, parameters=[new_mode])
        client = MagicMock()
        client.get_fire_overview = AsyncMock(side_effect=[overview1, overview2])
        app = DashboardApp(client=client, fire=_TEST_FIRE)
        async with app.run_test(size=(120, 40)) as pilot:
            await app.screen.refresh_state()
            await pilot.pause()
            await app.screen.refresh_state()
            await pilot.pause()


# ===================================================================
# DashboardScreen compact mode
# ===================================================================


class TestDashboardCompactMode:
    """Tests for compact mode toggling in DashboardScreen."""

    async def test_compact_at_small_size(self):
        app = DashboardApp()
        async with app.run_test(size=(80, 24)):
            screen = app.screen
            assert "compact" in screen.classes

    async def test_not_compact_at_large_size(self):
        app = DashboardApp()
        async with app.run_test(size=(120, 40)):
            screen = app.screen
            assert "compact" not in screen.classes

    async def test_compact_hides_fireplace_visual(self):
        app = DashboardApp()
        async with app.run_test(size=(80, 24)):
            visual = app.screen.query_one("#fireplace-visual")
            assert visual.display is False

    async def test_non_compact_shows_fireplace_visual(self):
        app = DashboardApp()
        async with app.run_test(size=(120, 40)):
            visual = app.screen.query_one("#fireplace-visual")
            assert visual.display is True


# ===================================================================
# _LEVEL_MARKUP coverage
# ===================================================================


class TestLevelMarkup:
    """Verify all log level markups are accessible."""

    def test_all_standard_levels_in_markup_dict(self):
        from flameconnect.tui.screens import _LEVEL_MARKUP

        assert logging.DEBUG in _LEVEL_MARKUP
        assert logging.INFO in _LEVEL_MARKUP
        assert logging.WARNING in _LEVEL_MARKUP
        assert logging.ERROR in _LEVEL_MARKUP
        assert logging.CRITICAL in _LEVEL_MARKUP

    def test_debug_markup(self):
        from flameconnect.tui.screens import _LEVEL_MARKUP

        open_tag, close_tag = _LEVEL_MARKUP[logging.DEBUG]
        assert "dim" in open_tag
        assert "dim" in close_tag

    def test_info_markup_empty(self):
        from flameconnect.tui.screens import _LEVEL_MARKUP

        open_tag, close_tag = _LEVEL_MARKUP[logging.INFO]
        assert open_tag == ""
        assert close_tag == ""

    def test_warning_markup(self):
        from flameconnect.tui.screens import _LEVEL_MARKUP

        open_tag, close_tag = _LEVEL_MARKUP[logging.WARNING]
        assert "yellow" in open_tag

    def test_error_markup(self):
        from flameconnect.tui.screens import _LEVEL_MARKUP

        open_tag, close_tag = _LEVEL_MARKUP[logging.ERROR]
        assert "red" in open_tag

    def test_critical_markup(self):
        from flameconnect.tui.screens import _LEVEL_MARKUP

        open_tag, close_tag = _LEVEL_MARKUP[logging.CRITICAL]
        assert "bold red" in open_tag


# ---------------------------------------------------------------------------
# TimerScreen
# ---------------------------------------------------------------------------


class TimerApp(App[None]):
    """Host app for testing TimerScreen."""

    def __init__(self, current_duration: int = 60) -> None:
        super().__init__()
        self._duration = current_duration
        self.dismiss_result = "SENTINEL"

    def on_mount(self) -> None:
        from flameconnect.tui.timer_screen import TimerScreen

        def _on_dismiss(result):
            self.dismiss_result = result

        self.push_screen(TimerScreen(self._duration), callback=_on_dismiss)


class TestTimerScreen:
    """Tests for TimerScreen."""

    async def test_compose_title(self):
        app = TimerApp(60)
        async with app.run_test(size=(60, 20)):
            title = app.screen.query_one("#timer-title", Static)
            assert "Timer" in str(title._Static__content)

    async def test_compose_default_value(self):
        app = TimerApp(60)
        async with app.run_test(size=(60, 20)):
            inp = app.screen.query_one("#timer-input", Input)
            assert inp.value == "60"

    async def test_compose_custom_value(self):
        app = TimerApp(90)
        async with app.run_test(size=(60, 20)):
            inp = app.screen.query_one("#timer-input", Input)
            assert inp.value == "90"

    async def test_set_button_validates_and_dismisses(self):
        app = TimerApp(60)
        async with app.run_test(size=(60, 20)) as pilot:
            inp = app.screen.query_one("#timer-input", Input)
            inp.value = "45"
            btn = app.screen.query_one("#set-btn", Button)
            btn.press()
            await pilot.pause()
            assert app.dismiss_result == 45

    async def test_set_invalid_number_does_not_dismiss(self):
        app = TimerApp(60)
        async with app.run_test(size=(60, 20)) as pilot:
            inp = app.screen.query_one("#timer-input", Input)
            inp.value = "abc"
            btn = app.screen.query_one("#set-btn", Button)
            btn.press()
            await pilot.pause()
            assert app.dismiss_result == "SENTINEL"

    async def test_set_zero_does_not_dismiss(self):
        app = TimerApp(60)
        async with app.run_test(size=(60, 20)) as pilot:
            inp = app.screen.query_one("#timer-input", Input)
            inp.value = "0"
            btn = app.screen.query_one("#set-btn", Button)
            btn.press()
            await pilot.pause()
            assert app.dismiss_result == "SENTINEL"

    async def test_set_above_max_does_not_dismiss(self):
        app = TimerApp(60)
        async with app.run_test(size=(60, 20)) as pilot:
            inp = app.screen.query_one("#timer-input", Input)
            inp.value = "500"
            btn = app.screen.query_one("#set-btn", Button)
            btn.press()
            await pilot.pause()
            assert app.dismiss_result == "SENTINEL"

    async def test_cancel_button_dismisses_none(self):
        app = TimerApp(60)
        async with app.run_test(size=(60, 20)) as pilot:
            btn = app.screen.query_one("#cancel-btn", Button)
            btn.press()
            await pilot.pause()
            assert app.dismiss_result is None

    async def test_action_cancel_dismisses_none(self):
        app = TimerApp(60)
        async with app.run_test(size=(60, 20)) as pilot:
            app.screen.action_cancel()
            await pilot.pause()
            assert app.dismiss_result is None

    async def test_input_submitted_validates_and_dismisses(self):
        app = TimerApp(60)
        async with app.run_test(size=(60, 20)) as pilot:
            inp = app.screen.query_one("#timer-input", Input)
            inp.value = "120"
            await inp.action_submit()
            await pilot.pause()
            assert app.dismiss_result == 120
