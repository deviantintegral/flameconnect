---
id: 1
group: "pytest-cov-integration"
dependencies: []
status: "completed"
created: 2026-02-25
skills:
  - "python-packaging"
---
# Add pytest-cov dependency and coverage configuration

## Objective
Add `pytest-cov>=5.0` as a dev dependency and configure `[tool.coverage.run]` in `pyproject.toml`.

## Skills Required
- python-packaging: Editing `pyproject.toml` dependency lists and tool configuration sections.

## Acceptance Criteria
- [ ] `pytest-cov>=5.0` is listed in `[project.optional-dependencies] dev`
- [ ] `[tool.coverage.run]` section exists with `source = ["src/flameconnect"]`
- [ ] No other coverage config sections are added (no `[tool.coverage.report]`, no `omit`)
- [ ] `uv sync --all-extras --dev` succeeds

## Technical Requirements
- Edit `/root/flameconnect/pyproject.toml`
- Add `"pytest-cov>=5.0"` to the existing dev dependency list
- Add a new `[tool.coverage.run]` section after the existing `[tool.pytest.ini_options]` section

## Input Dependencies
None.

## Output Artifacts
- Updated `pyproject.toml` with pytest-cov dependency and coverage.run config.

## Implementation Notes
- Follow existing version pinning pattern (minimum version with `>=`).
- Keep the `[tool.coverage.run]` section minimal: only `source`, no `omit` or `branch`.
