---
id: 2
group: "mutation-testing-expansion"
dependencies: [1]
status: "completed"
created: 2026-02-25
skills:
  - "python-testing"
  - "mutation-testing"
---
# Kill surviving mutants in b2c_login.py

## Objective
Raise b2c_login.py mutation score from 73% to ≥90% by writing targeted tests for the 125 surviving mutants.

## Acceptance Criteria
- [ ] New tests added to `tests/test_b2c_login.py`
- [ ] Mutation score ≥90% verified by `uv run mutmut run --paths-to-mutate=src/flameconnect/b2c_login.py --max-children 2`
- [ ] All tests pass
- [ ] No files in `src/` modified

## Technical Requirements
- Run mutmut on b2c_login.py to identify surviving mutants
- Focus on `b2c_login_with_credentials` function (~111 survivors): HTTP request URLs, form field names/values, redirect handling, error extraction
- `log_response` (9 survivors) and `log_request` (5 survivors) may contain equivalent mutants — document any that are truly unkillable
- The ≥90% target means killing at least ~88 of the 125 survivors

## Output Artifacts
- Updated `tests/test_b2c_login.py` with additional test assertions
