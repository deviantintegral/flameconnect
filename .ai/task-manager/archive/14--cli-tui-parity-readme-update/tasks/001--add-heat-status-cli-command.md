---
id: 1
group: "cli-parity"
dependencies: []
status: "completed"
created: 2026-02-25
skills:
  - python
  - pytest
---
# Add heat-status CLI Command and Tests

## Objective
Add a `heat-status` set parameter to the CLI for parity with the TUI's heat on/off toggle, update `_SET_PARAM_NAMES` and argparse help text, and add tests.

## Acceptance Criteria
- [ ] `_set_heat_status()` function added to `cli.py` following existing `_set_*` pattern
- [ ] `cmd_set()` dispatches `heat-status` to `_set_heat_status()`
- [ ] `_SET_PARAM_NAMES` includes `heat-status`
- [ ] Argparse help text includes `heat-status` and excludes stale `light-status`
- [ ] Tests in `test_cli_set.py` cover on/off and invalid values
- [ ] `ruff check`, `mypy`, and `pytest` pass

## Technical Requirements
- Pattern: fetch overview, find HeatParam, `dataclasses.replace(heat_status=...)`, write back
- HeatStatus enum: ON=1, OFF=0 (ParameterId 323)
- Import `HeatStatus` from models (already imported in cli.py)

## Input Dependencies
None

## Output Artifacts
- Modified `src/flameconnect/cli.py`
- Modified `tests/test_cli_set.py`
