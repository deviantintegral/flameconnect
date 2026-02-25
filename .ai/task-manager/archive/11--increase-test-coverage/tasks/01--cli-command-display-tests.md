---
id: 1
group: "increase-test-coverage"
dependencies: []
status: "completed"
created: 2026-02-25
skills:
  - "python-testing"
  - "mocking"
---
# Add CLI command and display function tests

## Objective
Create `tests/test_cli_commands.py` to cover the ~296 missed statements in `src/flameconnect/cli.py`. Focus on display functions, the `_display_parameter` dispatcher, CLI command entry points (`cmd_set`, `cmd_turn_on`, `cmd_turn_off`), and helper functions.

## Skills Required
- python-testing: pytest, pytest-asyncio
- mocking: unittest.mock for FlameConnectClient and terminal I/O

## Acceptance Criteria
- [ ] New file `tests/test_cli_commands.py` created
- [ ] Tests cover display functions: `_display_mode`, `_display_flame_effect`, `_display_heat`, `_display_heat_mode`, `_display_timer`, `_display_software_version`, `_display_error`, `_display_temp_unit`, `_display_flame_effect_param`, `_display_light_param`
- [ ] Tests cover the `_display_parameter` dispatch function
- [ ] Tests cover helper functions: `_enum_name`, `_format_rgbw`, `_find_temp_unit`, `_convert_temp`
- [ ] Tests cover CLI commands: `cmd_set`, `cmd_turn_on`, `cmd_turn_off`
- [ ] Tests cover `async_main` and `main` entry points where possible via mocking
- [ ] All tests pass
- [ ] No files in `src/` are modified

## Technical Requirements
- Follow patterns from existing `tests/test_cli_set.py` — mock `FlameConnectClient`, construct model objects, call functions directly
- Use `unittest.mock.patch` and `AsyncMock` for async client methods
- For `_masked_input` and `_cli_auth_prompt`, mock `asyncio.to_thread` and stdin — skip if not feasible without src/ changes
- Import display functions and helpers directly from `flameconnect.cli`

## Input Dependencies
None — independent task.

## Output Artifacts
- `tests/test_cli_commands.py`

## Implementation Notes
- Read `src/flameconnect/cli.py` to understand each uncovered function's signature and behavior
- The display functions typically take model parameter objects and print formatted output — test by capturing stdout or using mock print
- CLI commands use `argparse.Namespace` as input — construct test namespaces with required attributes
- `async_main` requires mocking auth flow and client construction — test the happy path
- Skip any function that cannot be tested without modifying src/ files
