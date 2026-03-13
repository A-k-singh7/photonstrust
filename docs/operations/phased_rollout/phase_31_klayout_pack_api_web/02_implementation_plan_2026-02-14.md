# Phase 31 - Implementation Plan - KLayout Artifact Pack API + Web Integration

## Metadata
- Work item ID: PT-PHASE-31
- Date: 2026-02-14
- Scope: Add API endpoint + web UI tab to run and review Phase 30 KLayout artifact packs from the managed run registry.

## Acceptance Criteria
- API endpoint exists:
  - `POST /v0/pic/layout/klayout/run`
  - Input contract (v0.1):
    - `layout_run_id` (required): run id of a prior layout build run
    - `settings` (optional): dict forwarded to KLayout artifact pack wrapper (layers, label prefix, tolerances)
    - `project_id` (optional): groups the run under a project
  - Behavior:
    - resolves GDS artifact path safely within the layout run dir (no traversal)
    - runs `build_klayout_run_artifact_pack(...)` in a new run dir
    - always writes `run_manifest.json` with served artifact relpaths
    - returns a response containing the new `run_id` and artifact relpaths
- Web UI integration:
  - Add `KLayout` tab to PIC mode (`web/src/App.jsx`)
  - Uses last Layout run id (`layoutBuildResult.run_id`)
  - Shows served links to:
    - `klayout_run_artifact_pack.json`
    - `klayout_stdout.txt` / `klayout_stderr.txt`
    - `ports_extracted.json`, `routes_extracted.json`, `drc_lite.json`, `macro_provenance.json` when present
  - Shows clear hint when prerequisites are missing:
    - no Layout run yet, or
    - `layout.gds` not emitted (missing `gdstk`)
- Tests:
  - API test that creates a synthetic layout run dir containing a dummy `layout.gds`
  - Endpoint returns `200` and writes a new run with a manifest and artifact pack JSON
- Gates:
  - `py -m pytest -q`
  - `py scripts/release/release_gate_check.py`
  - `cd web && npm run lint`
  - `cd web && npm run build`

## Build Steps

### 1) Backend: API endpoint
Edits:
- `photonstrust/api/server.py`
  - Import: `build_klayout_run_artifact_pack`
  - Add endpoint:
    - validates `layout_run_id`
    - resolves `layout.gds` via `run_store.resolve_artifact_path(...)`
    - creates new run dir and runs artifact pack wrapper
    - writes run manifest with `outputs_summary.pic_klayout`

### 2) Frontend: web tab + API function
Edits:
- `web/src/photontrust/api.js`
  - add `apiRunPicKlayoutPack(...)`
- `web/src/App.jsx`
  - add tab button `KLayout`
  - add state:
    - `klayoutPackSettings`
    - `klayoutPackResult`
  - add callback `runKlayoutPack` and render section

### 3) Tests
Edits:
- `tests/api/test_api_server_optional.py`
  - add test for `/v0/pic/layout/klayout/run` that is hermetic (tmp runs root)

### 4) Documentation updates
Deliver:
- `03_build_log_2026-02-14.md`
- `04_validation_report_2026-02-14.md`
- Update indices and phase mapping:
  - `docs/operations/phased_rollout/README.md`
  - `docs/operations/README.md`
  - `docs/research/deep_dive/21_v1_to_v3_fast_execution_plan.md`
  - `docs/research/15_platform_rollout_plan_2026-02-13.md`
  - `docs/research/14_physics_core_open_science_master_plan_2026-02-12.md`

