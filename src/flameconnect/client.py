"""Async API client for the Flame Connect cloud service."""

from __future__ import annotations

import base64
import logging
from typing import TYPE_CHECKING, Any

import aiohttp

from flameconnect.const import API_BASE, DEFAULT_HEADERS, ParameterId

if TYPE_CHECKING:
    from flameconnect.auth import AbstractAuth
from flameconnect.exceptions import ApiError
from flameconnect.models import (
    ConnectionState,
    Fire,
    FireMode,
    FireOverview,
    FlameEffect,
    FlameEffectParam,
    HeatModeParam,
    HeatParam,
    LogEffectParam,
    ModeParam,
    Parameter,
    SoundParam,
    TempUnitParam,
    TimerParam,
)
from flameconnect.protocol import decode_parameter, encode_parameter

_LOGGER = logging.getLogger(__name__)


def _get_parameter_id(param: Parameter) -> int:
    """Return the wire ParameterId integer for a parameter dataclass."""
    if isinstance(param, ModeParam):
        return ParameterId.MODE
    if isinstance(param, FlameEffectParam):
        return ParameterId.FLAME_EFFECT
    if isinstance(param, HeatParam):
        return ParameterId.HEAT_SETTINGS
    if isinstance(param, HeatModeParam):
        return ParameterId.HEAT_MODE
    if isinstance(param, TimerParam):
        return ParameterId.TIMER
    if isinstance(param, TempUnitParam):
        return ParameterId.TEMPERATURE_UNIT
    if isinstance(param, SoundParam):
        return ParameterId.SOUND
    if isinstance(param, LogEffectParam):
        return ParameterId.LOG_EFFECT
    msg = f"Unknown parameter type: {type(param).__name__}"
    raise ValueError(msg)


