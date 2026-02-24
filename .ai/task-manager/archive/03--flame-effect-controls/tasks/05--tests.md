---
id: 5
group: "testing"
dependencies: [1, 4]
status: "completed"
created: "2026-02-23"
skills:
  - python
  - unit-testing
---
# Add Tests for New CLI Commands and TUI Actions

## Objective
Add tests for all new CLI set command handlers and TUI action methods, following the established patterns in `test_cli_set.py` and `test_tui_actions.py`.

## Skills Required
- Python: pytest, async test methods, mock objects
- Unit testing: aioresponses for CLI HTTP mocking, unittest.mock for TUI action mocking

## Meaningful Test Strategy Guidelines

Your critical mantra for test generation is: "write a few tests, mostly integration".

**When TO write tests:** Custom business logic (colour parsing, value validation), critical user workflows (the read-modify-write pattern), edge cases (invalid input, write-in-progress guards).

**When NOT to write tests:** Framework functionality (Textual widget rendering), simple property access, obvious functionality.

**Focus areas:**
- CLI: Happy path (value accepted, API called with correct parameter) + invalid value (error message, sys.exit)
- TUI toggles: Happy path (value flipped correctly) + write guard (no-op when `_write_in_progress`)
- TUI dialogs: Apply method writes correct field + write guard

## Acceptance Criteria
- [ ] CLI tests: At least one happy-path and one invalid-value test per new handler (7 handlers)
- [ ] CLI colour tests: Test both RGBW format and named preset format for `media-color` and `overhead-color`
- [ ] CLI colour tests: Test `_parse_color` with invalid input
- [ ] TUI toggle tests: At least one happy-path and one write-guard test per toggle (6 toggles)
- [ ] TUI dialog tests: At least one happy-path test per apply method (4 dialog apply methods)
- [ ] All tests pass: `pytest`
- [ ] All quality gates pass: `ruff check`, `mypy --strict`

## Technical Requirements
- pytest with async support (existing `conftest.py` provides `token_auth` fixture)
- `aioresponses` for CLI HTTP mocking (existing pattern in `test_cli_set.py`)
- `unittest.mock.AsyncMock`, `MagicMock`, `PropertyMock` for TUI action mocking (existing pattern in `test_tui_actions.py`)

## Input Dependencies
- Task 1: CLI handlers and `NAMED_COLORS` must exist
- Task 4: TUI action methods must exist

## Output Artifacts
- Modified `tests/test_cli_set.py` with new test classes
- Modified `tests/test_tui_actions.py` with new test classes

## Implementation Notes

<details>
<summary>Detailed implementation guidance</summary>

### CLI Tests (`tests/test_cli_set.py`)

Add imports for new handler functions at the top:
```python
from flameconnect.cli import (
    # ... existing imports ...
    _set_flame_effect,
    _set_media_light,
    _set_media_color,
    _set_overhead_light,
    _set_overhead_color,
    _set_light_status,
    _set_ambient_sensor,
    _parse_color,
)
```

#### Simple on/off handler tests (5 handlers)

Follow the exact pattern of `TestSetPulsating` (existing class). Each test class needs:

1. **Happy path**: Mock GET (overview) + POST (write), call handler, assert POST was called with ParameterId 322.
2. **Invalid value**: Call handler with bad value, assert `sys.exit(1)` via `pytest.raises(SystemExit)`.

Example for `_set_flame_effect`:
```python
class TestSetFlameEffect:
    async def test_set_flame_effect_on(self, mock_api, token_auth, overview_payload):
        mock_api.get(OVERVIEW_URL, payload=overview_payload)
        mock_api.post(WRITE_URL, payload={})
        async with FlameConnectClient(token_auth) as client:
            await _set_flame_effect(client, FIRE_ID, "on")
        key = ("POST", URL(WRITE_URL))
        calls = mock_api.requests[key]
        assert len(calls) == 1
        body = calls[0].kwargs["json"]
        assert body["Parameters"][0]["ParameterId"] == 322

    async def test_set_flame_effect_invalid(self, mock_api, token_auth, capsys):
        async with FlameConnectClient(token_auth) as client:
            with pytest.raises(SystemExit):
                await _set_flame_effect(client, FIRE_ID, "maybe")
```

Repeat for: `_set_media_light`, `_set_overhead_light`, `_set_light_status`, `_set_ambient_sensor`.

#### Colour handler tests (2 handlers)

More tests needed because of dual input format:

