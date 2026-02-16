# Implementation Plan

## Metadata
- Work item ID: PT-PHASE-16
- Title: OrbitVerify web runner v0.1 (config-first pass envelopes)
- Date: 2026-02-13

## 1) Deliverables

### 1.1 Backend API endpoint
- Modify:
  - `photonstrust/api/server.py`
- Add:
  - `POST /v0/orbit/pass/run`
    - request:
      - `{ "config": <dict>, "output_root": <string optional> }`
      - allow posting the config dict directly as request body (compat)
    - response:
      - `run_id`
      - `output_dir`, `results_path`, `report_html_path`
      - `results` (parsed JSON)
      - provenance metadata

### 1.2 Optional API test
- Modify:
  - `tests/test_api_server_optional.py`
- Add:
  - smoke test for `POST /v0/orbit/pass/run` with `tmp_path` output root.

### 1.3 Web UI mode
- Modify:
  - `web/src/App.jsx`
  - `web/src/photontrust/api.js`
- Add:
  - `apiRunOrbitPass(baseUrl, config, { outputRoot })`
  - UI mode selector in topbar:
    - `Graph Editor` (existing)
    - `Orbit Pass` (new)
  - Orbit Pass view:
    - config JSON editor with default template
    - run action uses `/v0/orbit/pass/run`
    - results displayed in right panel as JSON + artifact paths

### 1.4 Docs
- Add Phase 16 artifacts:
  - `03_build_log_2026-02-13.md`
  - `04_validation_report_2026-02-13.md`
- Update indices after acceptance:
  - `docs/operations/phased_rollout/README.md`
  - `docs/operations/README.md`
  - `docs/research/02_architecture_and_interfaces.md` (new endpoint)
  - `docs/research/14_physics_core_open_science_master_plan_2026-02-12.md`
  - `docs/research/15_platform_rollout_plan_2026-02-13.md`
  - `docs/research/16_web_research_update_2026-02-13.md`

## 2) Validation gates

- Python:
  - `py -m pytest -q`
  - `py scripts/release_gate_check.py`
- Web:
  - `cd web && npm run lint`
  - `cd web && npm run build`

## 3) Security posture

- Orbit pass endpoint accepts a config dict only; it does not allow arbitrary
  filesystem reads.
- HTML report paths are returned as strings; no file serving is added in v0.1.

