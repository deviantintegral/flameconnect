---
id: 5
group: "mutation-testing-expansion"
dependencies: [1]
status: "pending"
created: 2026-02-25
skills:
  - "python-testing"
  - "mutation-testing"
---
# Kill surviving mutants in b2c_login.py

## Objective
Establish mutation testing on b2c_login.py with ≥90% kill rate.

## Acceptance Criteria
- [ ] New tests added to `tests/test_b2c_login.py`
- [ ] Mutation score ≥90% verified by mutmut
- [ ] All tests pass
- [ ] No files in `src/` modified

## Technical Requirements
- Run mutmut on b2c_login.py to identify all surviving mutants
- Write targeted tests for B2C login flow: HTTP redirect handling, HTML parsing, token exchange, error paths

## Output Artifacts
- Updated `tests/test_b2c_login.py` with additional test assertions
