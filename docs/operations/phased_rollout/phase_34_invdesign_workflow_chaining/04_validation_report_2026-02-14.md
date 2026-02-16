# Phase 34 - Invdesign Workflow Chaining - Validation Report

Date: 2026-02-14

## What Was Validated
Validation target: the new chained workflow API endpoint and its web surface, with hermetic test posture for optional external tools (KLayout).

## Automated Gates

### Python tests
Command:
```bash
py -m pytest -q
```
Result:
- 130 passed, 3 skipped

### Release gate
Command:
```bash
py scripts/release_gate_check.py
```
Result:
- PASS (writes `results/release_gate/release_gate_report.json`)

### Web lint
Command:
```bash
cd web
npm run lint
```
Result:
- PASS

### Web build
Command:
```bash
cd web
npm run build
```
Result:
- PASS

## API Contract Check (Workflow Chain)
Test coverage added in:
- `tests/test_api_server_optional.py::test_api_pic_invdesign_workflow_chain_writes_outputs`

Asserts:
- workflow run folder exists and includes `workflow_report.json`
- workflow run manifest exists and has `run_type="pic_workflow_invdesign_chain"`
- required child runs exist and have manifests (`invdesign`, `layout_build`, `lvs_lite`, `spice_export`)
- optional KLayout run is hermetic (KLayout not invoked during tests)

## Decision
Phase 34 is accepted as complete:
- required phase artifacts are present (`01..04`)
- validation gates pass
- workflow chaining feature is available through API + web UI

