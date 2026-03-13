# Phase 54 (W17-W20): Satellite S3/S4 + Pilot Hardening

Source anchors:
- `docs/research/deep_dive/32_satellite_qkd_realism_pack.md`
- `docs/operations/pilot_readiness_packet/*`

### W17 (2026-06-08 to 2026-06-14) - Background estimator
- Work: Add `radiance_proxy` background model with day/night and optics dependence.
- Artifacts: background model API + uncertainty fields.
- Validation: day-vs-night directional checks.
- Exit: Background defaults are physics-informed and override-able.

### W18 (2026-06-15 to 2026-06-21) - Finite-key pass budgeting
- Work: Enforce finite-key budgeting semantics for orbit-pass scenarios.
- Artifacts: pass-duration finite-key metrics and epsilon fields.
- Validation: pass-duration sensitivity tests.
- Exit: Orbit key claims tied to finite-pass constraints.

### W19 (2026-06-22 to 2026-06-28) - Satellite canonical benchmarks
- Work: Add canonical satellite scenarios and drift governance.
- Artifacts: canonical configs + baseline fixtures.
- Validation: `python scripts/validation/check_benchmark_drift.py`
- Exit: Satellite regimes covered by reproducible benchmark harness.

### W20 (2026-06-29 to 2026-07-05) - Pilot packet v2
- Work: Update intake/success criteria/claim boundaries/day-0 runbook for new satellite realism assumptions.
- Artifacts: refreshed `docs/operations/pilot_readiness_packet/*`.
- Validation: day-0 rehearsal rerun.
- Exit: Pilot packet synchronized with current model validity envelope.
