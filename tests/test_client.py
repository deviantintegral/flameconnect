"""Tests for FlameConnectClient with mocked HTTP responses."""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path

import aiohttp
import pytest
from aioresponses import aioresponses as aioresponses_mock
from yarl import URL

from flameconnect.auth import TokenAuth
from flameconnect.client import (
    FlameConnectClient,
    _get_parameter_id,
    _parse_fire,
    _parse_fire_features,
)
from flameconnect.const import API_BASE, DEFAULT_HEADERS
from flameconnect.exceptions import ApiError, FireUnavailableError
from flameconnect.models import (
    Brightness,
    ConnectionState,
    ErrorParam,
    Fire,
    FireFeatures,
    FireMode,
    FireOverviewResultCode,
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
from flameconnect.protocol import encode_parameter

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


def _make_overview_payload(
    fire_id="test-fire-001",
    friendly_name=None,
    brand=None,
    product_type=None,
    product_model=None,
    item_code=None,
    connection_state=None,
    with_heat=None,
    is_iot_fire=None,
    parameters=None,
    result_code=0,
    fire_details=None,
):
    """Build a minimal get_fire_overview response payload.

    Only includes keys that are explicitly provided (non-None),
    allowing tests to exercise the .get() fallback defaults.
    """
    wifi: dict = {"FireId": fire_id}
    if friendly_name is not None:
        wifi["FriendlyName"] = friendly_name
    if brand is not None:
        wifi["Brand"] = brand
    if product_type is not None:
        wifi["ProductType"] = product_type
    if product_model is not None:
        wifi["ProductModel"] = product_model
    if item_code is not None:
        wifi["ItemCode"] = item_code
    if connection_state is not None:
        wifi["IoTConnectionState"] = connection_state
    if with_heat is not None:
        wifi["WithHeat"] = with_heat
    if is_iot_fire is not None:
        wifi["IsIotFire"] = is_iot_fire
    if parameters is not None:
        wifi["Parameters"] = parameters
    payload: dict = {"ResultCode": result_code, "WifiFireOverview": wifi}
    if fire_details is not None:
        payload["FireDetails"] = fire_details
    return payload


# -------------------------------------------------------------------
# get_fires
# -------------------------------------------------------------------


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

        # FireFeatures assertions
        assert isinstance(fire.features, FireFeatures)
        assert fire.features.sound is True
        assert fire.features.simple_heat is True
        assert fire.features.advanced_heat is True
        assert fire.features.flame_height is True
        assert fire.features.rgb_flame_accent is True
        assert fire.features.moods is False

    async def test_empty_fires(self, mock_api, token_auth):
        url = f"{API_BASE}/api/Fires/GetFires"
        mock_api.get(url, payload=[])

        async with FlameConnectClient(token_auth) as client:
            fires = await client.get_fires()

        assert fires == []

    async def test_get_fires_uses_uppercase_get(
        self, mock_api, token_auth, get_fires_payload
    ):
        """Verify the HTTP method is uppercase GET.

        Kills mutant get_fires__mutmut_8: "GET" -> "get".
        """
        url = f"{API_BASE}/api/Fires/GetFires"
        mock_api.get(url, payload=get_fires_payload)

        async with FlameConnectClient(token_auth) as client:
            await client.get_fires()

        key = ("GET", URL(url))
        assert key in mock_api.requests
        assert len(mock_api.requests[key]) == 1


# -------------------------------------------------------------------
# get_fire_overview
# -------------------------------------------------------------------


class TestGetFireOverview:
    """Test the get_fire_overview() method."""

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

        # FireFeatures assertions
        assert isinstance(overview.fire.features, FireFeatures)
        assert overview.fire.features.sound is True
        assert overview.fire.features.simple_heat is True
        assert overview.fire.features.advanced_heat is True
        assert overview.fire.features.flame_height is True
        assert overview.fire.features.rgb_flame_accent is True
        assert overview.fire.features.moods is False

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
        assert mode.target_temperature == pytest.approx(22.5)

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
        assert flame.brightness == Brightness.LOW
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
        assert heat.boost_duration == 1

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

    async def test_overview_uses_uppercase_get(
        self, mock_api, token_auth, get_fire_overview_payload
    ):
        """Kills mutant overview__mutmut_8: 'GET' -> 'get'."""
        fire_id = "test-fire-001"
        url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        mock_api.get(url, payload=get_fire_overview_payload)

        async with FlameConnectClient(token_auth) as client:
            await client.get_fire_overview(fire_id)

        key = ("GET", URL(url))
        assert key in mock_api.requests

    async def test_overview_fire_fields_from_fixture(
        self, mock_api, token_auth, get_fire_overview_payload
    ):
        """Assert all Fire fields are parsed from overview.

        Kills mutants 17-23 (brand=None, product_type=None, etc.)
        and mutants 46-102 (wrong .get() keys/defaults).
        """
        fire_id = "test-fire-001"
        url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        mock_api.get(url, payload=get_fire_overview_payload)

        async with FlameConnectClient(token_auth) as client:
            overview = await client.get_fire_overview(fire_id)

        f = overview.fire
        assert f.fire_id == "test-fire-001"
        assert f.friendly_name == "Living Room"
        assert f.brand == "Dimplex"
        assert f.product_type == "Bold Ignite XL"
        assert f.product_model == "BIX-50"
        assert f.item_code == "ABC123"
        assert f.connection_state == ConnectionState.CONNECTED
        assert f.with_heat is True
        assert f.is_iot_fire is True

    async def test_overview_defaults_when_keys_missing(self, mock_api, token_auth):
        """When optional keys are absent, defaults are used.

        Kills mutants for .get() default values (brand="",
        product_type="", etc.) and .get() key name mutations.
        """
        fire_id = "minimal-fire"
        url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        payload = _make_overview_payload(fire_id=fire_id, parameters=[])
        mock_api.get(url, payload=payload)

        async with FlameConnectClient(token_auth) as client:
            overview = await client.get_fire_overview(fire_id)

        f = overview.fire
        # FriendlyName missing -> defaults to FireId
        assert f.friendly_name == fire_id
        # String fields default to ""
        assert f.brand == ""
        assert f.product_type == ""
        assert f.product_model == ""
        assert f.item_code == ""
        # IoTConnectionState missing -> defaults to 0 (UNKNOWN)
        assert f.connection_state == ConnectionState.UNKNOWN
        # Booleans default to False
        assert f.with_heat is False
        assert f.is_iot_fire is False
        # No parameters
        assert overview.parameters == []

    async def test_overview_no_parameters_key(self, mock_api, token_auth):
        """When Parameters key is absent, defaults to empty list.

        Kills mutants 105/107: Parameters default None or removed.
        """
        fire_id = "no-params-fire"
        url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        # Don't include "Parameters" key at all
        payload = {"WifiFireOverview": {"FireId": fire_id}}
        mock_api.get(url, payload=payload)

        async with FlameConnectClient(token_auth) as client:
            overview = await client.get_fire_overview(fire_id)

        assert overview.parameters == []

    async def test_fire_features_default_when_missing(self, mock_api, token_auth):
        """When FireFeature key is absent, features defaults to all-false."""
        fire_id = "no-features-fire"
        url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        payload = _make_overview_payload(fire_id=fire_id, parameters=[])
        mock_api.get(url, payload=payload)

        async with FlameConnectClient(token_auth) as client:
            overview = await client.get_fire_overview(fire_id)

        features = overview.fire.features
        assert isinstance(features, FireFeatures)
        assert features == FireFeatures()

    async def test_continue_on_decode_failure_not_break(self, mock_api, token_auth):
        """After a bad parameter, good ones still decode.

        Kills mutant 135: continue -> break. Place the bad
        param between two good ones.
        """
        fire_id = "test-fire-001"
        url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        mode_val = encode_parameter(
            ModeParam(
                mode=FireMode.MANUAL,
                target_temperature=22.0,
            )
        )
        heat_mode_val = encode_parameter(
            HeatModeParam(heat_control=HeatControl.ENABLED)
        )
        payload = _make_overview_payload(
            fire_id=fire_id,
            parameters=[
                {"ParameterId": 321, "Value": mode_val},
                # Bad param (truncated FlameEffect)
                {"ParameterId": 322, "Value": "AA=="},
                # Good param after bad one
                {"ParameterId": 325, "Value": heat_mode_val},
            ],
        )
        mock_api.get(url, payload=payload)

        async with FlameConnectClient(token_auth) as client:
            overview = await client.get_fire_overview(fire_id)

        # Both good params should be present
        assert len(overview.parameters) == 2
        types = [type(p) for p in overview.parameters]
        assert ModeParam in types
        assert HeatModeParam in types


# -------------------------------------------------------------------
# FireUnavailableError / ResultCode handling
# -------------------------------------------------------------------


class TestFireOverviewResultCode:
    """Test ResultCode handling in get_fire_overview."""

    @pytest.mark.parametrize(
        ("code", "expected_code"),
        [
            (1, FireOverviewResultCode.FIRE_OFFLINE),
            (2, FireOverviewResultCode.FAILED),
            (3, FireOverviewResultCode.FIRE_NO_LONGER_AVAILABLE),
            (4, FireOverviewResultCode.UPDATING_FIRMWARE),
        ],
    )
    async def test_non_success_result_code_raises(
        self, mock_api, token_auth, code, expected_code
    ):
        fire_id = "test-fire-001"
        url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        payload = {"ResultCode": code, "WifiFireOverview": None}
        mock_api.get(url, payload=payload)

        async with FlameConnectClient(token_auth) as client:
            with pytest.raises(FireUnavailableError) as exc_info:
                await client.get_fire_overview(fire_id)

        assert exc_info.value.result_code == expected_code
        assert exc_info.value.fire is None

    async def test_offline_with_fire_details(self, mock_api, token_auth):
        fire_id = "test-fire-001"
        url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        fire_details = {
            "FireId": fire_id,
            "FriendlyName": "Living Room",
            "Brand": "Dimplex",
            "ProductType": "Optiflame V1",
            "ProductModel": "OPT-V1",
            "ItemCode": "XYZ",
            "IoTConnectionState": 1,
            "WithHeat": False,
            "IsIotFire": True,
            "FireFeature": {"Sound": True},
        }
        payload = {
            "ResultCode": 1,
            "WifiFireOverview": None,
            "FireDetails": fire_details,
        }
        mock_api.get(url, payload=payload)

        async with FlameConnectClient(token_auth) as client:
            with pytest.raises(FireUnavailableError) as exc_info:
                await client.get_fire_overview(fire_id)

        assert exc_info.value.result_code == FireOverviewResultCode.FIRE_OFFLINE
        assert exc_info.value.fire is not None
        assert exc_info.value.fire.fire_id == fire_id
        assert exc_info.value.fire.friendly_name == "Living Room"
        assert exc_info.value.fire.brand == "Dimplex"
        assert exc_info.value.fire.features.sound is True

    async def test_offline_without_fire_details(self, mock_api, token_auth):
        fire_id = "test-fire-001"
        url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        payload = {"ResultCode": 1, "WifiFireOverview": None}
        mock_api.get(url, payload=payload)

        async with FlameConnectClient(token_auth) as client:
            with pytest.raises(FireUnavailableError) as exc_info:
                await client.get_fire_overview(fire_id)

        assert exc_info.value.fire is None

    async def test_offline_with_null_fire_details(self, mock_api, token_auth):
        fire_id = "test-fire-001"
        url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        payload = {
            "ResultCode": 1,
            "WifiFireOverview": None,
            "FireDetails": None,
        }
        mock_api.get(url, payload=payload)

        async with FlameConnectClient(token_auth) as client:
            with pytest.raises(FireUnavailableError) as exc_info:
                await client.get_fire_overview(fire_id)

        assert exc_info.value.fire is None

    async def test_malformed_fire_details_degrades_gracefully(
        self, mock_api, token_auth
    ):
        fire_id = "test-fire-001"
        url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        payload = {
            "ResultCode": 1,
            "WifiFireOverview": None,
            "FireDetails": {"broken": "data"},  # missing FireId
        }
        mock_api.get(url, payload=payload)

        async with FlameConnectClient(token_auth) as client:
            with pytest.raises(FireUnavailableError) as exc_info:
                await client.get_fire_overview(fire_id)

        assert exc_info.value.result_code == FireOverviewResultCode.FIRE_OFFLINE
        assert exc_info.value.fire is None

    async def test_omitted_result_code_defaults_to_success(self, mock_api, token_auth):
        """Backward compat: responses without ResultCode work as before."""
        fire_id = "test-fire-001"
        url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        payload = {
            "WifiFireOverview": {
                "FireId": fire_id,
                "Parameters": [],
            }
        }
        mock_api.get(url, payload=payload)

        async with FlameConnectClient(token_auth) as client:
            overview = await client.get_fire_overview(fire_id)

        assert overview.fire.fire_id == fire_id

    async def test_unknown_result_code_raises(self, mock_api, token_auth):
        fire_id = "test-fire-001"
        url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        payload = {"ResultCode": 99, "WifiFireOverview": None}
        mock_api.get(url, payload=payload)

        async with FlameConnectClient(token_auth) as client:
            with pytest.raises(FireUnavailableError) as exc_info:
                await client.get_fire_overview(fire_id)

        assert exc_info.value.result_code == 99

    async def test_success_result_code_returns_overview(self, mock_api, token_auth):
        fire_id = "test-fire-001"
        url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        payload = _make_overview_payload(result_code=0)
        mock_api.get(url, payload=payload)

        async with FlameConnectClient(token_auth) as client:
            overview = await client.get_fire_overview(fire_id)

        assert overview.fire.fire_id == fire_id

    async def test_turn_on_propagates_fire_unavailable(self, mock_api, token_auth):
        fire_id = "test-fire-001"
        url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        payload = {"ResultCode": 1, "WifiFireOverview": None}
        mock_api.get(url, payload=payload)

        async with FlameConnectClient(token_auth) as client:
            with pytest.raises(FireUnavailableError):
                await client.turn_on(fire_id)

    async def test_turn_off_propagates_fire_unavailable(self, mock_api, token_auth):
        fire_id = "test-fire-001"
        url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        payload = {"ResultCode": 1, "WifiFireOverview": None}
        mock_api.get(url, payload=payload)

        async with FlameConnectClient(token_auth) as client:
            with pytest.raises(FireUnavailableError):
                await client.turn_off(fire_id)

    async def test_fire_unavailable_error_message_includes_label(self):
        exc = FireUnavailableError(FireOverviewResultCode.FIRE_OFFLINE)
        assert "FIRE_OFFLINE" in str(exc)

    async def test_fire_unavailable_error_unknown_code_message(self):
        exc = FireUnavailableError(99)
        assert "UNKNOWN(99)" in str(exc)

    async def test_fire_unavailable_inherits_flameconnect_error(self):
        from flameconnect.exceptions import FlameConnectError

        exc = FireUnavailableError(FireOverviewResultCode.FAILED)
        assert isinstance(exc, FlameConnectError)


class TestParseFireHelper:
    """Test the _parse_fire helper function."""

    def test_complete_data(self):
        data = {
            "FireId": "f-1",
            "FriendlyName": "Kitchen",
            "Brand": "Faber",
            "ProductType": "PT",
            "ProductModel": "PM",
            "ItemCode": "IC",
            "IoTConnectionState": 2,
            "WithHeat": True,
            "IsIotFire": True,
            "FireFeature": {"Sound": True},
        }
        fire = _parse_fire(data)
        assert fire.fire_id == "f-1"
        assert fire.friendly_name == "Kitchen"
        assert fire.brand == "Faber"
        assert fire.connection_state == ConnectionState.CONNECTED
        assert fire.with_heat is True
        assert fire.features.sound is True

    def test_minimal_data(self):
        data = {"FireId": "f-2"}
        fire = _parse_fire(data)
        assert fire.fire_id == "f-2"
        assert fire.friendly_name == "f-2"  # defaults to fire_id
        assert fire.brand == ""
        assert fire.connection_state == ConnectionState.UNKNOWN
        assert fire.with_heat is False

    def test_features_override(self):
        data = {"FireId": "f-3", "FireFeature": {"Sound": True}}
        custom = FireFeatures(advanced_heat=True)
        fire = _parse_fire(data, features=custom)
        assert fire.features.advanced_heat is True
        assert fire.features.sound is False  # custom overrides data


# -------------------------------------------------------------------
# write_parameters
# -------------------------------------------------------------------


class TestWriteParameters:
    """Test the write_parameters() method."""

    async def test_sends_correct_payload(self, mock_api, token_auth):
        url = f"{API_BASE}/api/Fires/WriteWifiParameters"
        mock_api.post(url, payload={})

        mode = ModeParam(mode=FireMode.MANUAL, target_temperature=22.0)

        async with FlameConnectClient(token_auth) as client:
            await client.write_parameters("test-fire-001", [mode])

        key = ("POST", URL(url))
        calls = mock_api.requests[key]
        assert len(calls) == 1

        body = calls[0].kwargs["json"]
        assert body["FireId"] == "test-fire-001"
        assert len(body["Parameters"]) == 1
        assert body["Parameters"][0]["ParameterId"] == 321
        assert isinstance(body["Parameters"][0]["Value"], str)

    async def test_multiple_params(self, mock_api, token_auth):
        url = f"{API_BASE}/api/Fires/WriteWifiParameters"
        mock_api.post(url, payload={})

        mode = ModeParam(mode=FireMode.MANUAL, target_temperature=22.0)
        heat_mode = HeatModeParam(heat_control=HeatControl.ENABLED)

        async with FlameConnectClient(token_auth) as client:
            await client.write_parameters("test-fire-001", [mode, heat_mode])

        key = ("POST", URL(url))
        calls = mock_api.requests[key]
        body = calls[0].kwargs["json"]
        assert len(body["Parameters"]) == 2
        param_ids = {p["ParameterId"] for p in body["Parameters"]}
        assert param_ids == {321, 325}

    async def test_write_uses_post_method(self, mock_api, token_auth):
        """Verify write uses POST (not lowercase)."""
        url = f"{API_BASE}/api/Fires/WriteWifiParameters"
        mock_api.post(url, payload={})

        mode = ModeParam(mode=FireMode.MANUAL, target_temperature=22.0)

        async with FlameConnectClient(token_auth) as client:
            await client.write_parameters("fire-1", [mode])

        key = ("POST", URL(url))
        assert key in mock_api.requests


# -------------------------------------------------------------------
# turn_on
# -------------------------------------------------------------------


class TestTurnOn:
    """Test the turn_on() convenience method."""

    async def test_turn_on_preserves_settings(
        self,
        mock_api,
        token_auth,
        get_fire_overview_payload,
    ):
        fire_id = "test-fire-001"
        overview_url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        write_url = f"{API_BASE}/api/Fires/WriteWifiParameters"

        mock_api.get(overview_url, payload=get_fire_overview_payload)
        mock_api.post(write_url, payload={})

        async with FlameConnectClient(token_auth) as client:
            await client.turn_on(fire_id)

        key = ("POST", URL(write_url))
        calls = mock_api.requests[key]
        assert len(calls) == 1

        body = calls[0].kwargs["json"]
        assert body["FireId"] == fire_id

        param_ids = {p["ParameterId"] for p in body["Parameters"]}
        assert 321 in param_ids
        assert 322 in param_ids

    async def test_turn_on_preserves_existing_temperature(
        self,
        mock_api,
        token_auth,
        get_fire_overview_payload,
    ):
        """Verify turn_on preserves the current temperature.

        Kills turn_on__mutmut_5 (current_mode = None) and
        turn_on__mutmut_8 (22.0 -> 23.0).
        The fixture has target_temperature=22.5 which should
        be preserved in the written ModeParam.
        """
        fire_id = "test-fire-001"
        overview_url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        write_url = f"{API_BASE}/api/Fires/WriteWifiParameters"
        mock_api.get(overview_url, payload=get_fire_overview_payload)
        mock_api.post(write_url, payload={})

        async with FlameConnectClient(token_auth) as client:
            await client.turn_on(fire_id)

        key = ("POST", URL(write_url))
        body = mock_api.requests[key][0].kwargs["json"]
        # Decode the written ModeParam
        mode_wire = next(p for p in body["Parameters"] if p["ParameterId"] == 321)
        raw = base64.b64decode(mode_wire["Value"])
        # Byte 3 is mode (1=MANUAL), bytes 4-5 are temperature
        assert raw[3] == FireMode.MANUAL
        temp = float(raw[4]) + float(raw[5]) / 10.0
        assert temp == pytest.approx(22.5)

    async def test_turn_on_flame_effect_set_to_on(
        self,
        mock_api,
        token_auth,
        get_fire_overview_payload,
    ):
        """Verify turn_on sets flame_effect=ON.

        Kills turn_on__mutmut_20: replace(current_flame, ) with
        no args (which would preserve OFF if it was OFF).
        """
        fire_id = "test-fire-001"
        overview_url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        write_url = f"{API_BASE}/api/Fires/WriteWifiParameters"
        mock_api.get(overview_url, payload=get_fire_overview_payload)
        mock_api.post(write_url, payload={})

        async with FlameConnectClient(token_auth) as client:
            await client.turn_on(fire_id)

        key = ("POST", URL(write_url))
        body = mock_api.requests[key][0].kwargs["json"]
        flame_wire = next(p for p in body["Parameters"] if p["ParameterId"] == 322)
        raw = base64.b64decode(flame_wire["Value"])
        # Byte 3 is flame_effect: 1=ON
        assert raw[3] == FlameEffect.ON

    async def test_turn_on_default_temp_no_mode_param(self, mock_api, token_auth):
        """When no ModeParam exists, default temp is 22.0.

        Kills turn_on__mutmut_3 (current_mode="" instead of
        None), turn_on__mutmut_4, turn_on__mutmut_8.
        """
        fire_id = "no-mode-fire"
        overview_url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        write_url = f"{API_BASE}/api/Fires/WriteWifiParameters"
        # Overview with NO parameters
        payload = _make_overview_payload(fire_id=fire_id, parameters=[])
        mock_api.get(overview_url, payload=payload)
        mock_api.post(write_url, payload={})

        async with FlameConnectClient(token_auth) as client:
            await client.turn_on(fire_id)

        key = ("POST", URL(write_url))
        body = mock_api.requests[key][0].kwargs["json"]
        mode_wire = next(p for p in body["Parameters"] if p["ParameterId"] == 321)
        raw = base64.b64decode(mode_wire["Value"])
        temp = float(raw[4]) + float(raw[5]) / 10.0
        assert temp == pytest.approx(22.0)
        # No FlameEffectParam in overview -> only ModeParam
        assert len(body["Parameters"]) == 1

    async def test_turn_on_sets_flame_on_when_initially_off(self, mock_api, token_auth):
        """When flame effect is OFF, turn_on sets it to ON.

        Kills turn_on__mutmut_20: replace(current_flame, )
        would leave flame_effect=OFF unchanged; the correct
        code sets it to ON.
        """
        fire_id = "flame-off-fire"
        overview_url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        write_url = f"{API_BASE}/api/Fires/WriteWifiParameters"
        mode_val = encode_parameter(
            ModeParam(
                mode=FireMode.STANDBY,
                target_temperature=20.0,
            )
        )
        flame_off_val = encode_parameter(
            FlameEffectParam(
                flame_effect=FlameEffect.OFF,
                flame_speed=3,
                brightness=Brightness.LOW,
                pulsating_effect=PulsatingEffect.OFF,
                media_theme=MediaTheme.USER_DEFINED,
                media_light=LightStatus.OFF,
                media_color=RGBWColor(0, 0, 0, 0),
                overhead_light=LightStatus.OFF,
                overhead_color=RGBWColor(0, 0, 0, 0),
                light_status=LightStatus.OFF,
                flame_color=FlameEffect.OFF,
                ambient_sensor=LightStatus.OFF,
            )
        )
        payload = _make_overview_payload(
            fire_id=fire_id,
            parameters=[
                {"ParameterId": 321, "Value": mode_val},
                {
                    "ParameterId": 322,
                    "Value": flame_off_val,
                },
            ],
        )
        mock_api.get(overview_url, payload=payload)
        mock_api.post(write_url, payload={})

        async with FlameConnectClient(token_auth) as client:
            await client.turn_on(fire_id)

        key = ("POST", URL(write_url))
        body = mock_api.requests[key][0].kwargs["json"]
        flame_wire = next(p for p in body["Parameters"] if p["ParameterId"] == 322)
        raw = base64.b64decode(flame_wire["Value"])
        # Byte 3 is flame_effect: must be 1 (ON)
        assert raw[3] == FlameEffect.ON

    async def test_turn_on_no_flame_param_writes_only_mode(self, mock_api, token_auth):
        """When no FlameEffectParam, only ModeParam is written.

        Kills turn_on__mutmut_4 (current_flame="" instead of
        None).
        """
        fire_id = "no-flame-fire"
        overview_url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        write_url = f"{API_BASE}/api/Fires/WriteWifiParameters"
        mode_val = encode_parameter(
            ModeParam(
                mode=FireMode.STANDBY,
                target_temperature=20.0,
            )
        )
        payload = _make_overview_payload(
            fire_id=fire_id,
            parameters=[
                {"ParameterId": 321, "Value": mode_val},
            ],
        )
        mock_api.get(overview_url, payload=payload)
        mock_api.post(write_url, payload={})

        async with FlameConnectClient(token_auth) as client:
            await client.turn_on(fire_id)

        key = ("POST", URL(write_url))
        body = mock_api.requests[key][0].kwargs["json"]
        # Only ModeParam, no FlameEffectParam
        assert len(body["Parameters"]) == 1
        assert body["Parameters"][0]["ParameterId"] == 321


# -------------------------------------------------------------------
# turn_off
# -------------------------------------------------------------------


class TestTurnOff:
    """Test the turn_off() convenience method."""

    async def test_turn_off_sends_standby(
        self,
        mock_api,
        token_auth,
        get_fire_overview_payload,
    ):
        fire_id = "test-fire-001"
        overview_url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        write_url = f"{API_BASE}/api/Fires/WriteWifiParameters"
        mock_api.get(overview_url, payload=get_fire_overview_payload)
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

    async def test_turn_off_preserves_temperature(
        self,
        mock_api,
        token_auth,
        get_fire_overview_payload,
    ):
        """Verify turn_off preserves existing temperature.

        Kills turn_off__mutmut_4 (current_mode = None) and
        temperature is read from existing ModeParam.
        """
        fire_id = "test-fire-001"
        overview_url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        write_url = f"{API_BASE}/api/Fires/WriteWifiParameters"
        mock_api.get(overview_url, payload=get_fire_overview_payload)
        mock_api.post(write_url, payload={})

        async with FlameConnectClient(token_auth) as client:
            await client.turn_off(fire_id)

        key = ("POST", URL(write_url))
        body = mock_api.requests[key][0].kwargs["json"]
        mode_wire = body["Parameters"][0]
        raw = base64.b64decode(mode_wire["Value"])
        # Mode should be STANDBY (0)
        assert raw[3] == FireMode.STANDBY
        # Temperature should be 22.5 from the fixture
        temp = float(raw[4]) + float(raw[5]) / 10.0
        assert temp == pytest.approx(22.5)

    async def test_turn_off_default_temp_no_mode(self, mock_api, token_auth):
        """When no ModeParam, default temp is 22.0.

        Kills turn_off__mutmut_3 and turn_off__mutmut_7.
        """
        fire_id = "no-mode-fire"
        overview_url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        write_url = f"{API_BASE}/api/Fires/WriteWifiParameters"
        payload = _make_overview_payload(fire_id=fire_id, parameters=[])
        mock_api.get(overview_url, payload=payload)
        mock_api.post(write_url, payload={})

        async with FlameConnectClient(token_auth) as client:
            await client.turn_off(fire_id)

        key = ("POST", URL(write_url))
        body = mock_api.requests[key][0].kwargs["json"]
        raw = base64.b64decode(body["Parameters"][0]["Value"])
        assert raw[3] == FireMode.STANDBY
        temp = float(raw[4]) + float(raw[5]) / 10.0
        assert temp == pytest.approx(22.0)


# -------------------------------------------------------------------
# Error handling
# -------------------------------------------------------------------


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
        """Using client without context manager or session.

        Kills _request__mutmut_3/6/7/8 by matching both parts
        of the error message.
        """
        client = FlameConnectClient(token_auth)
        with pytest.raises(
            RuntimeError,
            match=(
                "No aiohttp session available.*"
                "Use the client as an async context manager"
            ),
        ):
            await client.get_fires()

    async def test_external_session(self, mock_api, token_auth):
        """Client should work with externally-provided session."""
        url = f"{API_BASE}/api/Fires/GetFires"
        mock_api.get(url, payload=[])

        async with (
            aiohttp.ClientSession() as session,
            FlameConnectClient(token_auth, session=session) as client,
        ):
            fires = await client.get_fires()

        assert fires == []

    async def test_300_raises_api_error(self, mock_api, token_auth):
        """Status 300 should raise ApiError.

        Kills mutant _request__mutmut_41 (>= 300 -> > 300)
        and _request__mutmut_42 (>= 300 -> >= 301).
        """
        url = f"{API_BASE}/api/Fires/GetFires"
        mock_api.get(url, status=300, body="Multiple Choices")

        async with FlameConnectClient(token_auth) as client:
            with pytest.raises(ApiError) as exc_info:
                await client.get_fires()

        assert exc_info.value.status == 300

    async def test_api_error_includes_response_text(self, mock_api, token_auth):
        """ApiError message should contain response body text.

        Kills _request__mutmut_43 (text=None) and
        _request__mutmut_45 (ApiError(status, None)).
        """
        url = f"{API_BASE}/api/Fires/GetFires"
        mock_api.get(url, status=503, body="Service Unavailable")

        async with FlameConnectClient(token_auth) as client:
            with pytest.raises(ApiError) as exc_info:
                await client.get_fires()

        assert exc_info.value.status == 503
        assert "Service Unavailable" in str(exc_info.value)


# -------------------------------------------------------------------
# _get_parameter_id edge cases
# -------------------------------------------------------------------


class TestGetParameterId:
    """Test _get_parameter_id for all parameter types."""

    def test_sound_param(self):
        param = SoundParam(volume=50, sound_file=1)
        assert _get_parameter_id(param) == 369

    def test_log_effect_param(self):
        param = LogEffectParam(
            log_effect=LogEffect.ON,
            color=RGBWColor(red=0, green=0, blue=0, white=0),
            pattern=0,
        )
        assert _get_parameter_id(param) == 370

    def test_unknown_type_raises_value_error(self):
        """Unknown type raises ValueError with type name."""
        with pytest.raises(ValueError, match="Unknown parameter type: str"):
            _get_parameter_id("not-a-param")

    def test_mode_param(self):
        param = ModeParam(
            mode=FireMode.MANUAL,
            target_temperature=22.0,
        )
        assert _get_parameter_id(param) == 321

    def test_flame_effect_param(self):
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
            flame_color=FlameEffect.OFF,
            ambient_sensor=LightStatus.OFF,
        )
        assert _get_parameter_id(param) == 322

    def test_heat_param(self):
        param = HeatParam(
            heat_status=HeatStatus.ON,
            heat_mode=HeatMode.NORMAL,
            setpoint_temperature=22.0,
            boost_duration=1,
        )
        assert _get_parameter_id(param) == 323

    def test_heat_mode_param(self):
        param = HeatModeParam(heat_control=HeatControl.ENABLED)
        assert _get_parameter_id(param) == 325

    def test_timer_param(self):
        param = TimerParam(timer_status=TimerStatus.DISABLED, duration=0)
        assert _get_parameter_id(param) == 326

    def test_temp_unit_param(self):
        param = TempUnitParam(unit=TempUnit.CELSIUS)
        assert _get_parameter_id(param) == 236


