# Implementation Plan

## Metadata
- Work item ID: PT-PHASE-19
- Title: Run registry + artifact serving v0.1 (managed-service hardening, local dev)
- Date: 2026-02-13

## 1) Deliverables

### 1.1 Run manifest writer/reader
- Add:
  - `photonstrust/api/runs.py`
- Responsibilities:
  - compute runs root (default `results/api_runs`; override via env var for tests/dev)
  - write `run_manifest.json` into a run directory
  - list runs by scanning for manifests
  - resolve artifact relative paths safely (reject absolute paths, drive letters, `..`, and enforce canonical containment)

### 1.2 API endpoints
- Modify:
  - `photonstrust/api/server.py`
- Add endpoints:
  - `GET /v0/runs`
    - returns list of run manifests (summary subset) sorted by most recent.
  - `GET /v0/runs/{run_id}`
    - returns full manifest for a run id (404 if missing).
  - `GET /v0/runs/{run_id}/artifact?path=<relative>`
    - serves an artifact file under the run directory (404/400 on invalid).

### 1.3 Run endpoints write manifests
- Modify:
  - `photonstrust/api/server.py`
- Update:
  - `POST /v0/qkd/run`
  - `POST /v0/orbit/pass/run`
- Behavior:
  - after successful execution, write `run_manifest.json` to the run directory
  - include `manifest_path` (and optionally `artifact_urls`) in API response

### 1.4 Web UI (minimal)
- Modify:
  - `web/src/App.jsx`
- Add:
  - In Orbit Pass run view: clickable links to open served artifacts:
    - `orbit_pass_report.html`
    - `orbit_pass_results.json`
  - In Graph run view (optional): link to `run_registry.json` when `run_id` is present.

### 1.5 Tests
- Modify:
  - `tests/test_api_server_optional.py`
- Add:
  - run registry smoke:
    - set `PHOTONTRUST_API_RUNS_ROOT` to `tmp_path`
    - run an orbit pass (API uses `PHOTONTRUST_API_RUNS_ROOT` for the runs root)
    - assert:
      - `GET /v0/runs` contains the run id
      - `GET /v0/runs/{run_id}` returns manifest
      - `GET /v0/runs/{run_id}/artifact?path=...` returns HTML/JSON

### 1.6 Docs
- Add Phase 19 artifacts:
  - `03_build_log_2026-02-13.md`
  - `04_validation_report_2026-02-13.md`
- Update indices after acceptance:
  - `docs/operations/phased_rollout/README.md`
  - `docs/operations/README.md`
  - `docs/research/02_architecture_and_interfaces.md`
  - `docs/research/14_physics_core_open_science_master_plan_2026-02-12.md`
  - `docs/research/15_platform_rollout_plan_2026-02-13.md`

## 2) Validation gates

- Python:
  - `py -m pytest -q`
  - `py scripts/release_gate_check.py`
- Web:
  - `cd web && npm run lint`
  - `cd web && npm run build`

## 3) Security posture

- Runs root is fixed/configured at server start (env var or default).
- Artifact serving only allows **relative** paths under a run directory.
- Canonical path checks ensure requested files cannot escape the run directory.
