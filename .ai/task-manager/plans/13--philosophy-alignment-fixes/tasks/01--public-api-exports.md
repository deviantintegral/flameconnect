---
id: 1
group: "philosophy-alignment-fixes"
dependencies: []
status: "completed"
created: 2026-02-26
skills:
  - "python-packaging"
---
# Export missing model types from __init__.py

## Objective
Add Brightness, PulsatingEffect, and NAMED_COLORS to the public API.

## Acceptance Criteria
- [x] `from flameconnect import Brightness, PulsatingEffect, NAMED_COLORS` works
- [x] All three are listed in `__all__`
- [x] mypy passes

## Output Artifacts
- Updated `src/flameconnect/__init__.py`
