# Phase 46: BBM92 Coincidence Model (Implementation Plan)

Date: 2026-02-15

## Scope

- Implement BBM92/E91 coincidence-based model in a dedicated protocol module.
- Update `photonstrust.qkd.compute_point` to dispatch BBM92/E91 to the new module.
- Preserve `QKDResult` surface and Reliability Card expectations.
- Update tests and regenerate canonical fixtures.

## Files

### New protocol module

- `photonstrust/photonstrust/qkd_protocols/bbm92.py`
  - Compute `Q`, `Q_true`, `Q_acc` (SPDC closed-form; emitter-cavity uses low-order mixture).
  - Compute QBER as a mixture model.
  - Map into existing `QKDResult` fields:
    - `p_pair` -> `Q_true`
    - `p_false` -> `Q_acc`
    - `q_multi` -> accidental-from-multipair contribution
    - `q_dark` -> accidental-from-noise contribution
    - `q_misalignment`, `q_source` -> split of visibility-driven true-coincidence errors
    - `q_timing` -> 0.0 (timing enters through window->noise probability)

### Dispatch

- `photonstrust/photonstrust/qkd.py`
  - Replace legacy BBM92/E91 direct-link block with:
    - `from photonstrust.qkd_protocols.bbm92 import compute_point_bbm92`
    - `return compute_point_bbm92(...)`

### Reporting

- `photonstrust/photonstrust/report.py`
  - Keep `derived.multiphoton.p_multi` as an emission-side proxy:
    - SPDC: `mu^2/(1+mu)^2`
    - emitter-cavity: `get_emitter_stats(...)["p_multi"]`
  - Avoid reconstructing p_multi from `q_multi*(p_pair+p_false)` (no longer meaningful).

### Tests / fixtures

- Update semantics tests:
  - `photonstrust/tests/test_qkd_semantics.py` (noise-only coincidences are squared)
- Update misalignment mapping test to isolate visibility from accidentals:
  - `photonstrust/tests/test_qkd_misalignment_floor.py`
- Regenerate canonical baseline fixture:
  - `py scripts/generate_phase41_canonical_baselines.py`

## Validation

- `py -m pytest -q` must pass.
