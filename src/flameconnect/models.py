"""Data models and enums for the flameconnect library."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

# ---------------------------------------------------------------------------
# Enums – values correspond to wire protocol byte values
# ---------------------------------------------------------------------------


class FireMode(IntEnum):
    """Fireplace operating mode."""

    STANDBY = 0
    MANUAL = 1


class FlameEffect(IntEnum):
    """Flame effect on/off."""

    OFF = 0
    ON = 1


class Brightness(IntEnum):
    """Flame brightness level."""

    LOW = 0
    HIGH = 1


class HeatStatus(IntEnum):
    """Heater on/off status."""

    OFF = 0
    ON = 1


class HeatMode(IntEnum):
    """Heater operating mode."""

    NORMAL = 0
    BOOST = 1
    ECO = 2
    FAN_ONLY = 3
    SCHEDULE = 4


class HeatControl(IntEnum):
    """Heat control availability."""

    SOFTWARE_DISABLED = 0
    HARDWARE_DISABLED = 1
    ENABLED = 2


class FlameColor(IntEnum):
    """Flame colour preset."""

    ALL = 0
    YELLOW_RED = 1
    YELLOW_BLUE = 2
    BLUE = 3
    RED = 4
    YELLOW = 5
    BLUE_RED = 6


class LightStatus(IntEnum):
    """Light on/off status."""

    OFF = 0
    ON = 1


class TimerStatus(IntEnum):
    """Timer enabled/disabled."""

    DISABLED = 0
    ENABLED = 1


class TempUnit(IntEnum):
    """Temperature display unit."""

    FAHRENHEIT = 0
    CELSIUS = 1


class LogEffect(IntEnum):
    """Log/ember bed effect on/off."""

    OFF = 0
    ON = 1


class MediaTheme(IntEnum):
    """Fuel-bed media theme preset."""

    USER_DEFINED = 0
    WHITE = 1
    BLUE = 2
    PURPLE = 3
    RED = 4
    GREEN = 5
    PRISM = 6
    KALEIDOSCOPE = 7
    MIDNIGHT = 8


class ConnectionState(IntEnum):
    """IoT connection state reported by the cloud."""

    UNKNOWN = 0
    NOT_CONNECTED = 1
    CONNECTED = 2
    UPDATING_FIRMWARE = 3


# ---------------------------------------------------------------------------
# Value-object dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RGBWColor:
    """RGBW colour value."""

    red: int
    green: int
    blue: int
    white: int


# ---------------------------------------------------------------------------
# Fire identity
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Fire:
    """Represents a registered fireplace."""

    fire_id: str
    friendly_name: str
    brand: str
    product_type: str
    product_model: str
    item_code: str
    connection_state: ConnectionState
    with_heat: bool
    is_iot_fire: bool


# ---------------------------------------------------------------------------
# Parameter dataclasses – one per parameter type
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ModeParam:
    """Mode parameter (ParameterId 321)."""

    mode: FireMode
    temperature: float


@dataclass(frozen=True, slots=True)
class FlameEffectParam:
    """Flame effect parameter (ParameterId 322)."""

    flame_effect: FlameEffect
    flame_speed: int
    brightness: Brightness
    media_theme: MediaTheme
    media_light: LightStatus
    media_color: RGBWColor
    overhead_light: LightStatus
    overhead_color: RGBWColor
    light_status: LightStatus
    flame_color: FlameColor
    ambient_sensor: LightStatus


@dataclass(frozen=True, slots=True)
class HeatParam:
    """Heat settings parameter (ParameterId 323)."""

    heat_status: HeatStatus
    heat_mode: HeatMode
    setpoint_temperature: float
    boost_duration: int


@dataclass(frozen=True, slots=True)
class HeatModeParam:
    """Heat mode/control parameter (ParameterId 325)."""

    heat_control: HeatControl


@dataclass(frozen=True, slots=True)
class TimerParam:
    """Timer parameter (ParameterId 326)."""

    timer_status: TimerStatus
    duration: int


@dataclass(frozen=True, slots=True)
class SoftwareVersionParam:
    """Software version parameter (ParameterId 327)."""

    ui_major: int
    ui_minor: int
    ui_test: int
    control_major: int
    control_minor: int
    control_test: int
    relay_major: int
    relay_minor: int
    relay_test: int


@dataclass(frozen=True, slots=True)
class ErrorParam:
    """Error parameter (ParameterId 329)."""

    error_byte1: int
    error_byte2: int
    error_byte3: int
    error_byte4: int


@dataclass(frozen=True, slots=True)
class TempUnitParam:
    """Temperature unit parameter (ParameterId 236)."""

    unit: TempUnit


@dataclass(frozen=True, slots=True)
class SoundParam:
    """Sound parameter (ParameterId 369)."""

    volume: int
    sound_file: int


@dataclass(frozen=True, slots=True)
class LogEffectParam:
    """Log effect parameter (ParameterId 370)."""

    log_effect: LogEffect
    color: RGBWColor
    pattern: int


# ---------------------------------------------------------------------------
# Parameter union type
# ---------------------------------------------------------------------------

Parameter = (
    ModeParam
    | FlameEffectParam
    | HeatParam
    | HeatModeParam
    | TimerParam
    | SoftwareVersionParam
    | ErrorParam
    | TempUnitParam
    | SoundParam
    | LogEffectParam
)

# ---------------------------------------------------------------------------
# Aggregate overview
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FireOverview:
    """Complete overview of a fireplace including its current parameters."""

    fire: Fire
    parameters: list[Parameter]
