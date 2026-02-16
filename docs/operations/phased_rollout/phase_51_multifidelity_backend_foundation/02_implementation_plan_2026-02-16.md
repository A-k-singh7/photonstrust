# Phase 51: Multi-Fidelity Backend Foundation (Implementation Plan)

Date: 2026-02-16

## Scope for this build slice

This implementation plan now covers Week 5 through Week 8:

- backend interface scaffolding (`base`, `analytic`, `stochastic`),
- multifidelity schema contract scaffolding,
- deterministic compatibility tests,
- QuTiP emitter-target backend lane with explicit applicability/provenance,
- Qiskit repeater primitive lane with deterministic formula-vs-circuit checks,
- multifidelity report wiring into run manifests/evidence bundles and trust views,
- baseline validation with full test suite, parity-lane execution, and release gate.

## Owner map lock (release-critical workstreams)

Owner roles follow `docs/research/deep_dive/13_raci_matrix.md`.

| Workstream | Accountable | Responsible | Consulted | Backup |
|---|---|---|---|---|
| Backend interface contract stability | TL | SIM | QA | DOC |
| Determinism and backward compatibility tests | QA | SIM | TL | DOC |
| Multifidelity schema contract discipline | TL | DOC | SIM | QA |
| Validation gate health (`pytest -q`) | QA | SIM | TL | DOC |

No release-critical stream is left without accountable and responsible roles.

## Implementation tasks

1. Add new backend package:
   - `photonstrust/physics/backends/__init__.py`
   - `photonstrust/physics/backends/base.py`
   - `photonstrust/physics/backends/analytic.py`
   - `photonstrust/physics/backends/stochastic.py`
2. Add schema helper path function:
   - `photonstrust/workflow/schema.py` (`multifidelity_report_schema_path`)
3. Add multifidelity report schema contract:
   - `schemas/photonstrust.multifidelity_report.v0.schema.json`
4. Add backend interface and schema tests:
   - `tests/test_physics_backends_interface.py`
   - `tests/test_multifidelity_report_schema.py`
5. Execute validation gate:
   - `py -3 -m pytest -q`
6. Add QuTiP backend wrapper for emitter-domain target:
   - `photonstrust/physics/backends/qutip_backend.py`
7. Register QuTiP backend in resolver:
   - `photonstrust/physics/backends/__init__.py`
8. Add QuTiP backend behavior tests:
   - `tests/test_qutip_backend_interface.py`
   - update `tests/test_physics_backends_interface.py`
9. Execute parity lane validation gate:
   - `py -3 scripts/run_qutip_parity_lane.py`
10. Record fallback policy notes for W06:
    - `05_w06_fallback_policy_notes_2026-02-16.md`
11. Add Qiskit backend wrapper for repeater primitive lane:
    - `photonstrust/physics/backends/qiskit_backend.py`
12. Register Qiskit backend in resolver and interface tests:
    - `photonstrust/physics/backends/__init__.py`
    - `tests/test_physics_backends_interface.py`
13. Add deterministic protocol-level cross-check helpers/tests:
    - `photonstrust/protocols/circuits.py`
    - `photonstrust/protocols/compiler.py`
    - `tests/test_protocol_circuits_qiskit.py`
    - `tests/test_protocol_compiler.py`
14. Generate run-level multifidelity artifacts with schema validation:
    - `photonstrust/sweep.py`
    - `tests/test_multifidelity_execution.py`
15. Wire multifidelity artifact into QKD run manifests and evidence bundles:
    - `photonstrust/api/server.py`
    - `photonstrust/api/runs.py`
    - `tests/test_api_server_optional.py`
16. Surface multifidelity presence in run UI trust context:
    - `web/src/App.jsx`
17. Execute W07/W08 validation gates:
    - `py -3 -m pytest -q`
    - `py -3 scripts/release_gate_check.py`

## Week 5 acceptance gates

- Backend interface layer (`base`, `analytic`, `stochastic`) exists and is importable.
- Deterministic behavior and compatibility tests pass for backend wrappers.
- Multifidelity schema contract exists and validates minimal instances.
- Existing baseline test suite remains green under default runtime paths.

## Week 6 acceptance gates

- QuTiP backend lane exists for emitter target and is resolver-addressable.
- QuTiP backend reports explicit applicability and provenance payloads.
- Missing QuTiP dependency path remains non-breaking with explicit fallback signal.
- QuTiP parity runner executes and produces parity artifacts under `results/qutip_parity/`.

## Week 7 acceptance gates

- Qiskit backend lane is resolver-addressable and optional-dependency safe.
- Repeater primitive formula-vs-circuit cross-check is deterministic.
- Qiskit-specific tests pass with dependency present and skip/fail clearly when absent.

## Week 8 acceptance gates

- `multifidelity_report.json` is generated per QKD run and schema-valid.
- QKD run manifest contains multifidelity artifact relpath and summary presence bit.
- Evidence bundle export includes the multifidelity artifact.
- Run trust surface displays multifidelity presence.
