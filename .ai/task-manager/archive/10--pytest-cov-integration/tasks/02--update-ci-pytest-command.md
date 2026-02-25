---
id: 2
group: "pytest-cov-integration"
dependencies: []
status: "completed"
created: 2026-02-25
skills:
  - "ci-config"
---
# Update CI pytest command with coverage flags

## Objective
Update the pytest invocation in the GitHub Actions CI workflow to include coverage reporting flags.

## Skills Required
- ci-config: Editing GitHub Actions workflow YAML files.

## Acceptance Criteria
- [ ] The Test step in `.github/workflows/ci.yml` runs `uv run pytest --cov=flameconnect --cov-report=term-missing --tb=short`
- [ ] No other CI steps are modified
- [ ] The workflow YAML remains valid

## Technical Requirements
- Edit `/root/flameconnect/.github/workflows/ci.yml`
- Change the Test step `run` command from `uv run pytest --tb=short` to `uv run pytest --cov=flameconnect --cov-report=term-missing --tb=short`

## Input Dependencies
None.

## Output Artifacts
- Updated `.github/workflows/ci.yml` with coverage-enabled pytest command.

## Implementation Notes
- Only the `run:` line of the "Test" step needs to change.
- Do not modify the mutation test step — coverage flags should NOT be added there.
