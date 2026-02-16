# Phase 30 - Validation Report - KLayout Macro Templates + Run Artifact Pack Contract

Date: 2026-02-14

## Gates Run
- `py -m pytest -q`
  - Result: PASS
  - Evidence: `125 passed, 2 skipped`
- `py scripts/release_gate_check.py`
  - Result: PASS
  - Evidence: `results/release_gate/release_gate_report.json` reports PASS

## Notes
- KLayout execution remains an optional tool seam.
  - When KLayout is not discoverable (PATH or `PHOTONTRUST_KLAYOUT_EXE`), the artifact pack wrapper emits a schema-valid pack with `status="skipped"`.
- Optional integration test `test_klayout_artifact_pack_optional_real_run` is expected to skip unless:
  - KLayout is discoverable, and
  - `gdstk` is installed to generate a real GDS fixture for macro execution.

## Decision
Phase 30 is **approved**: contracts added, wrappers implemented, optional tool posture preserved, and gates pass.

