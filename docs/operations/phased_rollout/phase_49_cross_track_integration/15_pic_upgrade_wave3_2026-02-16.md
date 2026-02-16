# PIC Upgrade Wave 3 (advanced signoff) — 2026-02-16

## What was added

Building on Wave 2, PIC verification now includes two additional advanced checks focused on production-readiness:

1. **Wavelength-sweep signoff check**
   - `verify_wavelength_sweep_signoff(...)`
   - Verifies per-channel optical quality + grid spacing:
     - insertion loss budget
     - extinction ratio floor
     - optional linewidth bounds
     - pairwise channel spacing minimum

2. **Process-yield estimation check**
   - `estimate_process_yield(...)`
   - Estimates yield under an independent Gaussian process model using metric limits.
   - Provides analytic yield and optional deterministic Monte Carlo estimate.
   - Supports pass/fail gating via `min_required_yield`.

3. **Signoff bundle expanded again**
   - `verify_layout_signoff_bundle(...)` now accepts:
     - `wavelength_sweep_signoff`
     - `process_yield`
   - This enables a broader one-call PIC signoff surface (physics + DRC + thermal + spectral + yield).

Exports updated in:
- `photonstrust/pic/layout/verification/__init__.py`

Tests expanded in:
- `tests/test_pic_layout_verification_core.py`

## Validation status

- PIC verification test file: **11 passed**
- Full suite: **184 passed, 7 skipped**
- Release gate: **PASS**

## Why this is better

The PIC path now covers not just static constraints, but also:
- **spectral channel quality** (what customers see in WDM behavior), and
- **yield confidence** (what operations/tapeout teams need before committing).

This is a clear step from “demo checks” toward practical signoff logic.
