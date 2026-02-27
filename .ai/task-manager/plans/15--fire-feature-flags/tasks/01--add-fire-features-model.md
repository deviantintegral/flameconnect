---
id: 1
group: "fire-feature-flags"
dependencies: []
status: "completed"
created: 2026-02-27
skills:
  - python-dataclasses
---
# Add FireFeatures Dataclass and Update Fire Model

## Objective
Add a `FireFeatures` frozen dataclass to `models.py` with all 24 boolean feature flags, and add a `features` field to the `Fire` dataclass. Also add a `_parse_fire_features()` helper to `client.py` and wire it into both `get_fires()` and `get_fire_overview()`.

## Skills Required
- Python dataclasses and type annotations

## Acceptance Criteria
- [ ] `FireFeatures` dataclass exists in `models.py` with all 24 boolean fields defaulting to `False`
- [ ] `Fire` dataclass has a `features: FireFeatures` field with default `FireFeatures()`
- [ ] `FireFeatures` is exported from `__init__.py`
- [ ] `_parse_fire_features()` helper in `client.py` maps PascalCase JSON keys to snake_case fields
- [ ] `get_fires()` populates `Fire.features` from `entry.get("FireFeature", {})`
- [ ] `get_fire_overview()` populates `Fire.features` checking `data.get("FireDetails", {}).get("FireFeature", {})` first, then `wifi.get("FireFeature", {})` as fallback
- [ ] Test fixtures updated with `"FireFeature"` data
- [ ] New tests for `FireFeatures` defaults, `_parse_fire_features`, and both client methods
- [ ] `uv run ruff check .` passes
- [ ] `uv run mypy src/` passes
- [ ] `uv run pytest` passes (all existing + new tests)

## Technical Requirements
- `FireFeatures` must be `@dataclass(frozen=True, slots=True)` matching existing conventions
- The 24 boolean fields (in snake_case): `sound`, `simple_heat`, `advanced_heat`, `seven_day_timer`, `count_down_timer`, `moods`, `flame_height`, `rgb_flame_accent`, `flame_dimming`, `rgb_fuel_bed`, `fuel_bed_dimming`, `flame_fan_speed`, `rgb_back_light`, `front_light_amber`, `pir_toggle_smart_sense`, `lgt1_to_5`, `requires_warm_up`, `apply_flame_only_first`, `flame_amber`, `check_if_remote_was_used`, `media_accent`, `power_boost`, `fan_only`, `rgb_log_effect`
- PascalCase API key mapping: `Sound`, `SimpleHeat`, `AdvancedHeat`, `SevenDayTimer`, `CountDownTimer`, `Moods`, `FlameHeight`, `RgbFlameAccent`, `FlameDimming`, `RgbFuelBed`, `FuelBedDimming`, `FlameFanSpeed`, `RgbBackLight`, `FrontLightAmber`, `PirToggleSmartSense`, `Lgt1To5`, `RequiresWarmUp`, `ApplyFlameOnlyFirst`, `FlameAmber`, `CheckIfRemoteWasUsed`, `MediaAccent`, `PowerBoost`, `FanOnly`, `RgbLogEffect`
- `features` field must come AFTER existing `Fire` fields (with a default) to avoid breaking existing constructor calls

## Input Dependencies
None — this is the foundation task.

## Output Artifacts
- Updated `src/flameconnect/models.py` with `FireFeatures` dataclass and updated `Fire`
- Updated `src/flameconnect/__init__.py` with `FireFeatures` export
- Updated `src/flameconnect/client.py` with `_parse_fire_features()` and updated `get_fires()`/`get_fire_overview()`
- Updated test fixtures and new tests

## Implementation Notes
- Follow the existing code conventions (frozen dataclasses, slots=True, type annotations)
- The `_parse_fire_features` helper should accept `dict[str, Any]` and use `.get(key, False)` for each field
- For `get_fire_overview()`, check `data.get("FireDetails", {}).get("FireFeature", {})` first (canonical location per C# model), then `wifi.get("FireFeature", {})` as fallback
