# Phase 35 - Workflow Replay + Evidence Bundle Export - Implementation Plan

## Goal
Add three missing control-plane capabilities:
1. Evidence bundle export (zip) for any run (and include workflow child runs by default).
2. Workflow replay for `pic_workflow_invdesign_chain` runs.
3. Run-to-run linking UX in the Run Browser for workflow runs.

## Non-Goals (This Phase)
- No cloud storage/export; bundles are generated from the local run registry.
- No cryptographic signing/attestation (hashes only).
- No “full reproducible environment” packaging (e.g., Docker/conda lock) beyond what already exists in release gates.

---

## API Changes

### 1) Evidence Bundle Export
Add endpoint:
- `GET /v0/runs/{run_id}/bundle`

Behavior:
- Builds and returns a zip archive containing:
  - `run_manifest.json`
  - all files referenced by `manifest.artifacts` (including nested `cards[*].artifacts`)
- If the run is a workflow (`run_type == "pic_workflow_invdesign_chain"` or `outputs_summary.pic_workflow` exists):
  - include child runs’ manifests + artifacts by default.

Determinism posture:
- stable file ordering
- stable zip entry timestamps (fixed)
- include `bundle_manifest.json` inside zip with per-file sha256 and sizes

Safety posture:
- only include files resolved under run directories using `run_store.resolve_artifact_path`.

### 2) Record Workflow Request Inputs
Update workflow chain endpoint:
- `POST /v0/pic/workflow/invdesign_chain`

New artifacts written in the workflow run directory:
- `workflow_request.json` (sanitized, schema-stable snapshot of the request payload)

Manifest updates:
- add `workflow_request_json` to `manifest.artifacts`

### 3) Workflow Replay
Add endpoint:
- `POST /v0/pic/workflow/invdesign_chain/replay`

Request:
```json
{
  "workflow_run_id": "<prior workflow run id>",
  "project_id": "optional override"
}
```

Behavior:
- Loads `<prior_run>/workflow_request.json`
- Optionally overrides `project_id`
- Calls the normal chain endpoint to produce a new workflow run
- New workflow run records `replayed_from_run_id` in:
  - workflow report `inputs`
  - workflow manifest `input`

---

## Web Changes

### 1) Run Browser Enhancements (Runs -> Manifest)
When a selected run is a workflow:
- show:
  - "Download evidence bundle (zip)" link (calls `/v0/runs/{run_id}/bundle`)
  - child-run manifest links (invdesign/layout/LVS/KLayout/SPICE) if present
  - "Replay workflow" button

### 2) Graph Mode Convenience
When `workflowResult.run_id` exists:
- show a "Download bundle (zip)" link for the workflow run.

---

## Tests

Add tests in `tests/api/test_api_server_optional.py`:
- `test_api_runs_bundle_returns_zip_for_workflow`
  - create a workflow run
  - `GET /v0/runs/{workflow_run_id}/bundle`
  - assert response is zip and contains:
    - `run_manifest.json` for workflow run
    - `workflow_report.json`
    - child run manifests (invdesign/layout/LVS/SPICE)
- `test_api_pic_invdesign_workflow_chain_replay_creates_new_run`
  - create a workflow run
  - replay it
  - assert new run id differs and records `replayed_from_run_id`

Hermetic posture:
- monkeypatch `find_klayout_exe` to `None` in tests to prevent local tool execution.

---

## Validation Gates
- `py -m pytest -q`
- `py scripts/release/release_gate_check.py`
- `cd web; npm run lint`
- `cd web; npm run build`

---

## Documentation Updates (End of Phase)
Mark Phase 35 complete and update planned next phase:
- `docs/operations/phased_rollout/README.md`
- `docs/operations/README.md`
- `docs/research/deep_dive/21_v1_to_v3_fast_execution_plan.md`
- `docs/research/15_platform_rollout_plan_2026-02-13.md`
- `docs/research/14_physics_core_open_science_master_plan_2026-02-12.md`

