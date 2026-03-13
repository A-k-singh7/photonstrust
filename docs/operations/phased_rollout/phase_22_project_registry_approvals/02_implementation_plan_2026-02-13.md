# Phase 22 Implementation Plan: Project Registry + Approvals (v0.1)

## Metadata
- Work item ID: PT-PHASE-22
- Date: 2026-02-13
- Scope: Minimal project grouping + approvals log (append-only) for managed-service trust workflows.

## Acceptance Criteria
- Runs can be tagged with a `project_id` and that tag is stored in `run_manifest.json`: PASS
- `GET /v0/runs` supports filtering by `project_id`: PASS
- `GET /v0/projects` lists projects inferred from stored runs: PASS
- Approvals are append-only and retrievable:
  - `POST /v0/projects/{project_id}/approvals`: PASS
  - `GET /v0/projects/{project_id}/approvals`: PASS
- Web UI can:
  - filter runs by project: PASS
  - submit an approval for the selected run: PASS
- All gates pass:
  - `py -m pytest -q`
  - `py scripts/release/release_gate_check.py`
  - `cd web && npm run lint`
  - `cd web && npm run build`

## Build Plan

### 1) Backend: project_id tagging + filtering
- Add `project_id` to manifest `input` for:
  - `POST /v0/qkd/run`
  - `POST /v0/orbit/pass/run`
- Extend run listing helper to include and optionally filter by project.

Files:
- `photonstrust/api/runs.py`
- `photonstrust/api/server.py`

### 2) Backend: project inference + approvals event log
- Create a filesystem-backed project store:
  - infer projects from run manifests (no explicit "create project" required for v0.1)
  - approvals stored as JSONL append-only log under `runs_root/projects/`
- Add endpoints:
  - `GET /v0/projects`
  - `GET /v0/projects/{project_id}/approvals`
  - `POST /v0/projects/{project_id}/approvals`

Files:
- `photonstrust/api/projects.py` (new)
- `photonstrust/api/server.py`

### 3) Web UI: project selector + approve action
- Add API client helpers:
  - list projects
  - filter runs by project
  - submit approval events
- Add Runs mode UI:
  - project selector (all vs specific project)
  - approve selected run (actor/note)

Files:
- `web/src/photontrust/api.js`
- `web/src/App.jsx`

### 4) Tests
- Extend API optional tests:
  - run creation with `project_id`
  - `GET /v0/projects` contains project
  - `GET /v0/runs?project_id=...` filters
  - approvals POST/GET behavior is append-only and project-consistent

Files:
- `tests/api/test_api_server_optional.py`

## Documentation Updates (Phase 22 completion checklist)
- Add Phase 22 artifacts:
  - `03_build_log_2026-02-13.md`
  - `04_validation_report_2026-02-13.md`
- Update indices:
  - `docs/operations/phased_rollout/README.md`
  - `docs/operations/README.md`
- Update architecture docs to include new endpoints and project/approval semantics:
  - `docs/research/02_architecture_and_interfaces.md`
  - `docs/research/14_physics_core_open_science_master_plan_2026-02-12.md`
  - `docs/research/15_platform_rollout_plan_2026-02-13.md`
