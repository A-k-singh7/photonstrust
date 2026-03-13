# Implementation Plan

## Metadata
- Work item ID: PT-PHASE-15
- Title: Graph validation + structured diagnostics (params, ports, kind support)
- Date: 2026-02-13

## 1) Deliverables

### 1.1 Backend validation module
- Add:
  - `photonstrust/graph/diagnostics.py` (or `validation.py`)
- Functions:
  - `validate_graph_semantics(graph) -> {errors, warnings, summary}`
  - Validation checks:
    - param schemas (types, enum membership, ranges)
    - unknown params (warning)
    - `applies_when` mismatch (warning)
    - PIC port existence checks using `component_ports(kind)`
    - PIC unsupported kind checks using `supported_component_kinds()`

### 1.2 API endpoints
- Modify:
  - `photonstrust/api/server.py`
- Add:
  - `POST /v0/graph/validate` (graph in request body; returns diagnostics)
- Extend:
  - `/v0/graph/compile` to include `diagnostics` in response

### 1.3 Web editor display
- Modify:
  - `web/src/App.jsx`
- Add:
  - compile tab renders diagnostics block (errors/warnings) when present.

### 1.4 Tests
- Add:
  - `tests/test_graph_diagnostics.py` for validation logic
- Extend:
  - `tests/api/test_api_server_optional.py` to cover `/v0/graph/validate`.

### 1.5 Docs
- Add Phase 15 artifacts:
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

## 3) Non-goals

- No formal certification-mode gating yet (Phase 15 provides diagnostics; gating can be Phase 16+).
- No full graph schema bump (keep `schema_version: 0.1`).

