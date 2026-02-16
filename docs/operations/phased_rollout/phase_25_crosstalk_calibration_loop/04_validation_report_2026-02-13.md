# Phase 25 — Validation Report — 2026-02-13

## Decision
APPROVED.

## Validation Evidence

### 1) Python unit tests
Command:
```bash
py -m pytest -q
```
Result: PASS (116 passed, 1 skipped)

### 2) Release gate (includes calibration drift gate)
Command:
```bash
py scripts/release_gate_check.py
```
Result: PASS

### 3) Web lint
Command:
```bash
cd web && npm run lint
```
Result: PASS

### 4) Web build
Command:
```bash
cd web && npm run build
```
Result: PASS

## Functional Checks
- Schema validation:
  - `tests/fixtures/measurement_bundle_pic_crosstalk/data/pic_crosstalk_sweep.json` validates against
    `schemas/photonstrust.pic_crosstalk_sweep.v0.schema.json` via the loader.
- Fitter:
  - `tests/test_pic_crosstalk_calibration.py` shows deterministic parameter recovery on a synthetic sweep.
- Drift gate:
  - `py scripts/check_pic_crosstalk_calibration_drift.py` returns PASS on the baseline fixture.

