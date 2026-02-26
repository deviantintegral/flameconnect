---
id: 2
group: "philosophy-alignment-fixes"
dependencies: []
status: "completed"
created: 2026-02-26
skills:
  - "documentation"
---
# Fix documentation and brand name inconsistencies

## Objective
Align brand names, remove stale references, and fix inaccurate parameter docs.

## Acceptance Criteria
- [x] Brand names say "Dimplex, Faber, and Real Flame" in __init__.py, pyproject.toml, cli.py
- [x] README heat-mode example does not mention fan-only
- [x] README brightness shows low/high instead of 0-255
- [x] argparse help text does not mention light-status
- [x] All CI checks pass

## Output Artifacts
- Updated `src/flameconnect/__init__.py`, `pyproject.toml`, `src/flameconnect/cli.py`, `README.md`
