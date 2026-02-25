---
id: 2
group: "mutation-testing-expansion"
dependencies: [1]
status: "pending"
created: 2026-02-25
skills:
  - "python-testing"
  - "mutation-testing"
---
# Kill surviving mutants in protocol.py

## Objective
Write targeted tests to raise protocol.py mutation score from 62% to ≥90% by killing the 266 surviving mutants.

## Acceptance Criteria
- [ ] New tests added to `tests/test_protocol.py`
- [ ] Mutation score ≥90% verified by `uv run mutmut run --paths-to-mutate=src/flameconnect/protocol.py --no-progress`
- [ ] All tests pass
- [ ] No files in `src/` modified

## Technical Requirements
- Run mutmut to identify surviving mutants
- Analyze each surviving mutant to understand what assertion is missing
- Write targeted test assertions for: individual decoded field values, byte-level encoding correctness, constant values, boundary conditions

## Output Artifacts
- Updated `tests/test_protocol.py` with additional test assertions
