# Phase 25 — Implementation Plan — Crosstalk Calibration Loop v0.1

## Metadata
- Work item ID: PT-PHASE-25
- Date: 2026-02-13
- Scope: Add a schema-valid sweep format + deterministic fitter + drift gate script.

## Acceptance Criteria
- New measurement data schema exists:
  - `schemas/photonstrust.pic_crosstalk_sweep.v0.schema.json`: PASS
- New fitter exists and is deterministic:
  - `photonstrust/calibrate/pic_crosstalk.py`: PASS
  - Fits: `kappa0_per_um`, `gap_decay_um`, `lambda_exp` (with fixed `lambda_ref_nm`)
  - Produces: parameters + RMSE + worst error + provenance hashes
- Reference fixture dataset exists as a measurement bundle:
  - `tests/fixtures/measurement_bundle_pic_crosstalk/measurement_bundle.json`: PASS
  - includes a schema-valid sweep file + correct sha256
- Drift check exists and is wired into release discipline (script runnable from CI):
  - `scripts/check_pic_crosstalk_calibration_drift.py`: PASS
  - baseline file in `tests/fixtures/` with tolerances
- Tests:
  - schema validation for sweep data: PASS
  - fitter recovers known synthetic parameters within tolerance: PASS
- Gates:
  - `py -m pytest -q`
  - `py scripts/release_gate_check.py`
  - `cd web && npm run lint`
  - `cd web && npm run build`

## Build Plan

### 1) Add sweep data schema
File:
- `schemas/photonstrust.pic_crosstalk_sweep.v0.schema.json` (new)

Proposed fields:
- `schema_version`, `kind`
- `parallel_length_um`
- `lambda_ref_nm`
- `wavelengths_nm` (list)
- `gaps_um` (list)
- `xt_db` (2D array [len(gaps), len(wavelengths)])
- `notes` + optional `provenance`

### 2) Implement deterministic fitter
File:
- `photonstrust/calibrate/pic_crosstalk.py` (new)

Method:
- Use least-squares regression on:
  - intercept term
  - `gap_um`
  - `log10(wavelength_nm / lambda_ref_nm)`
- Derive:
  - `kappa0_per_um`
  - `gap_decay_um`
  - `lambda_exp`

### 3) Add test fixture measurement bundle
Files:
- `tests/fixtures/measurement_bundle_pic_crosstalk/measurement_bundle.json` (new)
- `tests/fixtures/measurement_bundle_pic_crosstalk/data/pic_crosstalk_sweep.json` (new)

### 4) Add drift check script + baseline
Files:
- `scripts/check_pic_crosstalk_calibration_drift.py` (new)
- `tests/fixtures/pic_crosstalk_calibration_baseline.json` (new)

### 5) Add tests
Files:
- `tests/test_pic_crosstalk_calibration.py` (new)
- Extend `tests/test_measurement_ingestion.py` to ingest the new bundle: optional.

## Documentation Updates (Phase 25 completion checklist)
- Add Phase 25 artifacts:
  - `03_build_log_2026-02-13.md`
  - `04_validation_report_2026-02-13.md`
- Update indices:
  - `docs/operations/phased_rollout/README.md`
  - `docs/operations/README.md`
- Update strategy docs:
  - `docs/research/deep_dive/21_v1_to_v3_fast_execution_plan.md`
  - `docs/research/15_platform_rollout_plan_2026-02-13.md`
  - `docs/research/14_physics_core_open_science_master_plan_2026-02-12.md`

