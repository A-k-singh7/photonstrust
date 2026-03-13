# Implementation Plan

## Metadata
- Work item ID: PT-PHASE-14
- Title: Trust panel v0.2 (parameter registry + units/ranges + validation surface)
- Date: 2026-02-13

## 1) Deliverables

### 1.1 Backend: kinds registry
- Add new module:
  - `photonstrust/registry/kinds.py`
  - `photonstrust/registry/__init__.py`
- Registry must include:
  - kind id (e.g., `qkd.source`, `pic.waveguide`)
  - title + category
  - ports (`in`/`out` lists, for graph/UI handle rendering)
  - parameter schema entries (type, unit, default, min/max, enum, description)

### 1.2 Backend API endpoint
- Modify:
  - `photonstrust/api/server.py`
- Add:
  - `GET /v0/registry/kinds`
    - returns registry JSON + provenance (version, python, platform)

### 1.3 Web editor: trust panel
- Modify:
  - `web/src/App.jsx`
  - (optional) `web/src/photontrust/kinds.js` fallback list remains for offline dev.
- Add UI features:
  - fetch kinds registry from API on load (and/or on “Ping”)
  - palette sourced from backend registry when available
  - inspector shows:
    - param schema table (units/defaults/ranges)
    - generated field editors for scalar params
    - raw JSON editor retained for advanced use

### 1.4 Tests
- Update optional API tests:
  - `tests/api/test_api_server_optional.py`
  - add coverage for `/v0/registry/kinds`

### 1.5 Docs
- Add Phase 14 build/validation docs:
  - `03_build_log_2026-02-13.md`
  - `04_validation_report_2026-02-13.md`
- Update index docs after acceptance:
  - `docs/operations/phased_rollout/README.md`
  - `docs/operations/README.md`
  - `docs/research/02_architecture_and_interfaces.md`
  - `docs/research/14_physics_core_open_science_master_plan_2026-02-12.md`
  - `docs/research/15_platform_rollout_plan_2026-02-13.md`

## 2) Validation gates

- Python:
  - `py -m pytest -q`
  - `py scripts/release/release_gate_check.py`
- Web:
  - `cd web && npm run lint`
  - `cd web && npm run build`

## 3) Non-goals (explicit)

- No production auth/multi-tenant model yet.
- No full formal semantics / certified parameter ontology yet.
- No enabling Touchstone file reads via API (stays CLI-only by default).

