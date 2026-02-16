# Validation Report

## Metadata
- Work item ID: PT-PHASE-15
- Title: Graph validation + structured diagnostics (params, ports, kind support)
- Date: 2026-02-13

## 1) Automated validation

Python:
- `py -m pytest -q`
  - Result: PASS (`86 passed`)
- `py scripts/release_gate_check.py`
  - Result: PASS
  - Report: `results/release_gate/release_gate_report.json`

Web:
- `cd web && npm run lint`
  - Result: PASS
- `cd web && npm run build`
  - Result: PASS

## 2) Manual validation checklist (local dev)

1. Start API:
   - `cd photonstrust`
   - `py scripts/run_api_server.py --reload`
2. Validate an intentionally-broken PIC graph:
   - send a `pic_circuit` graph to `POST /v0/graph/validate` with an invalid
     `from_port`
   - expect diagnostics includes `edge.from_port` error.
3. In the UI:
   - Compile any template and confirm diagnostics blocks render in the compile tab.

## 3) Decision

Phase 15 is **accepted**: diagnostics are backend-owned, deterministic,
machine-readable, and surfaced in the UI; automated gates pass.