```python
class TestSetMediaColor:
    async def test_set_media_color_named(self, mock_api, token_auth, overview_payload):
        mock_api.get(OVERVIEW_URL, payload=overview_payload)
        mock_api.post(WRITE_URL, payload={})
        async with FlameConnectClient(token_auth) as client:
            await _set_media_color(client, FIRE_ID, "light-red")
        key = ("POST", URL(WRITE_URL))
        assert len(mock_api.requests[key]) == 1

    async def test_set_media_color_rgbw(self, mock_api, token_auth, overview_payload):
        mock_api.get(OVERVIEW_URL, payload=overview_payload)
        mock_api.post(WRITE_URL, payload={})
        async with FlameConnectClient(token_auth) as client:
            await _set_media_color(client, FIRE_ID, "255,0,0,0")
        key = ("POST", URL(WRITE_URL))
        assert len(mock_api.requests[key]) == 1

    async def test_set_media_color_invalid(self, mock_api, token_auth, capsys):
        async with FlameConnectClient(token_auth) as client:
            with pytest.raises(SystemExit):
                await _set_media_color(client, FIRE_ID, "not-a-color")
```

Same pattern for `TestSetOverheadColor`.

#### _parse_color unit tests

```python
class TestParseColor:
    def test_named_preset(self):
        result = _parse_color("light-red")
        assert result == RGBWColor(red=255, green=0, blue=0, white=80)

    def test_rgbw_format(self):
        result = _parse_color("100,200,50,25")
        assert result == RGBWColor(red=100, green=200, blue=50, white=25)

    def test_invalid_string(self):
        assert _parse_color("not-a-color") is None

    def test_out_of_range(self):
        assert _parse_color("256,0,0,0") is None

    def test_wrong_count(self):
        assert _parse_color("100,200,50") is None
```

### TUI Tests (`tests/test_tui_actions.py`)

#### Toggle action tests (6 toggles)

Follow the `TestToggleBrightness` pattern exactly. Each needs:

1. **Happy path**: Assert `write_parameters` was called with the toggled value.
2. **Write guard**: Set `_write_in_progress = True`, assert `write_parameters` not called.

Example for `action_toggle_flame_effect`:
```python
class TestToggleFlameEffect:
    async def test_toggles_on_to_off(self, mock_client, mock_dashboard):
        # Default fixture has flame_effect ON
        app = _make_app(mock_client, mock_dashboard)
        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            await app.action_toggle_flame_effect()
        written_param = mock_client.write_parameters.call_args[0][1][0]
        assert isinstance(written_param, FlameEffectParam)
        assert written_param.flame_effect == FlameEffect.OFF

    async def test_no_op_when_write_in_progress(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app._write_in_progress = True
        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            await app.action_toggle_flame_effect()
        mock_client.write_parameters.assert_not_awaited()
```

Repeat for: `action_toggle_pulsating` (OFF→ON), `action_toggle_media_light` (ON→OFF), `action_toggle_overhead_light` (ON→OFF), `action_toggle_light_status` (ON→OFF), `action_toggle_ambient_sensor` (OFF→ON).

Note: Check `_DEFAULT_FLAME_EFFECT` fixture values (line 33-46) to know the starting state for each field.

#### Dialog apply method tests (4 dialog applies)

Follow the `TestApplyFlameSpeed` pattern. Each needs at least a happy-path test:

```python
class TestApplyFlameColor:
    async def test_sets_flame_color(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            await app._apply_flame_color(FlameColor.BLUE)
        written_param = mock_client.write_parameters.call_args[0][1][0]
        assert written_param.flame_color == FlameColor.BLUE

    async def test_no_op_when_write_in_progress(self, mock_client, mock_dashboard):
        app = _make_app(mock_client, mock_dashboard)
        app._write_in_progress = True
        with patch.object(type(app), "screen", new_callable=PropertyMock) as prop:
            prop.return_value = mock_dashboard
            await app._apply_flame_color(FlameColor.RED)
        mock_client.write_parameters.assert_not_awaited()
```

Repeat for: `_apply_media_theme` (with `MediaTheme.BLUE`), `_apply_media_color` (with `RGBWColor(...)`), `_apply_overhead_color` (with `RGBWColor(...)`).

### Import updates for test_tui_actions.py

Add to the imports block:
```python
from flameconnect.models import (
    # ... existing ...
    FlameEffect,
    PulsatingEffect,
)
```

`FlameColor`, `MediaTheme`, `LightStatus`, `RGBWColor` are already imported.

</details>
