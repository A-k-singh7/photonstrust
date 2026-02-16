# Validation Report

## Metadata
- Work item ID: PT-PHASE-14
- Title: Trust panel v0.2 (parameter registry + units/ranges + validation surface)
- Date: 2026-02-13

## 1) Automated validation

Python:
- `py -m pytest -q`
  - Result: PASS (`82 passed`)
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
2. Start web:
   - `cd photonstrust/web`
   - `npm install`
   - `npm run dev`
3. In the UI:
   - Click `Ping` and confirm API ok.
   - Select a node and confirm the trust panel shows:
     - parameter units/ranges/defaults (when published)
     - enum options (e.g., detector class)
     - “API disabled” banner for `pic.touchstone_2port` (if selected)
4. Run a template:
   - `Templates -> QKD Link`, `Compile`, `Run`
   - `Templates -> PIC Chain`, `Run`

## 3) Decision

Phase 14 is **accepted**: artifacts exist, automated gates pass, and the trust
panel registry contract is in place for future validation and documentation
generation.