class FlameConnectClient:
    """Async client for the Flame Connect cloud API.

    Use as an async context manager to manage the underlying aiohttp session::

        async with FlameConnectClient(auth) as client:
            fires = await client.get_fires()
    """

    def __init__(
        self,
        auth: AbstractAuth,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self._auth = auth
        self._external_session = session is not None
        self._session = session

    async def __aenter__(self) -> FlameConnectClient:
        """Enter the async context manager, creating a session if needed."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, *exc: object) -> None:
        """Exit the async context manager, closing the session if we own it."""
        if not self._external_session and self._session:
            await self._session.close()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        url: str,
        json: dict[str, Any] | None = None,
    ) -> Any:
        """Make an authenticated HTTP request and return parsed JSON.

        Args:
            method: HTTP method (GET, POST, etc.).
            url: Full URL to request.
            json: Optional JSON body for POST requests.

        Returns:
            Parsed JSON response.

        Raises:
            RuntimeError: If the client is used outside a context manager
                without providing a session.
            ApiError: If the response status is not 2xx.
        """
        if self._session is None:
            msg = (
                "No aiohttp session available. "
                "Use the client as an async context manager or provide a session."
            )
            raise RuntimeError(msg)

        token = await self._auth.get_token()

        headers: dict[str, str] = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            **DEFAULT_HEADERS,
        }

        async with self._session.request(
            method, url, headers=headers, json=json
        ) as response:
            _LOGGER.debug("%s %s -> %s", method, url, response.status)

            if response.status < 200 or response.status >= 300:
                text = await response.text()
                raise ApiError(response.status, text)

            result: Any = await response.json()
            return result

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_fires(self) -> list[Fire]:
        """Fetch all registered fireplaces.

        Returns:
            A list of Fire dataclass instances.
        """
        url = f"{API_BASE}/api/Fires/GetFires"
        data: list[dict[str, Any]] = await self._request("GET", url)

        fires: list[Fire] = []
        for entry in data:
            fire = Fire(
                fire_id=entry["FireId"],
                friendly_name=entry["FriendlyName"],
                brand=entry["Brand"],
                product_type=entry["ProductType"],
                product_model=entry["ProductModel"],
                item_code=entry["ItemCode"],
                connection_state=ConnectionState(entry["IoTConnectionState"]),
                with_heat=entry["WithHeat"],
                is_iot_fire=entry["IsIotFire"],
            )
            fires.append(fire)

        return fires

    async def get_fire_overview(self, fire_id: str) -> FireOverview:
        """Fetch the current state and parameters for a fireplace.

        Args:
            fire_id: The unique identifier of the fireplace.

        Returns:
            A FireOverview containing the fire identity and decoded parameters.
        """
        url = f"{API_BASE}/api/Fires/GetFireOverview?FireId={fire_id}"
        data: dict[str, Any] = await self._request("GET", url)

        wifi: dict[str, Any] = data["WifiFireOverview"]
        fire_data: dict[str, Any] = wifi

        fire = Fire(
            fire_id=fire_data["FireId"],
            friendly_name=fire_data.get("FriendlyName", fire_data["FireId"]),
            brand=fire_data.get("Brand", ""),
            product_type=fire_data.get("ProductType", ""),
            product_model=fire_data.get("ProductModel", ""),
            item_code=fire_data.get("ItemCode", ""),
            connection_state=ConnectionState(fire_data.get("IoTConnectionState", 0)),
            with_heat=fire_data.get("WithHeat", False),
            is_iot_fire=fire_data.get("IsIotFire", False),
        )

        raw_params: list[dict[str, Any]] = wifi.get("Parameters", [])
        parameters: list[Parameter] = []

        for entry in raw_params:
            param_id: int = entry["ParameterId"]
            raw = base64.b64decode(entry["Value"])
            try:
                param = decode_parameter(param_id, raw)
            except Exception as exc:
                _LOGGER.warning("Failed to decode parameter %d: %s", param_id, exc)
                continue
            parameters.append(param)

        return FireOverview(fire=fire, parameters=parameters)

    async def write_parameters(self, fire_id: str, params: list[Parameter]) -> None:
        """Write control parameters to a fireplace.

        Args:
            fire_id: The unique identifier of the fireplace.
            params: A list of parameter dataclass instances to write.
        """
        url = f"{API_BASE}/api/Fires/WriteWifiParameters"

        wire_params: list[dict[str, Any]] = []
        for param in params:
            param_id = _get_parameter_id(param)
            value = encode_parameter(param)
            wire_params.append({"ParameterId": param_id, "Value": value})

        payload: dict[str, Any] = {
            "FireId": fire_id,
            "Parameters": wire_params,
        }

        await self._request("POST", url, json=payload)

    async def turn_on(self, fire_id: str) -> None:
        """Turn on the fireplace, preserving current flame effect settings.

        Reads the current state first to preserve existing temperature and
        flame effect configuration, then sets the mode to MANUAL and the
        flame effect to ON.

        Args:
            fire_id: The unique identifier of the fireplace.
        """
        overview = await self.get_fire_overview(fire_id)

        # Find current ModeParam to preserve temperature
        current_mode: ModeParam | None = None
        current_flame: FlameEffectParam | None = None
        for param in overview.parameters:
            if isinstance(param, ModeParam):
                current_mode = param
            elif isinstance(param, FlameEffectParam):
                current_flame = param

        temperature = current_mode.temperature if current_mode else 22.0

        new_mode = ModeParam(mode=FireMode.MANUAL, temperature=temperature)

        params_to_write: list[Parameter] = [new_mode]

        if current_flame is not None:
            new_flame = FlameEffectParam(
                flame_effect=FlameEffect.ON,
                flame_speed=current_flame.flame_speed,
                brightness=current_flame.brightness,
                pulsating_effect=current_flame.pulsating_effect,
                media_theme=current_flame.media_theme,
                media_light=current_flame.media_light,
                media_color=current_flame.media_color,
                overhead_light=current_flame.overhead_light,
                overhead_color=current_flame.overhead_color,
                light_status=current_flame.light_status,
                flame_color=current_flame.flame_color,
                ambient_sensor=current_flame.ambient_sensor,
            )
            params_to_write.append(new_flame)

        await self.write_parameters(fire_id, params_to_write)

    async def turn_off(self, fire_id: str) -> None:
        """Turn off the fireplace, preserving current temperature.

        Reads the current state first to preserve the existing temperature,
        then sets the mode to STANDBY.

        Args:
            fire_id: The unique identifier of the fireplace.
        """
        overview = await self.get_fire_overview(fire_id)

        current_mode: ModeParam | None = None
        for param in overview.parameters:
            if isinstance(param, ModeParam):
                current_mode = param
                break

        temperature = current_mode.temperature if current_mode else 22.0

        mode_param = ModeParam(mode=FireMode.STANDBY, temperature=temperature)
        await self.write_parameters(fire_id, [mode_param])
