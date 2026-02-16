# Phase 45: Raman Coexistence Effective-Length Model (Implementation Plan)

Date: 2026-02-15

## Scope

- Implement an attenuation-aware Raman coexistence model using analytic effective lengths.
- Add a `raman_model` selector to allow fall back to legacy linear scaling.
- Thread per-band fiber loss into Raman computation where available.
- For relay protocols, compute and sum per-arm Raman contributions.
- Add unit tests for model semantics (alpha->0 limit, sublinear scaling, directionality).

## Files

### Raman model

- `photonstrust/photonstrust/channels/coexistence.py`
  - Extend `compute_raman_counts_cps()` signature to accept optional `fiber_loss_db_per_km`.
  - Add `raman_model` config key:
    - `effective_length` (default)
    - `legacy` (linear-in-distance)
  - Use numerically stable `expm1` forms for `1 - exp(-x)`.

### Call sites

- `photonstrust/photonstrust/qkd.py`
  - Pass `channel.fiber_loss_db_per_km` to `compute_raman_counts_cps()`.

- `photonstrust/photonstrust/qkd_protocols/mdi_qkd.py`
- `photonstrust/photonstrust/qkd_protocols/pm_qkd.py`
  - Replace single end-to-end Raman computation with per-arm sum:
    - `raman(da_km) + raman(db_km)`
  - Pass segment fiber loss (`alpha`) into the Raman model.

### Reporting

- `photonstrust/photonstrust/report.py`
  - Update Reliability Card notes text for coexistence to reflect effective-length model.

### Tests

- Add: `photonstrust/tests/test_raman_effective_length.py`
  - alpha->0 returns linear scaling
  - attenuation yields sublinear scaling
  - co vs counter differs

## Validation

- `py -m pytest -q`
