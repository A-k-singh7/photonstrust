# Validation Report

## Metadata
- Work item ID: PT-PHASE-18
- Title: OrbitVerify evidence hardening v0.2 (availability envelope + standards anchors)
- Date: 2026-02-13

## Acceptance Criteria Check

- Orbit pass config supports `orbit_pass.availability.clear_fraction`:
  - Pass (validated by tests + diagnostics)
- Results include `summary.expected_total_keys_bits`:
  - Pass
- Diagnostics validate clear_fraction range:
  - Pass
- HTML report includes availability assumption and expected keys:
  - Pass (manual inspection supported; not CI-rendered)
- Validation gates pass:
  - Pass (evidence below)

## Gate Evidence

### Python
- `py -m pytest -q`
  - Result: `102 passed in 8.07s`
- `py scripts/release/release_gate_check.py`
  - Result: `Release gate: PASS`
  - Report: `results\\release_gate\\release_gate_report.json`

### Web
- `cd web && npm run lint`
  - Result: PASS
- `cd web && npm run build`
  - Result: PASS

## Decision

Phase 18 is **accepted** as complete.

