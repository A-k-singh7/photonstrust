# Phase 60: Platform Performance and Security Scale-Up (Implementation Plan)

Date: 2026-02-16

## Scope

Implement Phase 60 W41-W44 by adding async orchestration and compile cache,
deterministic performance acceleration, role-based governance controls, and
immutable evidence publication primitives.

## Owner map lock (release-critical workstreams)

Owner roles follow `docs/research/deep_dive/13_raci_matrix.md`.

| Workstream | Accountable | Responsible | Consulted | Backup |
|---|---|---|---|---|
| Async jobs + compile cache integration | TL | SIM | QA | DOC |
| Deterministic uncertainty parallelization + detector fast path | TL | SIM | QA | DOC |
| RBAC enforcement for governance endpoints | TL | SIM | QA | DOC |
| SBOM + publish-by-digest artifact chain | QA | SIM | TL | DOC |

## Implementation tasks

1. Add async job registry and compile cache integration:
   - `photonstrust/api/jobs.py`
   - `photonstrust/api/compile_cache.py`
   - `photonstrust/api/server.py`
   - `photonstrust/api/runs.py`
   - `tests/test_api_server_optional.py`
2. Add deterministic uncertainty parallelization and detector fast path:
   - `photonstrust/qkd.py`
   - `photonstrust/physics/detector.py`
   - `tests/test_qkd_uncertainty_parallel.py`
   - `tests/test_detector_fast_path.py`
3. Add RBAC controls for runs/artifacts/approvals/jobs:
   - `photonstrust/api/server.py`
   - `tests/test_api_auth_rbac.py`
4. Add SBOM and digest publication flow:
   - `photonstrust/api/server.py`
   - `schemas/photonstrust.evidence_bundle_manifest.v0.schema.json`
   - `schemas/photonstrust.evidence_bundle_publish_manifest.v0.schema.json`
   - `photonstrust/workflow/schema.py`
   - `tests/test_evidence_bundle_manifest_schema.py`
   - `tests/test_evidence_bundle_publish_manifest_schema.py`

## Acceptance gates

- Async QKD jobs can be submitted, tracked, and resolved deterministically.
- Compile cache returns stable key and optional hit metrics without breaking
  deterministic compile contracts.
- Uncertainty results are invariant under worker-count changes with fixed seeds.
- RBAC header mode enforces 401/403 semantics for governance endpoints.
- Bundle exports include SBOM and digest publish/verify APIs pass schema+verify
  checks.
