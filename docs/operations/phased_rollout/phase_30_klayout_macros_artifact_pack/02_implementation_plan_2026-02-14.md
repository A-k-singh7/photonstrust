# Phase 30 - Implementation Plan - KLayout Macro Templates + "KLayout Run Artifact Pack" Contract

## Metadata
- Work item ID: PT-PHASE-30
- Date: 2026-02-14
- Scope: Add a built-in KLayout macro template and a deterministic artifact pack contract + wrapper for capturing KLayout batch runs as provenance-grade evidence.

## Acceptance Criteria (Phase 30)
- KLayout macro template exists (v0.1) and is runnable in batch mode:
  - Path: `tools/klayout/macros/pt_pic_extract_and_drc_lite.py`
  - Inputs via `-rd`:
    - `input_gds` (required)
    - `output_dir` (required)
    - layer specs: `wg_layer`, `wg_datatype`, `label_layer`, `label_datatype`
    - label parsing: `label_prefix`
    - rules: `min_waveguide_width_um`, `endpoint_snap_tol_um`
    - output paths (optional overrides): `ports_json`, `routes_json`, `drc_json`, `provenance_json`
  - Outputs written (always attempted):
    - `ports_extracted.json`
    - `routes_extracted.json`
    - `drc_lite.json`
    - `macro_provenance.json`
- A "KLayout run artifact pack" schema exists (v0):
  - `schemas/photonstrust.pic_klayout_run_artifact_pack.v0.schema.json`
- A Python wrapper exists to run the macro and write the artifact pack manifest:
  - `photonstrust/layout/pic/klayout_artifact_pack.py`
  - Behavior:
    - discovers KLayout via PATH or `PHOTONTRUST_KLAYOUT_EXE`
    - runs macro with deterministic variable ordering
    - captures stdout/stderr to files
    - records input/output SHA256 hashes and command provenance
    - produces a single manifest JSON matching schema
    - does not require KLayout for core repo tests to pass (optional seam)
- Tests exist:
  - schema validation test(s) for the artifact pack contract
  - optional integration test(s) that run KLayout only if present and a GDS generator backend is available
- Docs updated:
  - Phase 30 build log + validation report added
  - `docs/operations/phased_rollout/README.md` updated (Phase 30 complete; next planned phase shifted)
  - v1->v3 overlay updated (`docs/research/deep_dive/21_v1_to_v3_fast_execution_plan.md`)
  - platform rollout docs updated (`docs/research/15_platform_rollout_plan_2026-02-13.md`, `docs/research/14_physics_core_open_science_master_plan_2026-02-12.md`)

## Build Plan

### 1) Macro templates (KLayout)
Deliver:
- `tools/klayout/macros/pt_pic_extract_and_drc_lite.py`
  - Reads GDS via `pya.Layout().read(...)`
  - Extracts:
    - text labels on label layer matching `{label_prefix}:{node}:{port}`
    - PATH centerlines on waveguide layer (route spines)
  - Performs DRC-lite checks (v0.1):
    - PATH width >= `min_waveguide_width_um`
    - route spine is Manhattan (axis-aligned segments only)
    - route endpoints are within `endpoint_snap_tol_um` of some extracted port label
    - port label uniqueness (node, port)
  - Writes JSON artifacts with stable ordering.

### 2) Artifact pack wrapper + schema
Deliver:
- `photonstrust/layout/pic/klayout_artifact_pack.py`
  - Constructs the macro variable map and output filenames
  - Runs KLayout via `photonstrust/layout/pic/klayout_runner.py`
  - Writes:
    - `klayout_stdout.txt`, `klayout_stderr.txt`
    - `klayout_run_artifact_pack.json`
- `schemas/photonstrust.pic_klayout_run_artifact_pack.v0.schema.json`
  - Validates:
    - required metadata
    - inputs (paths + hashes)
    - execution record (backend, command, return code)
    - output artifact relpaths (nullable when skipped)

### 3) Tests
Deliver:
- `tests/test_klayout_artifact_pack_schema.py`
  - Always validates a minimal (synthetic) artifact pack instance against schema.
  - Optionally runs a real KLayout extraction if:
    - KLayout is discoverable, and
    - a GDS generator is available (e.g., `gdstk`) for producing a small fixture.

### 4) Documentation updates
Deliver:
- `03_build_log_2026-02-14.md`
- `04_validation_report_2026-02-14.md`
- Updates to:
  - `docs/operations/phased_rollout/README.md`
  - `docs/research/deep_dive/21_v1_to_v3_fast_execution_plan.md`
  - `docs/research/15_platform_rollout_plan_2026-02-13.md`
  - `docs/research/14_physics_core_open_science_master_plan_2026-02-12.md`

## Security/Trust Notes
- The macro template is treated as a trusted, repo-owned artifact. Managed-service endpoints (future) must only allow selecting approved templates (by ID) and must not accept arbitrary macro/script paths.
- Tool execution provenance (stdout/stderr/command line) is part of the evidence chain; logs are first-class artifacts.

## Non-Goals (v0.1)
- No foundry DRC deck execution.
- No device recognition / parasitic extraction.
- No multi-cell hierarchical extraction beyond selecting one top cell.

