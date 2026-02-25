"""Tests for the CLI set commands (_set_pulsating, _set_flame_color, etc.)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from aioresponses import aioresponses as aioresponses_mock
from yarl import URL

from flameconnect.cli import (
    _parse_color,
    _set_ambient_sensor,
    _set_brightness,
    _set_flame_color,
    _set_flame_effect,
    _set_flame_speed,
    _set_heat_mode,
    _set_heat_temp,
    _set_media_color,
    _set_media_light,
    _set_media_theme,
    _set_mode,
    _set_overhead_color,
    _set_overhead_light,
    _set_pulsating,
    _set_temp_unit,
    _set_timer,
    cmd_set,
)
from flameconnect.client import FlameConnectClient
from flameconnect.const import API_BASE
from flameconnect.models import RGBWColor

FIXTURES_DIR = Path(__file__).parent / "fixtures"
FIRE_ID = "test-fire-001"
OVERVIEW_URL = f"{API_BASE}/api/Fires/GetFireOverview?FireId={FIRE_ID}"
WRITE_URL = f"{API_BASE}/api/Fires/WriteWifiParameters"


@pytest.fixture
def mock_api():
    with aioresponses_mock() as m:
        yield m


@pytest.fixture
def overview_payload() -> dict:
    return json.loads((FIXTURES_DIR / "get_fire_overview.json").read_text())


# ---------------------------------------------------------------------------
# _set_pulsating
# ---------------------------------------------------------------------------


class TestSetPulsating:
    """Tests for the _set_pulsating CLI command."""

    async def test_set_pulsating_on(self, mock_api, token_auth, overview_payload):
        mock_api.get(OVERVIEW_URL, payload=overview_payload)
        mock_api.post(WRITE_URL, payload={})

        async with FlameConnectClient(token_auth) as client:
            await _set_pulsating(client, FIRE_ID, "on")

        key = ("POST", URL(WRITE_URL))
        calls = mock_api.requests[key]
        assert len(calls) == 1
        body = calls[0].kwargs["json"]
        assert body["FireId"] == FIRE_ID
        assert len(body["Parameters"]) == 1
        assert body["Parameters"][0]["ParameterId"] == 322

    async def test_set_pulsating_off(self, mock_api, token_auth, overview_payload):
        mock_api.get(OVERVIEW_URL, payload=overview_payload)
        mock_api.post(WRITE_URL, payload={})

        async with FlameConnectClient(token_auth) as client:
            await _set_pulsating(client, FIRE_ID, "off")

        key = ("POST", URL(WRITE_URL))
        calls = mock_api.requests[key]
        assert len(calls) == 1

    async def test_set_pulsating_invalid(self, mock_api, token_auth, capsys):
        async with FlameConnectClient(token_auth) as client:
            with pytest.raises(SystemExit):
                await _set_pulsating(client, FIRE_ID, "invalid")
        captured = capsys.readouterr()
        assert "Error" in captured.out


# ---------------------------------------------------------------------------
# _set_flame_color
# ---------------------------------------------------------------------------


class TestSetFlameColor:
    """Tests for the _set_flame_color CLI command."""

    async def test_set_flame_color_blue(self, mock_api, token_auth, overview_payload):
        mock_api.get(OVERVIEW_URL, payload=overview_payload)
        mock_api.post(WRITE_URL, payload={})

        async with FlameConnectClient(token_auth) as client:
            await _set_flame_color(client, FIRE_ID, "blue")

        key = ("POST", URL(WRITE_URL))
        calls = mock_api.requests[key]
        assert len(calls) == 1
        body = calls[0].kwargs["json"]
        assert body["FireId"] == FIRE_ID
        assert body["Parameters"][0]["ParameterId"] == 322

    async def test_set_flame_color_all(self, mock_api, token_auth, overview_payload):
        mock_api.get(OVERVIEW_URL, payload=overview_payload)
        mock_api.post(WRITE_URL, payload={})

        async with FlameConnectClient(token_auth) as client:
            await _set_flame_color(client, FIRE_ID, "all")

        key = ("POST", URL(WRITE_URL))
        calls = mock_api.requests[key]
        assert len(calls) == 1

    async def test_set_flame_color_yellow_red(
        self, mock_api, token_auth, overview_payload
    ):
        mock_api.get(OVERVIEW_URL, payload=overview_payload)
        mock_api.post(WRITE_URL, payload={})

        async with FlameConnectClient(token_auth) as client:
            await _set_flame_color(client, FIRE_ID, "yellow-red")

        key = ("POST", URL(WRITE_URL))
        assert len(mock_api.requests[key]) == 1

    async def test_set_flame_color_invalid(self, mock_api, token_auth, capsys):
        async with FlameConnectClient(token_auth) as client:
            with pytest.raises(SystemExit):
                await _set_flame_color(client, FIRE_ID, "rainbow")
        captured = capsys.readouterr()
        assert "Error" in captured.out


# ---------------------------------------------------------------------------
# _set_media_theme
# ---------------------------------------------------------------------------


class TestSetMediaTheme:
    """Tests for the _set_media_theme CLI command."""

    async def test_set_media_theme_kaleidoscope(
        self, mock_api, token_auth, overview_payload
    ):
        mock_api.get(OVERVIEW_URL, payload=overview_payload)
        mock_api.post(WRITE_URL, payload={})

        async with FlameConnectClient(token_auth) as client:
            await _set_media_theme(client, FIRE_ID, "kaleidoscope")

        key = ("POST", URL(WRITE_URL))
        calls = mock_api.requests[key]
        assert len(calls) == 1
        body = calls[0].kwargs["json"]
        assert body["Parameters"][0]["ParameterId"] == 322

    async def test_set_media_theme_midnight(
        self, mock_api, token_auth, overview_payload
    ):
        mock_api.get(OVERVIEW_URL, payload=overview_payload)
        mock_api.post(WRITE_URL, payload={})

        async with FlameConnectClient(token_auth) as client:
            await _set_media_theme(client, FIRE_ID, "midnight")

        key = ("POST", URL(WRITE_URL))
        assert len(mock_api.requests[key]) == 1

    async def test_set_media_theme_user_defined(
        self, mock_api, token_auth, overview_payload
    ):
        mock_api.get(OVERVIEW_URL, payload=overview_payload)
        mock_api.post(WRITE_URL, payload={})

        async with FlameConnectClient(token_auth) as client:
            await _set_media_theme(client, FIRE_ID, "user-defined")

        key = ("POST", URL(WRITE_URL))
        assert len(mock_api.requests[key]) == 1

    async def test_set_media_theme_invalid(self, mock_api, token_auth, capsys):
        async with FlameConnectClient(token_auth) as client:
            with pytest.raises(SystemExit):
                await _set_media_theme(client, FIRE_ID, "neon")
        captured = capsys.readouterr()
        assert "Error" in captured.out


# ---------------------------------------------------------------------------
# _set_temp_unit
# ---------------------------------------------------------------------------


class TestSetTempUnit:
    """Tests for the _set_temp_unit CLI command (no GET needed)."""

    async def test_set_temp_unit_celsius(self, mock_api, token_auth):
        mock_api.post(WRITE_URL, payload={})

        async with FlameConnectClient(token_auth) as client:
            await _set_temp_unit(client, FIRE_ID, "celsius")

        key = ("POST", URL(WRITE_URL))
        calls = mock_api.requests[key]
        assert len(calls) == 1
        body = calls[0].kwargs["json"]
        assert body["FireId"] == FIRE_ID
        assert body["Parameters"][0]["ParameterId"] == 236

    async def test_set_temp_unit_fahrenheit(self, mock_api, token_auth):
        mock_api.post(WRITE_URL, payload={})

        async with FlameConnectClient(token_auth) as client:
            await _set_temp_unit(client, FIRE_ID, "fahrenheit")

        key = ("POST", URL(WRITE_URL))
        calls = mock_api.requests[key]
        assert len(calls) == 1

    async def test_set_temp_unit_invalid(self, mock_api, token_auth, capsys):
        async with FlameConnectClient(token_auth) as client:
            with pytest.raises(SystemExit):
                await _set_temp_unit(client, FIRE_ID, "kelvin")
        captured = capsys.readouterr()
        assert "Error" in captured.out


# ---------------------------------------------------------------------------
# _set_mode
# ---------------------------------------------------------------------------


class TestSetMode:
    """Tests for the _set_mode CLI command."""

    async def test_set_mode_manual(self, mock_api, token_auth, overview_payload):
        mock_api.get(OVERVIEW_URL, payload=overview_payload)
        mock_api.post(WRITE_URL, payload={})

        async with FlameConnectClient(token_auth) as client:
            await _set_mode(client, FIRE_ID, "manual")

        key = ("POST", URL(WRITE_URL))
        calls = mock_api.requests[key]
        assert len(calls) == 1
        body = calls[0].kwargs["json"]
        assert body["Parameters"][0]["ParameterId"] == 321

    async def test_set_mode_standby(self, mock_api, token_auth, overview_payload):
        mock_api.get(OVERVIEW_URL, payload=overview_payload)
        mock_api.post(WRITE_URL, payload={})

        async with FlameConnectClient(token_auth) as client:
            await _set_mode(client, FIRE_ID, "standby")

        key = ("POST", URL(WRITE_URL))
        assert len(mock_api.requests[key]) == 1

    async def test_set_mode_invalid(self, mock_api, token_auth, capsys):
        async with FlameConnectClient(token_auth) as client:
            with pytest.raises(SystemExit):
                await _set_mode(client, FIRE_ID, "turbo")
        captured = capsys.readouterr()
        assert "Error" in captured.out


# ---------------------------------------------------------------------------
# _set_flame_speed
# ---------------------------------------------------------------------------


class TestSetFlameSpeed:
    """Tests for the _set_flame_speed CLI command."""

    async def test_set_flame_speed_valid(
        self, mock_api, token_auth, overview_payload
    ):
        mock_api.get(OVERVIEW_URL, payload=overview_payload)
        mock_api.post(WRITE_URL, payload={})

        async with FlameConnectClient(token_auth) as client:
            await _set_flame_speed(client, FIRE_ID, "5")

        key = ("POST", URL(WRITE_URL))
        calls = mock_api.requests[key]
        assert len(calls) == 1
        body = calls[0].kwargs["json"]
        assert body["Parameters"][0]["ParameterId"] == 322

    async def test_set_flame_speed_too_high(
        self, mock_api, token_auth, overview_payload, capsys
    ):
        mock_api.get(OVERVIEW_URL, payload=overview_payload)

        async with FlameConnectClient(token_auth) as client:
            with pytest.raises(SystemExit):
                await _set_flame_speed(client, FIRE_ID, "6")
        captured = capsys.readouterr()
        assert "Error" in captured.out

    async def test_set_flame_speed_too_low(
        self, mock_api, token_auth, overview_payload, capsys
    ):
        mock_api.get(OVERVIEW_URL, payload=overview_payload)

        async with FlameConnectClient(token_auth) as client:
            with pytest.raises(SystemExit):
                await _set_flame_speed(client, FIRE_ID, "0")
        captured = capsys.readouterr()
        assert "Error" in captured.out


# ---------------------------------------------------------------------------
# _set_brightness
# ---------------------------------------------------------------------------


class TestSetBrightness:
    """Tests for the _set_brightness CLI command."""

    async def test_set_brightness_low(self, mock_api, token_auth, overview_payload):
        mock_api.get(OVERVIEW_URL, payload=overview_payload)
        mock_api.post(WRITE_URL, payload={})

        async with FlameConnectClient(token_auth) as client:
            await _set_brightness(client, FIRE_ID, "low")

        key = ("POST", URL(WRITE_URL))
        calls = mock_api.requests[key]
        assert len(calls) == 1

    async def test_set_brightness_high(self, mock_api, token_auth, overview_payload):
        mock_api.get(OVERVIEW_URL, payload=overview_payload)
        mock_api.post(WRITE_URL, payload={})

        async with FlameConnectClient(token_auth) as client:
            await _set_brightness(client, FIRE_ID, "high")

        key = ("POST", URL(WRITE_URL))
        assert len(mock_api.requests[key]) == 1

    async def test_set_brightness_invalid(self, mock_api, token_auth, capsys):
        async with FlameConnectClient(token_auth) as client:
            with pytest.raises(SystemExit):
                await _set_brightness(client, FIRE_ID, "medium")
        captured = capsys.readouterr()
        assert "Error" in captured.out


# ---------------------------------------------------------------------------
# _set_heat_mode
# ---------------------------------------------------------------------------


class TestSetHeatMode:
    """Tests for the _set_heat_mode CLI command."""

    async def test_set_heat_mode_normal(self, mock_api, token_auth, overview_payload):
        mock_api.get(OVERVIEW_URL, payload=overview_payload)
        mock_api.post(WRITE_URL, payload={})

        async with FlameConnectClient(token_auth) as client:
            await _set_heat_mode(client, FIRE_ID, "normal")

        key = ("POST", URL(WRITE_URL))
        calls = mock_api.requests[key]
        assert len(calls) == 1
        body = calls[0].kwargs["json"]
        assert body["Parameters"][0]["ParameterId"] == 323

    async def test_set_heat_mode_boost(self, mock_api, token_auth, overview_payload):
        mock_api.get(OVERVIEW_URL, payload=overview_payload)
        mock_api.post(WRITE_URL, payload={})

        async with FlameConnectClient(token_auth) as client:
            await _set_heat_mode(client, FIRE_ID, "boost")

        key = ("POST", URL(WRITE_URL))
        calls = mock_api.requests[key]
        assert len(calls) == 1
        body = calls[0].kwargs["json"]
        assert body["Parameters"][0]["ParameterId"] == 323

    async def test_set_heat_mode_eco(self, mock_api, token_auth, overview_payload):
        mock_api.get(OVERVIEW_URL, payload=overview_payload)
        mock_api.post(WRITE_URL, payload={})

        async with FlameConnectClient(token_auth) as client:
            await _set_heat_mode(client, FIRE_ID, "eco")

        key = ("POST", URL(WRITE_URL))
        assert len(mock_api.requests[key]) == 1

    async def test_set_heat_mode_boost_with_duration(
        self, mock_api, token_auth, overview_payload
    ):
        mock_api.get(OVERVIEW_URL, payload=overview_payload)
        mock_api.post(WRITE_URL, payload={})

        async with FlameConnectClient(token_auth) as client:
            await _set_heat_mode(client, FIRE_ID, "boost:15")

        key = ("POST", URL(WRITE_URL))
        calls = mock_api.requests[key]
        assert len(calls) == 1
        body = calls[0].kwargs["json"]
        assert body["Parameters"][0]["ParameterId"] == 323

    async def test_set_heat_mode_boost_duration_out_of_range(
        self, mock_api, token_auth, capsys
    ):
        async with FlameConnectClient(token_auth) as client:
            with pytest.raises(SystemExit):
                await _set_heat_mode(client, FIRE_ID, "boost:25")
        captured = capsys.readouterr()
        assert "Error" in captured.out

    async def test_set_heat_mode_boost_duration_zero(
        self, mock_api, token_auth, capsys
    ):
        async with FlameConnectClient(token_auth) as client:
            with pytest.raises(SystemExit):
                await _set_heat_mode(client, FIRE_ID, "boost:0")
        captured = capsys.readouterr()
        assert "Error" in captured.out

    async def test_set_heat_mode_boost_duration_invalid_format(
        self, mock_api, token_auth, capsys
    ):
        async with FlameConnectClient(token_auth) as client:
            with pytest.raises(SystemExit):
                await _set_heat_mode(client, FIRE_ID, "boost:abc")
        captured = capsys.readouterr()
        assert "Error" in captured.out

    async def test_set_heat_mode_boost_duration_21(
        self, mock_api, token_auth, capsys
    ):
        async with FlameConnectClient(token_auth) as client:
            with pytest.raises(SystemExit):
                await _set_heat_mode(client, FIRE_ID, "boost:21")
        captured = capsys.readouterr()
        assert "Error" in captured.out

    async def test_set_heat_mode_reject_fan_only(
        self, mock_api, token_auth, capsys
    ):
        async with FlameConnectClient(token_auth) as client:
            with pytest.raises(SystemExit):
                await _set_heat_mode(client, FIRE_ID, "fan-only")
        captured = capsys.readouterr()
        assert "Error" in captured.out

    async def test_set_heat_mode_invalid(self, mock_api, token_auth, capsys):
        async with FlameConnectClient(token_auth) as client:
            with pytest.raises(SystemExit):
                await _set_heat_mode(client, FIRE_ID, "turbo")
        captured = capsys.readouterr()
        assert "Error" in captured.out


# ---------------------------------------------------------------------------
# _set_heat_temp
# ---------------------------------------------------------------------------


class TestSetHeatTemp:
    """Tests for the _set_heat_temp CLI command."""

    async def test_set_heat_temp(self, mock_api, token_auth, overview_payload):
        mock_api.get(OVERVIEW_URL, payload=overview_payload)
        mock_api.post(WRITE_URL, payload={})

        async with FlameConnectClient(token_auth) as client:
            await _set_heat_temp(client, FIRE_ID, "25.5")

        key = ("POST", URL(WRITE_URL))
        calls = mock_api.requests[key]
        assert len(calls) == 1
        body = calls[0].kwargs["json"]
        assert body["Parameters"][0]["ParameterId"] == 323


# ---------------------------------------------------------------------------
# _set_timer
# ---------------------------------------------------------------------------


class TestSetTimer:
    """Tests for the _set_timer CLI command."""

    async def test_set_timer_60(self, mock_api, token_auth):
        mock_api.post(WRITE_URL, payload={})

        async with FlameConnectClient(token_auth) as client:
            await _set_timer(client, FIRE_ID, "60")

        key = ("POST", URL(WRITE_URL))
        calls = mock_api.requests[key]
        assert len(calls) == 1
        body = calls[0].kwargs["json"]
        assert body["Parameters"][0]["ParameterId"] == 326

    async def test_set_timer_disable(self, mock_api, token_auth):
        mock_api.post(WRITE_URL, payload={})

        async with FlameConnectClient(token_auth) as client:
            await _set_timer(client, FIRE_ID, "0")

        key = ("POST", URL(WRITE_URL))
        assert len(mock_api.requests[key]) == 1

    async def test_set_timer_negative(self, mock_api, token_auth, capsys):
        async with FlameConnectClient(token_auth) as client:
            with pytest.raises(SystemExit):
                await _set_timer(client, FIRE_ID, "-1")
        captured = capsys.readouterr()
        assert "Error" in captured.out


# ---------------------------------------------------------------------------
# cmd_set dispatch
# ---------------------------------------------------------------------------


class TestCmdSetDispatch:
    """Tests for the cmd_set() dispatch function."""

    async def test_dispatch_pulsating(self, mock_api, token_auth, overview_payload):
        mock_api.get(OVERVIEW_URL, payload=overview_payload)
        mock_api.post(WRITE_URL, payload={})

        async with FlameConnectClient(token_auth) as client:
            await cmd_set(client, FIRE_ID, "pulsating", "on")

        key = ("POST", URL(WRITE_URL))
        assert len(mock_api.requests[key]) == 1

    async def test_dispatch_flame_color(
        self, mock_api, token_auth, overview_payload
    ):
        mock_api.get(OVERVIEW_URL, payload=overview_payload)
        mock_api.post(WRITE_URL, payload={})

        async with FlameConnectClient(token_auth) as client:
            await cmd_set(client, FIRE_ID, "flame-color", "blue")

        key = ("POST", URL(WRITE_URL))
        assert len(mock_api.requests[key]) == 1

    async def test_dispatch_media_theme(
        self, mock_api, token_auth, overview_payload
    ):
        mock_api.get(OVERVIEW_URL, payload=overview_payload)
        mock_api.post(WRITE_URL, payload={})

        async with FlameConnectClient(token_auth) as client:
            await cmd_set(client, FIRE_ID, "media-theme", "prism")

        key = ("POST", URL(WRITE_URL))
        assert len(mock_api.requests[key]) == 1

    async def test_dispatch_temp_unit(self, mock_api, token_auth):
        mock_api.post(WRITE_URL, payload={})

        async with FlameConnectClient(token_auth) as client:
            await cmd_set(client, FIRE_ID, "temp-unit", "celsius")

        key = ("POST", URL(WRITE_URL))
        assert len(mock_api.requests[key]) == 1

    async def test_dispatch_unknown_param(self, mock_api, token_auth, capsys):
        async with FlameConnectClient(token_auth) as client:
            with pytest.raises(SystemExit):
                await cmd_set(client, FIRE_ID, "unknown-param", "value")
        captured = capsys.readouterr()
        assert "Error" in captured.out
        assert "unknown-param" in captured.out


# ---------------------------------------------------------------------------
# _parse_color
# ---------------------------------------------------------------------------


class TestParseColor:
    """Tests for the _parse_color helper function."""

    def test_named_preset(self):
        result = _parse_color("light-red")
        assert result == RGBWColor(red=255, green=0, blue=0, white=80)

    def test_rgbw_format(self):
        result = _parse_color("100,200,50,25")
        assert result == RGBWColor(red=100, green=200, blue=50, white=25)

    def test_invalid_string(self):
        assert _parse_color("not-a-color") is None

    def test_out_of_range(self):
        assert _parse_color("256,0,0,0") is None

    def test_wrong_count(self):
        assert _parse_color("100,200,50") is None


# ---------------------------------------------------------------------------
# _set_flame_effect
# ---------------------------------------------------------------------------


class TestSetFlameEffect:
    """Tests for the _set_flame_effect CLI command."""

    async def test_set_flame_effect_on(
        self, mock_api, token_auth, overview_payload
    ):
        mock_api.get(OVERVIEW_URL, payload=overview_payload)
        mock_api.post(WRITE_URL, payload={})

        async with FlameConnectClient(token_auth) as client:
            await _set_flame_effect(client, FIRE_ID, "on")

        key = ("POST", URL(WRITE_URL))
        calls = mock_api.requests[key]
        assert len(calls) == 1
        body = calls[0].kwargs["json"]
        assert body["FireId"] == FIRE_ID
        assert len(body["Parameters"]) == 1
        assert body["Parameters"][0]["ParameterId"] == 322

    async def test_set_flame_effect_invalid(self, mock_api, token_auth, capsys):
        async with FlameConnectClient(token_auth) as client:
            with pytest.raises(SystemExit):
                await _set_flame_effect(client, FIRE_ID, "maybe")
        captured = capsys.readouterr()
        assert "Error" in captured.out


# ---------------------------------------------------------------------------
# _set_media_light
# ---------------------------------------------------------------------------


class TestSetMediaLight:
    """Tests for the _set_media_light CLI command."""

    async def test_set_media_light_on(
        self, mock_api, token_auth, overview_payload
    ):
        mock_api.get(OVERVIEW_URL, payload=overview_payload)
        mock_api.post(WRITE_URL, payload={})

        async with FlameConnectClient(token_auth) as client:
            await _set_media_light(client, FIRE_ID, "on")

        key = ("POST", URL(WRITE_URL))
        calls = mock_api.requests[key]
        assert len(calls) == 1
        body = calls[0].kwargs["json"]
        assert body["FireId"] == FIRE_ID
        assert body["Parameters"][0]["ParameterId"] == 322

    async def test_set_media_light_invalid(self, mock_api, token_auth, capsys):
        async with FlameConnectClient(token_auth) as client:
            with pytest.raises(SystemExit):
                await _set_media_light(client, FIRE_ID, "maybe")
        captured = capsys.readouterr()
        assert "Error" in captured.out


# ---------------------------------------------------------------------------
# _set_overhead_light
# ---------------------------------------------------------------------------


class TestSetOverheadLight:
    """Tests for the _set_overhead_light CLI command."""

    async def test_set_overhead_light_on(
        self, mock_api, token_auth, overview_payload
    ):
        mock_api.get(OVERVIEW_URL, payload=overview_payload)
        mock_api.post(WRITE_URL, payload={})

        async with FlameConnectClient(token_auth) as client:
            await _set_overhead_light(client, FIRE_ID, "on")

        key = ("POST", URL(WRITE_URL))
        calls = mock_api.requests[key]
        assert len(calls) == 1
        body = calls[0].kwargs["json"]
        assert body["FireId"] == FIRE_ID
        assert body["Parameters"][0]["ParameterId"] == 322

    async def test_set_overhead_light_invalid(self, mock_api, token_auth, capsys):
        async with FlameConnectClient(token_auth) as client:
            with pytest.raises(SystemExit):
                await _set_overhead_light(client, FIRE_ID, "maybe")
        captured = capsys.readouterr()
        assert "Error" in captured.out


# ---------------------------------------------------------------------------
# _set_ambient_sensor
# ---------------------------------------------------------------------------


class TestSetAmbientSensor:
    """Tests for the _set_ambient_sensor CLI command."""

    async def test_set_ambient_sensor_on(
        self, mock_api, token_auth, overview_payload
    ):
        mock_api.get(OVERVIEW_URL, payload=overview_payload)
        mock_api.post(WRITE_URL, payload={})

        async with FlameConnectClient(token_auth) as client:
            await _set_ambient_sensor(client, FIRE_ID, "on")

        key = ("POST", URL(WRITE_URL))
        calls = mock_api.requests[key]
        assert len(calls) == 1
        body = calls[0].kwargs["json"]
        assert body["FireId"] == FIRE_ID
        assert body["Parameters"][0]["ParameterId"] == 322

    async def test_set_ambient_sensor_invalid(self, mock_api, token_auth, capsys):
        async with FlameConnectClient(token_auth) as client:
            with pytest.raises(SystemExit):
                await _set_ambient_sensor(client, FIRE_ID, "maybe")
        captured = capsys.readouterr()
        assert "Error" in captured.out


# ---------------------------------------------------------------------------
# _set_media_color
# ---------------------------------------------------------------------------


class TestSetMediaColor:
    """Tests for the _set_media_color CLI command."""

    async def test_set_media_color_named(
        self, mock_api, token_auth, overview_payload
    ):
        mock_api.get(OVERVIEW_URL, payload=overview_payload)
        mock_api.post(WRITE_URL, payload={})

        async with FlameConnectClient(token_auth) as client:
            await _set_media_color(client, FIRE_ID, "light-red")

        key = ("POST", URL(WRITE_URL))
        calls = mock_api.requests[key]
        assert len(calls) == 1
        body = calls[0].kwargs["json"]
        assert body["FireId"] == FIRE_ID
        assert body["Parameters"][0]["ParameterId"] == 322

    async def test_set_media_color_rgbw(
        self, mock_api, token_auth, overview_payload
    ):
        mock_api.get(OVERVIEW_URL, payload=overview_payload)
        mock_api.post(WRITE_URL, payload={})

        async with FlameConnectClient(token_auth) as client:
            await _set_media_color(client, FIRE_ID, "255,0,0,0")

        key = ("POST", URL(WRITE_URL))
        calls = mock_api.requests[key]
        assert len(calls) == 1

    async def test_set_media_color_invalid(self, mock_api, token_auth, capsys):
        async with FlameConnectClient(token_auth) as client:
            with pytest.raises(SystemExit):
                await _set_media_color(client, FIRE_ID, "not-a-color")
        captured = capsys.readouterr()
        assert "Error" in captured.out


# ---------------------------------------------------------------------------
# _set_overhead_color
# ---------------------------------------------------------------------------


class TestSetOverheadColor:
    """Tests for the _set_overhead_color CLI command."""

    async def test_set_overhead_color_named(
        self, mock_api, token_auth, overview_payload
    ):
        mock_api.get(OVERVIEW_URL, payload=overview_payload)
        mock_api.post(WRITE_URL, payload={})

        async with FlameConnectClient(token_auth) as client:
            await _set_overhead_color(client, FIRE_ID, "dark-blue")

        key = ("POST", URL(WRITE_URL))
        calls = mock_api.requests[key]
        assert len(calls) == 1
        body = calls[0].kwargs["json"]
        assert body["FireId"] == FIRE_ID
        assert body["Parameters"][0]["ParameterId"] == 322

    async def test_set_overhead_color_rgbw(
        self, mock_api, token_auth, overview_payload
    ):
        mock_api.get(OVERVIEW_URL, payload=overview_payload)
        mock_api.post(WRITE_URL, payload={})

        async with FlameConnectClient(token_auth) as client:
            await _set_overhead_color(client, FIRE_ID, "0,0,180,0")

        key = ("POST", URL(WRITE_URL))
        calls = mock_api.requests[key]
        assert len(calls) == 1

    async def test_set_overhead_color_invalid(self, mock_api, token_auth, capsys):
        async with FlameConnectClient(token_auth) as client:
            with pytest.raises(SystemExit):
                await _set_overhead_color(client, FIRE_ID, "not-a-color")
        captured = capsys.readouterr()
        assert "Error" in captured.out
