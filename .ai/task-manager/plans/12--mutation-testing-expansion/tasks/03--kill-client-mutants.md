---
id: 3
group: "mutation-testing-expansion"
dependencies: [1]
status: "pending"
created: 2026-02-25
skills:
  - "python-testing"
  - "mutation-testing"
---
# Kill surviving mutants in client.py

## Objective
Write targeted tests to raise client.py mutation score from 64% to ≥90% by killing the 116 surviving mutants.

## Acceptance Criteria
- [ ] New tests added to `tests/test_client.py`
- [ ] Mutation score ≥90% verified by mutmut
- [ ] All tests pass
- [ ] No files in `src/` modified

## Technical Requirements
- Run mutmut to identify surviving mutants
- Write tests asserting on specific URL paths, request payloads, HTTP methods, headers, and parsed response fields

## Output Artifacts
- Updated `tests/test_client.py` with additional test assertions
