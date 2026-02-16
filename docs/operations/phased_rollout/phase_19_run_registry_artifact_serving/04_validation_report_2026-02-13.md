# Validation Report

## Metadata
- Work item ID: PT-PHASE-19
- Date: 2026-02-13
- Decision: ACCEPT

## Acceptance Criteria Check
- API exposes:
  - `GET /v0/runs`: PASS
  - `GET /v0/runs/{run_id}`: PASS
  - `GET /v0/runs/{run_id}/artifact?path=<relative>`: PASS
- `POST /v0/qkd/run` and `POST /v0/orbit/pass/run` write `run_manifest.json`: PASS
- Artifact serving rejects traversal attempts and only serves files under the run directory: PASS
- Web UI (Orbit Pass mode) surfaces served artifact links: PASS

## Gates
- Python tests:
  - Command: `py -m pytest -q`
  - Result: PASS (`103 passed`)
- Release gate:
  - Command: `py scripts/release_gate_check.py`
  - Result: PASS
  - Report: `results/release_gate/release_gate_report.json`
- Web lint:
  - Command: `cd web && npm run lint`
  - Result: PASS
- Web build:
  - Command: `cd web && npm run build`
  - Result: PASS (Vite build; `200 modules transformed`)

## Evidence (tests)
- `tests/test_api_server_optional.py` includes:
  - run creation under `PHOTONTRUST_API_RUNS_ROOT=tmp_path`
  - `/v0/runs` contains the new `run_id`
  - `/v0/runs/{run_id}` returns the manifest
  - `/v0/runs/{run_id}/artifact?path=...` serves HTML + JSON and rejects `../` paths
