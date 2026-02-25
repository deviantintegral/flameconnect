---
id: 1
group: "mutation-testing-expansion"
dependencies: []
status: "completed"
created: 2026-02-25
skills:
  - "ci-config"
---
# Setup mutmut configuration, .gitignore, and CI update

## Objective
Create `setup.cfg` with mutmut configuration, update `.gitignore` with `mutants/`, and expand CI mutation testing to all 4 core modules.

## Acceptance Criteria
- [ ] `setup.cfg` exists with `[mutmut]` section containing `paths_to_mutate` and `also_copy`
- [ ] `.gitignore` includes `mutants/` and replaces stale `.mutmut-cache/` entry
- [ ] CI workflow runs mutmut on protocol.py, client.py, auth.py, and b2c_login.py
- [ ] `uv run mutmut run --paths-to-mutate=src/flameconnect/auth.py --no-progress` works locally

## Technical Requirements
- Create `setup.cfg` with `[mutmut]` section
- Update `.gitignore`: add `mutants/`, remove `.mutmut-cache/`
- Update `.github/workflows/ci.yml` mutation test step to run on all 4 modules

## Output Artifacts
- `setup.cfg` (new), `.gitignore` (updated), `.github/workflows/ci.yml` (updated)
