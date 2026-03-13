# Scripts and Configs Cleanup Matrix (2026-03-13)

## Purpose

This matrix defines how `scripts/` and `configs/` should evolve from historical
accumulation into curated public-facing surfaces.

## Scripts: Current State

Observed script prefix counts:

- `run_*`: 20
- `check_*`: 11
- `build_*`: 9
- `generate_*`: 8
- smaller groups: `verify_*`, `refresh_*`, `init_*`, `publish_*`, `bundle_*`

This is good at the verb level but too crowded at the folder level.

## Target Script Structure

- `scripts/dev/`
- `scripts/validation/`
- `scripts/release/`
- `scripts/product/`
- `scripts/pic/`
- `scripts/satellite/`
- `scripts/ops/`

## Script Grouping Matrix

| Current file pattern | Example | Target folder |
|---|---|---|
| local dev | `run_api_server.py`, `start_product_local.py` | `scripts/dev/` |
| product UX/demo | `product_readiness_gate.py`, `run_product_pilot_demo.py` | `scripts/product/` |
| validation | `run_validation_harness.py`, `validate_recent_research_examples.py` | `scripts/validation/` |
| release | `release_gate_check.py`, `build_release_gate_packet.py` | `scripts/release/` |
| satellite/orbit | `run_satellite_chain_*`, `run_orbit_provider_parity.py` | `scripts/satellite/` |
| PIC/tapeout | `build_pic_*`, `init_pic_*`, `refresh_pic_handoff_daily.py` | `scripts/pic/` |
| repo/ops | `apply_branch_protection.py`, `compute_ci_health_metrics.py`, `run_prefect_flow.py` | `scripts/ops/` |

## Configs: Current State

Top-level config names currently mix:

- numbered demos (`demo1_*`, `demo11_*`, `demo13_*`)
- generic examples (`calibration_example.yml`, `optimization_example.yml`)
- pilot/program names (`pilot_day0_kickoff.yml`)

## Target Config Structure

- `configs/quickstart/`
- `configs/research/`
- `configs/product/`
- `configs/canonical/`
- `configs/satellite/`
- `configs/compliance/`
- `configs/pic/`

## Config Migration Matrix

| Current name | Recommended canonical target | Notes |
|---|---|---|
| `demo1_quick_smoke.yml` | `quickstart/qkd_quick_smoke.yml` | Best first-run config |
| `demo1_default.yml` | `quickstart/qkd_default.yml` | General-purpose baseline |
| `demo11_orbit_pass_envelope.yml` | `quickstart/orbit_pass_envelope.yml` | Strong public demo |
| `demo12_fiber_coexistence.yml` | `research/fiber_coexistence.yml` | Research/advanced example |
| `demo13_finite_key_example.yml` | `research/finite_key_example.yml` | Research/advanced example |
| `optimization_example.yml` | `research/optimization_example.yml` | Already descriptive |
| `calibration_example.yml` | `research/calibration_example.yml` | Already descriptive |
| `pilot_day0_kickoff.yml` | `product/pilot_day0_kickoff.yml` | Product/internal journey config |

## Migration Safety Rules

1. move or rename scripts/configs only in commits that update all references,
2. keep compatibility wrappers for user-facing paths if needed,
3. do not move CI-critical paths without test updates in the same change.
