# Implementation Plan

## Metadata
- Work item ID: PT-PHASE-20
- Title: Run browser + run diff v0.1 (managed-service hardening, local dev)
- Date: 2026-02-13

## 1) Deliverables

### 1.1 API: Run diff endpoint
- Modify:
  - `photonstrust/api/server.py`
- Add:
  - `POST /v0/runs/diff`
- Request (proposed):
  - `lhs_run_id` (string)
  - `rhs_run_id` (string)
  - `scope` (string; default: `input`)
  - `limit` (int; default: 200; max: 2000)
- Response (proposed):
  - `generated_at`
  - `lhs` summary (run_id, run_type, generated_at, input_hash)
  - `rhs` summary (run_id, run_type, generated_at, input_hash)
  - `diff`:
    - `changes`: list of `{path, lhs, rhs}`
    - `summary`: `{change_count, truncated}`
  - `provenance`

### 1.2 Web: Runs mode UI
- Modify:
  - `web/src/App.jsx`
  - `web/src/photontrust/api.js`
- Add:
  - Mode selector option: `Runs`
  - Run list panel (via `GET /v0/runs`)
  - Run manifest viewer (via `GET /v0/runs/{run_id}`)
  - Two-run diff controls (two selects + Diff button)
  - Artifact links based on manifest `artifacts` relpaths (served via `/v0/runs/{run_id}/artifact`)

### 1.3 Tests
- Modify:
  - `tests/api/test_api_server_optional.py`
- Add:
  - a test that creates two runs with different inputs and asserts:
    - `POST /v0/runs/diff` returns at least one change in scope `input`
    - diff path format is stable (string) and bounded

### 1.4 Docs
- Add Phase 20 artifacts:
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

- Diff endpoint operates only on run manifests under the configured runs root.
- Diff scope defaults to `input` to avoid pulling large artifacts into API responses.
- No new file reads are introduced beyond the manifest reads already in Phase 19.

## 4) How This Fits the v1 -> v3 Fast Execution Plan

Phase 20 is a workflow prerequisite for denial-resistant demos and review:
- Performance DRC and inverse-design runs produce artifacts + manifests; Phase 20
  makes them inspectable and diffable without filesystem access.
- This enables "performance DRC as a gate" in a real engineering loop:
  author -> run -> diff -> approve.

Reference:
- `../../../research/deep_dive/21_v1_to_v3_fast_execution_plan.md`
