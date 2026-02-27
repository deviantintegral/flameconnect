"""Async Python library for controlling Dimplex, Faber, and Real Flame fireplaces."""

from __future__ import annotations

__version__ = "0.3.0"

from flameconnect.auth import AbstractAuth, MsalAuth, TokenAuth
from flameconnect.client import FlameConnectClient
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
    "NAMED_COLORS",
    # Type aliases
    "Parameter",
]