# -------------------------------------------------------------------
# get_fire_overview decode failure path
# -------------------------------------------------------------------


class TestGetFireOverviewDecodeFailure:
    """Test decode failures in get_fire_overview."""

    async def test_bad_parameter_skipped(self, mock_api, token_auth):
        """Parameter that fails to decode is skipped."""
        fire_id = "test-fire-001"
        url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"

        payload = {
            "WifiFireOverview": {
                "FireId": fire_id,
                "FriendlyName": "Living Room",
                "Brand": "Dimplex",
                "ProductType": "Bold Ignite XL",
                "ProductModel": "BIX-50",
                "ItemCode": "ABC123",
                "IoTConnectionState": 2,
                "WithHeat": True,
                "IsIotFire": True,
                "Parameters": [
                    {
                        "ParameterId": 321,
                        "Value": "QQEDARYF",
                    },
                    {
                        "ParameterId": 322,
                        "Value": "AA==",
                    },
                ],
            }
        }

        mock_api.get(url, payload=payload)

        async with FlameConnectClient(token_auth) as client:
            overview = await client.get_fire_overview(fire_id)

        assert len(overview.parameters) == 1
        assert isinstance(overview.parameters[0], ModeParam)


# -------------------------------------------------------------------
# __init__ and __aexit__ session handling
# -------------------------------------------------------------------


