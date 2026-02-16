# Phase 32 - Validation Report - KLayout Pack: Run Registry Source Selection

Date: 2026-02-14

## Scope Validated
Allow running the trusted KLayout macro template ("KLayout run artifact pack") on a `.gds` artifact selected from the Run Registry picker (Runs mode), not only the "last Layout build run".

## Acceptance Criteria Results

### Backend
- `POST /v0/pic/layout/klayout/run` accepts:
  - `layout_run_id` (legacy): PASS
  - `source_run_id` (new): PASS
- `gds_artifact_path`:
  - explicit selection supported: PASS
  - default selection when omitted:
    - prefers `artifacts.layout_gds`: PASS
    - else uses the single top-level `.gds` artifact if unambiguous: PASS
    - else uses `layout.gds` if present in the run dir (legacy/manual runs): PASS
    - else requests explicit `gds_artifact_path` (400): PASS
- Run manifest input stores:
  - `source_run_id`: PASS
  - `source_gds_artifact_path`: PASS
  - `layout_run_id` when provided: PASS

### Frontend
- Runs browser (mode `runs`, tab `Manifest`) includes a KLayout runner section when:
  - a run is selected: PASS
  - at least one `.gds` artifact is present in `manifest.artifacts`: PASS
- User can select a `.gds` artifact path and run the pack: PASS
- Result displays served artifact links + JSON payload: PASS

### Tests
- Added hermetic API test for `source_run_id` + explicit `gds_artifact_path`: PASS

### Gates
- `py -m pytest -q`: PASS (126 passed, 3 skipped)
- `py scripts/release_gate_check.py`: PASS
- `cd web && npm run lint`: PASS
- `cd web && npm run build`: PASS

## Manual Validation Notes
- If KLayout is not discoverable on a machine, the API intentionally returns a pack with `status="skipped"` (and still emits the artifact pack JSON + stdout/stderr) to preserve the "evidence pack" contract and avoid silent failures.
