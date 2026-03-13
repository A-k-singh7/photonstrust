# Phase 28 - Implementation Plan - SPICE + KLayout Interop (EDA Tool Seams)

## Metadata
- Work item ID: PT-PHASE-28
- Date: 2026-02-14
- Scope: Deterministic SPICE export for PIC graphs + optional ngspice runner seam. KLayout runner seam is referenced from Phase 27.

## Acceptance Criteria (Phase 28)
- Deterministic SPICE export exists (v0.1):
  - `photonstrust/spice/export.py`
  - input: PIC graph (`profile=pic_circuit`)
  - output artifacts:
    - `netlist.sp` (SPICE-like netlist connectivity)
    - `spice_map.json` (terminal->net mapping)
    - `spice_provenance.json` (hashes + settings)
  - schema:
    - `schemas/photonstrust.pic_spice_export.v0.schema.json`
- Optional ngspice runner seam exists (v0.1):
  - `photonstrust/spice/ngspice_runner.py`
  - behavior:
    - discovers `ngspice` on PATH
    - runs in batch mode when available
    - raises a clear error when missing
- Tests:
  - export report schema validation
  - export determinism check (ignoring timestamps)
  - ngspice runner behavior: missing-tool error OR successful execution when tool exists
- Gates:
  - `py -m pytest -q`
  - `py scripts/release/release_gate_check.py`
  - `cd web && npm run lint`
  - `cd web && npm run build`

## Build Plan

### 1) Implement export: PIC graph -> SPICE-like netlist
Deliver:
- `photonstrust/spice/export.py`
  - compile graph -> normalized netlist
  - union-find nets across edges
  - deterministic net naming
  - deterministic subckt naming per node kind
  - optional stub `.subckt` definitions for portability

### 2) Implement optional ngspice runner
Deliver:
- `photonstrust/spice/ngspice_runner.py`
  - `find_ngspice_exe()`
  - `run_ngspice(netlist_path, output_dir, ...)`

### 3) Tests and schema validation
Deliver:
- `schemas/photonstrust.pic_spice_export.v0.schema.json`
- `tests/test_pic_spice_export.py`
- `tests/test_ngspice_runner_optional.py`

## Documentation Updates (Phase 28 completion checklist)
- Add Phase 28 artifacts:
  - `03_build_log_2026-02-14.md`
  - `04_validation_report_2026-02-14.md`
- Update phase index:
  - `docs/operations/phased_rollout/README.md`
  - `docs/operations/README.md`
- Update strategy docs:
  - `docs/research/deep_dive/21_v1_to_v3_fast_execution_plan.md`
  - `docs/research/15_platform_rollout_plan_2026-02-13.md`
  - `docs/research/14_physics_core_open_science_master_plan_2026-02-12.md`

## Non-goals (v0.1)
- No claim of optical-physics-correct SPICE simulation.
- No parsing of ngspice `.raw` into PhotonTrust measurement bundles yet.
- No foundry/EDA model libraries embedded into open-core.
