# Phase 33 - Implementation Plan - Inverse Design Robustness + Evidence Pack

## Metadata
- Work item ID: PT-PHASE-33
- Date: 2026-02-14
- Scope: Add a schema-validated invdesign evidence pack contract + robustness evaluation support; add one additional deterministic synthesis primitive.

## Acceptance Criteria
- Evidence contract:
  - Add JSON schema: `schemas/photonstrust.pic_invdesign_report.v0.schema.json`
  - Inverse-design report artifacts emitted by the API validate against this schema.
- Robustness:
  - Inverse-design requests can include a list of robustness cases (corner overrides).
  - Objective aggregation rules are explicit and stored in the report:
    - wavelength objective aggregation: `mean` or `max`
    - case objective aggregation: `mean` or `max`
  - The report contains a per-case evaluation summary for the chosen best design.
- New synthesis primitive:
  - Implement `pic.invdesign.coupler_ratio` as a deterministic 1D scan that tunes one `pic.coupler` node's `coupling_ratio` to hit a target output power fraction.
  - API endpoint exists: `POST /v0/pic/invdesign/coupler_ratio`
  - Web UI supports selecting the invdesign kind and required inputs.
- Gates:
  - `py -m pytest -q`
  - `py scripts/release/release_gate_check.py`
  - `cd web && npm run lint`
  - `cd web && npm run build`

## Build Steps (Edits by Area)

### 1) Schemas + validators
- Add schema file:
  - `schemas/photonstrust.pic_invdesign_report.v0.schema.json`
- Add helper path function:
  - `photonstrust/invdesign/schema.py` (`invdesign_report_schema_path()`)
- Add tests:
  - `tests/test_invdesign_report_schema.py` validates generated reports against the schema.

### 2) Inverse-design engine (open-core)
- Extend existing `photonstrust/invdesign/mzi_phase.py`:
  - accept optional robustness:
    - `robustness_cases`: list of `{id,label,overrides}`
    - `wavelength_objective_agg`: `mean|max`
    - `case_objective_agg`: `mean|max`
  - include robustness evaluation summary in the report for the best design.
  - bump report `schema_version` to `0.1` and align to new schema contract.

- Add new primitive:
  - `photonstrust/invdesign/coupler_ratio.py`
  - exported via `photonstrust/invdesign/__init__.py`

- Add unit tests:
  - `tests/test_invdesign_coupler_ratio.py` (hits target fraction reasonably; robust evaluation smoke).

### 3) API surface + run artifacts
- Extend existing endpoint:
  - `photonstrust/api/server.py` `POST /v0/pic/invdesign/mzi_phase`
    - parse robustness fields and pass through
    - outputs_summary includes aggregation choices and best objective
- Add new endpoint:
  - `photonstrust/api/server.py` `POST /v0/pic/invdesign/coupler_ratio`
    - mirrors MZI endpoint structure:
      - compiles graph -> netlist
      - runs invdesign primitive
      - writes `invdesign_report.json` + `optimized_graph.json`
      - writes run manifest with `run_type=invdesign`

- Add optional API test:
  - extend `tests/api/test_api_server_optional.py` to cover the new endpoint (hermetic, deterministic).

### 4) Web UI
- Web API client:
  - add `apiInvdesignCouplerRatio(...)` in `web/src/photontrust/api.js`
  - extend invdesign calls to pass optional robustness cases/aggregators.

- Web UI:
  - `web/src/App.jsx`
    - add invdesign "kind" selector: `mzi_phase` vs `coupler_ratio`
    - add coupler node picker (detect `pic.coupler` node IDs)
    - add advanced JSON editor for robustness cases
    - wire `runInvdesign` to call the selected invdesign endpoint

## Validation Plan
- Unit tests:
  - schema validation tests pass
  - invdesign primitives meet basic objective sanity (>= threshold fraction in fixtures)
- API tests:
  - new endpoint creates a run dir and writes artifacts
- Web build:
  - lints clean and builds

## Non-Goals (Phase 33)
- No EM/adjoint solver integration in core (Meep/Ceviche/Lumopt remain future plugin backends).
- No automatic chaining from invdesign -> layout -> LVS/KLayout/SPICE in a single workflow endpoint (planned later).

