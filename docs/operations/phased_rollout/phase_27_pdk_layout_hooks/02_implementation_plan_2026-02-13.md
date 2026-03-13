# Phase 27 - Implementation Plan - PDK-Aware Layout Hooks (Deterministic Sidecars + LVS-lite)

## Metadata
- Work item ID: PT-PHASE-27
- Date: 2026-02-13
- Scope: Deterministic layout build artifacts + LVS-lite mismatch summaries + optional KLayout runner seam.

## Decisions (v0.1 defaults)
- Backend strategy: sidecar-first, optional GDS emission via `gdstk` (optional dependency).
- KLayout: optional external runner seam only (no hard dependency; no foundry decks embedded).
- gdsfactory: deferred until after the sidecar/LVS-lite contracts are stable.

## Acceptance Criteria (Phase 27)
- Deterministic layout artifacts exist (v0.1):
  - `photonstrust/layout/pic/build_layout.py`
  - input: PIC graph + PDK + layout settings
  - output artifacts:
    - `ports.json` (port markers)
    - `routes.json` (Manhattan polylines)
    - `layout_provenance.json` (hashes, tool versions)
    - `layout.gds` (optional; emitted when `gdstk` is installed)
- LVS-lite exists (v0.1):
  - `photonstrust/verification/lvs_lite.py`
  - mismatch report includes:
    - missing edges
    - extra edges
    - ambiguous/invalid port-role connections
    - unconnected ports
- Optional KLayout runner seam exists (v0.1):
  - `photonstrust/layout/pic/klayout_runner.py`
  - can discover and execute KLayout in batch mode when installed.
- Schemas:
  - `schemas/photonstrust.pic_layout_build.v0.schema.json`
  - `schemas/photonstrust.pic_lvs_lite.v0.schema.json`
- Tests:
  - deterministic layout artifacts + LVS-lite pass/fail behavior
  - KLayout runner emits a clear error when KLayout is not installed
- Gates:
  - `py -m pytest -q`
  - `py scripts/release/release_gate_check.py`
  - `cd web && npm run lint`
  - `cd web && npm run build`

## Build Plan

### 1) Define layout settings normalization
Deliver:
- `photonstrust/layout/pic/spec.py`
  - normalize numeric settings and layer specs
  - parse node UI placement positions deterministically

### 2) Implement deterministic builder (sidecar-first)
Deliver:
- `photonstrust/layout/pic/build_layout.py`
  - compile PIC graph to normalized netlist
  - place components from `node.ui.position` (fallback to grid)
  - derive port marker coordinates from component port lists
  - route each optical edge using a deterministic Manhattan polyline
  - emit `ports.json`, `routes.json`, `layout_provenance.json`
  - optionally emit `layout.gds` using `gdstk` when available

### 3) Implement connectivity extraction and LVS-lite
Deliver:
- `photonstrust/layout/pic/extract_connectivity.py`
  - snap each route endpoint to nearest port marker within tolerance
  - output observed connectivity edges + dangling routes
- `photonstrust/verification/lvs_lite.py`
  - compare expected netlist connectivity vs observed connectivity
  - generate mismatch summaries

### 4) Optional KLayout runner seam
Deliver:
- `photonstrust/layout/pic/klayout_runner.py`
  - discover `klayout` executable on PATH
  - run a macro/script in batch mode with `-rd` variables

## Documentation Updates (Phase 27 completion checklist)
- Add Phase 27 artifacts:
  - `03_build_log_2026-02-14.md`
  - `04_validation_report_2026-02-14.md`
- Update indices:
  - `docs/operations/phased_rollout/README.md`
  - `docs/operations/README.md`
- Update architecture doc:
  - `docs/research/02_architecture_and_interfaces.md`
- Update strategy docs:
  - `docs/research/deep_dive/21_v1_to_v3_fast_execution_plan.md`
  - `docs/research/15_platform_rollout_plan_2026-02-13.md`
  - `docs/research/14_physics_core_open_science_master_plan_2026-02-12.md`
