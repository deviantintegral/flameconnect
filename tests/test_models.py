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
    TempUnitParam,
    TimerStatus,
    convert_from_display,
    convert_temp,
    display_name,
    temp_suffix,
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


# ---------------------------------------------------------------------------
# Display / conversion utilities
# ---------------------------------------------------------------------------


class TestConvertTemp:
    """Tests for convert_temp()."""

    def test_celsius_passthrough(self):
        assert convert_temp(22.0, TempUnit.CELSIUS) == 22.0

    def test_fahrenheit_conversion(self):
        assert convert_temp(0.0, TempUnit.FAHRENHEIT) == 32.0

    def test_fahrenheit_100(self):
        assert convert_temp(100.0, TempUnit.FAHRENHEIT) == 212.0

    def test_fahrenheit_negative(self):
        assert convert_temp(-40.0, TempUnit.FAHRENHEIT) == -40.0

    def test_fahrenheit_rounding(self):
        assert convert_temp(22.0, TempUnit.FAHRENHEIT) == 71.6

    def test_fahrenheit_rounding_precision(self):
        """22.3°C -> 72.14°F: round to 1 decimal gives 72.1, not 72.14."""
        assert convert_temp(22.3, TempUnit.FAHRENHEIT) == 72.1


class TestConvertFromDisplay:
    """Tests for convert_from_display() (inverse of convert_temp)."""

    def test_celsius_passthrough(self):
        assert convert_from_display(22.2, TempUnit.CELSIUS) == 22.2

    def test_fahrenheit_conversion(self):
        assert convert_from_display(32.0, TempUnit.FAHRENHEIT) == 0.0

    def test_fahrenheit_72(self):
        # round((72-32)*5/9, 1) == 22.2
        assert convert_from_display(72.0, TempUnit.FAHRENHEIT) == 22.2

    def test_fahrenheit_negative(self):
        assert convert_from_display(-40.0, TempUnit.FAHRENHEIT) == -40.0

    def test_round_trips_with_convert_temp(self):
        # Celsius -> display -> back should be stable at 1-decimal precision.
        assert (
            convert_from_display(
                convert_temp(25.0, TempUnit.FAHRENHEIT), TempUnit.FAHRENHEIT
            )
            == 25.0
        )


class TestTempSuffix:
    """Tests for temp_suffix()."""

    def test_none_returns_empty(self):
        assert temp_suffix(None) == ""

    def test_celsius(self):
        assert temp_suffix(TempUnitParam(unit=TempUnit.CELSIUS)) == "C"

    def test_fahrenheit(self):
        assert temp_suffix(TempUnitParam(unit=TempUnit.FAHRENHEIT)) == "F"


class TestKebabName:
    """Tests for kebab_name()."""

    def test_single_word(self):
        from flameconnect.models import kebab_name

        assert kebab_name(FireMode.STANDBY) == "standby"

    def test_multi_word_underscore(self):
        from flameconnect.models import kebab_name

        assert kebab_name(HeatMode.FAN_ONLY) == "fan-only"

    def test_underscore_replaced_with_hyphen(self):
        from flameconnect.models import kebab_name

        result = kebab_name(FlameColor.YELLOW_RED)
        assert "_" not in result
        assert "-" in result
        assert result == "yellow-red"

    def test_lowercased(self):
        from flameconnect.models import kebab_name

        result = kebab_name(HeatControl.SOFTWARE_DISABLED)
        assert result == result.lower()
        assert result == "software-disabled"

    def test_all_enum_members(self):
        from flameconnect.models import kebab_name

        for member in MediaTheme:
            result = kebab_name(member)
            assert result == member.name.lower().replace("_", "-")


class TestDisplayName:
    """Tests for display_name()."""

    def test_single_word(self):
        assert display_name(FireMode.STANDBY) == "Standby"

    def test_single_word_manual(self):
        assert display_name(FireMode.MANUAL) == "On"

    def test_multi_word_underscore(self):
        assert display_name(HeatMode.FAN_ONLY) == "Fan Only"

    def test_multi_word_compound(self):
        assert display_name(HeatControl.SOFTWARE_DISABLED) == "Software Disabled"

    def test_on_off(self):
        assert display_name(FlameEffect.ON) == "On"
        assert display_name(FlameEffect.OFF) == "Off"

    def test_connection_states(self):
        assert display_name(ConnectionState.CONNECTED) == "Connected"
        assert display_name(ConnectionState.NOT_CONNECTED) == "Not Connected"

    def test_temp_unit(self):
        assert display_name(TempUnit.CELSIUS) == "Celsius"
        assert display_name(TempUnit.FAHRENHEIT) == "Fahrenheit"

    def test_flame_color(self):
        assert display_name(FlameColor.YELLOW_RED) == "Yellow/Red"
