---
id: 2
group: "tui-refinements"
dependencies: []
status: "completed"
created: 2026-02-25
skills:
  - "python"
---
# Git Hash in Header and Label Renames

## Objective
Show a meaningful build identifier in the TUI header (git short hash with dirty flag, falling back to version string) and rename remaining "Fuel Bed" labels to "Media" across the codebase.

## Skills Required
- Python subprocess for git commands
- String replacement across multiple files

## Acceptance Criteria
- [ ] Header shows git short hash (e.g., `FlameConnect abc1234`) when no release tag matches the current commit
- [ ] Header shows `FlameConnect v0.1.0` when the current commit has a matching release tag
- [ ] `-dirty` suffix appended when working tree has uncommitted changes OR untracked files
- [ ] Falls back to `v{__version__}` when git is unavailable (not a git repo, git not installed)
- [ ] `app.py`: `ColorScreen` title changed from `"Fuel Bed Color"` to `"Media Color"`
- [ ] `app.py`: Command palette description changed from `"Set fuel bed color"` to `"Set media color"`
- [ ] `cli.py`: `"Fuel Bed Light:"` changed to `"Media Light:"`
- [ ] All existing tests pass
- [ ] No lint errors

## Technical Requirements

### Git Hash Resolution
Create a `_resolve_version()` function in `app.py`:
1. Run `git describe --tags --exact-match HEAD` to check for release tag. If it matches `__version__`, return `f"v{__version__}"`.
2. Otherwise: run `git rev-parse --short HEAD` for the short hash. Check dirty state via `git status --porcelain` (non-empty output = dirty, catches both uncommitted changes and untracked files). Return hash with optional `-dirty` suffix.
3. If git unavailable: fall back to `f"v{__version__}"`.

Use `subprocess.run()` with `capture_output=True` and `timeout=2`. Cache result in a module-level variable (compute once at import time).

Set `TITLE = f"FlameConnect {_resolve_version()}"`.

### Label Renames
Three locations:
1. `app.py` line ~691: `ColorScreen(current.media_color, "Fuel Bed Color")` -> `"Media Color"`
2. `app.py` line ~46: `("Media Color", "Set fuel bed color", ...)` -> `"Set media color"`
3. `cli.py` line ~211: `"Fuel Bed Light:"` -> `"Media Light:"`

### Files
- `src/flameconnect/tui/app.py`
- `src/flameconnect/cli.py`

## Input Dependencies
None

## Output Artifacts
- `_resolve_version()` function in `app.py`
- Updated TITLE with dynamic version
- Renamed labels in app.py and cli.py

## Implementation Notes
- `__version__` is imported from `flameconnect.__init__` (currently `"0.1.0"`).
- Standard `git describe --dirty` only checks tracked files. The explicit `git status --porcelain` check is needed for untracked files.
- Internal identifiers (`media_color`, `set_media_color`) remain unchanged — only user-facing labels are updated.
