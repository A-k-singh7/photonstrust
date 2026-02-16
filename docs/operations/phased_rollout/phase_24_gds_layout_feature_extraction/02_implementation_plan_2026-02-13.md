# Phase 24 — Implementation Plan — GDS Layout Feature Extraction (v0.2 seam)

## Metadata
- Work item ID: PT-PHASE-24
- Date: 2026-02-13
- Scope: Optional GDS importer -> PhotonTrust `routes[*]` contract; add schema for extracted parallel-run features.

## Acceptance Criteria
- Optional dependency exists:
  - `pyproject.toml` includes `layout = ["gdstk>=0.9"]`: PASS
- New GDS route extractor exists (optional import):
  - `photonstrust/layout/gds_extract.py`: PASS
  - Behavior:
    - if `gdstk` missing: raises a clear `OptionalDependencyError`
    - imports GDS with `unit=1e-6` so routes are expressed in microns
    - extracts PATH spines to `routes[*]`
    - optionally converts axis-aligned rectangle polygons to routes
    - can restrict by `(layer, datatype)` via `filter_layers`
- New JSON schema exists for layout parallel run output:
  - `schemas/photonstrust.layout_parallel_runs.v0_1.schema.json`: PASS
  - `extract_parallel_waveguide_runs_from_request()` validates against it: PASS
- Tests:
  - minimal schema validation: PASS
  - optional gdstk test coverage:
    - in minimal env: dependency error test passes
    - if gdstk installed: roundtrip test runs and passes
- Gates:
  - `py -m pytest -q`
  - `py scripts/release_gate_check.py`
  - `cd web && npm run lint`
  - `cd web && npm run build`

## Build Plan

### 1) Add optional dependency extra
File:
- `pyproject.toml`

Add:
- `layout = ["gdstk>=0.9"]`

### 2) Implement GDS route extraction module
File:
- `photonstrust/layout/gds_extract.py` (new)

API:
- `extract_routes_from_gds(gds_path, cell=None, filter_layers=None, include_rectangles=True, manhattan_only=True, ...)`

### 3) Formalize a schema for extracted parallel-run outputs
File:
- `schemas/photonstrust.layout_parallel_runs.v0_1.schema.json` (new)

### 4) Add tests
Files:
- `tests/test_layout_features_schema.py` (new): validates extraction output against schema.
- `tests/test_gds_extract_optional.py` (new):
  - ensures `OptionalDependencyError` in minimal env
  - optional roundtrip when `gdstk` is installed.

## Documentation Updates (Phase 24 completion checklist)
- Add Phase 24 artifacts:
  - `03_build_log_2026-02-13.md`
  - `04_validation_report_2026-02-13.md`
- Update indices:
  - `docs/operations/phased_rollout/README.md`
  - `docs/operations/README.md`
- Update strategy docs:
  - `docs/research/deep_dive/21_v1_to_v3_fast_execution_plan.md`
  - `docs/research/15_platform_rollout_plan_2026-02-13.md`
  - `docs/research/14_physics_core_open_science_master_plan_2026-02-12.md`
  - `docs/research/02_architecture_and_interfaces.md` (optional note about layout extra)

