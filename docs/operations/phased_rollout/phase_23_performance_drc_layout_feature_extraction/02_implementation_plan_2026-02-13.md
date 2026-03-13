# Phase 23 — Implementation Plan — Performance DRC + Layout Feature Extraction v0.1

## Metadata
- Work item ID: PT-PHASE-23
- Date: 2026-02-13
- Owner: PhotonTrust core
- Scope: Route-level parallel-run feature extraction + performance DRC integration (worst-case envelope across extracted segments).

## Acceptance Criteria
- New deterministic route extractor exists:
  - `photonstrust/layout/route_extract.py`: PASS
  - Constraints: Manhattan polylines only; deterministic ordering; canonicalization of colinear points.
- Performance DRC accepts route input (backwards compatible):
  - `photonstrust/verification/performance_drc.py`: PASS
  - `run_parallel_waveguide_crosstalk_check()` supports:
    - scalar mode (`gap_um`, `parallel_length_um`) and
    - route mode (`routes`, optional `layout_extract`).
  - In route mode, results represent the **worst-case XT envelope** across extracted segments.
- Physical DRC min-gap checks run across *all extracted segments* in route mode: PASS
- HTML report surfaces extracted layout summary when available: PASS
- Tests:
  - route extraction unit tests cover 3 cases: PASS
  - performance DRC schema validation still passes in scalar + route mode: PASS
  - API optional test covers `/v0/performance_drc/crosstalk` with routes: PASS
- Gates:
  - `py -m pytest -q`
  - `py scripts/release/release_gate_check.py`
  - `cd web && npm run lint`
  - `cd web && npm run build`

## Build Plan

### 1) Implement route-level feature extraction library
Goal: Extract “parallel run” segments between waveguides from route polylines.

Files:
- `photonstrust/layout/route_extract.py` (new)
- `photonstrust/layout/__init__.py` (new)

Key behaviors:
- validate `routes[*]` has:
  - `route_id` (or `id` fallback),
  - `width_um > 0`,
  - `points_um` list with >=2 points.
- canonicalize polylines:
  - remove duplicate consecutive points,
  - remove colinear interior points.
- support only Manhattan segments; reject diagonals with a clear error.
- compute for each overlapping, parallel segment pair:
  - `parallel_length_um` (projection overlap),
  - `gap_um` as **edge-to-edge** (centerline distance minus half-widths).

### 2) Add verification wrapper for request-level extraction
Goal: Validate request contract and provide a compact extraction summary for reports/HTML.

Files:
- `photonstrust/verification/layout_features.py` (new)

### 3) Integrate route extraction into Performance DRC
Goal: Allow `/v0/performance_drc/crosstalk` to run from `routes` and return a worst-case envelope.

Files:
- `photonstrust/verification/performance_drc.py` (modify)

Route-mode algorithm:
- Extract parallel runs from `routes`.
- Compute DRC min-gap violations across all runs.
- For each wavelength:
  - evaluate XT for each run,
  - choose the maximum XT (worst-case at that wavelength).
- Overall:
  - `worst_xt_db` is the max of the per-wavelength envelope,
  - `worst_margin_db` is the min margin vs `target_xt_db` (if provided).
- Set `check.inputs.gap_um` and `check.inputs.parallel_length_um` to the worst-case run (so schema-required fields remain present).
- Add `results.layout` summary and `provenance.layout_hash` to make extraction visible in evidence.

Backwards compatibility:
- If `routes` is absent, behavior is unchanged (scalar mode).

### 4) Improve HTML report surface
Files:
- `photonstrust/reporting/performance_drc_report.py` (modify)

Behavior:
- If `results.layout` exists, display:
  - number of routes,
  - extracted parallel-run count,
  - min extracted gap,
  - max parallel length.

### 5) Tests
Files:
- `tests/test_layout_route_extract.py` (new)
- `tests/test_performance_drc_schema.py` (modify; add route-mode schema instance)
- `tests/api/test_api_server_optional.py` (modify; add route-mode API test)

## Documentation Updates (Phase 23 completion checklist)
After validation passes:
- Add Phase 23 artifacts:
  - `03_build_log_2026-02-13.md`
  - `04_validation_report_2026-02-13.md`
- Update indices:
  - `docs/operations/phased_rollout/README.md`
  - `docs/operations/README.md`
- Update strategy/plan docs to reflect “layout extraction from routes” is implemented:
  - `docs/research/deep_dive/21_v1_to_v3_fast_execution_plan.md`
  - `docs/research/15_platform_rollout_plan_2026-02-13.md`
  - `docs/research/14_physics_core_open_science_master_plan_2026-02-12.md`
  - `docs/research/02_architecture_and_interfaces.md`

