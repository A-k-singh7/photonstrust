# Phase 1A Environment Validation Report

> **Historical note (superseded):** This file captures the initial failing state before Phase 3/4 fixes. Final Phase 49 gate status is green and recorded in:
> `docs/operations/phased_rollout/phase_49_cross_track_integration/10_phase49_closeout_report_2026-02-16.md`

Date: 2026-02-16 08:11 CET  
Repo: `/mnt/c/Users/aksin/Desktop/Qutip+qskit projects/photonstrust`

## Scope executed
- Verified venv: `.venv` (Python 3.12.3)
- Installed required deps into venv (base + dev): `numpy`, `pyyaml`, `matplotlib`, `pytest`, `jsonschema`, `cryptography`
- Ran:
  1. `python scripts/ci_checks.py`
  2. `pytest -q`
  3. `python scripts/run_validation_harness.py --output-root results/validation`

Logs:
- `results/phase1a_validation_logs/ci_checks.log`
- `results/phase1a_validation_logs/pytest_q.log`
- `results/phase1a_validation_logs/validation_harness.log`

## Pass/Fail matrix

| Check | Command | Status | Key Result |
|---|---|---|---|
| Venv present | `.venv/bin/python -V` | ✅ PASS | Python 3.12.3 |
| Dependencies installed | `pip install ...` + import check | ✅ PASS | All required base/dev deps import successfully |
| CI checks | `.venv/bin/python scripts/ci_checks.py` | ❌ FAIL | Fails at pytest gate |
| Test suite | `.venv/bin/python -m pytest -q` | ❌ FAIL | `7 failed, 169 passed, 7 skipped, 2 warnings` |
| Validation harness | `.venv/bin/python scripts/run_validation_harness.py --output-root results/validation` | ❌ FAIL | `ok=false`, `failed_cases=2`, `total_failures=114` |

## Exact failing tests/errors (pytest -q)
1. `tests/test_completion_quality.py::test_channel_polarization_penalty_is_optional_and_reduces_key_rate`
   - Error: `assert b.loss_db == pytest.approx(a.loss_db, rel=0.0, abs=0.0)`
   - Observed: `33.214724095162595`
   - Expected: `11.5 ± 0.0e+00`

2. `tests/test_emitter_model.py::test_compute_point_does_not_mutate_source_g2`
   - Error: `AttributeError: module 'photonstrust.qkd' has no attribute 'get_emitter_stats'`
   - Failure point: monkeypatch target `photonstrust.qkd.get_emitter_stats`

3. `tests/test_phase41_canonical_baselines.py::test_phase41_canonical_baselines_match_fixture`
   - Error sample: `assert 2.2318210259262616 == 2.2317200448066696 ± 2.2e-06`

4. `tests/test_regression_baselines.py::test_regression_baselines`
   - Error sample: `assert 436511.81598283397 == 0.0 ± 1.0e-12`

5. `tests/test_reliability_card_trust_metadata_consistency.py::test_trust_metadata_fields_present_for_all_protocols_v1_1[PM_QKD]`
   - Error: `jsonschema.exceptions.ValidationError: 'PM_QKD' is not one of ['qualitative', 'security_target_ready', 'engineering_grade']`
   - Field: `instance['safe_use_label']['label']`

6. `tests/test_reliability_card_trust_metadata_consistency.py::test_trust_metadata_fields_present_for_all_protocols_v1_1[TF_QKD]`
   - Error: `jsonschema.exceptions.ValidationError: 'TF_QKD' is not one of ['qualitative', 'security_target_ready', 'engineering_grade']`
   - Field: `instance['safe_use_label']['label']`

7. `tests/test_validation_harness.py::test_validation_harness_writes_artifacts_and_passes_for_demo_baseline`
   - Error: `assert summary["ok"] is True` (observed `False`)

Warnings (non-fatal but relevant):
- QuTiP unavailable fallback warning from `photonstrust/physics/emitter.py:80` (`No module named 'qutip'`), analytic model used.

## Validation harness failure detail
Run directory: `results/validation/20260216T071112Z`

- Overall: `ok=false`, `case_count=7`, `failed_cases=2`, `total_failures=114`
- Failed cases:
  1. `demo1_default_regression` — 112 failures
     - Example: `demo1_multiband/nir_795 key_rate_bps[0] drift: observed=436511.815983 expected=0`
     - Example: `demo1_multiband/c_1550 qber[0] drift: observed=0.0185577521733 expected=0.5`
  2. `phase41::phase41_longhaul_120km_c_1550_abort` — 2 failures
     - `key_rate_bps[0]`: observed `2.23182102593`, expected `2.23172004481`
     - `qber[0]`: observed `0.0153954775455`, expected `0.0153984613167`

## Immediate fixes (priority order)
1. **Fix emitter monkeypatch contract in `photonstrust.qkd`**
   - Re-expose/import `get_emitter_stats` at `photonstrust.qkd` module scope (or update tests to patch actual call site).

2. **Fix polarization modeling regression**
   - Ensure `polarization_coherence_length_km` affects visibility/QBER penalty only, not `loss_db` attenuation path.

3. **Fix reliability card safe-use label mapping**
   - `safe_use_label.label` must be one of schema enum values (`qualitative`, `security_target_ready`, `engineering_grade`), not protocol ids (`PM_QKD`, `TF_QKD`).

4. **Regenerate/update baseline fixtures after model corrections**
   - Large drift indicates stale baselines or behavior changes:
     - `tests/fixtures/baselines.json`
     - `tests/fixtures/canonical_phase41_baselines.json`
   - Preferred one-command flow: `./.venv/bin/python scripts/regenerate_baseline_fixtures.py` (regenerates both fixtures and reruns validation/tests).

5. **Install optional QuTiP dependency for parity checks**
   - Current run used analytic fallback. Install `qutip` in venv to eliminate backend skew risk during regression validation.

## Outcome
Phase 1A is **not complete** yet due deterministic test and baseline/harness failures above. Environment itself is usable (venv + core/dev deps working), but code + baseline consistency issues must be resolved before closeout.
