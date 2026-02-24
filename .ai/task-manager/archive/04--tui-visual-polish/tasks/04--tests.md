---
id: 4
group: "testing"
dependencies: [3]
status: "completed"
created: "2026-02-24"
skills:
  - python
  - pytest
---
# Add tests for heat mode dialog, fire switcher, CLI heat-mode, and DashboardScreen constructor

## Objective
Write tests covering the new heat mode dialog flow, fire switcher dialog flow, CLI `_set_heat_mode` boost:N syntax, and update existing test fixtures for the DashboardScreen constructor change.

## Skills Required
- Python (pytest, unittest.mock, async testing)
- pytest (fixtures, parametrize, mock patching)

## Meaningful Test Strategy Guidelines

Your critical mantra for test generation is: "write a few tests, mostly integration".

**When TO Write Tests:**
- Custom business logic and algorithms
- Critical user workflows and data transformations
- Edge cases and error conditions for core functionality
- Integration points between different system components

**When NOT to Write Tests:**
- Third-party library functionality (Textual's ModalScreen, Button, etc.)
- Framework features (already tested upstream)
- Simple CRUD operations without custom logic

## Acceptance Criteria
- [ ] `TestCycleHeatMode` in `test_tui_actions.py` replaced/updated for `action_set_heat_mode` dialog flow
- [ ] Test: `action_set_heat_mode` opens HeatModeScreen with current mode/boost values
- [ ] Test: `_apply_heat_mode` writes correct HeatParam for Normal, Eco, and Boost (with duration)
- [ ] Test: `action_switch_fire` re-fetches fires, opens FireSelectScreen, handles callback
- [ ] Test: `action_switch_fire` single-fire guard (notifies, no dialog)
- [ ] Test: CLI `_set_heat_mode` with `normal`, `eco`, `boost:15` values
- [ ] Test: CLI `_set_heat_mode` rejects `fan-only`, `boost:0`, `boost:21`, `boost:abc`
- [ ] DashboardScreen test fixtures updated to pass `Fire` object instead of `fire_id`/`fire_name`
- [ ] All existing tests still pass: `uv run pytest`
- [ ] `uv run ruff check tests/` passes
- [ ] `uv run mypy --strict tests/` passes (or matches pre-existing error baseline)

Use your internal Todo tool to track these and keep on track.

## Technical Requirements
- Follow existing test patterns in `test_tui_actions.py` and `test_cli_set.py`
- Use `unittest.mock.patch` for `client.write_parameters` and `client.get_fires`
- Use `unittest.mock.AsyncMock` for async methods
- For DashboardScreen fixtures, create a `Fire` object with test data (brand, product_model, etc.)
- CLI tests should call `_set_heat_mode` directly (not through argparse)

## Input Dependencies
- Task 03 must be complete: all new dialog screens, app.py actions, and CLI changes implemented

## Output Artifacts
- Updated `tests/test_tui_actions.py`
- Updated `tests/test_cli_set.py`

## Implementation Notes

<details>
<summary>Detailed implementation guidance</summary>

### DashboardScreen Fixture Update
The existing test fixtures create `DashboardScreen(client, fire_id, fire_name)`. These must be updated to `DashboardScreen(client, fire)` where `fire` is a `Fire` object:
```python
from flameconnect.models import Fire, ConnectionState

_TEST_FIRE = Fire(
    fire_id="test-fire-id",
    friendly_name="Test Fire",
    brand="TestBrand",
    product_type="Electric",
    product_model="TM-100",
    item_code="TB-001",
    connection_state=ConnectionState.CONNECTED,
    with_heat=True,
    is_iot_fire=True,
)
```
Search for all `DashboardScreen(` calls in test files and update them.

### Heat Mode TUI Tests
Replace `TestCycleHeatMode` with tests for the dialog flow. Follow the pattern used for `TestSetFlameSpeed`:
- Mock `push_screen` to capture the HeatModeScreen and its callback
- Invoke the callback with test data
- Verify `write_parameters` was called with correct `HeatParam`

Test `_apply_heat_mode` specifically:
- Normal: `replace(current, heat_mode=HeatMode.NORMAL)` — boost_duration preserved
- Eco: `replace(current, heat_mode=HeatMode.ECO)` — boost_duration preserved
- Boost with 15 min: `replace(current, heat_mode=HeatMode.BOOST, boost_duration=15)`

### Fire Switcher TUI Tests
- Test that `action_switch_fire` calls `client.get_fires()` first
- Test single-fire guard: mock `get_fires` returning 1 fire, verify `notify` called
- Test multi-fire: mock `get_fires` returning 2+ fires, verify `push_screen` called with `FireSelectScreen`
- Test callback: verify `pop_screen`, `fire_id` update, and `_push_dashboard` call

### CLI Tests
Add tests to `test_cli_set.py`:
```python
class TestSetHeatMode:
    async def test_set_normal(self, ...):
        await _set_heat_mode(client, fire_id, "normal")
        # verify write_parameters called with HeatMode.NORMAL

    async def test_set_eco(self, ...):
        await _set_heat_mode(client, fire_id, "eco")

    async def test_set_boost_with_duration(self, ...):
        await _set_heat_mode(client, fire_id, "boost:15")
        # verify write_parameters called with HeatMode.BOOST, boost_duration=15

    async def test_reject_fan_only(self, ...):
        # verify sys.exit(1) called

    async def test_reject_boost_no_duration(self, ...):
        # "boost" without :N

    async def test_reject_boost_out_of_range(self, ...):
        # "boost:0", "boost:21"

    async def test_reject_boost_invalid_format(self, ...):
        # "boost:abc"
```

Follow existing `TestSetHeatMode` if it exists, or the `TestSetFlameEffect` pattern.

### Pre-existing test/mypy baselines
- Known pre-existing mypy errors: `b2c_login.py:112` (arg-type), `flame_speed_screen.py:72` (Button variant)
- Run quality gates on specific new/modified files if needed to avoid flagging pre-existing issues

</details>
