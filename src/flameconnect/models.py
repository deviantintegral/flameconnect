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

    HIGH = 0
    LOW = 1


class PulsatingEffect(IntEnum):
    """Pulsating flame effect."""

    OFF = 0
    ON = 1


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


NAMED_COLORS: dict[str, RGBWColor] = {
    "dark-red": RGBWColor(red=180, green=0, blue=0, white=0),
    "light-red": RGBWColor(red=255, green=0, blue=0, white=80),
    "dark-yellow": RGBWColor(red=180, green=120, blue=0, white=0),
    "light-yellow": RGBWColor(red=255, green=200, blue=0, white=80),
    "dark-green": RGBWColor(red=0, green=180, blue=0, white=0),
    "light-green": RGBWColor(red=0, green=255, blue=0, white=80),
    "dark-cyan": RGBWColor(red=0, green=180, blue=180, white=0),
    "light-cyan": RGBWColor(red=0, green=255, blue=255, white=80),
    "dark-blue": RGBWColor(red=0, green=0, blue=180, white=0),
    "light-blue": RGBWColor(red=0, green=0, blue=255, white=80),
    "dark-purple": RGBWColor(red=128, green=0, blue=180, white=0),
    "light-purple": RGBWColor(red=180, green=0, blue=255, white=80),
    "dark-pink": RGBWColor(red=180, green=0, blue=80, white=0),
    "light-pink": RGBWColor(red=255, green=0, blue=128, white=80),
}

# ---------------------------------------------------------------------------
# Fire identity
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FireFeatures:
    """Boolean feature flags reported by the fireplace."""

    sound: bool = False
    simple_heat: bool = False
    advanced_heat: bool = False
    seven_day_timer: bool = False
    count_down_timer: bool = False
    moods: bool = False
    flame_height: bool = False
    rgb_flame_accent: bool = False
    flame_dimming: bool = False
    rgb_fuel_bed: bool = False
    fuel_bed_dimming: bool = False
    flame_fan_speed: bool = False
    rgb_back_light: bool = False
    front_light_amber: bool = False
    pir_toggle_smart_sense: bool = False
    lgt1_to_5: bool = False
    requires_warm_up: bool = False
    apply_flame_only_first: bool = False
    flame_amber: bool = False
    check_if_remote_was_used: bool = False
    media_accent: bool = False
    power_boost: bool = False
    fan_only: bool = False
    rgb_log_effect: bool = False


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
    features: FireFeatures = FireFeatures()


# ---------------------------------------------------------------------------
# Parameter dataclasses – one per parameter type
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ModeParam:
    """Mode parameter (ParameterId 321)."""

    mode: FireMode
    target_temperature: float


@dataclass(frozen=True, slots=True)
class FlameEffectParam:
    """Flame effect parameter (ParameterId 322)."""

    flame_effect: FlameEffect
    flame_speed: int
    brightness: Brightness
    pulsating_effect: PulsatingEffect
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
