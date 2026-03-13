# Phase 36 - Evidence Bundle Attestation + Schema Contracts - Validation Report

Date: 2026-02-14

## Automated Gates

### Python tests
Command:
```bash
py -m pytest -q
```
Result:
- 134 passed, 3 skipped

### Release gate
Command:
```bash
py scripts/release/release_gate_check.py
```
Result:
- PASS

### Web lint
Command:
```bash
cd web
npm run lint
```
Result:
- PASS

### Web build
Command:
```bash
cd web
npm run build
```
Result:
- PASS

## New Schema Validation Coverage
- `tests/test_workflow_chain_report_schema.py`
  - validates workflow chain report JSON against:
    - `schemas/photonstrust.pic_workflow_invdesign_chain_report.v0.schema.json`
- `tests/test_evidence_bundle_manifest_schema.py`
  - validates bundle manifest JSON against:
    - `schemas/photonstrust.evidence_bundle_manifest.v0.schema.json`

Hermetic posture:
- tests monkeypatch KLayout discovery to avoid invoking local KLayout.

## Decision
Phase 36 is accepted as complete:
- required phase artifacts are present (`01..04`)
- validation gates pass
- workflow/bundle artifact contracts are now schema-enforced by tests

