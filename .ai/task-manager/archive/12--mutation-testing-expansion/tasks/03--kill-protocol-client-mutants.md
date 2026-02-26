---
id: 3
group: "mutation-testing-expansion"
dependencies: [1]
status: "completed"
created: 2026-02-25
skills:
  - "python-testing"
  - "mutation-testing"
---
# Kill surviving mutants in protocol.py and client.py

## Objective
Kill the remaining 3 protocol.py survivors and 7 client.py survivors, or document them as equivalent mutants.

## Acceptance Criteria
- [ ] Protocol.py survivors addressed (killed or documented as equivalent)
- [ ] Client.py survivors addressed (killed or documented as equivalent)
- [ ] Mutation scores verified by mutmut
- [ ] All tests pass
- [ ] No files in `src/` modified

## Technical Requirements
- **protocol.py** (3 survivors): `encode_temperature` (1), `_make_header` (1), `encode_parameter` (1). Add targeted assertions to `tests/test_protocol.py`.
- **client.py** (7 survivors): `_request` (3), `get_fire_overview` (2), `turn_on` (1), `turn_off` (1). Add assertions to `tests/test_client.py`.
- Run mutmut per-module to verify: `uv run mutmut run --paths-to-mutate=src/flameconnect/protocol.py --max-children 2` and same for client.py

## Output Artifacts
- Updated `tests/test_protocol.py` and `tests/test_client.py`
