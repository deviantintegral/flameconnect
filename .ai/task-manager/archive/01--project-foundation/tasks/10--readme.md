---
id: 10
group: "documentation"
dependencies: [7, 8]
created: "2026-02-23"
skills:
  - documentation
status: "completed"
---
# Write human-oriented README

## Objective
Create a README.md written for humans (not AIs) that covers installation, usage examples (library, CLI, TUI), API coverage documentation (what's implemented vs. what's available for future contribution), and contributing guidelines.

## Skills Required
- Technical documentation writing

## Acceptance Criteria
- [ ] `README.md` exists at project root
- [ ] Includes project description and purpose
- [ ] Installation instructions (pip, uv, with and without TUI extra)
- [ ] Library usage examples (async context manager, get_fires, turn_on/off)
- [ ] CLI usage examples (all commands)
- [ ] TUI section with screenshot description or usage
- [ ] API coverage table: lists all known endpoints, marks which are implemented vs. planned
- [ ] Authentication section explaining token injection vs. built-in credentials
- [ ] Contributing section (mentions conventional commits, ruff, mypy, pytest)
- [ ] License section
- [ ] Written for humans — clear, concise, not auto-generated boilerplate

Use your internal Todo tool to track these and keep on track.

## Technical Requirements
- Use GitHub-flavored Markdown
- Code examples must be accurate and runnable
- API coverage table should reference the endpoints from `FLAMECONNECT_API_REPORT.md`
- Include badges for CI status, PyPI version, Python version

## Input Dependencies
- Task 7: CLI commands must be finalized (for usage examples)
- Task 8: TUI must be implemented (for TUI section)
- All core library modules for accurate library usage examples

## Output Artifacts
- `README.md` (replaces or supplements existing `FLAMECONNECT_API_REPORT.md`)

## Implementation Notes

<details>
<summary>Detailed implementation guidance</summary>

1. **Structure**:
   ```markdown
   # FlameConnect

   [badges: CI, PyPI, Python version]

   Async Python library for controlling Dimplex, Faber, and Real Flame fireplaces via the Flame Connect cloud API.

   ## Installation
   ## Quick Start (Library)
   ## CLI Usage
   ## TUI
   ## Authentication
   ## API Coverage
   ## Contributing
   ## License
   ```

2. **Installation section**:
   ```markdown
   ## Installation

   pip install flameconnect

   # With TUI support:
   pip install flameconnect[tui]

   # Or with uv:
   uv add flameconnect
   uv add flameconnect[tui]
   ```

3. **Quick Start**:
   ```python
   import asyncio
   from flameconnect import FlameConnectClient, MsalAuth

   async def main():
       auth = MsalAuth()
       async with FlameConnectClient(auth=auth) as client:
           fires = await client.get_fires()
           for fire in fires:
               print(f"{fire.friendly_name} ({fire.fire_id})")
           await client.turn_on(fires[0].fire_id)

   asyncio.run(main())
   ```

4. **API Coverage table**:
   | Endpoint | Status | Description |
   |----------|--------|-------------|
   | GetFires | Implemented | List registered fireplaces |
   | GetFireOverview | Implemented | Read fireplace state |
   | WriteWifiParameters | Implemented | Send control commands |
   | AddFire | Planned | Register a new fireplace |
   | ... | ... | ... |

5. **Authentication section**: Explain the two modes:
   - **Standalone** (CLI/TUI): Uses built-in MSAL browser login. First run opens browser, subsequent runs use cached tokens.
   - **Integration** (Home Assistant): Pass your own token or async token provider.

6. **Keep `FLAMECONNECT_API_REPORT.md`**: It remains as the detailed technical reference. The README links to it for developers who want deep API details.

7. **Contributing section**: Mention conventional commits, `uv sync --dev`, `ruff check`, `mypy src/`, `pytest`.
</details>