class TestSessionHandling:
    """Test __init__ and __aexit__ session management.

    Kills __init____mutmut_2/3/4 and
    __aexit____mutmut_1/2.
    """

    async def test_external_session_flag_is_true(self, token_auth):
        """When session is provided, _external_session=True.

        Kills __init____mutmut_2 (_external_session=None)
        and __init____mutmut_3 (is None instead of is not None).
        """
        session = aiohttp.ClientSession()
        try:
            client = FlameConnectClient(token_auth, session=session)
            assert client._external_session is True
        finally:
            await session.close()

    async def test_no_session_flag_is_false(self, token_auth):
        """When no session provided, _external_session=False.

        Kills __init____mutmut_3 (is None instead of
        is not None).
        """
        client = FlameConnectClient(token_auth)
        assert client._external_session is False

    async def test_init_stores_provided_session(self, token_auth):
        """Provided session is stored in _session.

        Kills __init____mutmut_4 (_session = None).
        """
        session = aiohttp.ClientSession()
        try:
            client = FlameConnectClient(token_auth, session=session)
            assert client._session is session
        finally:
            await session.close()

    async def test_aexit_closes_own_session(self, mock_api, token_auth):
        """When we created the session, __aexit__ closes it.

        Kills __aexit____mutmut_1 (and -> or) and
        __aexit____mutmut_2 (not removed).
        """
        url = f"{API_BASE}/api/Fires/GetFires"
        mock_api.get(url, payload=[])

        client = FlameConnectClient(token_auth)
        async with client:
            await client.get_fires()
            session = client._session
            assert session is not None

        # Session should be closed after __aexit__
        assert session.closed

    async def test_aexit_does_not_close_external_session(self, mock_api, token_auth):
        """External session should NOT be closed by client.

        Kills __aexit____mutmut_2 (removed 'not' for
        _external_session).
        """
        url = f"{API_BASE}/api/Fires/GetFires"
        mock_api.get(url, payload=[])

        session = aiohttp.ClientSession()
        try:
            async with FlameConnectClient(token_auth, session=session) as client:
                await client.get_fires()

            # External session should still be open
            assert not session.closed
        finally:
            await session.close()


