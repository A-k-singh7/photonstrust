# Validation Report

## Metadata
- Work item ID: PT-PHASE-21
- Date: 2026-02-13
- Decision: ACCEPT

## Acceptance Criteria Check
- Run manifests include `outputs_summary`:
  - QKD runs: PASS
  - Orbit pass runs: PASS
- API supports output-aware diffs:
  - `POST /v0/runs/diff` with `scope=outputs_summary`: PASS
- Web UI supports selecting diff scope: PASS
- Automated gates pass: PASS

## Gates
- Python tests:
  - Command: `py -m pytest -q`
  - Result: PASS (`104 passed`)
- Release gate:
  - Command: `py scripts/release_gate_check.py`
  - Result: PASS
  - Report: `results/release_gate/release_gate_report.json`
- Web lint:
  - Command: `cd web && npm run lint`
  - Result: PASS
- Web build:
  - Command: `cd web && npm run build`
  - Result: PASS (Vite build)

## Evidence (tests)
- `tests/test_api_server_optional.py` includes:
  - assertions that `run_manifest.json` contains `outputs_summary` for QKD and Orbit runs
  - a diff test that:
    - creates two orbit runs with different `dt_s`
    - calls `POST /v0/runs/diff` with `scope=input` and `scope=outputs_summary`
    - asserts `/orbit_pass/cases` changes in outputs summary scope
