"""Tests for FlameConnectClient with mocked HTTP responses."""

from __future__ import annotations

import json
from pathlib import Path

import aiohttp
import pytest
from aioresponses import aioresponses as aioresponses_mock
from yarl import URL

from flameconnect.auth import TokenAuth
from flameconnect.client import FlameConnectClient
from flameconnect.const import API_BASE
from flameconnect.exceptions import ApiError
from flameconnect.models import (
    ConnectionState,
    ErrorParam,
    Fire,
    FireMode,
    FlameEffect,
    FlameEffectParam,
    HeatControl,
    HeatMode,
    HeatModeParam,
    HeatParam,
    HeatStatus,
    LogEffectParam,
    MediaTheme,
    ModeParam,
    SoftwareVersionParam,
    SoundParam,
    TempUnitParam,
    TimerParam,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def mock_api():
    with aioresponses_mock() as m:
        yield m


@pytest.fixture
def token_auth() -> TokenAuth:
    return TokenAuth("test-token-123")


@pytest.fixture
def get_fires_payload() -> list[dict]:
    return json.loads((FIXTURES_DIR / "get_fires.json").read_text())


@pytest.fixture
def get_fire_overview_payload() -> dict:
    return json.loads((FIXTURES_DIR / "get_fire_overview.json").read_text())


# ---------------------------------------------------------------------------
# get_fires
# ---------------------------------------------------------------------------


class TestGetFires:
    """Test the get_fires() method."""

    async def test_returns_fire_list(self, mock_api, token_auth, get_fires_payload):
        url = f"{API_BASE}/api/Fires/GetFires"
        mock_api.get(url, payload=get_fires_payload)

        async with FlameConnectClient(token_auth) as client:
            fires = await client.get_fires()

        assert len(fires) == 1
        fire = fires[0]
        assert isinstance(fire, Fire)
        assert fire.fire_id == "test-fire-001"
        assert fire.friendly_name == "Living Room"
        assert fire.brand == "Dimplex"
        assert fire.product_type == "Bold Ignite XL"
        assert fire.product_model == "BIX-50"
        assert fire.item_code == "ABC123"
        assert fire.connection_state == ConnectionState.CONNECTED
        assert fire.with_heat is True
        assert fire.is_iot_fire is True

    async def test_empty_fires(self, mock_api, token_auth):
        url = f"{API_BASE}/api/Fires/GetFires"
        mock_api.get(url, payload=[])

        async with FlameConnectClient(token_auth) as client:
            fires = await client.get_fires()

        assert fires == []


# ---------------------------------------------------------------------------
# get_fire_overview
# ---------------------------------------------------------------------------


class TestGetFireOverview:
    """Test the get_fire_overview() method with fully decoded parameters."""

    async def test_decodes_all_parameters(
        self, mock_api, token_auth, get_fire_overview_payload
    ):
        fire_id = "test-fire-001"
        url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        mock_api.get(url, payload=get_fire_overview_payload)

        async with FlameConnectClient(token_auth) as client:
            overview = await client.get_fire_overview(fire_id)

        assert overview.fire.fire_id == fire_id
        assert overview.fire.friendly_name == "Living Room"
        assert len(overview.parameters) == 10

        # Verify each decoded parameter type
        param_types = {type(p) for p in overview.parameters}
        assert ModeParam in param_types
        assert FlameEffectParam in param_types
        assert HeatParam in param_types
        assert HeatModeParam in param_types
        assert TimerParam in param_types
        assert SoftwareVersionParam in param_types
        assert ErrorParam in param_types
        assert TempUnitParam in param_types
        assert SoundParam in param_types
        assert LogEffectParam in param_types

    async def test_mode_param_values(
        self, mock_api, token_auth, get_fire_overview_payload
    ):
        fire_id = "test-fire-001"
        url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        mock_api.get(url, payload=get_fire_overview_payload)

        async with FlameConnectClient(token_auth) as client:
            overview = await client.get_fire_overview(fire_id)

        mode = next(p for p in overview.parameters if isinstance(p, ModeParam))
        assert mode.mode == FireMode.MANUAL
        assert mode.temperature == pytest.approx(22.5)

    async def test_flame_effect_param_values(
        self, mock_api, token_auth, get_fire_overview_payload
    ):
        fire_id = "test-fire-001"
        url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        mock_api.get(url, payload=get_fire_overview_payload)

        async with FlameConnectClient(token_auth) as client:
            overview = await client.get_fire_overview(fire_id)

        flame = next(p for p in overview.parameters if isinstance(p, FlameEffectParam))
        assert flame.flame_effect == FlameEffect.ON
        assert flame.flame_speed == 3
        assert flame.brightness == 200
        assert flame.media_theme == MediaTheme.KALEIDOSCOPE
        assert flame.media_color.red == 100
        assert flame.media_color.green == 75
        assert flame.media_color.blue == 50
        assert flame.media_color.white == 25

    async def test_heat_param_values(
        self, mock_api, token_auth, get_fire_overview_payload
    ):
        fire_id = "test-fire-001"
        url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        mock_api.get(url, payload=get_fire_overview_payload)

        async with FlameConnectClient(token_auth) as client:
            overview = await client.get_fire_overview(fire_id)

        heat = next(p for p in overview.parameters if isinstance(p, HeatParam))
        assert heat.heat_status == HeatStatus.ON
        assert heat.heat_mode == HeatMode.NORMAL
        assert heat.setpoint_temperature == pytest.approx(22.0)
        assert heat.boost_duration == 1  # wire 0 → model 1 (1-indexed)

    async def test_software_version_values(
        self, mock_api, token_auth, get_fire_overview_payload
    ):
        fire_id = "test-fire-001"
        url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        mock_api.get(url, payload=get_fire_overview_payload)

        async with FlameConnectClient(token_auth) as client:
            overview = await client.get_fire_overview(fire_id)

        sw = next(p for p in overview.parameters if isinstance(p, SoftwareVersionParam))
        assert sw.ui_major == 1
        assert sw.ui_minor == 2
        assert sw.ui_test == 3
        assert sw.control_major == 4
        assert sw.control_minor == 5
        assert sw.control_test == 6
        assert sw.relay_major == 7
        assert sw.relay_minor == 8
        assert sw.relay_test == 9


# ---------------------------------------------------------------------------
# write_parameters
# ---------------------------------------------------------------------------


class TestWriteParameters:
    """Test the write_parameters() method."""

    async def test_sends_correct_payload(self, mock_api, token_auth):
        url = f"{API_BASE}/api/Fires/WriteWifiParameters"
        mock_api.post(url, payload={})

        mode = ModeParam(mode=FireMode.MANUAL, temperature=22.0)

        async with FlameConnectClient(token_auth) as client:
            await client.write_parameters("test-fire-001", [mode])

        # Verify the request was made
        key = ("POST", URL(url))
        calls = mock_api.requests[key]
        assert len(calls) == 1

        body = calls[0].kwargs["json"]
        assert body["FireId"] == "test-fire-001"
        assert len(body["Parameters"]) == 1
        assert body["Parameters"][0]["ParameterId"] == 321
        # Value should be a base64 string
        assert isinstance(body["Parameters"][0]["Value"], str)

    async def test_multiple_params(self, mock_api, token_auth):
        url = f"{API_BASE}/api/Fires/WriteWifiParameters"
        mock_api.post(url, payload={})

        mode = ModeParam(mode=FireMode.MANUAL, temperature=22.0)
        heat_mode = HeatModeParam(heat_control=HeatControl.ENABLED)

        async with FlameConnectClient(token_auth) as client:
            await client.write_parameters("test-fire-001", [mode, heat_mode])

        key = ("POST", URL(url))
        calls = mock_api.requests[key]
        body = calls[0].kwargs["json"]
        assert len(body["Parameters"]) == 2
        param_ids = {p["ParameterId"] for p in body["Parameters"]}
        assert param_ids == {321, 325}


# ---------------------------------------------------------------------------
# turn_on
# ---------------------------------------------------------------------------


class TestTurnOn:
    """Test the turn_on() convenience method."""

    async def test_turn_on_preserves_settings(
        self, mock_api, token_auth, get_fire_overview_payload
    ):
        fire_id = "test-fire-001"
        overview_url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        write_url = f"{API_BASE}/api/Fires/WriteWifiParameters"

        mock_api.get(overview_url, payload=get_fire_overview_payload)
        mock_api.post(write_url, payload={})

        async with FlameConnectClient(token_auth) as client:
            await client.turn_on(fire_id)

        # Verify write was called
        key = ("POST", URL(write_url))
        calls = mock_api.requests[key]
        assert len(calls) == 1

        body = calls[0].kwargs["json"]
        assert body["FireId"] == fire_id

        # Should write Mode (321) and FlameEffect (322)
        param_ids = {p["ParameterId"] for p in body["Parameters"]}
        assert 321 in param_ids
        assert 322 in param_ids


# ---------------------------------------------------------------------------
# turn_off
# ---------------------------------------------------------------------------


class TestTurnOff:
    """Test the turn_off() convenience method."""

    async def test_turn_off_sends_standby(self, mock_api, token_auth):
        fire_id = "test-fire-001"
        write_url = f"{API_BASE}/api/Fires/WriteWifiParameters"
        mock_api.post(write_url, payload={})

        async with FlameConnectClient(token_auth) as client:
            await client.turn_off(fire_id)

        key = ("POST", URL(write_url))
        calls = mock_api.requests[key]
        assert len(calls) == 1

        body = calls[0].kwargs["json"]
        assert body["FireId"] == fire_id
        assert len(body["Parameters"]) == 1
        assert body["Parameters"][0]["ParameterId"] == 321


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestApiErrorHandling:
    """Test non-2xx response handling."""

    async def test_401_raises_api_error(self, mock_api, token_auth):
        url = f"{API_BASE}/api/Fires/GetFires"
        mock_api.get(url, status=401, body="Unauthorized")

        async with FlameConnectClient(token_auth) as client:
            with pytest.raises(ApiError) as exc_info:
                await client.get_fires()

        assert exc_info.value.status == 401

    async def test_500_raises_api_error(self, mock_api, token_auth):
        url = f"{API_BASE}/api/Fires/GetFires"
        mock_api.get(url, status=500, body="Internal Server Error")

        async with FlameConnectClient(token_auth) as client:
            with pytest.raises(ApiError) as exc_info:
                await client.get_fires()

        assert exc_info.value.status == 500

    async def test_404_raises_api_error(self, mock_api, token_auth):
        fire_id = "nonexistent"
        url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        mock_api.get(url, status=404, body="Not Found")

        async with FlameConnectClient(token_auth) as client:
            with pytest.raises(ApiError) as exc_info:
                await client.get_fire_overview(fire_id)

        assert exc_info.value.status == 404

    async def test_no_session_raises_runtime_error(self, token_auth):
        """Using client without context manager or session should raise."""
        client = FlameConnectClient(token_auth)
        with pytest.raises(RuntimeError, match="No aiohttp session"):
            await client.get_fires()

    async def test_external_session(self, mock_api, token_auth):
        """Client should work with an externally-provided session."""
        url = f"{API_BASE}/api/Fires/GetFires"
        mock_api.get(url, payload=[])

        async with (
            aiohttp.ClientSession() as session,
            FlameConnectClient(token_auth, session=session) as client,
        ):
            fires = await client.get_fires()

        assert fires == []
