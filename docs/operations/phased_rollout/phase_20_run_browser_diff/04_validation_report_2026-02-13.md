# Validation Report

## Metadata
- Work item ID: PT-PHASE-20
- Date: 2026-02-13
- Decision: ACCEPT

## Acceptance Criteria Check
- API exposes:
  - `POST /v0/runs/diff`: PASS
- Web UI supports:
  - listing runs: PASS
  - viewing manifests: PASS
  - diffing two runs (input scope): PASS
- Automated gates pass: PASS

## Gates
- Python tests:
  - Command: `py -m pytest -q`
  - Result: PASS (`104 passed`)
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
- `tests/test_api_server_optional.py` includes a diff test that:
  - creates two runs under `PHOTONTRUST_API_RUNS_ROOT=tmp_path`
  - calls `POST /v0/runs/diff` with scope `input`
  - asserts diff includes `/config_hash` changes and respects the `limit`
