---
id: 9
group: "infrastructure"
dependencies: [6]
status: "pending"
created: "2026-02-23"
skills:
  - github-actions
  - ci-cd
---
# Set up GitHub Actions CI/CD workflows

## Objective
Create three GitHub Actions workflows: CI (lint, type-check, test, mutation test on every push/PR), conventional commits validation, and release management with release-please and PyPI publishing.

## Skills Required
- GitHub Actions workflow authoring
- CI/CD pipeline design

## Acceptance Criteria
- [ ] `.github/workflows/ci.yml` — runs ruff, mypy, pytest, and mutmut on push/PR
- [ ] `.github/workflows/conventional-commits.yml` — validates PR titles follow conventional commit format
- [ ] `.github/workflows/release.yml` — release-please for changelog/versioning + PyPI publish on release
- [ ] CI workflow uses uv for dependency installation
- [ ] CI workflow tests on Python 3.13
- [ ] Release workflow builds wheel and publishes to PyPI via trusted publishing
- [ ] All workflows pass syntax validation

Use your internal Todo tool to track these and keep on track.

## Technical Requirements
- Use `astral-sh/setup-uv` action for uv installation in CI
- Use `actions/setup-python` with python-version: "3.13"
- ruff step: `uv run ruff check . && uv run ruff format --check .`
- mypy step: `uv run mypy src/`
- pytest step: `uv run pytest`
- mutmut step: `uv run mutmut run --paths-to-mutate=src/flameconnect/protocol.py --no-progress` (focus on protocol module to keep CI fast)
- Conventional commits: use `amannn/action-semantic-pull-request` or equivalent
- Release: use `googleapis/release-please-action` with `release-type: python`
- PyPI publish: use `pypa/gh-action-pypi-publish` with trusted publishing (OIDC)

## Input Dependencies
- Task 6: Tests must exist and pass for CI to be meaningful
- Task 1: `pyproject.toml` must exist for uv/tool configuration

## Output Artifacts
- `.github/workflows/ci.yml`
- `.github/workflows/conventional-commits.yml`
- `.github/workflows/release.yml`

## Implementation Notes

<details>
<summary>Detailed implementation guidance</summary>

1. **CI workflow** (`.github/workflows/ci.yml`):
   ```yaml
   name: CI
   on:
     push:
       branches: [main]
     pull_request:

   jobs:
     lint-and-test:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - uses: astral-sh/setup-uv@v3
         - uses: actions/setup-python@v5
           with:
             python-version: "3.13"
         - run: uv sync --all-extras --dev
         - name: Lint
           run: uv run ruff check .
         - name: Format check
           run: uv run ruff format --check .
         - name: Type check
           run: uv run mypy src/
         - name: Test
           run: uv run pytest --tb=short
         - name: Mutation test
           run: uv run mutmut run --paths-to-mutate=src/flameconnect/protocol.py --no-progress
   ```

2. **Conventional commits workflow** (`.github/workflows/conventional-commits.yml`):
   ```yaml
   name: Conventional Commits
   on:
     pull_request:
       types: [opened, edited, synchronize]

   jobs:
     validate:
       runs-on: ubuntu-latest
       steps:
         - uses: amannn/action-semantic-pull-request@v5
           env:
             GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
   ```

3. **Release workflow** (`.github/workflows/release.yml`):
   ```yaml
   name: Release
   on:
     push:
       branches: [main]

   permissions:
     contents: write
     pull-requests: write
     id-token: write  # For PyPI trusted publishing

   jobs:
     release-please:
       runs-on: ubuntu-latest
       outputs:
         release_created: ${{ steps.release.outputs.release_created }}
       steps:
         - uses: googleapis/release-please-action@v4
           id: release
           with:
             release-type: python

     publish:
       needs: release-please
       if: ${{ needs.release-please.outputs.release_created }}
       runs-on: ubuntu-latest
       environment: pypi
       permissions:
         id-token: write
       steps:
         - uses: actions/checkout@v4
         - uses: astral-sh/setup-uv@v3
         - uses: actions/setup-python@v5
           with:
             python-version: "3.13"
         - run: uv build
         - uses: pypa/gh-action-pypi-publish@release/v1
   ```

4. **Note**: The PyPI trusted publishing requires configuring the GitHub environment "pypi" in repository settings and setting up the trusted publisher on PyPI. This is a manual step documented but not automated.

5. **mutmut in CI**: Start with only `protocol.py` to keep mutation testing fast. The `--no-progress` flag suppresses interactive output. If mutmut finds surviving mutants, the step will fail with a non-zero exit code.
</details>