# -------------------------------------------------------------------
# _request internals
# -------------------------------------------------------------------


class TestRequestInternals:
    """Test _request method header/auth construction.

    Kills mutants on Authorization, Content-Type, token,
    headers dict, and DEFAULT_HEADERS integration.
    """

    async def test_request_sends_authorization_header(self, mock_api, token_auth):
        """Verify Authorization header with Bearer token.

        Kills _request__mutmut_10 (token=None),
        _request__mutmut_12-14 (key mutations),
        _request__mutmut_11 (headers=None).
        """
        url = f"{API_BASE}/api/Fires/GetFires"
        mock_api.get(url, payload=[])

        async with FlameConnectClient(token_auth) as client:
            await client.get_fires()

        key = ("GET", URL(url))
        call = mock_api.requests[key][0]
        headers = call.kwargs["headers"]
        assert "Authorization" in headers
        assert headers["Authorization"] == ("Bearer test-token-123")

    async def test_request_sends_content_type(self, mock_api, token_auth):
        """Verify Content-Type header is application/json.

        Kills _request__mutmut_15-19.
        """
        url = f"{API_BASE}/api/Fires/GetFires"
        mock_api.get(url, payload=[])

        async with FlameConnectClient(token_auth) as client:
            await client.get_fires()

        key = ("GET", URL(url))
        call = mock_api.requests[key][0]
        headers = call.kwargs["headers"]
        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"

    async def test_request_includes_default_headers(self, mock_api, token_auth):
        """Verify DEFAULT_HEADERS are included.

        Kills _request__mutmut_22 (headers=None) and
        _request__mutmut_26 (headers kwarg removed).
        """
        url = f"{API_BASE}/api/Fires/GetFires"
        mock_api.get(url, payload=[])

        async with FlameConnectClient(token_auth) as client:
            await client.get_fires()

        key = ("GET", URL(url))
        call = mock_api.requests[key][0]
        headers = call.kwargs["headers"]
        for hdr_key, hdr_val in DEFAULT_HEADERS.items():
            assert headers.get(hdr_key) == hdr_val

    async def test_request_passes_json_body(self, mock_api, token_auth):
        """Verify json body is passed through to request."""
        url = f"{API_BASE}/api/Fires/WriteWifiParameters"
        mock_api.post(url, payload={})

        mode = ModeParam(mode=FireMode.MANUAL, target_temperature=22.0)

        async with FlameConnectClient(token_auth) as client:
            await client.write_parameters("f1", [mode])

        key = ("POST", URL(url))
        call = mock_api.requests[key][0]
        body = call.kwargs["json"]
        assert body is not None
        assert body["FireId"] == "f1"

    async def test_request_uses_token_from_auth(self, mock_api):
        """Verify the token from auth provider is used.

        Kills _request__mutmut_10 (token=None).
        """
        auth = TokenAuth("my-special-token")
        url = f"{API_BASE}/api/Fires/GetFires"
        mock_api.get(url, payload=[])

        async with FlameConnectClient(auth) as client:
            await client.get_fires()

        key = ("GET", URL(url))
        call = mock_api.requests[key][0]
        assert call.kwargs["headers"]["Authorization"] == ("Bearer my-special-token")


