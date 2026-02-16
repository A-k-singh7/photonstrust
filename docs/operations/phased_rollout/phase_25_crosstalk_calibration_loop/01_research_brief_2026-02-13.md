# Phase 25 — Crosstalk Calibration Loop v0.1

## Metadata
- Work item ID: PT-PHASE-25
- Date: 2026-02-13
- Scope: Establish a reproducible calibration loop for the parallel-waveguide crosstalk predictor:
  - measurement bundle -> validated sweep data -> fit model params -> evidence report -> drift gate.

## Why This Phase Matters (Moat + Scientific Trust)
PhotonTrust’s performance DRC becomes defensible when it is:
- **calibrated** to real measurements (or at minimum a published/synthetic reference set),
- **versioned** (model params and fit method are explicit),
- **auditable** (fit residuals are reported),
- and **governed** (future changes are blocked by drift gates unless approved).

This is the difference between “a heuristic slider” and “a verification primitive with evidence.”

## Existing Baseline (in repo)
- Predictor:
  - `photonstrust/components/pic/crosstalk.py`
  - model params: `kappa0_per_um`, `gap_decay_um`, `lambda_ref_nm`, `lambda_exp`
- Performance DRC runner (supports scalar + route-mode envelope):
  - `photonstrust/verification/performance_drc.py`
- Measurement bundle ingestion + redaction scan:
  - `photonstrust/measurements/*`
  - schema: `schemas/photonstrust.measurement_bundle.v0.schema.json`

## Calibration Target (v0.1)
We calibrate the predictor parameters so predicted `xt_db(gap, length, wavelength)` matches measured sweeps.

For the current model:
```
kappa(g, λ) = kappa0 * exp(-g / gap_decay) * (λ/λ_ref)^lambda_exp * corner_scale
P_xt ≈ (kappa * L)^2     (quadratic approximation region; monotonic)
XT_dB = 10*log10(P_xt)
```

Calibration approach (v0.1):
- Fit `kappa0_per_um`, `gap_decay_um`, `lambda_exp` using least-squares regression in the quadratic region.
- Keep `lambda_ref_nm` fixed (default 1550) for interpretability.

## Data Contract (v0.1)
Define a sweep file format that is:
- schema-validatable (JSON),
- easy to generate from lab scripts,
- and unambiguous about units and dimensions.

We’ll package it inside the existing `measurement_bundle.json` mechanism:
- `measurement_bundle.kind = "pic_crosstalk_sweep"`
- includes one JSON data file validated against a new schema.

## Drift Governance (v0.1)
Add a simple drift check:
- run calibration on a fixed reference dataset,
- compare fitted parameters (and/or RMSE) against a baseline file,
- fail the gate if drift exceeds tolerance.

This is intentionally strict because the performance DRC wedge must be denial-resistant.

## Exit Criteria
- New schema for `pic_crosstalk_sweep` data file.
- Deterministic fitter produces:
  - fitted params
  - fit residual metrics (RMSE, worst error)
  - a provenance block (input hash, model hash, fit method version)
- A drift-check script exists and passes on the reference fixture dataset.
- All gates pass.

