# Phase 26 — Implementation Plan — PIC Solver Extensions (Rings v0.2)

## Metadata
- Work item ID: PT-PHASE-26
- Date: 2026-02-13
- Scope: Implement wavelength-dependent ring model for `pic.ring` and validate via sweep tests.

## Acceptance Criteria
- `pic.ring` is no longer a pure placeholder:
  - `photonstrust/components/pic/library.py` implements an all-pass ring transfer when resonator params are provided.
  - Falls back to the old insertion-loss placeholder behavior when only `insertion_loss_db` is given.
- Registry kind is updated to reflect the new parameters (without breaking old graphs):
  - `photonstrust/registry/kinds.py`
- Tests:
  - A wavelength sweep shows non-flat response (resonance notch) for a ring with resonator params.
  - Existing PIC simulation tests remain stable.
- Gates:
  - `py -m pytest -q`
  - `py scripts/release/release_gate_check.py`
  - `cd web && npm run lint`
  - `cd web && npm run build`

## Build Plan

### 1) Implement ring transfer function
File:
- `photonstrust/components/pic/library.py`

Add a new matrix function for `pic.ring`:
- reads params:
  - `coupling_ratio` (power)
  - `radius_um` or `round_trip_length_um`
  - `n_eff`
  - `loss_db_per_cm`
  - optional `insertion_loss_db` (extra bus loss)
- computes:
  - `L_rt_um`
  - `a_rt` from loss
  - `phi(λ)` from `n_eff` and `L_rt`
  - `H(λ)` all-pass through transfer

Backwards compat:
- if no resonator params present, keep placeholder insertion loss matrix.

### 2) Update param registry definition
File:
- `photonstrust/registry/kinds.py`

Update `pic.ring` params and notes to reflect v0.2 resonator model.

### 3) Add tests
File:
- `tests/test_pic_ring_resonance.py` (new)

Test:
- construct a small 2-port chain containing a ring
- run `simulate_pic_netlist_sweep` over a wavelength range
- assert transmission varies (e.g., min power significantly less than max power).

## Documentation Updates (Phase 26 completion checklist)
- Add Phase 26 artifacts:
  - `03_build_log_2026-02-13.md`
  - `04_validation_report_2026-02-13.md`
- Update indices:
  - `docs/operations/phased_rollout/README.md`
  - `docs/operations/README.md`
- Update strategy docs:
  - `docs/research/deep_dive/21_v1_to_v3_fast_execution_plan.md`
  - `docs/research/15_platform_rollout_plan_2026-02-13.md`
  - `docs/research/14_physics_core_open_science_master_plan_2026-02-12.md`