# -------------------------------------------------------------------
# Logging output tests
# -------------------------------------------------------------------


class TestRequestLogging:
    """Test _LOGGER.debug output from _request.

    Kills _request__mutmut_28-37 which mutate the
    _LOGGER.debug() call arguments.
    """

    async def test_request_logs_method_url_status(self, mock_api, token_auth, caplog):
        """Verify debug log contains method, URL, status."""
        url = f"{API_BASE}/api/Fires/GetFires"
        mock_api.get(url, payload=[])

        with caplog.at_level(logging.DEBUG, logger="flameconnect.client"):
            async with FlameConnectClient(token_auth) as client:
                await client.get_fires()

        # Find the debug message from _request
        found = [
            r
            for r in caplog.records
            if r.name == "flameconnect.client" and "GET" in r.message
        ]
        assert len(found) >= 1
        msg = found[0].message
        assert "GET" in msg
        assert url in msg
        assert "200" in msg


class TestOverviewDecodeWarningLogging:
    """Test _LOGGER.warning on decode failure.

    Kills overview__mutmut_128/132/133 which mutate the
    _LOGGER.warning() call format/args.
    """

    async def test_decode_failure_logs_warning(self, mock_api, token_auth, caplog):
        """Verify warning log on decode failure."""
        fire_id = "test-fire-001"
        url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        mode_val = encode_parameter(
            ModeParam(
                mode=FireMode.MANUAL,
                target_temperature=22.0,
            )
        )
        payload = _make_overview_payload(
            fire_id=fire_id,
            parameters=[
                {"ParameterId": 321, "Value": mode_val},
                {"ParameterId": 322, "Value": "AA=="},
            ],
        )
        mock_api.get(url, payload=payload)

        with caplog.at_level(logging.WARNING, logger="flameconnect.client"):
            async with FlameConnectClient(token_auth) as client:
                await client.get_fire_overview(fire_id)

        warnings = [
            r
            for r in caplog.records
            if r.name == "flameconnect.client" and r.levelno == logging.WARNING
        ]
        assert len(warnings) >= 1
        msg = warnings[0].message
        assert "Failed to decode parameter" in msg
        assert "322" in msg


# -------------------------------------------------------------------
# Targeted mutant-killing tests
# -------------------------------------------------------------------


class TestRequestErrorMessageExact:
    """Kill _request__mutmut_3 and _request__mutmut_6.

    mutmut_3 changes "No aiohttp session available. " to
    "XXNo aiohttp session available. XX".
    mutmut_6 changes the second part of the message.

    We need to check that the message starts exactly with "No"
    and ends exactly with "session." to detect the XX prefixes/suffixes.
    """

    async def test_no_session_error_starts_with_no(self, token_auth):
        """Error message must start with 'No' (not 'XXNo')."""
        client = FlameConnectClient(token_auth)
        with pytest.raises(RuntimeError) as exc_info:
            await client.get_fires()
        msg = str(exc_info.value)
        assert msg.startswith("No aiohttp session available.")

    async def test_no_session_error_ends_with_session(self, token_auth):
        """Error message must end with 'session.' (not 'session.XX')."""
        client = FlameConnectClient(token_auth)
        with pytest.raises(RuntimeError) as exc_info:
            await client.get_fires()
        msg = str(exc_info.value)
        assert msg.endswith("or provide a session.")


class TestRequestDebugLog:
    """Kill _request__mutmut_36.

    mutmut_36 changes the debug log format string from
    "%s %s -> %s" to "XX%s %s -> %sXX".
    We verify the debug log format starts with the method, not "XX".
    """

    async def test_request_debug_log_format(self, mock_api, token_auth, caplog):
        """Request summary log must start with method name, not 'XX'."""
        url = f"{API_BASE}/api/Fires/GetFires"
        mock_api.get(url, payload=[])

        with caplog.at_level(logging.INFO, logger="flameconnect.client"):
            async with FlameConnectClient(token_auth) as client:
                await client.get_fires()

        info_msgs = [
            r
            for r in caplog.records
            if r.name == "flameconnect.client" and r.levelno == logging.INFO
        ]
        assert len(info_msgs) >= 1
        msg = info_msgs[0].getMessage()
        assert msg.startswith("GET ")
        assert "XX" not in msg


