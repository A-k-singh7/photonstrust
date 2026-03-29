# Regression and Baseline Gate (GA Cycle)

## Gate context
- Scenario set: canonical validation harness set + quick smoke replay (`configs/quickstart/qkd_quick_smoke.yml`)
- Baseline file version:
  - `tests/fixtures/baselines.json`
  - `tests/fixtures/canonical_phase41_baselines.json`
  - `tests/fixtures/canonical_phase54_satellite_baselines.json`
  - `tests/fixtures/pic_crosstalk_calibration_baseline.json`
- Test run ID: `release_gate_report.json @ 2026-02-16`

## Checks
- [x] Unit tests passed
- [x] Integration tests passed
- [x] Baseline regression test passed
- [x] Golden report hash test passed
- [x] Schema validation test passed

## Drift analysis
- Metrics with notable drift: none detected against configured tolerances.
- Drift rationale: not applicable.
- Approved by: QA

## Decision
- [x] Gate passed
- [ ] Gate failed
- Notes:
  - `py -3 scripts/lock_rc_baseline.py --regenerate` generated baseline lock manifest.
  - `py -3 scripts/validation/check_benchmark_drift.py` passed.
  - `py -3 scripts/release/release_gate_check.py` passed.
