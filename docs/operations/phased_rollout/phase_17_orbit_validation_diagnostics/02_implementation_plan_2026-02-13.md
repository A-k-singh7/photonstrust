# Implementation Plan

## Metadata
- Work item ID: PT-PHASE-17
- Title: OrbitVerify validation + diagnostics v0.1 (schema + validate endpoint + UI surfacing)
- Date: 2026-02-13

## 1) Deliverables

### 1.1 Orbit pass JSON Schema (v0.1)
- Add:
  - `schemas/photonstrust.orbit_pass_envelope.v0_1.schema.json`
- Notes:
  - config-first (matches `configs/demo11_orbit_pass_envelope.yml` after YAML->dict)
  - allow additional top-level keys for forward compatibility
  - strongly type and range-check envelope samples (distance/elevation/background)

### 1.2 Engine-owned semantic diagnostics
- Add:
  - `photonstrust/orbit/diagnostics.py`
    - `validate_orbit_pass_semantics(config: dict) -> dict`
      - deterministic, side-effect free
      - returns `{ errors, warnings, summary }` compatible with graph diagnostics shape

### 1.3 Schema validation helper
- Add:
  - `photonstrust/orbit/schema.py`
    - `validate_orbit_pass_config(config: dict, *, require_jsonschema: bool = False) -> None`
    - mirrors `photonstrust/graph/schema.py` behavior (jsonschema optional at runtime)

### 1.4 API endpoints
- Modify:
  - `photonstrust/api/server.py`
- Add:
  - `POST /v0/orbit/pass/validate`
    - request:
      - `{ "config": <dict>, "require_schema": <bool optional> }`
      - allow posting config directly as request body
    - response:
      - `generated_at`
      - `config_hash`
      - `diagnostics`
      - provenance metadata
  - Update `POST /v0/orbit/pass/run`
    - include `diagnostics` in successful responses

### 1.5 Web UI surfacing
- Modify:
  - `web/src/photontrust/api.js`
  - `web/src/App.jsx`
- Add:
  - `apiValidateOrbitPass(baseUrl, config, { requireSchema })`
  - Orbit Pass mode:
    - add a `Validate` action (topbar) calling `/v0/orbit/pass/validate`
    - add a right-side `Validate` tab showing diagnostics blocks
    - preserve existing run output panel (results + artifact paths)

### 1.6 Tests
- Add:
  - `tests/test_orbit_diagnostics.py` (unit tests for semantic checks)
- Modify:
  - `tests/api/test_api_server_optional.py`
    - add smoke test for `/v0/orbit/pass/validate`
    - ensure `/v0/orbit/pass/run` response includes diagnostics

### 1.7 Docs
- Add Phase 17 artifacts:
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

- Validation endpoints do not read local files.
- Schema validation is deterministic and uses local schema files.
- Diagnostics do not execute long-running simulations.

