# Validation Report

## Metadata
- Work item ID: PT-PHASE-22
- Date: 2026-02-13
- Decision: ACCEPT

## Acceptance Criteria Check
- Runs are project-tagged (`input.project_id` in `run_manifest.json`): PASS
- Runs can be filtered by project:
  - `GET /v0/runs?project_id=...`: PASS
- Projects can be listed:
  - `GET /v0/projects`: PASS
- Approvals are append-only and retrievable:
  - `POST /v0/projects/{project_id}/approvals`: PASS
  - `GET /v0/projects/{project_id}/approvals`: PASS
- Web UI supports project filter + approvals action: PASS
- Automated gates pass: PASS

## Gates
- Python tests:
  - Command: `py -m pytest -q`
  - Result: PASS (`106 passed`)
- Release gate:
  - Command: `py scripts/release/release_gate_check.py`
  - Result: PASS
  - Report: `results/release_gate/release_gate_report.json`
- Web lint:
  - Command: `cd web && npm run lint`
  - Result: PASS
- Web build:
  - Command: `cd web && npm run build`
  - Result: PASS (Vite build)

## Evidence (tests)
- `tests/api/test_api_server_optional.py` includes `test_api_projects_and_approvals` covering:
  - project inference via `GET /v0/projects`
  - run filtering via `GET /v0/runs?project_id=...`
  - approvals append + list via `POST/GET /v0/projects/{project_id}/approvals`
