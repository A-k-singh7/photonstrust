# Test Naming Cleanup Matrix (2026-03-13)

## Purpose

This matrix defines how the Python test suite should be reorganized so the repo
looks predictable and professional at scale.

## Current Patterns Observed

### Stable domain patterns

- `test_detector_model.py`
- `test_graph_compiler.py`
- `test_qkd_smoke.py`
- `test_satellite_chain_pipeline.py`

These are good and should remain the model.

### Script test patterns

- `test_build_pic_gate_e_packet_script.py`
- `test_run_orbit_provider_parity_script.py`
- `test_run_satellite_chain_sweep_script.py`

These are also good and should be grouped under a dedicated folder.

### Internal-program or milestone patterns

- `test_packaging_readiness.py`
- `test_ga_release_cycle.py`
- `test_post_ga_hardening.py`
- `test_day10_tapeout_rehearsal.py`
- `test_m3_checkpoint.py`

These are understandable internally, but are not ideal as a flat public test
surface.

## Target Test Folder Structure

- `tests/unit/`
- `tests/integration/`
- `tests/contracts/`
- `tests/api/`
- `tests/scripts/`
- `tests/ui/`
- `tests/validation/`
- `tests/fixtures/`

## Migration Matrix

| Current pattern | Example | Target folder | Naming action |
|---|---|---|---|
| API tests | `test_api_contract_v1.py` | `tests/api/` | Keep filename, move folder |
| Script tests | `test_apply_branch_protection_script.py` | `tests/scripts/` | Keep filename, move folder |
| Contract tests | `test_protocol_engine_contract.py` | `tests/contracts/` | Keep filename, move folder |
| Schema tests | `test_evidence_bundle_manifest_schema.py` | `tests/contracts/` or `tests/validation/` | Keep filename, group consistently |
| Domain tests | `test_detector_model.py` | `tests/unit/` or `tests/integration/` | Keep filename, move folder |
| Validation baseline tests | `test_canonical_baselines.py` | `tests/validation/program/` | Keep filename initially, add README |
| Milestone/day tests | `test_day10_tapeout_rehearsal.py` | `tests/validation/milestones/` | Keep filename initially, add README |
| UI helper Python tests | `test_ui_data_helpers.py` | `tests/ui/` | Keep filename, move folder |

## Renaming Rules

### Keep as-is

- script tests ending with `_script.py`
- contract tests ending with `_contract.py`
- schema tests ending with `_schema.py`

### Review/rename later if needed

- `test_m3_checkpoint.py`
  - candidate future name: `test_program_m3_checkpoint.py`
- `test_day10_tapeout_rehearsal.py`
  - candidate future name: `test_tapeout_day10_rehearsal.py`
- `test_ga_release_cycle.py`
  - (already renamed from `test_phase62_ga_release_cycle.py`)

## Recommended Execution Order

1. move files into subfolders without renaming,
2. update imports and CI paths,
3. add `tests/README.md` with folder semantics,
4. only then consider renaming milestone files.
