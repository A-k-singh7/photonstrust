# CI Baseline Rules - Week 1 (2026-02-12)

This document defines the Week 1 minimum CI and repository quality controls for
PhotonTrust M1 (`W1-W4`).

## Current baseline pipeline
Workflow file:
- `.github/workflows/ci.yml`

Current required job:
- `test` job on `push` and `pull_request`

Current required commands:
```bash
python -m pip install --upgrade pip
pip install -e .[dev]
pytest -q
```

## Required quality gates for M1
1. `pytest -q` must pass on every PR.
2. Schema validation tests must pass:
   - `tests/test_schema_validation.py`
3. Regression/golden checks must pass when outputs change:
   - `tests/test_regression_baselines.py`
   - `tests/test_golden_report.py`
4. Any failing test is merge-blocking.

## Test naming conventions (enforced by review + CI)
- test files: `tests/test_*.py`
- test functions: `test_*`
- deterministic tests must set or rely on deterministic seed paths
- fixture updates for baseline changes must be explicit in PR description

## Branch protection baseline (GitHub settings to apply)
1. Require pull request before merge.
2. Require status checks to pass before merge.
3. Mark CI check `ci / test` (or equivalent `test` job) as required.
4. Require conversation resolution before merge.
5. Disallow force pushes to protected branch.

## PR checklist baseline for M1
Each PR touching runtime behavior must include:
- impacted contracts from
  `docs/operations/week1/api_contract_table_2026-02-12.md`
- tests added/updated
- schema impact statement (`none` or specific file changes)
- docs impact statement (`none` or exact file list)

Repository automation:
- `.github/pull_request_template.md` provides the default checklist.

## Local pre-push check
```bash
pip install -e .[dev]
pytest -q
```

## Ownership and escalation
- CI policy owner: `QA`
- Architecture policy owner: `TL`
- Documentation policy owner: `DOC`
- Escalation: if CI is red for >24h on main branch, QA escalates to TL.
