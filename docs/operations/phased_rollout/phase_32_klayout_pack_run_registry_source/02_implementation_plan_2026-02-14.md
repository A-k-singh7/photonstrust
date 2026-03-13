# Phase 32 - Implementation Plan - KLayout Pack: Run Registry Source Selection

## Metadata
- Work item ID: PT-PHASE-32
- Date: 2026-02-14
- Scope: Extend the KLayout pack endpoint and UI so any run-registry-selected GDS artifact can be checked.

## Acceptance Criteria
- Backend:
  - `POST /v0/pic/layout/klayout/run` accepts either:
    - `layout_run_id` (legacy), or
    - `source_run_id` (new; generic run id)
  - `gds_artifact_path` may be provided explicitly (recommended when multiple `.gds` exist).
  - If `gds_artifact_path` is omitted:
    - if run manifest declares `artifacts.layout_gds`, use it
    - else if exactly one top-level artifact ends with `.gds`, use it
    - else if `layout.gds` exists in the run directory (legacy/manual runs), use it
    - else error with a clear message requesting explicit `gds_artifact_path`
  - Run manifest input stores:
    - `source_run_id`
    - `source_gds_artifact_path`
    - `layout_run_id` when provided (for compatibility)
- Frontend:
  - Runs browser (mode `runs`, tab `Manifest`) includes a KLayout runner section when:
    - a run is selected, and
    - at least one `.gds` artifact is present
  - User can select the `.gds` artifact path and run the KLayout pack.
  - The result is shown with served artifact links.
- Tests:
  - API test covers `source_run_id` + `gds_artifact_path` path (hermetic dummy GDS file).
- Gates:
  - `py -m pytest -q`
  - `py scripts/release/release_gate_check.py`
  - `cd web && npm run lint`
  - `cd web && npm run build`

## Build Steps
1) Update `photonstrust/api/server.py` endpoint contract and default-GDS selection logic.
2) Update `web/src/photontrust/api.js` to support `sourceRunId`.
3) Add Runs-mode UI section in `web/src/App.jsx` manifest view:
   - choose `.gds` artifact path from selected run
   - run pack and show result links
4) Update `tests/api/test_api_server_optional.py` with a `source_run_id` coverage test.
5) Add Phase 32 build log + validation report; update phase indices and rollup docs.