class TestOverviewDecodeWarningFormat:
    """Kill get_fire_overview__mutmut_128 and __mutmut_132.

    mutmut_128: replaces exc with None in the warning args.
    mutmut_132: mutates the format string to include XX prefix/suffix.

    We verify the exact format string and that the exception text
    (not None) appears in the formatted message.
    """

    async def test_decode_failure_warning_format_string(
        self, mock_api, token_auth, caplog
    ):
        """The raw format string must be exactly as expected."""
        fire_id = "test-fire-001"
        url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        mode_val = encode_parameter(
            ModeParam(
                mode=FireMode.MANUAL,
                target_temperature=22.0,
            )
        )
        payload = _make_overview_payload(
            fire_id=fire_id,
            parameters=[
                {"ParameterId": 321, "Value": mode_val},
                {"ParameterId": 322, "Value": "AA=="},
            ],
        )
        mock_api.get(url, payload=payload)

        with caplog.at_level(logging.WARNING, logger="flameconnect.client"):
            async with FlameConnectClient(token_auth) as client:
                await client.get_fire_overview(fire_id)

        warnings = [
            r
            for r in caplog.records
            if r.name == "flameconnect.client" and r.levelno == logging.WARNING
        ]
        assert len(warnings) >= 1
        record = warnings[0]
        # Kill mutmut_132: check the raw format string has no XX
        assert record.msg == "Failed to decode parameter %d: %s"
        # Kill mutmut_128: the second arg must be the actual exception, not None
        assert record.args[1] is not None
        # Additionally verify the formatted message includes exception text
        formatted = record.getMessage()
        assert "Insufficient data" in formatted or "expected" in formatted


class TestTurnOnTurnOffInitNone:
    """Document turn_on__mutmut_3 and turn_off__mutmut_3 as equivalent.

    Both mutants change `current_mode: ModeParam | None = None` to
    `current_mode: ModeParam | None = ""`.

    Since empty string "" is falsy in Python (just like None), the
    conditional `current_mode.target_temperature if current_mode else 22.0`
    behaves identically for both None and "".

    When no ModeParam is found in the parameters loop, current_mode
    stays at its initial value. Both None and "" are falsy, so the
    ternary always takes the else branch returning 22.0.

    These are equivalent mutants that cannot be killed.
    """

    async def test_turn_on_no_mode_uses_default_temp(self, mock_api, token_auth):
        """Verify turn_on uses 22.0 when no ModeParam present."""
        fire_id = "no-mode-fire"
        overview_url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        write_url = f"{API_BASE}/api/Fires/WriteWifiParameters"
        payload = _make_overview_payload(fire_id=fire_id, parameters=[])
        mock_api.get(overview_url, payload=payload)
        mock_api.post(write_url, payload={})

        async with FlameConnectClient(token_auth) as client:
            await client.turn_on(fire_id)

        key = ("POST", URL(write_url))
        body = mock_api.requests[key][0].kwargs["json"]
        mode_wire = next(p for p in body["Parameters"] if p["ParameterId"] == 321)
        raw = base64.b64decode(mode_wire["Value"])
        temp = float(raw[4]) + float(raw[5]) / 10.0
        assert temp == pytest.approx(22.0)

    async def test_turn_off_no_mode_uses_default_temp(self, mock_api, token_auth):
        """Verify turn_off uses 22.0 when no ModeParam present."""
        fire_id = "no-mode-fire"
        overview_url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        write_url = f"{API_BASE}/api/Fires/WriteWifiParameters"
        payload = _make_overview_payload(fire_id=fire_id, parameters=[])
        mock_api.get(overview_url, payload=payload)
        mock_api.post(write_url, payload={})

        async with FlameConnectClient(token_auth) as client:
            await client.turn_off(fire_id)

        key = ("POST", URL(write_url))
        body = mock_api.requests[key][0].kwargs["json"]
        raw = base64.b64decode(body["Parameters"][0]["Value"])
        assert raw[3] == FireMode.STANDBY
        temp = float(raw[4]) + float(raw[5]) / 10.0
        assert temp == pytest.approx(22.0)


# -------------------------------------------------------------------
# Security regression tests
# -------------------------------------------------------------------


class TestGetFireOverviewUrlEncoding:
    """Security tests: fire_id must be URL-encoded in get_fire_overview.

    A compromised API server could return a FireId containing URL
    special characters (e.g. '&evil=true') to inject extra query
    parameters into subsequent requests. The fix URL-encodes fire_id
    via urllib.parse.quote() so injected characters are escaped.
    """

    async def test_ampersand_in_fire_id_is_encoded(self, mock_api, token_auth):
        """'&' in fire_id must be percent-encoded, not passed raw."""
        fire_id = "abc&evil=true"
        # The URL must encode '&' as '%26' and '=' as '%3D'
        encoded_id = "abc%26evil%3Dtrue"
        url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={encoded_id}"
        mock_api.get(url, payload={"WifiFireOverview": {"FireId": fire_id}})

        async with FlameConnectClient(token_auth) as client:
            overview = await client.get_fire_overview(fire_id)

        assert overview.fire.fire_id == fire_id

    async def test_hash_in_fire_id_is_encoded(self, mock_api, token_auth):
        """'#' in fire_id must be percent-encoded."""
        fire_id = "abc#fragment"
        encoded_id = "abc%23fragment"
        url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={encoded_id}"
        mock_api.get(url, payload={"WifiFireOverview": {"FireId": fire_id}})

        async with FlameConnectClient(token_auth) as client:
            overview = await client.get_fire_overview(fire_id)

        assert overview.fire.fire_id == fire_id

    async def test_normal_fire_id_unchanged(
        self, mock_api, token_auth, get_fire_overview_payload
    ):
        """A plain alphanumeric fire_id is unaffected by encoding."""
        fire_id = "test-fire-001"
        url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        mock_api.get(url, payload=get_fire_overview_payload)

        async with FlameConnectClient(token_auth) as client:
            overview = await client.get_fire_overview(fire_id)

        assert overview.fire.fire_id == fire_id


# -------------------------------------------------------------------
# _parse_fire_features tests
# -------------------------------------------------------------------


class TestParseFireFeatures:
    """Tests for _parse_fire_features to kill mutants."""

    def test_all_true(self):
        data = {
            "Sound": True,
            "SimpleHeat": True,
            "AdvancedHeat": True,
            "SevenDayTimer": True,
            "CountDownTimer": True,
            "Moods": True,
            "FlameHeight": True,
            "RgbFlameAccent": True,
            "FlameDimming": True,
            "RgbFuelBed": True,
            "FuelBedDimming": True,
            "FlameFanSpeed": True,
            "RgbBackLight": True,
            "FrontLightAmber": True,
            "PirToggleSmartSense": True,
            "Lgt1To5": True,
            "RequiresWarmUp": True,
            "ApplyFlameOnlyFirst": True,
            "FlameAmber": True,
            "CheckIfRemoteWasUsed": True,
            "MediaAccent": True,
            "PowerBoost": True,
            "FanOnly": True,
            "RgbLogEffect": True,
        }
        result = _parse_fire_features(data)
        assert result.sound is True
        assert result.simple_heat is True
        assert result.advanced_heat is True
        assert result.seven_day_timer is True
        assert result.count_down_timer is True
        assert result.moods is True
        assert result.flame_height is True
        assert result.rgb_flame_accent is True
        assert result.flame_dimming is True
        assert result.rgb_fuel_bed is True
        assert result.fuel_bed_dimming is True
        assert result.flame_fan_speed is True
        assert result.rgb_back_light is True
        assert result.front_light_amber is True
        assert result.pir_toggle_smart_sense is True
        assert result.lgt1_to_5 is True
        assert result.requires_warm_up is True
        assert result.apply_flame_only_first is True
        assert result.flame_amber is True
        assert result.check_if_remote_was_used is True
        assert result.media_accent is True
        assert result.power_boost is True
        assert result.fan_only is True
        assert result.rgb_log_effect is True

    def test_empty_dict_defaults_to_false(self):
        result = _parse_fire_features({})
        assert result.sound is False
        assert result.simple_heat is False
        assert result.advanced_heat is False
        assert result.seven_day_timer is False
        assert result.count_down_timer is False
        assert result.moods is False
        assert result.flame_height is False
        assert result.rgb_flame_accent is False
        assert result.flame_dimming is False
        assert result.rgb_fuel_bed is False
        assert result.fuel_bed_dimming is False
        assert result.flame_fan_speed is False
        assert result.rgb_back_light is False
        assert result.front_light_amber is False
        assert result.pir_toggle_smart_sense is False
        assert result.lgt1_to_5 is False
        assert result.requires_warm_up is False
        assert result.apply_flame_only_first is False
        assert result.flame_amber is False
        assert result.check_if_remote_was_used is False
        assert result.media_accent is False
        assert result.power_boost is False
        assert result.fan_only is False
        assert result.rgb_log_effect is False

    def test_each_key_maps_correctly(self):
        """Verify each JSON key maps to the right field."""
        mapping = {
            "Sound": "sound",
            "SimpleHeat": "simple_heat",
            "AdvancedHeat": "advanced_heat",
            "SevenDayTimer": "seven_day_timer",
            "CountDownTimer": "count_down_timer",
            "Moods": "moods",
            "FlameHeight": "flame_height",
            "RgbFlameAccent": "rgb_flame_accent",
            "FlameDimming": "flame_dimming",
            "RgbFuelBed": "rgb_fuel_bed",
            "FuelBedDimming": "fuel_bed_dimming",
            "FlameFanSpeed": "flame_fan_speed",
            "RgbBackLight": "rgb_back_light",
            "FrontLightAmber": "front_light_amber",
            "PirToggleSmartSense": "pir_toggle_smart_sense",
            "Lgt1To5": "lgt1_to_5",
            "RequiresWarmUp": "requires_warm_up",
            "ApplyFlameOnlyFirst": "apply_flame_only_first",
            "FlameAmber": "flame_amber",
            "CheckIfRemoteWasUsed": "check_if_remote_was_used",
            "MediaAccent": "media_accent",
            "PowerBoost": "power_boost",
            "FanOnly": "fan_only",
            "RgbLogEffect": "rgb_log_effect",
        }
        for json_key, field_name in mapping.items():
            data = {json_key: True}
            result = _parse_fire_features(data)
            assert getattr(result, field_name) is True, f"{json_key} -> {field_name}"
            for other_field in mapping.values():
                if other_field != field_name:
                    assert getattr(result, other_field) is False


