# Script Index

The `scripts/` directory contains maintainer-oriented automation. The list is
large, so use this grouping instead of browsing file names blindly.

## Main Categories

- Local development and product startup
  - `run_api_server.py`
  - `start_product_local.py`
  - `clean_local_workspace.py`
  - `run_product_pilot_demo.py`
  - `product_readiness_gate.py`
- Validation and regression
  - `ci_checks.py`
  - `check_benchmark_drift.py`
  - `run_validation_harness.py`
  - `validate_recent_research_examples.py`
  - `compare_recent_research_benchmarks.py`
- Release and governance
  - `release_gate_check.py`
  - `build_release_gate_packet.py`
  - `sign_release_gate_packet.py`
  - `verify_release_gate_packet.py`
  - `verify_release_gate_packet_signature.py`
- PIC and tapeout operations
  - `run_corner_sweep_demo.py`
  - `run_certify_demo.py`
  - `build_pic_*`
  - `init_pic_*`
  - `refresh_pic_handoff_daily.py`
- Satellite and orbit lanes
  - `run_satellite_chain_demo.py`
  - `run_satellite_chain_sweep.py`
  - `run_satellite_chain_optuna.py`
  - `run_orbit_provider_parity.py`
  - `replay_satellite_chain_reports.py`
- Data and artifacts
  - `generate_repro_pack.py`
  - `publish_artifact_pack.py`
  - `ingest_measurement_bundle.py`
  - `check_open_benchmarks.py`

## Common Commands

```bash
python scripts/ci_checks.py
python scripts/run_validation_harness.py --output-root results/validation
python scripts/start_product_local.py
python scripts/product_readiness_gate.py --spawn-api
```

If a script supports `--help`, prefer reading that output before reading the
script source.
