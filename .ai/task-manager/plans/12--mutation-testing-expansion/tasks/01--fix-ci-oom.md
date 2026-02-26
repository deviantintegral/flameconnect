---
id: 1
group: "mutation-testing-expansion"
dependencies: []
status: "completed"
created: 2026-02-25
skills:
  - "ci-config"
---
# Fix CI OOM by limiting mutmut parallelism

## Objective
Update the CI workflow to pass `--max-children 2` to mutmut, preventing out-of-memory kills on GitHub Actions.

## Acceptance Criteria
- [ ] `.github/workflows/ci.yml` mutation test step uses `uv run mutmut run --max-children 2`
- [ ] All existing tests still pass locally

## Technical Requirements
- Edit `.github/workflows/ci.yml`: change `uv run mutmut run` to `uv run mutmut run --max-children 2`
- This is a one-line change in the workflow file

## Output Artifacts
- Updated `.github/workflows/ci.yml`