# -------------------------------------------------------------------
# Client __init__, __aenter__, __aexit__ tests
# -------------------------------------------------------------------


class TestClientLifecycle:
    """Tests for FlameConnectClient lifecycle methods."""

    async def test_init_with_session(self, token_auth):
        session = aiohttp.ClientSession()
        try:
            client = FlameConnectClient(token_auth, session=session)
            assert client._external_session is True
            assert client._session is session
        finally:
            await session.close()

    async def test_init_without_session(self, token_auth):
        client = FlameConnectClient(token_auth)
        assert client._external_session is False
        assert client._session is None

    async def test_aenter_creates_session(self, token_auth):
        client = FlameConnectClient(token_auth)
        async with client:
            assert client._session is not None

    async def test_aexit_closes_own_session(self, token_auth):
        client = FlameConnectClient(token_auth)
        async with client:
            session = client._session
        assert session is not None
        assert session.closed

    async def test_aexit_does_not_close_external(self, token_auth):
        session = aiohttp.ClientSession()
        try:
            async with FlameConnectClient(token_auth, session=session):
                pass
            assert not session.closed
        finally:
            await session.close()


# -------------------------------------------------------------------
# _request tests
# -------------------------------------------------------------------


class TestClientRequest:
    """Tests for FlameConnectClient._request."""

    async def test_no_session_raises(self, token_auth):
        client = FlameConnectClient(token_auth)
        with pytest.raises(RuntimeError, match="No aiohttp"):
            await client._request("GET", "http://example.com")

    async def test_request_includes_auth_header(self, mock_api, token_auth):
        url = f"{API_BASE}/api/test"
        mock_api.get(url, payload={"ok": True})

        async with FlameConnectClient(token_auth) as client:
            await client._request("GET", url)

        key = ("GET", URL(url))
        calls = mock_api.requests[key]
        headers = calls[0].kwargs["headers"]
        assert headers["Authorization"] == "Bearer test-token-123"
        assert headers["Content-Type"] == "application/json"

    async def test_request_includes_default_headers(self, mock_api, token_auth):
        url = f"{API_BASE}/api/test"
        mock_api.get(url, payload={})

        async with FlameConnectClient(token_auth) as client:
            await client._request("GET", url)

        key = ("GET", URL(url))
        calls = mock_api.requests[key]
        headers = calls[0].kwargs["headers"]
        for k, v in DEFAULT_HEADERS.items():
            assert headers[k] == v

    async def test_request_4xx_raises(self, mock_api, token_auth):
        url = f"{API_BASE}/api/test"
        mock_api.get(url, status=404, body="Not Found")

        async with FlameConnectClient(token_auth) as client:
            with pytest.raises(ApiError):
                await client._request("GET", url)

    async def test_request_5xx_raises(self, mock_api, token_auth):
        url = f"{API_BASE}/api/test"
        mock_api.get(url, status=500, body="Server Error")

        async with FlameConnectClient(token_auth) as client:
            with pytest.raises(ApiError):
                await client._request("GET", url)

    async def test_request_post_json(self, mock_api, token_auth):
        url = f"{API_BASE}/api/test"
        mock_api.post(url, payload={"result": "ok"})

        async with FlameConnectClient(token_auth) as client:
            result = await client._request("POST", url, json={"key": "val"})

        assert result == {"result": "ok"}

    async def test_request_199_raises(self, mock_api, token_auth):
        url = f"{API_BASE}/api/test"
        mock_api.get(url, status=199, body="x")

        async with FlameConnectClient(token_auth) as client:
            with pytest.raises(ApiError):
                await client._request("GET", url)

    async def test_request_300_raises(self, mock_api, token_auth):
        url = f"{API_BASE}/api/test"
        mock_api.get(url, status=300, body="x")

        async with FlameConnectClient(token_auth) as client:
            with pytest.raises(ApiError):
                await client._request("GET", url)


# -------------------------------------------------------------------
# get_fires detailed tests
# -------------------------------------------------------------------


class TestGetFiresDetailed:
    """Detailed field-level tests for get_fires."""

    async def test_fire_fields(self, mock_api, token_auth, get_fires_payload):
        url = f"{API_BASE}/api/Fires/GetFires"
        mock_api.get(url, payload=get_fires_payload)

        async with FlameConnectClient(token_auth) as client:
            fires = await client.get_fires()

        assert len(fires) == 1
        fire = fires[0]
        assert fire.fire_id == "test-fire-001"
        assert fire.friendly_name == "Living Room"
        assert fire.brand == "Dimplex"
        assert fire.product_type == "Bold Ignite XL"
        assert fire.product_model == "BIX-50"
        assert fire.item_code == "ABC123"
        assert fire.connection_state == ConnectionState.CONNECTED
        assert fire.with_heat is True
        assert fire.is_iot_fire is True
        assert fire.features.sound is True
        assert fire.features.simple_heat is True
        assert fire.features.advanced_heat is True
        assert fire.features.flame_height is True
        assert fire.features.rgb_flame_accent is True
        assert fire.features.moods is False

    async def test_empty_fires(self, mock_api, token_auth):
        url = f"{API_BASE}/api/Fires/GetFires"
        mock_api.get(url, payload=[])

        async with FlameConnectClient(token_auth) as client:
            fires = await client.get_fires()

        assert fires == []

    async def test_multiple_fires(self, mock_api, token_auth):
        url = f"{API_BASE}/api/Fires/GetFires"
        payload = [
            {
                "FireId": "f1",
                "FriendlyName": "Fire 1",
                "Brand": "B1",
                "ProductType": "T1",
                "ProductModel": "M1",
                "ItemCode": "IC1",
                "IoTConnectionState": 2,
                "WithHeat": True,
                "IsIotFire": True,
                "FireFeature": {},
            },
            {
                "FireId": "f2",
                "FriendlyName": "Fire 2",
                "Brand": "B2",
                "ProductType": "T2",
                "ProductModel": "M2",
                "ItemCode": "IC2",
                "IoTConnectionState": 1,
                "WithHeat": False,
                "IsIotFire": False,
                "FireFeature": {},
            },
        ]
        mock_api.get(url, payload=payload)

        async with FlameConnectClient(token_auth) as client:
            fires = await client.get_fires()

        assert len(fires) == 2
        assert fires[0].fire_id == "f1"
        assert fires[1].fire_id == "f2"
        assert fires[1].with_heat is False
        assert fires[1].is_iot_fire is False
        cs = ConnectionState.NOT_CONNECTED
        assert fires[1].connection_state == cs


# -------------------------------------------------------------------
# get_fire_overview detailed tests
# -------------------------------------------------------------------


