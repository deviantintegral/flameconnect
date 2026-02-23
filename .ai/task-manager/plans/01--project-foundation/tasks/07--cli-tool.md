---
id: 7
group: "interfaces"
dependencies: [5]
status: "pending"
created: "2026-02-23"
skills:
  - python
---
# Implement CLI tool with argparse

## Objective
Create `cli.py` with an argparse-based command-line interface that exposes all fireplace operations. The CLI bridges synchronous entry points to the async library using `asyncio.run()` and uses the built-in MSAL credential flow for authentication.

## Skills Required
- Python CLI development (argparse)

## Acceptance Criteria
- [ ] `src/flameconnect/cli.py` exists with `main()` function
- [ ] `flameconnect list` — lists registered fireplaces (name, ID, connection state)
- [ ] `flameconnect status <fire_id>` — shows current fireplace state with decoded parameters
- [ ] `flameconnect on <fire_id>` — turns on fireplace
- [ ] `flameconnect off <fire_id>` — turns off fireplace
- [ ] `flameconnect set <fire_id> <param> <value>` — sets a parameter (at minimum: mode, flame-speed, brightness, heat-mode, heat-temp, timer)
- [ ] `flameconnect tui` — launches TUI with lazy textual import; shows clear error if textual not installed
- [ ] `python -m flameconnect` works via `__main__.py`
- [ ] Logging configured: `-v` for DEBUG, default is WARNING
- [ ] Passes `mypy --strict` and `ruff check`
- [ ] No `print()` in library code; CLI output uses `print()` only for user-facing output (this is acceptable in CLI entry point)
- [ ] Validated against live API (see Live API Validation Protocol below)

Use your internal Todo tool to track these and keep on track.

## Technical Requirements
- Use `argparse` with subparsers for each command
- `main()` function: parse args, configure logging level, call `asyncio.run(async_main(args))`
- `async_main()`: create `MsalAuth`, create `FlameConnectClient`, dispatch to command handler
- Status command: format decoded parameters for terminal display (similar to existing `display_parameter` functions)
- Set command: parse param name to ParameterId, parse value to appropriate type, encode and send
- TUI command: try `from flameconnect.tui import run_tui`, catch `ImportError`, show install instructions

## Input Dependencies
- Task 5: `client.py` (FlameConnectClient)
- Task 4: `auth.py` (MsalAuth)
- Task 2: `models.py` (all types for display formatting), `const.py`

## Output Artifacts
- `src/flameconnect/cli.py`
- Updated `src/flameconnect/__main__.py` (if needed)

## Implementation Notes

<details>
<summary>Detailed implementation guidance</summary>

1. **argparse structure**:
   ```python
   def build_parser() -> argparse.ArgumentParser:
       parser = argparse.ArgumentParser(prog="flameconnect", description="Control Dimplex fireplaces")
       parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
       subparsers = parser.add_subparsers(dest="command", required=True)

       subparsers.add_parser("list", help="List registered fireplaces")

       status_parser = subparsers.add_parser("status", help="Show fireplace state")
       status_parser.add_argument("fire_id", help="Fireplace ID")

       on_parser = subparsers.add_parser("on", help="Turn on fireplace")
       on_parser.add_argument("fire_id", help="Fireplace ID")

       off_parser = subparsers.add_parser("off", help="Turn off fireplace")
       off_parser.add_argument("fire_id", help="Fireplace ID")

       set_parser = subparsers.add_parser("set", help="Set a parameter")
       set_parser.add_argument("fire_id", help="Fireplace ID")
       set_parser.add_argument("param", help="Parameter name (mode, flame-speed, brightness, heat-mode, heat-temp, timer)")
       set_parser.add_argument("value", help="Parameter value")

       subparsers.add_parser("tui", help="Launch interactive TUI")
       return parser
   ```

2. **main() entry point**:
   ```python
   def main() -> None:
       parser = build_parser()
       args = parser.parse_args()
       logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING)
       asyncio.run(async_main(args))
   ```

3. **TUI lazy import**:
   ```python
   async def cmd_tui(args: argparse.Namespace) -> None:
       try:
           from flameconnect.tui import run_tui
       except ImportError:
           print("The TUI requires the 'tui' extra. Install with:")
           print("  pip install flameconnect[tui]")
           print("  # or: uv add flameconnect[tui]")
           sys.exit(1)
       await run_tui()
   ```

4. **Status display**: Port the formatting from `display_fire_info` (lines 380-392) and `display_parameter` (lines 394-475) of `flameconnect_reader.py`. Adapt to use the typed dataclass fields instead of dict access.

5. **Set command mapping**: Map param name strings to parameter construction:
   - `mode` → ModeParam (value: "standby" or "manual")
   - `flame-speed` → FlameEffectParam modification (value: 1-5)
   - `brightness` → FlameEffectParam modification (value: 0-255)
   - `heat-mode` → HeatParam modification (value: "normal", "boost", "eco", "fan-only")
   - `heat-temp` → HeatParam modification (value: float temperature)
   - `timer` → TimerParam (value: minutes as int, 0 to disable)

6. **__main__.py** should simply be:
   ```python
   from flameconnect.cli import main
   main()
   ```

7. **Live API Validation Protocol**: After implementing the CLI, validate each command against the real API. For every live API call, follow this mandatory three-step process:
   - **Explain**: Tell the user exactly which CLI command you will run, what API call it triggers, and what effect it will have.
   - **Confirm**: Wait for the user to explicitly approve before executing.
   - **Verify**: Show the user the output and ask if it matched their expectations.

   Recommended validation sequence:
   1. `flameconnect list` — read-only, lists fireplaces. Confirm output matches user's registered fireplaces.
   2. `flameconnect status <fire_id>` — read-only, shows current state. Confirm parameters look correct.
   3. `flameconnect on <fire_id>` — **write operation**. User must confirm fireplace is safe to turn on.
   4. `flameconnect status <fire_id>` — read-only, confirm state changed.
   5. `flameconnect off <fire_id>` — **write operation**. User must confirm.
   6. `flameconnect set <fire_id> flame-speed 3` — **write operation**. User must confirm.
</details>
