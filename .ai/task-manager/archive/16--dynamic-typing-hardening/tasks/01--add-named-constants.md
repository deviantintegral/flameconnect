---
id: 1
group: "dynamic-typing-hardening"
dependencies: []
status: "completed"
created: 2026-03-01
skills:
  - "python-typing"
  - "refactoring"
---
# Add Named Constants for Magic Literals

## Objective
Eliminate magic numbers scattered across the codebase by adding named constants to `const.py` and replacing all occurrences.

## Skills Required
Python typing, refactoring across multiple modules.

## Acceptance Criteria
- [ ] All constants added to `const.py` with correct types and values
- [ ] All magic number occurrences replaced in `client.py`, `cli.py`, and TUI modules
- [ ] New constants added to `__all__` in `__init__.py`
- [ ] `uv run ruff check .` passes
- [ ] `uv run mypy src/` passes
- [ ] `uv run pytest` passes

## Technical Requirements

Add these constants to `src/flameconnect/const.py`:
- `DEFAULT_TARGET_TEMPERATURE: float = 22.0`
- `MAX_FLAME_SPEED: int = 5`
- `MIN_FLAME_SPEED: int = 1`
- `MAX_TIMER_DURATION: int = 480`
- `MAX_BOOST_DURATION: int = 20`
- `MIN_BOOST_DURATION: int = 1`
- `MIN_TEMP_CELSIUS: float = 5.0`
- `MAX_TEMP_CELSIUS: float = 35.0`
- `MIN_TEMP_FAHRENHEIT: float = 40.0`
- `MAX_TEMP_FAHRENHEIT: float = 95.0`
- `DEFAULT_TIMER_DURATION: int = 60`

Replace occurrences at these locations:
- `22.0` in `client.py:296`, `client.py:325`, `cli.py:480`
- `5`/`1` (flame speed) in `cli.py:492`, `tui/widgets.py:169`, `tui/flame_speed_screen.py:73`
- `480` in `tui/timer_screen.py:85,100`
- `20`/`1` (boost) in `cli.py:543`, `tui/heat_mode_screen.py:101,138`
- `5.0/35.0` in `tui/temperature_screen.py:89,119`
- `40.0/95.0` in `tui/temperature_screen.py:89,121`
- `60` in `tui/app.py:851`

Add each new constant to `__all__` in `__init__.py`.

## Input Dependencies
None — this is a standalone task.

## Output Artifacts
Named constants in `const.py` that other tasks can import.

## Implementation Notes
- Be careful with `5` — only replace where it refers to max flame speed, not other uses of the number 5.
- The `60` in `tui/app.py:851` is `current.duration or 60` — replace `60` with `DEFAULT_TIMER_DURATION`.
- Line numbers are approximate; search for the patterns rather than relying on exact lines.