class TestGetFireOverviewDetailed:
    """Detailed field tests for get_fire_overview."""

    async def test_overview_fire_fields(
        self, mock_api, token_auth, get_fire_overview_payload
    ):
        fire_id = "test-fire-001"
        url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        mock_api.get(url, payload=get_fire_overview_payload)

        async with FlameConnectClient(token_auth) as client:
            overview = await client.get_fire_overview(fire_id)

        fire = overview.fire
        assert fire.fire_id == fire_id
        assert fire.friendly_name == "Living Room"
        assert fire.brand == "Dimplex"
        assert fire.product_type == "Bold Ignite XL"
        assert fire.product_model == "BIX-50"
        assert fire.item_code == "ABC123"
        cs = ConnectionState.CONNECTED
        assert fire.connection_state == cs
        assert fire.with_heat is True
        assert fire.is_iot_fire is True

    async def test_overview_parameters_decoded(
        self, mock_api, token_auth, get_fire_overview_payload
    ):
        fire_id = "test-fire-001"
        url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        mock_api.get(url, payload=get_fire_overview_payload)

        async with FlameConnectClient(token_auth) as client:
            overview = await client.get_fire_overview(fire_id)

        assert len(overview.parameters) == 10
        param_types = [type(p) for p in overview.parameters]
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

    async def test_overview_defaults_for_missing(self, mock_api, token_auth):
        fire_id = "min-fire"
        url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        payload = {
            "WifiFireOverview": {
                "FireId": fire_id,
                "Parameters": [],
            },
        }
        mock_api.get(url, payload=payload)

        async with FlameConnectClient(token_auth) as client:
            overview = await client.get_fire_overview(fire_id)

        fire = overview.fire
        assert fire.friendly_name == fire_id
        assert fire.brand == ""
        assert fire.product_type == ""
        assert fire.product_model == ""
        assert fire.item_code == ""
        assert fire.connection_state == ConnectionState.UNKNOWN
        assert fire.with_heat is False
        assert fire.is_iot_fire is False
        assert overview.parameters == []

    async def test_features_from_fire_details(self, mock_api, token_auth):
        fire_id = "feat-fire"
        url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        payload = {
            "WifiFireOverview": {
                "FireId": fire_id,
                "FireFeature": {"Sound": False},
                "Parameters": [],
            },
            "FireDetails": {
                "FireFeature": {"Sound": True},
            },
        }
        mock_api.get(url, payload=payload)

        async with FlameConnectClient(token_auth) as client:
            overview = await client.get_fire_overview(fire_id)

        assert overview.fire.features.sound is True

    async def test_features_fallback_to_wifi(self, mock_api, token_auth):
        fire_id = "fb-fire"
        url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        payload = {
            "WifiFireOverview": {
                "FireId": fire_id,
                "FireFeature": {"FanOnly": True},
                "Parameters": [],
            },
            "FireDetails": {},
        }
        mock_api.get(url, payload=payload)

        async with FlameConnectClient(token_auth) as client:
            overview = await client.get_fire_overview(fire_id)

        assert overview.fire.features.fan_only is True

    async def test_skips_invalid_parameter(self, mock_api, token_auth, caplog):
        fire_id = "bad-param"
        url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        payload = {
            "WifiFireOverview": {
                "FireId": fire_id,
                "Parameters": [
                    {"ParameterId": 999, "Value": "AAAA"},
                ],
            },
        }
        mock_api.get(url, payload=payload)

        async with FlameConnectClient(token_auth) as client:
            with caplog.at_level(logging.WARNING):
                ov = await client.get_fire_overview(fire_id)

        assert len(ov.parameters) == 0
        assert any("Failed to decode" in r.message for r in caplog.records)


# -------------------------------------------------------------------
# write_parameters detailed tests
# -------------------------------------------------------------------


class TestWriteParametersDetailed:
    """More detailed tests for write_parameters."""

    async def test_write_single_param(self, mock_api, token_auth):
        url = f"{API_BASE}/api/Fires/WriteWifiParameters"
        mock_api.post(url, payload={})

        param = TempUnitParam(unit=TempUnit.CELSIUS)
        async with FlameConnectClient(token_auth) as client:
            await client.write_parameters("fire-1", [param])

        key = ("POST", URL(url))
        calls = mock_api.requests[key]
        body = calls[0].kwargs["json"]
        assert body["FireId"] == "fire-1"
        assert len(body["Parameters"]) == 1
        assert body["Parameters"][0]["ParameterId"] == 236

    async def test_write_multiple_params(self, mock_api, token_auth):
        url = f"{API_BASE}/api/Fires/WriteWifiParameters"
        mock_api.post(url, payload={})

        params = [
            TempUnitParam(unit=TempUnit.FAHRENHEIT),
            TimerParam(timer_status=TimerStatus.ENABLED, duration=60),
        ]
        async with FlameConnectClient(token_auth) as client:
            await client.write_parameters("fire-2", params)

        key = ("POST", URL(url))
        body = mock_api.requests[key][0].kwargs["json"]
        assert body["FireId"] == "fire-2"
        assert len(body["Parameters"]) == 2
        ids = {p["ParameterId"] for p in body["Parameters"]}
        assert ids == {236, 326}


# -------------------------------------------------------------------
# turn_on / turn_off tests
# -------------------------------------------------------------------


class TestTurnOnOff:
    """Tests for turn_on and turn_off."""

    async def test_turn_on_sends_manual(
        self, mock_api, token_auth, get_fire_overview_payload
    ):
        fire_id = "test-fire-001"
        ov_url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        wr_url = f"{API_BASE}/api/Fires/WriteWifiParameters"
        mock_api.get(ov_url, payload=get_fire_overview_payload)
        mock_api.post(wr_url, payload={})

        async with FlameConnectClient(token_auth) as client:
            await client.turn_on(fire_id)

        key = ("POST", URL(wr_url))
        body = mock_api.requests[key][0].kwargs["json"]
        assert body["FireId"] == fire_id
        ids = {p["ParameterId"] for p in body["Parameters"]}
        assert 321 in ids

    async def test_turn_off_sends_standby(
        self, mock_api, token_auth, get_fire_overview_payload
    ):
        fire_id = "test-fire-001"
        ov_url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        wr_url = f"{API_BASE}/api/Fires/WriteWifiParameters"
        mock_api.get(ov_url, payload=get_fire_overview_payload)
        mock_api.post(wr_url, payload={})

        async with FlameConnectClient(token_auth) as client:
            await client.turn_off(fire_id)

        key = ("POST", URL(wr_url))
        body = mock_api.requests[key][0].kwargs["json"]
        assert body["FireId"] == fire_id
        ids = {p["ParameterId"] for p in body["Parameters"]}
        assert 321 in ids

    async def test_turn_on_preserves_temperature(
        self, mock_api, token_auth, get_fire_overview_payload
    ):
        fire_id = "test-fire-001"
        ov_url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        wr_url = f"{API_BASE}/api/Fires/WriteWifiParameters"
        mock_api.get(ov_url, payload=get_fire_overview_payload)
        mock_api.post(wr_url, payload={})

        async with FlameConnectClient(token_auth) as client:
            await client.turn_on(fire_id)

        key = ("POST", URL(wr_url))
        body = mock_api.requests[key][0].kwargs["json"]
        mode_wire = next(p for p in body["Parameters"] if p["ParameterId"] == 321)
        raw = base64.b64decode(mode_wire["Value"])
        assert raw[3] == FireMode.MANUAL

    async def test_turn_off_preserves_temperature(
        self, mock_api, token_auth, get_fire_overview_payload
    ):
        fire_id = "test-fire-001"
        ov_url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        wr_url = f"{API_BASE}/api/Fires/WriteWifiParameters"
        mock_api.get(ov_url, payload=get_fire_overview_payload)
        mock_api.post(wr_url, payload={})

        async with FlameConnectClient(token_auth) as client:
            await client.turn_off(fire_id)

        key = ("POST", URL(wr_url))
        body = mock_api.requests[key][0].kwargs["json"]
        mode_wire = next(p for p in body["Parameters"] if p["ParameterId"] == 321)
        raw = base64.b64decode(mode_wire["Value"])
        assert raw[3] == FireMode.STANDBY

    async def test_turn_on_no_mode_uses_default(self, mock_api, token_auth):
        fire_id = "no-mode-fire"
        ov_url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        wr_url = f"{API_BASE}/api/Fires/WriteWifiParameters"
        payload = {
            "WifiFireOverview": {
                "FireId": fire_id,
                "Parameters": [],
            },
        }
        mock_api.get(ov_url, payload=payload)
        mock_api.post(wr_url, payload={})

        async with FlameConnectClient(token_auth) as client:
            await client.turn_on(fire_id)

        key = ("POST", URL(wr_url))
        body = mock_api.requests[key][0].kwargs["json"]
        assert len(body["Parameters"]) >= 1

    async def test_turn_on_includes_flame_effect(
        self, mock_api, token_auth, get_fire_overview_payload
    ):
        fire_id = "test-fire-001"
        ov_url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        wr_url = f"{API_BASE}/api/Fires/WriteWifiParameters"
        mock_api.get(ov_url, payload=get_fire_overview_payload)
        mock_api.post(wr_url, payload={})

        async with FlameConnectClient(token_auth) as client:
            await client.turn_on(fire_id)

        key = ("POST", URL(wr_url))
        body = mock_api.requests[key][0].kwargs["json"]
        ids = {p["ParameterId"] for p in body["Parameters"]}
        assert 322 in ids
