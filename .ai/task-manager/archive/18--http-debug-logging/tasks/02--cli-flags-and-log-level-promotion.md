---
id: 2
group: "http-debug-logging"
dependencies: []
status: "completed"
created: 2026-03-11
skills:
  - python
  - argparse
---
# CLI flag restructuring and log level promotion

## Objective
Add `--debug` flag, adjust `--verbose` semantics, promote key DEBUG messages to INFO, and update TUI `run_tui` signature.

## Skills Required
- Python `argparse` (mutually exclusive groups)
- Python `logging` module

## Acceptance Criteria
- [ ] `--verbose` and `--debug` are mutually exclusive flags in `build_parser()`
- [ ] `--verbose` help text is `"Enable verbose logging"`
- [ ] `--debug` help text is `"Enable verbose logging including HTTP requests and responses"`
- [ ] `main()` maps: `--debug` → `logging.DEBUG`, `--verbose` → `logging.INFO`, default → `logging.WARNING`
- [ ] `run_tui` signature changes from `verbose: bool` to `log_level: int` (default `logging.WARNING`)
- [ ] `cmd_tui` and `async_main` pass computed `log_level` to `run_tui`
- [ ] `client.py:174` request summary promoted from `_LOGGER.debug` to `_LOGGER.info`
- [ ] `auth.py` lines 126, 134, 138, 189 promoted from `_LOGGER.debug` to `_LOGGER.info`
- [ ] All existing tests updated to pass with new flag structure and `log_level` parameter
- [ ] mypy strict passes, ruff passes

## Technical Requirements
- Use `parser.add_mutually_exclusive_group()` for `--verbose`/`--debug`
- In `main()`: `logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO if args.verbose else logging.WARNING)`
- In `run_tui`: replace `if verbose: fc_logger.setLevel(logging.DEBUG)` with `fc_logger.setLevel(log_level)`
- Update `cmd_tui` signature from `verbose: bool` to `log_level: int`
- In `async_main`: compute `log_level` from `args.verbose`/`args.debug` and pass to `run_tui`/`cmd_tui`
- Update all test assertions that reference `verbose=True/False` to use `log_level=...`

## Input Dependencies
None — flag restructuring and log level changes are independent of the new `_http_logging` module.

## Output Artifacts
- Modified `src/flameconnect/cli.py` — new flags, updated `main()`, `cmd_tui`, `async_main`
- Modified `src/flameconnect/tui/app.py` — updated `run_tui` signature
- Modified `src/flameconnect/client.py` — one line promoted to INFO
- Modified `src/flameconnect/auth.py` — four lines promoted to INFO
- Updated tests in `tests/test_cli_commands.py`

## Implementation Notes
- The `-v` short flag should remain on `--verbose`.
- `--debug` does not need a short flag.
- When neither flag is given, `args.verbose` and `args.debug` are both `False`.
- The TUI's `DashboardScreen._log_handler` attaches at whatever level the logger is set to — no changes needed there.
