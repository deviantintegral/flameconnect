"""Async Python library for controlling Dimplex/Faber fireplaces."""

from __future__ import annotations

__version__ = "0.1.0"

from flameconnect.exceptions import (
    ApiError,
    AuthenticationError,
    FlameConnectError,
    ProtocolError,
)
from flameconnect.models import (
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
    # Exceptions
    "ApiError",
    "AuthenticationError",
    "FlameConnectError",
    "ProtocolError",
    # Enums
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
    # Type aliases
    "Parameter",
]
