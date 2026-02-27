"""Tests for data models and enums."""

from __future__ import annotations

import dataclasses

import pytest

from flameconnect.models import (
    ConnectionState,
    Fire,
    FireFeatures,
    FireMode,
    FlameColor,
    FlameEffect,
    HeatControl,
    HeatMode,
    HeatStatus,
    LightStatus,
    LogEffect,
    MediaTheme,
    ModeParam,
    RGBWColor,
    TempUnit,
    TimerStatus,
)

# ---------------------------------------------------------------------------
# Dataclass construction
# ---------------------------------------------------------------------------


class TestFireConstruction:
    """Test Fire dataclass construction."""

    def test_basic_construction(self):
        fire = Fire(
            fire_id="abc-123",
            friendly_name="My Fire",
            brand="Dimplex",
            product_type="Bold Ignite XL",
            product_model="BIX-50",
            item_code="XYZ",
            connection_state=ConnectionState.CONNECTED,
            with_heat=True,
            is_iot_fire=True,
        )
        assert fire.fire_id == "abc-123"
        assert fire.friendly_name == "My Fire"
        assert fire.brand == "Dimplex"
        assert fire.product_type == "Bold Ignite XL"
        assert fire.product_model == "BIX-50"
        assert fire.item_code == "XYZ"
        assert fire.connection_state == ConnectionState.CONNECTED
        assert fire.with_heat is True
        assert fire.is_iot_fire is True

    def test_without_heat(self):
        fire = Fire(
            fire_id="abc-123",
            friendly_name="Flame Only",
            brand="Faber",
            product_type="Type",
            product_model="Model",
            item_code="IC",
            connection_state=ConnectionState.NOT_CONNECTED,
            with_heat=False,
            is_iot_fire=True,
        )
        assert fire.with_heat is False
        assert fire.connection_state == ConnectionState.NOT_CONNECTED


class TestRGBWColorConstruction:
    """Test RGBWColor dataclass construction."""

    def test_basic_construction(self):
        color = RGBWColor(red=255, green=128, blue=64, white=32)
        assert color.red == 255
        assert color.green == 128
        assert color.blue == 64
        assert color.white == 32

    def test_all_zeros(self):
        color = RGBWColor(red=0, green=0, blue=0, white=0)
        assert color.red == 0
        assert color.green == 0
        assert color.blue == 0
        assert color.white == 0

    def test_equality(self):
        c1 = RGBWColor(red=10, green=20, blue=30, white=40)
        c2 = RGBWColor(red=10, green=20, blue=30, white=40)
        assert c1 == c2

    def test_inequality(self):
        c1 = RGBWColor(red=10, green=20, blue=30, white=40)
        c2 = RGBWColor(red=10, green=20, blue=30, white=50)
        assert c1 != c2


class TestFireFeaturesDefaults:
    """Test FireFeatures dataclass defaults."""

    def test_all_fields_default_to_false(self):
        features = FireFeatures()
        for field in dataclasses.fields(features):
            assert getattr(features, field.name) is False, (
                f"FireFeatures.{field.name} should default to False"
            )


# ---------------------------------------------------------------------------
# Frozen immutability
# ---------------------------------------------------------------------------


class TestFrozenDataclasses:
    """Frozen dataclasses should raise on attribute mutation."""

    def test_fire_is_frozen(self):
        fire = Fire(
            fire_id="abc",
            friendly_name="Name",
            brand="Brand",
            product_type="Type",
            product_model="Model",
            item_code="IC",
            connection_state=ConnectionState.CONNECTED,
            with_heat=True,
            is_iot_fire=True,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            fire.friendly_name = "New Name"  # type: ignore[misc]

    def test_rgbw_color_is_frozen(self):
        color = RGBWColor(red=1, green=2, blue=3, white=4)
        with pytest.raises(dataclasses.FrozenInstanceError):
            color.red = 99  # type: ignore[misc]

    def test_mode_param_is_frozen(self):
        mode = ModeParam(mode=FireMode.MANUAL, target_temperature=22.0)
        with pytest.raises(dataclasses.FrozenInstanceError):
            mode.target_temperature = 25.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Enum integer values
# ---------------------------------------------------------------------------


class TestEnumValues:
    """Verify enum integer values match the wire protocol."""

    def test_fire_mode(self):
        assert FireMode.STANDBY == 0
        assert FireMode.MANUAL == 1

    def test_flame_effect(self):
        assert FlameEffect.OFF == 0
        assert FlameEffect.ON == 1

    def test_heat_status(self):
        assert HeatStatus.OFF == 0
        assert HeatStatus.ON == 1

    def test_heat_mode(self):
        assert HeatMode.NORMAL == 0
        assert HeatMode.BOOST == 1
        assert HeatMode.ECO == 2
        assert HeatMode.FAN_ONLY == 3
        assert HeatMode.SCHEDULE == 4

    def test_heat_control(self):
        assert HeatControl.SOFTWARE_DISABLED == 0
        assert HeatControl.HARDWARE_DISABLED == 1
        assert HeatControl.ENABLED == 2

    def test_flame_color(self):
        assert FlameColor.ALL == 0
        assert FlameColor.YELLOW_RED == 1
        assert FlameColor.YELLOW_BLUE == 2
        assert FlameColor.BLUE == 3
        assert FlameColor.RED == 4
        assert FlameColor.YELLOW == 5
        assert FlameColor.BLUE_RED == 6

    def test_light_status(self):
        assert LightStatus.OFF == 0
        assert LightStatus.ON == 1

    def test_timer_status(self):
        assert TimerStatus.DISABLED == 0
        assert TimerStatus.ENABLED == 1

    def test_temp_unit(self):
        assert TempUnit.FAHRENHEIT == 0
        assert TempUnit.CELSIUS == 1

    def test_log_effect(self):
        assert LogEffect.OFF == 0
        assert LogEffect.ON == 1

    def test_media_theme(self):
        assert MediaTheme.USER_DEFINED == 0
        assert MediaTheme.WHITE == 1
        assert MediaTheme.MIDNIGHT == 8

    def test_connection_state(self):
        assert ConnectionState.UNKNOWN == 0
        assert ConnectionState.NOT_CONNECTED == 1
        assert ConnectionState.CONNECTED == 2
        assert ConnectionState.UPDATING_FIRMWARE == 3
