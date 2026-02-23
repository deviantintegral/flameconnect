---
id: 1
group: "packaging"
dependencies: []
status: "completed"
created: "2026-02-23"
skills:
  - python
  - packaging
status: "completed"
status: "completed"
---
# Initialize project scaffolding with uv and configure tooling

## Objective
Create the Python package skeleton with `src/` layout, configure `pyproject.toml` with all dependencies and tool settings (ruff, mypy, pytest, mutmut), and initialize the uv project. This is the foundation all other tasks build on.

## Skills Required
- Python packaging (pyproject.toml, src layout, PEP 621)
- uv dependency manager

## Acceptance Criteria
- [ ] `pyproject.toml` exists with project metadata (name=flameconnect, version=0.1.0, python>=3.13)
- [ ] `src/flameconnect/__init__.py` exists with package version
- [ ] `src/flameconnect/__main__.py` exists (delegates to CLI)
- [ ] `src/flameconnect/py.typed` marker file exists (empty file)
- [ ] Dependencies declared: aiohttp, msal (runtime); ruff, mypy, pytest, pytest-aiohttp, mutmut (dev)
- [ ] Optional dependency group `tui` with textual
- [ ] `[project.scripts]` entry: `flameconnect = "flameconnect.cli:main"`
- [ ] ruff config in pyproject.toml (line-length=88, target-version="py313")
- [ ] mypy config in pyproject.toml (strict=true)
- [ ] pytest config in pyproject.toml
- [ ] `uv sync` succeeds and installs all dependencies
- [ ] `tests/` directory with empty `conftest.py` and `__init__.py`
- [ ] `.gitignore` updated for uv (.venv, dist, *.egg-info, .mypy_cache, .ruff_cache, .pytest_cache, .mutmut-cache)

Use your internal Todo tool to track these and keep on track.

## Technical Requirements
- Use PEP 621 `[project]` table in pyproject.toml (not legacy setup.py/setup.cfg)
- Use `[build-system]` with hatchling as build backend (standard for uv)
- `src/` layout: `[tool.hatch.build.targets.wheel] packages = ["src/flameconnect"]`
- Python requires-python = ">=3.13"
- Initial version: "0.1.0"

## Input Dependencies
None — this is the first task.

## Output Artifacts
- `pyproject.toml` — complete project configuration
- `src/flameconnect/__init__.py`, `__main__.py`, `py.typed`
- `tests/conftest.py`, `tests/__init__.py`
- `.venv/` created by uv
- Updated `.gitignore`

## Implementation Notes

<details>
<summary>Detailed implementation guidance</summary>

1. **Initialize the project**: Run `uv init` if not already initialized, or manually create `pyproject.toml`. The project is already a git repo.

2. **pyproject.toml structure**:
   ```toml
   [build-system]
   requires = ["hatchling"]
   build-backend = "hatchling.build"

   [project]
   name = "flameconnect"
   version = "0.1.0"
   description = "Async Python library for controlling Dimplex/Faber fireplaces via the Flame Connect cloud API"
   readme = "README.md"
   license = "MIT"
   requires-python = ">=3.13"
   dependencies = [
       "aiohttp>=3.9",
       "msal>=1.28",
   ]

   [project.optional-dependencies]
   tui = ["textual>=0.50"]
   dev = [
       "ruff>=0.4",
       "mypy>=1.10",
       "pytest>=8.0",
       "pytest-aiohttp>=1.0",
       "pytest-asyncio>=0.23",
       "mutmut>=2.4",
       "aioresponses>=0.7",
   ]

   [project.scripts]
   flameconnect = "flameconnect.cli:main"

   [tool.hatch.build.targets.wheel]
   packages = ["src/flameconnect"]

   [tool.ruff]
   line-length = 88
   target-version = "py313"

   [tool.ruff.lint]
   select = ["E", "F", "W", "I", "UP", "B", "SIM", "TCH"]

   [tool.mypy]
   strict = true

   [tool.pytest.ini_options]
   asyncio_mode = "auto"
   testpaths = ["tests"]
   ```

3. **Create directory structure**:
   - `src/flameconnect/__init__.py` — export `__version__ = "0.1.0"`
   - `src/flameconnect/__main__.py` — `from flameconnect.cli import main; main()`
   - `src/flameconnect/py.typed` — empty file
   - `tests/__init__.py` — empty
   - `tests/conftest.py` — empty (will be populated by test tasks)

4. **Update .gitignore**: Add uv/Python packaging entries (`.venv/`, `dist/`, `*.egg-info/`, `.mypy_cache/`, `.ruff_cache/`, `.pytest_cache/`, `.mutmut-cache/`)

5. **Run `uv sync`** to create the virtual environment and install all dependencies.

6. **Important**: `src/flameconnect/cli.py` does not need to exist yet — just ensure the entry point in pyproject.toml points to the correct location for when it's created in task 7.
</details>
