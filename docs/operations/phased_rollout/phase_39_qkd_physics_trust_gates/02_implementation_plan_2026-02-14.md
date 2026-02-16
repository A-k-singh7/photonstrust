# Phase 39 - Implementation Plan (QKD Physics Trust Gates)

Date: 2026-02-14

## Deliverables

- PLOB sanity test gate added to unit tests.
- Configurable seeding for QKD uncertainty sampling.
- Free-space airmass approximation upgraded to Kasten & Young (1989) with low-elevation warning.
- Docs updated to reflect the implemented gates.

## Code Changes

### 1) Seeded uncertainty sampling

File: `photonstrust/qkd.py`

Change:

- Replace hardcoded RNG seed with `uncertainty.seed` (fallback: `scenario.seed`, fallback: `42`).
- Derive RNG per sample: `np.random.default_rng(seed_base + sample_idx)`

Acceptance:

- Deterministic CI bands for identical inputs and seed.
- Negative seeds do not crash (clamp to 0).
- Output shape remains `dict[distance_km -> {low, high, outage_probability}]`.

### 2) Airmass model upgrade (free-space)

File: `photonstrust/channels/free_space.py`

Change:

- Implement `_kasten_young_airmass(elevation_deg)` using Kasten & Young (1989):
  `airmass = 1 / (sin(h) + 0.50572 * (h + 6.07995)^-1.6364)`
- In `atmospheric_transmission(...)`, clamp elevation to `[0, 90]`, set
  `airmass = max(1.0, _kasten_young_airmass(...))`, and warn when `elevation_deg < 5`.

Acceptance:

- `airmass` remains finite near the horizon (no singularities).
- A warning is emitted for low elevations.

### 3) PLOB sanity test gate

File: `tests/test_qkd_plob_bound.py` (new)

Change:

- Add a unit test that checks:
  `compute_point(...).key_rate_bps <= (-log2(1 - eta) * rep_rate_hz) * 1.01`,
  where `eta = 10 ** (-loss_db / 10.0)` and `loss_db` comes from the modeled channel loss budget.

Acceptance:

- Test passes across a small distance sweep.
- Test is deterministic and fast.

### 4) Airmass regression test

File: `tests/test_free_space_channel.py`

Change:

- Add a test asserting low-elevation airmass is finite, greater than 1, and not explosively large
  (guards against regression back to plane-parallel `1/sin(h)`).

Acceptance:

- Test captures the `UserWarning` emitted below 5 degrees.

## Documentation Updates

- Update audit status for implemented items:
  - `docs/audit/00_audit_index.md`
  - `docs/audit/01_physics_model_assumptions.md`
  - `docs/audit/02_test_coverage_gaps.md`
- Add this phase folder to `docs/operations/phased_rollout/README.md` and update planned phase numbering.
- Add a fast execution overlay mapping file: `docs/operations/phased_rollout/FAST_EXECUTION_OVERLAY.md`

## Validation Plan

1. Unit tests:

```powershell
cd c:\Users\aksin\Desktop\Qutip+qskit projects\photonstrust
py -m pytest -q
```

2. CLI smoke: QKD scenario run (artifact output)

```powershell
py -m photonstrust.cli run configs\demo1_quick_smoke.yml --output results\phase_39_smoke_qkd
```

3. CLI smoke: Orbit pass envelope run (ensures free-space channel path works)

```powershell
py -m photonstrust.cli run configs\demo11_orbit_pass_envelope.yml --output results\phase_39_smoke_orbit
```
