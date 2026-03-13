# Phase 52: Protocol Expansion (Implementation Plan)

Date: 2026-02-16

## Scope

Implement Phase 52 W09-W12 by introducing a protocol module contract + dispatch
registry, preserving protocol-family behavior for BBM92/BB84/MDI/PM/TF, and
making bound-gate routing explicit and testable.

## Owner map lock (release-critical workstreams)

Owner roles follow `docs/research/deep_dive/13_raci_matrix.md`.

| Workstream | Accountable | Responsible | Consulted | Backup |
|---|---|---|---|---|
| Protocol dispatch contract refactor | TL | SIM | QA | DOC |
| Applicability + bound-gate routing policy | TL | QA | SIM | DOC |
| API artifact protocol metadata explicitness | TL | SIM | QA | DOC |
| Regression + release-gate validation | QA | SIM | TL | DOC |

## Implementation tasks

1. Add protocol contract and registry:
   - `photonstrust/qkd_protocols/base.py`
   - `photonstrust/qkd_protocols/registry.py`
2. Refactor QKD protocol dispatch to registry contract:
   - `photonstrust/qkd.py`
   - `photonstrust/qkd_protocols/__init__.py`
3. Surface explicit protocol selection and bound-gate policy in QKD run
   artifacts/summaries:
   - `photonstrust/api/server.py`
   - `photonstrust/api/runs.py`
4. Add protocol-contract and bound-routing tests:
   - `tests/test_qkd_protocol_registry.py`
   - `tests/test_qkd_bound_gate_routing.py`
   - update `tests/api/test_api_server_optional.py`
5. Execute validation gates:
   - `py -3 -m pytest -q`
   - `py -3 scripts/release/release_gate_check.py`
6. Add migration note for protocol dispatch contract:
   - `05_protocol_dispatch_migration_notes_2026-02-16.md`

## Acceptance gates

- Protocol selection is explicit via contract/registry rather than inline
  conditional branching.
- Protocol applicability returns deterministic pass/fail labels.
- QKD run manifests include explicit protocol selection metadata.
- Bound-gate routing is protocol-aware and tested for TF/PM/MDI skip behavior.
- Full regression suite and release gate remain green.
