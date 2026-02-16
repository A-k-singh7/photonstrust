# Validation Report

## Metadata
- Work item ID: PT-PHASE-13
- Title: Web drag-drop MVP v0.1 (managed service surface)
- Date: 2026-02-13

## 1) Automated validation

Python:
- `py -m pytest -q`
  - Result: PASS (`81 passed`)
- `py scripts/release_gate_check.py`
  - Result: PASS
  - Report: `results/release_gate/release_gate_report.json`

Web:
- `cd web && npm run build`
  - Result: PASS
- `cd web && npm run lint`
  - Result: PASS

## 2) Manual validation checklist (local dev)

### 2.1 Start backend API
1. `cd photonstrust`
2. `py scripts/run_api_server.py --reload`
3. Confirm:
   - `GET http://127.0.0.1:8000/healthz` returns `{ "status": "ok", ... }`

### 2.2 Start web editor
1. `cd photonstrust/web`
2. `npm install`
3. `npm run dev`
4. Open the Vite URL (typically `http://127.0.0.1:5173`).

### 2.3 QKD graph: edit -> compile -> run
1. Load `Templates -> QKD Link`.
2. Click `Compile`:
   - expect compile result includes `compiled`, `assumptions_md`, `graph_hash`.
3. Click `Run`:
   - expect response includes `run_id`, `output_dir`, and `results.cards[]`.

### 2.4 PIC graph: edit -> compile -> simulate
1. Load `Templates -> PIC Chain`.
2. Click `Run`:
   - expect `results.chain_solver.applicable == true`.
3. Load `Templates -> PIC MZI`.
4. Click `Run`:
   - expect `results.dag_solver.external_outputs` includes `cpl_out.out1` and
     `cpl_out.out2` (or equivalent outputs depending on template).

### 2.5 Graph export/import roundtrip
1. Click `Export JSON` and copy the graph payload.
2. Click `Import JSON` and paste payload.
3. Confirm nodes/edges and approximate node positions are restored.

### 2.6 Security posture check (Touchstone)
1. Import/create a PIC graph containing `pic.touchstone_2port`.
2. Click `Run`.
3. Expect a server error stating Touchstone is disabled in the API server.

## 3) Decision

Phase 13 is **accepted**: build artifacts exist, automated gates pass, and the
manual validation checklist is defined for local verification of the full
edit-to-run workflow.

