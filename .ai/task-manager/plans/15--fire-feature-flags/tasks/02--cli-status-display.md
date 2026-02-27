---
id: 2
group: "fire-feature-flags"
dependencies: [1]
status: "completed"
created: 2026-02-27
skills:
  - python-cli
---
# Display Fire Feature Flags in CLI Status Command

## Objective
Add a `_display_features()` function to `cli.py` that shows all 24 fire feature flags with Yes/No values in the `cmd_status` output, and add tests for it.

## Skills Required
- Python CLI output formatting

## Acceptance Criteria
- [ ] `_display_features(features: FireFeatures)` function exists in `cli.py`
- [ ] `cmd_status` calls `_display_features` after fire identity info and before parameters
- [ ] All 24 feature flags are displayed with human-readable labels and Yes/No values
- [ ] Tests in `test_cli_commands.py` verify the features section appears in status output
- [ ] `uv run ruff check .` passes
- [ ] `uv run mypy src/` passes
- [ ] `uv run pytest` passes

## Technical Requirements
- Display format should match existing `_display_*` style in `cli.py` (indented, with section header)
- Human-readable labels derived from field names (e.g., `simple_heat` → `Simple Heat`)
- Section header: "Supported Features"
- Show all 24 features with Yes/No values

## Input Dependencies
- Task 01: `FireFeatures` dataclass in `models.py`, `Fire.features` field populated by client

## Output Artifacts
- Updated `src/flameconnect/cli.py` with `_display_features()` and updated `cmd_status`
- New tests in `tests/test_cli_commands.py`

## Implementation Notes
- Place the features section between the Connection line and the parameter count line
- Use the same indentation style as other display functions (2-space indent for header, 4-space for values)
- Match the `_display_*` naming convention
