# Implementation Plan

## Metadata
- Work item ID: PT-PHASE-21
- Title: Run output summaries + output diff scope v0.1 (managed-service hardening, local dev)
- Date: 2026-02-13

## 1) Deliverables

### 1.1 Run manifests include `outputs_summary`

- Modify:
  - `photonstrust/api/server.py`
- Update:
  - `POST /v0/qkd/run`
    - add `outputs_summary.qkd.cards[]` with:
      - `scenario_id`, `band`, `key_rate_bps`, `qber`, `safe_use`
  - `POST /v0/orbit/pass/run`
    - add `outputs_summary.orbit_pass.cases[]` with:
      - `case_id`, `label`, `total_keys_bits`, `expected_total_keys_bits`,
        `avg_key_rate_bps`, `min_key_rate_bps`, `max_key_rate_bps`

### 1.2 API: diff supports `scope=outputs_summary`
- Modify:
  - `photonstrust/api/server.py`
- Update:
  - `POST /v0/runs/diff`
    - allow `scope` values: `input`, `outputs_summary`, `all`
    - default remains `input`

### 1.3 Web: diff scope selector
- Modify:
  - `web/src/App.jsx`
  - `web/src/photontrust/api.js`
- Update:
  - Runs mode diff controls include scope selector:
    - `input` (default)
    - `outputs_summary`

### 1.4 Tests
- Modify:
  - `tests/test_api_server_optional.py`
- Add:
  - Run manifest assertions for `outputs_summary` presence
  - Diff test with `scope=outputs_summary` returns at least one change when
    outputs differ (or explicitly returns empty when identical)

### 1.5 Docs
- Add Phase 21 artifacts:
  - `03_build_log_2026-02-13.md`
  - `04_validation_report_2026-02-13.md`
- Update indices after acceptance:
  - `docs/operations/phased_rollout/README.md`
  - `docs/operations/README.md`
  - `docs/research/02_architecture_and_interfaces.md`
  - `docs/research/14_physics_core_open_science_master_plan_2026-02-12.md`
  - `docs/research/15_platform_rollout_plan_2026-02-13.md`

## 2) Validation gates

- Python:
  - `py -m pytest -q`
  - `py scripts/release_gate_check.py`
- Web:
  - `cd web && npm run lint`
  - `cd web && npm run build`

## 3) Scientific integrity constraints

- `outputs_summary` must be a pure summary of already-computed artifacts.
- No new heuristics should be introduced that could be misinterpreted as
  certification-grade physics.

