# Phase 29 - Implementation Plan (2026-02-14)

## Metadata
- Work item ID: PT-PHASE-29
- Date: 2026-02-14
- Scope: API + web UI integration for PIC layout/LVS-lite/SPICE exports.

## Deliverables

### 1) API endpoints (run-registry integrated)
Modify:
- `photonstrust/api/server.py`

Add:
1. `POST /v0/pic/layout/build`
   - inputs: `{graph, pdk?, settings?, require_schema?, project_id?}`
   - writes artifacts into the run directory:
     - `layout_build_report.json`
     - `ports.json`
     - `routes.json`
     - `layout_provenance.json`
     - optional `layout.gds`
   - writes `run_manifest.json` with:
     - `run_type: pic_layout_build`
     - artifact relpaths
     - outputs_summary for diff/approval workflows

2. `POST /v0/pic/layout/lvs_lite`
   - inputs:
     - `{graph, layout_run_id, settings?, require_schema?, project_id?}` (preferred)
     - or `{graph, ports, routes, settings?}`
   - writes artifacts:
     - `lvs_lite_report.json`
   - writes `run_manifest.json` with:
     - `run_type: pic_lvs_lite`

3. `POST /v0/pic/spice/export`
   - inputs: `{graph, settings?, require_schema?, project_id?}`
   - writes artifacts:
     - `spice_export_report.json`
     - `netlist.sp`
     - `spice_map.json`
     - `spice_provenance.json`
   - writes `run_manifest.json` with:
     - `run_type: pic_spice_export`

Optional small improvement:
- serve `.sp/.cir/.log/.txt/.md` as `text/plain` for easier review.

### 2) Web API client functions
Modify:
- `web/src/photontrust/api.js`

Add:
- `apiBuildPicLayout()`
- `apiRunPicLvsLite()`
- `apiExportPicSpice()`

Also extend existing run APIs to accept an optional `projectId` for better run grouping.

### 3) Web UI tabs
Modify:
- `web/src/App.jsx`

Add PIC-only right-sidebar tabs:
- Layout
- LVS-lite
- SPICE

Requirements:
- run buttons call the API endpoints
- results show served artifact links and a manifest link
- results are shown as JSON for trust/review

### 4) Tests
Modify:
- `tests/test_api_server_optional.py`

Add:
- layout build writes outputs + manifest
- LVS-lite writes outputs + manifest (using `layout_run_id`)
- SPICE export writes outputs + manifest

## Validation Gates
- `py -m pytest -q`
- `py scripts/release_gate_check.py`
- `cd web && npm run lint`
- `cd web && npm run build`

## Documentation Updates
After implementation:
- add Phase 29 artifacts:
  - `03_build_log_2026-02-14.md`
  - `04_validation_report_2026-02-14.md`
- update indices:
  - `docs/operations/phased_rollout/README.md`
  - `docs/operations/README.md`
- update architecture/contracts:
  - `docs/research/02_architecture_and_interfaces.md`
- update strategy docs:
  - `docs/research/deep_dive/21_v1_to_v3_fast_execution_plan.md`
  - `docs/research/15_platform_rollout_plan_2026-02-13.md`
  - `docs/research/14_physics_core_open_science_master_plan_2026-02-12.md`
