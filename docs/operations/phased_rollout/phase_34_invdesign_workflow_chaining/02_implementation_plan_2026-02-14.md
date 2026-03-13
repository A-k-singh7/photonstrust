# Phase 34 - Invdesign Workflow Chaining - Implementation Plan

## Goal
Add a single "workflow run" that chains:
1. inverse design (mzi phase or coupler ratio)
2. layout build
3. LVS-lite
4. optional KLayout artifact pack (if GDS is available)
5. SPICE export

The workflow run must:
- write a deterministic `workflow_report.json`,
- write a normal `run_manifest.json`,
- and reference child run IDs so provenance is reviewable in the Run Browser.

## Non-Goals (This Phase)
- No full foundry DRC/LVS/extraction signoff.
- No SPICE simulation execution (ngspice runner remains an optional seam, not invoked by default here).
- No new EM solver integration or adjoint optimization.
- No "monolithic run directory" that duplicates all artifacts; we will reference child runs instead.

## API Contract (v0.1)
### Endpoint
- `POST /v0/pic/workflow/invdesign_chain`

### Request (shape)
```json
{
  "project_id": "default",
  "graph": { "...": "pic_circuit graph" },
  "invdesign": {
    "kind": "mzi_phase | coupler_ratio",
    "phase_node_id": "ps1",
    "coupler_node_id": "cpl1",
    "target_output_node": "cpl_out",
    "target_output_port": "out1",
    "target_power_fraction": 0.9,
    "steps": 181,
    "wavelength_sweep_nm": [1550.0],
    "robustness_cases": [{"id":"nominal","label":"Nominal","overrides":{}}],
    "wavelength_objective_agg": "mean|max",
    "case_objective_agg": "mean|max"
  },
  "layout": { "pdk": {"name":"generic_silicon_photonics"}, "settings": { } },
  "lvs_lite": { "settings": { } },
  "klayout": { "settings": { } },
  "spice": { "settings": { } },
  "require_schema": false
}
```

Notes:
- `output_root` override remains forbidden (same security posture as other API runs).
- `invdesign.kind` selects which inverse-design primitive to run.

### Response (shape)
```json
{
  "generated_at": "ISO-8601",
  "run_id": "workflow_run_id",
  "output_dir": ".../run_<id>",
  "status": "ok",
  "steps": {
    "invdesign": {"run_id":"...", "kind":"pic.invdesign.mzi_phase"},
    "layout_build": {"run_id":"..."},
    "lvs_lite": {"run_id":"..."},
    "klayout_pack": {"run_id":"...", "status":"pass|fail|error|skipped", "note":"optional"},
    "spice_export": {"run_id":"..."}
  },
  "report": { "...": "workflow_report.json content" },
  "manifest_path": ".../run_manifest.json",
  "artifact_relpaths": {"workflow_report_json":"workflow_report.json"}
}
```

## Workflow Report Artifact (v0.1)
- Path: `workflow_report.json`
- Contents:
  - `schema_version`, `generated_at`
  - `kind: "pic.workflow.invdesign_chain"`
  - `inputs`: settings hashes + original graph hash
  - `steps`: child run IDs + step statuses + optional skip/error reasons
  - `summary`: overall status

## Backend Implementation Steps
### 1) Add the endpoint
File: `photonstrust/api/server.py`
- Implement `POST /v0/pic/workflow/invdesign_chain`.
- Validate:
  - payload is object
  - `graph` is present and is an object
  - `project_id` is valid
  - `invdesign.kind` is supported
  - forbid `output_root` override
- Execute chain by calling existing endpoint functions directly (internal function calls):
  - `pic_invdesign_mzi_phase` or `pic_invdesign_coupler_ratio`
  - `pic_layout_build`
  - `pic_layout_lvs_lite` (using `layout_run_id`)
  - optional `pic_layout_klayout_run` if layout emitted `layout_gds`
  - `pic_spice_export`
- Create a new workflow run:
  - generate `workflow_run_id`
  - write `workflow_report.json`
  - write `run_manifest.json` with:
    - `run_type = "pic_workflow_invdesign_chain"`
    - `artifacts.workflow_report_json = "workflow_report.json"`
    - `outputs_summary.pic_workflow` containing child run IDs + key step statuses

### 2) Optional-step posture (KLayout)
- KLayout step must be "best effort" and must not fail the workflow:
  - if layout has no `.gds` artifact: mark step as `skipped`
  - if KLayout tool is missing: the child run will be created with `status="skipped"` (existing behavior)
  - if any other KLayout error occurs: record `error` in the workflow report and continue

## Web Implementation Steps
### 1) Add API client function
File: `web/src/photontrust/api.js`
- Add `apiRunPicInvdesignWorkflowChain(baseUrl, graph, options)` to call `/v0/pic/workflow/invdesign_chain`.

### 2) Add UI surface
File: `web/src/App.jsx`
- Add a "Run Full Workflow" button in the InvDesign tab that:
  - sends the current graph + invdesign settings + layout/LVS/KLayout/SPICE settings
  - shows the workflow run ID and links to child run manifests
  - optionally updates the graph view to the optimized graph (from the invdesign step)

## Tests
File: `tests/api/test_api_server_optional.py`
- Add `test_api_pic_invdesign_workflow_chain_writes_outputs`:
  - set `PHOTONTRUST_API_RUNS_ROOT=tmp_path`
  - monkeypatch `photonstrust.layout.pic.klayout_runner.find_klayout_exe` to return `None` (hermetic)
  - call `/v0/pic/workflow/invdesign_chain` with `_pic_mzi_graph()`
  - assert:
    - workflow run folder exists
    - `workflow_report.json` exists
    - workflow manifest exists and `run_type` matches
    - required child run IDs exist and their manifests exist

## Validation Gates (Must Pass)
- `py -m pytest -q`
- `py scripts/release_gate_check.py`
- `cd web; npm run lint`
- `cd web; npm run build`

## Documentation Updates (End of Phase)
- Mark Phase 34 complete in:
  - `docs/operations/phased_rollout/README.md`
  - `docs/operations/README.md`
  - `docs/research/deep_dive/21_v1_to_v3_fast_execution_plan.md`
  - `docs/research/15_platform_rollout_plan_2026-02-13.md`

