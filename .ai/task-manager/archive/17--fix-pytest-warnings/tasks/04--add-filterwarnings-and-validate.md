---
id: 4
group: "fix-pytest-warnings"
dependencies: [1, 2, 3]
status: "completed"
created: 2026-03-02
skills:
  - pytest-configuration
  - python-testing
---
# Add filterwarnings to pyproject.toml and run full validation

## Objective
Add a `filterwarnings` entry to `pyproject.toml` that promotes unawaited coroutine RuntimeWarnings to test errors, then run the full test suite and linters to validate all fixes.

## Skills Required
- pytest configuration (filterwarnings)
- Python testing

## Acceptance Criteria
- [ ] `pyproject.toml` contains a `filterwarnings` entry under `[tool.pytest.ini_options]` that turns RuntimeWarning about unawaited coroutines into errors
- [ ] `uv run pytest --cov=flameconnect --cov-report=term-missing --tb=short --cov-fail-under=95` passes with 0 warnings and all tests passing
- [ ] Coverage remains at or above 95%
- [ ] `uv run ruff check .` passes
- [ ] `uv run mypy src/` passes

## Technical Requirements

Add to `[tool.pytest.ini_options]` in `pyproject.toml`:
```toml
filterwarnings = ["error::RuntimeWarning"]
```

This promotes all RuntimeWarnings (including unawaited coroutine warnings) to hard test failures. This is the safety net that ensures no new unawaited coroutines are introduced.

Then run the full validation suite to confirm all fixes from Tasks 1-3 are working correctly together.

**File to modify**: `pyproject.toml`

## Input Dependencies
Requires completion of Tasks 1, 2, and 3 (all test fixes must be in place before promoting warnings to errors).

## Output Artifacts
- Modified `pyproject.toml` with filterwarnings configuration
- Validated clean test run with 0 warnings
