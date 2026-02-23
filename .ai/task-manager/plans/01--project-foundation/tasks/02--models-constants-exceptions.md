---
id: 2
group: "core-library"
dependencies: [1]
status: "pending"
created: "2026-02-23"
skills:
  - python
---
# Implement models, enums, constants, and exceptions

## Objective
Create the typed foundation of the library: Python `Enum` classes for all parameter values, `dataclass` types for API responses and parameter structures, constants for API configuration, and a custom exception hierarchy. These are the building blocks consumed by all other modules.

## Skills Required
- Python type system (dataclasses, Enum, type annotations)

## Acceptance Criteria
- [ ] `src/flameconnect/const.py` — API base URL, client ID, authority, scopes, default headers, ParameterId constants
- [ ] `src/flameconnect/models.py` — All enums (FireMode, FlameEffect, HeatStatus, HeatMode, HeatControl, FlameColor, LightStatus, TimerStatus, TempUnit, LogEffect, MediaTheme, ConnectionState) and dataclasses (Fire, FireOverview, ModeParam, FlameEffectParam, HeatParam, HeatModeParam, TimerParam, SoftwareVersionParam, ErrorParam, TempUnitParam, SoundParam, LogEffectParam)
- [ ] `src/flameconnect/exceptions.py` — FlameConnectError base, AuthenticationError, ApiError, ProtocolError
- [ ] All files pass `mypy --strict` with zero errors
- [ ] All files pass `ruff check` and `ruff format --check` with zero errors

Use your internal Todo tool to track these and keep on track.

## Technical Requirements
- Use `@dataclass(frozen=True, slots=True)` for immutable parameter types
- Use `IntEnum` for enums that map to wire protocol integer values
- Dataclasses must have full type annotations (no `Any` types)
- Temperature fields should be `float` type
- RGBW color fields should use a nested `RGBWColor` dataclass with `red`, `green`, `blue`, `white` as `int` fields

## Input Dependencies
- Task 1: Package skeleton must exist (`src/flameconnect/` directory, `pyproject.toml`)

## Output Artifacts
- `src/flameconnect/const.py`
- `src/flameconnect/models.py`
- `src/flameconnect/exceptions.py`

## Implementation Notes

<details>
<summary>Detailed implementation guidance</summary>

1. **const.py**: Extract all constants from `flameconnect_reader.py`:
   ```python
   API_BASE = "https://mobileapi.gdhv-iot.com"
   CLIENT_ID = "1af761dc-085a-411f-9cb9-53e5e2115bd2"
   AUTHORITY = "https://gdhvb2cflameconnect.b2clogin.com/gdhvb2cflameconnect.onmicrosoft.com/B2C_1A_FirePhoneSignUpOrSignInWithPhoneOrEmail"
   SCOPES = ["https://gdhvb2cflameconnect.onmicrosoft.com/Mobile/read"]
   ```
   Include default HTTP headers (app_name, api_version, app_version, etc.) as a dict constant.
   Include `ParameterId` constants as an `IntEnum` or module-level constants:
   - TEMPERATURE_UNIT = 236, MODE = 321, FLAME_EFFECT = 322, HEAT_SETTINGS = 323, HEAT_MODE = 325, TIMER = 326, SOFTWARE_VERSION = 327, ERROR = 329, SOUND = 369, LOG_EFFECT = 370

2. **models.py**: Reference `flameconnect_reader.py` lines 33-59 for existing enum mappings. Convert each dict to a proper `IntEnum`:
   ```python
   class FireMode(IntEnum):
       STANDBY = 0
       MANUAL = 1
   ```

   For parameter dataclasses, reference the `decode_parameter` function (lines 224-283) and `FLAMECONNECT_API_REPORT.md` parameter reference section. Each decoded parameter type gets its own dataclass.

   The `Fire` dataclass represents a fireplace from the GetFires response:
   ```python
   @dataclass(frozen=True, slots=True)
   class Fire:
       fire_id: str
       friendly_name: str
       brand: str
       product_type: str
       product_model: str
       item_code: str
       connection_state: ConnectionState
       with_heat: bool
       is_iot_fire: bool
   ```

   Create a `RGBWColor` dataclass reused in FlameEffectParam and LogEffectParam:
   ```python
   @dataclass(frozen=True, slots=True)
   class RGBWColor:
       red: int
       green: int
       blue: int
       white: int
   ```

   The `FlameEffectParam` dataclass should include media_theme (RGBWColor + theme + light), overhead_light (RGBWColor + light), flame fields, etc. Reference lines 234-248 of flameconnect_reader.py.

3. **exceptions.py**: Simple hierarchy:
   ```python
   class FlameConnectError(Exception): ...
   class AuthenticationError(FlameConnectError): ...
   class ApiError(FlameConnectError):
       def __init__(self, status: int, message: str) -> None: ...
   class ProtocolError(FlameConnectError): ...
   ```

4. **Important**: Use `logging.getLogger(__name__)` in any module that needs logging. No `print()`.

5. **Update `__init__.py`**: Export the key public types (FlameConnectError, Fire, and the parameter dataclasses) from the package root.
</details>
