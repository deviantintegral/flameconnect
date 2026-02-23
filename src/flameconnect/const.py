"""Constants for the flameconnect library."""

from __future__ import annotations

from enum import IntEnum

API_BASE: str = "https://mobileapi.gdhv-iot.com"

CLIENT_ID: str = "1af761dc-085a-411f-9cb9-53e5e2115bd2"

AUTHORITY: str = (
    "https://gdhvb2cflameconnect.b2clogin.com/"
    "gdhvb2cflameconnect.onmicrosoft.com/"
    "B2C_1A_FirePhoneSignUpOrSignInWithPhoneOrEmail"
)

SCOPES: list[str] = [
    "https://gdhvb2cflameconnect.onmicrosoft.com/Mobile/read",
]

DEFAULT_HEADERS: dict[str, str] = {
    "app_name": "FlameConnect",
    "api_version": "1.0",
    "app_version": "2.22.0",
    "app_device_os": "android",
    "device_version": "14",
    "device_manufacturer": "Python",
    "device_model": "FlameConnectReader",
    "lang_code": "en",
    "country": "US",
    "logging_required_flag": "True",
}


class ParameterId(IntEnum):
    """Wire protocol parameter identifiers."""

    TEMPERATURE_UNIT = 236
    MODE = 321
    FLAME_EFFECT = 322
    HEAT_SETTINGS = 323
    HEAT_MODE = 325
    TIMER = 326
    SOFTWARE_VERSION = 327
    ERROR = 329
    SOUND = 369
    LOG_EFFECT = 370
