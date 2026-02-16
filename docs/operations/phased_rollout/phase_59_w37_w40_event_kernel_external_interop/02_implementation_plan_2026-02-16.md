# Phase 59: Event Kernel and External Interop (Implementation Plan)

Date: 2026-02-16

## Scope

Implement Phase 59 W37-W40 by adding deterministic trace artifacts, protocol
step/QASM outputs, external simulator ingest-to-card flow, and interop-aware
run diff summaries.

## Owner map lock (release-critical workstreams)

Owner roles follow `docs/research/deep_dive/13_raci_matrix.md`.

| Workstream | Accountable | Responsible | Consulted | Backup |
|---|---|---|---|---|
| Deterministic event trace contract and hash gating | TL | SIM | QA | DOC |
| Protocol step log + QASM artifact publication | TL | SIM | QA | DOC |
| External simulator import contract and card flow | TL | SIM | QA | DOC |
| Interop-aware run diff comparison surfaces | QA | SIM | TL | DOC |

## Implementation tasks

1. Event kernel trace contract extensions:
   - `photonstrust/events/kernel.py`
   - `tests/test_event_kernel.py`
2. Protocol steps and optional QASM artifacts:
   - `photonstrust/protocols/steps.py`
   - `photonstrust/protocols/__init__.py`
   - `photonstrust/api/server.py`
3. External simulator import and card flow:
   - `photonstrust/report.py`
   - `photonstrust/api/server.py`
4. Interop-aware run diff summary block:
   - `photonstrust/api/server.py`
   - `tests/test_api_server_optional.py`
5. Schema and path helper additions:
   - `schemas/photonstrust.event_trace.v0.schema.json`
   - `schemas/photonstrust.protocol_steps.v0.schema.json`
   - `schemas/photonstrust.external_sim_result.v0.schema.json`
   - `photonstrust/workflow/schema.py`

## Acceptance gates

- Deterministic event traces produce stable hash for same seed/input ordering.
- QKD API run manifests include `protocol_steps_json` and `event_trace_json`.
- External import endpoint accepts schema-valid payload and writes card +
  manifest artifacts.
- Run diff includes `interop_diff` block when native/imported summaries exist.
- Targeted tests and core quality gates pass using `py -3` commands.
