# Phase 51: Multi-Fidelity Backend Foundation (Research Brief)

Date: 2026-02-16

## Goal

Start Phase 51 with a low-risk backend-interface scaffold that prepares the codebase
for later QuTiP and Qiskit lanes without breaking default analytic/stochastic paths.

## Week 5 scope (Phase 51 W05)

1. Add backend interface modules:
   - `photonstrust/physics/backends/base.py`
   - `photonstrust/physics/backends/analytic.py`
   - `photonstrust/physics/backends/stochastic.py`
2. Keep runtime behavior backward compatible by leaving existing public physics APIs
   unchanged while adding backend-layer wrappers.
3. Add multifidelity schema contract for future evidence integration:
   - `schemas/photonstrust.multifidelity_report.v0.schema.json`
4. Add deterministic and compatibility-focused tests for backend scaffolding.
5. Validate with full suite run:
   - `py -3 -m pytest -q`

## Week 6 scope (Phase 51 W06)

1. Implement one narrow QuTiP backend target behind the new backend interface.
2. Add explicit applicability and provenance reporting for the QuTiP lane.
3. Keep fallback behavior non-breaking (analytic fallback remains allowed).
4. Validate parity lane execution and artifact generation:
   - `py -3 scripts/run_qutip_parity_lane.py`

## Codebase anchors reviewed

- Physics implementations currently used by runtime and tests:
  - `photonstrust/physics/emitter.py`
  - `photonstrust/physics/memory.py`
  - `photonstrust/physics/detector.py`
- Existing QuTiP parity lane and findings:
  - `docs/operations/phased_rollout/phase_49_cross_track_integration/10_phase5a_qutip_parity_lane_report_2026-02-16.md`
- Multi-fidelity architecture plan:
  - `docs/research/deep_dive/26_physics_engine_multifidelity_quutip_qiskit_plan.md`

## Why this sequencing is required

Phase 51 W05 establishes the shared backend contracts before any higher-fidelity
backend is promoted. This avoids coupling QuTiP/Qiskit-specific decisions to
core runtime APIs and preserves deterministic baseline behavior.

## Week 7-8 completion scope

W07 and W08 were executed as a continuation of this phase with the following
research anchors applied in implementation:

- Qiskit repeater lane: deterministic formula-vs-circuit cross-check on a
  repeater primitive via protocol circuit templates and backend wrapper.
- Multifidelity evidence integration: run-level `multifidelity_report.json`
  generation with schema validation and manifest/bundle wiring.
- UI trust surfacing: run-list and manifest trust indicators based on
  multifidelity artifact presence.

## Week 7-8 implementation references

- Qiskit backend and lane tests:
  - `photonstrust/physics/backends/qiskit_backend.py`
  - `tests/test_qiskit_backend_interface.py`
  - `tests/test_protocol_circuits_qiskit.py`
  - `tests/test_protocol_compiler.py`
- Multifidelity run artifact generation and manifest integration:
  - `photonstrust/sweep.py`
  - `photonstrust/api/server.py`
  - `photonstrust/api/runs.py`
  - `tests/test_multifidelity_execution.py`
  - `tests/test_api_server_optional.py`
- Minimal trust-surface UI updates:
  - `web/src/App.jsx`

## Week 6 implementation references

- QuTiP backend wrapper:
  - `photonstrust/physics/backends/qutip_backend.py`
- Optional parity lane runner and artifacts:
  - `scripts/run_qutip_parity_lane.py`
  - `results/qutip_parity/qutip_parity_report.json`
  - `results/qutip_parity/qutip_parity_report.md`
- Fallback policy note:
  - `docs/operations/phased_rollout/phase_51_multifidelity_backend_foundation/05_w06_fallback_policy_notes_2026-02-16.md`
