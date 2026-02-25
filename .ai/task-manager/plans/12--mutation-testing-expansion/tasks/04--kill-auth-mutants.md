---
id: 4
group: "mutation-testing-expansion"
dependencies: [1]
status: "pending"
created: 2026-02-25
skills:
  - "python-testing"
  - "mutation-testing"
---
# Kill surviving mutants in auth.py

## Objective
Establish mutation testing on auth.py with ≥90% kill rate.

## Acceptance Criteria
- [ ] New tests added to `tests/test_auth.py`
- [ ] Mutation score ≥90% verified by mutmut
- [ ] All tests pass
- [ ] No files in `src/` modified

## Technical Requirements
- Run mutmut on auth.py to identify all surviving mutants
- Write targeted tests for authentication logic: token acquisition, cache handling, error paths

## Output Artifacts
- Updated `tests/test_auth.py` with additional test assertions
