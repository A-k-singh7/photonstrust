# Phase 36 - Evidence Bundle Attestation + Schema Contracts - Implementation Plan

## Goal
Make the new control-plane artifacts "contract stable" by adding JSON schemas and validation tests for:
1. `workflow_report.json` produced by `pic_workflow_invdesign_chain`
2. `bundle_manifest.json` embedded in run evidence bundles (`/v0/runs/{run_id}/bundle`)

## Scope
- Add schema files under `schemas/`
- Add schema path helpers under a small workflow module
- Add tests that validate real generated outputs against schemas

## Non-Goals
- No cryptographic signing or key management yet (schemas + hashes only).
- No changes to run registry storage model.

---

## Schema Additions

### 1) Workflow Report Schema
Add:
- `schemas/photonstrust.pic_workflow_invdesign_chain_report.v0.schema.json`

Validates:
- top-level `schema_version`, `kind`, `inputs`, `steps`, `summary`, `provenance`
- hashes are 64-hex sha256 strings
- run IDs match `^[a-f0-9]{8,64}$`
- `summary.status` is `pass|fail`
- `artifact_relpaths` are objects with string values (relative paths)

### 2) Evidence Bundle Manifest Schema
Add:
- `schemas/photonstrust.evidence_bundle_manifest.v0.schema.json`

Validates:
- `files[*]` entries with `{path, sha256, bytes}`
- `missing[*]` entries with `{run_id, path|null, error}`

---

## Code Additions
Add module:
- `photonstrust/workflow/schema.py`

Exports:
- `workflow_invdesign_chain_report_schema_path()`
- `evidence_bundle_manifest_schema_path()`

---

## Tests

### Workflow report schema validation
Add:
- `tests/test_workflow_chain_report_schema.py`

Test:
- create a workflow chain run via API
- validate returned `report` against the workflow report schema

### Evidence bundle manifest schema validation
Add:
- `tests/test_evidence_bundle_manifest_schema.py`

Test:
- create a workflow chain run via API
- download `/v0/runs/{run_id}/bundle`
- extract `{bundle_root}/bundle_manifest.json` from zip
- validate against bundle manifest schema

---

## Validation Gates
- `py -m pytest -q`
- `py scripts/release_gate_check.py`
- `cd web; npm run lint`
- `cd web; npm run build`

---

## Documentation Updates
Mark Phase 36 complete and update planned next phase:
- `docs/operations/phased_rollout/README.md`
- `docs/operations/README.md`
- `docs/research/deep_dive/21_v1_to_v3_fast_execution_plan.md`
- `docs/research/15_platform_rollout_plan_2026-02-13.md`
- `docs/research/14_physics_core_open_science_master_plan_2026-02-12.md`

