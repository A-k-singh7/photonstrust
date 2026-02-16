# Phase 35 - Workflow Replay + Evidence Bundle Export - Validation Report

Date: 2026-02-14

## What Was Validated
- Evidence bundle export endpoint returns a zip with the expected run artifacts and child-run inclusion semantics.
- Workflow replay endpoint produces a new workflow run and records provenance linking (`replayed_from_run_id`).
- UI surfaces bundle download and replay actions without breaking existing tabs.

## Automated Gates

### Python tests
Command:
```bash
py -m pytest -q
```
Result:
- 132 passed, 3 skipped

### Release gate
Command:
```bash
py scripts/release_gate_check.py
```
Result:
- PASS

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

## Test Evidence (New Coverage)
- `tests/test_api_server_optional.py::test_api_runs_bundle_returns_zip_for_workflow`
  - creates a workflow run
  - downloads `/v0/runs/{run_id}/bundle`
  - validates the zip contains:
    - workflow run manifest + workflow artifacts
    - key child run manifests and SPICE netlist artifact
- `tests/test_api_server_optional.py::test_api_pic_invdesign_workflow_chain_replay_creates_new_run`
  - replays a workflow run
  - asserts new workflow run is created and `replayed_from_run_id` is recorded

Hermetic posture:
- tests monkeypatch `find_klayout_exe` to `None` to prevent executing local KLayout during CI-style runs.

## Decision
Phase 35 is accepted as complete:
- required phase artifacts are present (`01..04`)
- validation gates pass
- evidence bundle export and workflow replay are usable via API and UI

