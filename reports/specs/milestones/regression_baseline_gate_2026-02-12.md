# Regression and Baseline Gate

## Gate context
- Scenario set: core QKD baseline (`configs/quickstart/qkd_default.yml`) + smoke scenario suite under `results/smoke/`
- Baseline file version: `tests/fixtures/baselines.json` (current repository fixture)
- Test run ID: `release_gate_report.json @ 2026-02-12T22:12:32.468321+00:00`

## Checks
- [x] Unit tests passed
- [x] Integration tests passed
- [x] Baseline regression test passed
- [x] Golden report hash test passed
- [x] Schema validation test passed

## Drift analysis
- Metrics with notable drift: none detected against baseline tolerance.
- Drift rationale: not applicable.
- Approved by: QA

## Decision
- [x] Gate passed
- [ ] Gate failed
- Notes:
  - `pytest -q` passed (`32 passed`).
  - `py -3 scripts/validation/check_benchmark_drift.py` passed.

