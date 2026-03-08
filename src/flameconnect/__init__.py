"""Async Python library for controlling Dimplex, Faber, and Real Flame fireplaces."""

from __future__ import annotations

__version__ = "0.5.3"

from flameconnect.auth import AbstractAuth, MsalAuth, TokenAuth
from flameconnect.client import FlameConnectClient
from flameconnect.const import (
    DEFAULT_TARGET_TEMPERATURE,
    DEFAULT_TIMER_DURATION,
    MAX_BOOST_DURATION,
    MAX_FLAME_SPEED,
    MAX_TEMP_CELSIUS,
    MAX_TEMP_FAHRENHEIT,
    MAX_TIMER_DURATION,
    MIN_BOOST_DURATION,
    MIN_FLAME_SPEED,
    MIN_TEMP_CELSIUS,
    MIN_TEMP_FAHRENHEIT,
)
from flameconnect.exceptions import (
    ApiError,
    AuthenticationError,
    FlameConnectError,
    ProtocolError,
)
from flameconnect.models import (
    NAMED_COLORS,
    Brightness,
    ConnectionState,
    ErrorParam,
    Fire,
    FireFeatures,
    FireMode,
    FireOverview,
    FlameColor,
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
    Parameter,
    PulsatingEffect,
    RGBWColor,
    SoftwareVersionParam,
    SoundParam,
    TempUnit,
    TempUnitParam,
    TimerParam,
    TimerStatus,
    convert_temp,
    display_name,
    kebab_name,
    temp_suffix,
)

__all__ = [
    "__version__",
    # Auth
    "AbstractAuth",
    "MsalAuth",
    "TokenAuth",
    # Client
    "FlameConnectClient",
    # Exceptions
    "ApiError",
    "AuthenticationError",
    "FlameConnectError",
    "ProtocolError",
    # Enums
    "Brightness",
    "ConnectionState",
    "FireMode",
    "FlameColor",
    "FlameEffect",
    "HeatControl",
    "HeatMode",
    "HeatStatus",
    "LightStatus",
    "LogEffect",
    "MediaTheme",
    "PulsatingEffect",
    "TempUnit",
    "TimerStatus",
    # Dataclasses
    "ErrorParam",
    "Fire",
    "FireFeatures",
    "FireOverview",
    "FlameEffectParam",
    "HeatModeParam",
    "HeatParam",
    "LogEffectParam",
    "ModeParam",
    "RGBWColor",
    "SoftwareVersionParam",
    "SoundParam",
    "TempUnitParam",
    "TimerParam",
    # Constants
    "DEFAULT_TARGET_TEMPERATURE",
    "DEFAULT_TIMER_DURATION",
    "MAX_BOOST_DURATION",
    "MAX_FLAME_SPEED",
    "MAX_TEMP_CELSIUS",
    "MAX_TEMP_FAHRENHEIT",
    "MAX_TIMER_DURATION",
    "MIN_BOOST_DURATION",
    "MIN_FLAME_SPEED",
    "MIN_TEMP_CELSIUS",
    "MIN_TEMP_FAHRENHEIT",
    "NAMED_COLORS",
    # Type aliases
    "Parameter",
    # Utilities
    "convert_temp",
    "display_name",
    "kebab_name",
    "temp_suffix",
]
