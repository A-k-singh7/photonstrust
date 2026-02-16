# PIC Upgrade Wave 4 (correlated yield + trace-native spectral signoff) — 2026-02-16

## What was added

Building on Wave 3, PIC verification now supports two additional signoff-oriented capabilities:

1. **Trace-native wavelength signoff (auto extraction)**
   - `verify_wavelength_sweep_signoff_from_trace(...)`
   - Converts raw wavelength sweep traces directly into per-channel signoff metrics:
     - center wavelength
     - insertion loss
     - extinction ratio
     - linewidth (interpolated at configurable drop level)
   - Runs the existing channel quality/spacing gate (`verify_wavelength_sweep_signoff`) on extracted metrics.
   - Enables a one-call path from measurement/simulation sweep traces to signoff verdicts.

2. **Correlated process-yield modeling**
   - `estimate_process_yield(...)` now supports `correlation_matrix`.
   - Retains backward-compatible independent analytic yield.
   - Adds correlated Monte Carlo mode (deterministic via `seed`) for non-independent process effects.
   - If correlation is provided without sample count, a deterministic default sample budget is applied so correlated mode is active by default.

3. **Signoff bundle expansion**
   - `verify_layout_signoff_bundle(...)` now accepts:
     - `wavelength_sweep_trace_signoff`
   - This extends one-call bundle coverage to include direct trace-driven spectral signoff.

## Files updated

- `photonstrust/pic/layout/verification/core.py`
  - added `verify_wavelength_sweep_signoff_from_trace(...)`
  - added linewidth interpolation helper
  - extended `estimate_process_yield(...)` with correlated Monte Carlo support
  - extended `verify_layout_signoff_bundle(...)` request surface
- `photonstrust/pic/layout/verification/__init__.py`
  - exported `verify_wavelength_sweep_signoff_from_trace`
- `tests/test_pic_layout_verification_core.py`
  - added trace-signoff pass/fail tests
  - added correlated-yield mode + validation tests
  - expanded bundle coverage with trace-signoff path

## Validation status

- PIC verification test file: **13 passed**
- Full suite: **186 passed, 7 skipped**
- Release gate: **PASS**

## Why this is better

Wave 4 closes two practical signoff gaps:
- **Spectral signoff no longer depends on pre-derived channel tables** (reduces manual preprocessing risk).
- **Yield estimation can model correlated process behavior**, giving a more realistic production-readiness signal than independent-only assumptions.
