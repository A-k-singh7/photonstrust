# Script Index

The `scripts/` tree contains maintainer-oriented automation grouped by domain so
the repository is easier to navigate.

## Main Folders

- `dev/`
  - local development helpers and launcher utilities
- `product/`
  - product/demo/readiness workflows
- `validation/`
  - benchmark, validation, and regression helpers
- `release/`
  - release-gate and packet signing/verification flows
- top-level `build_*`, `init_*`, `run_*`, `check_*`
  - legacy or domain-specific scripts still pending later grouping waves

## Main Categories

- Local development and product startup
  - `dev/run_api_server.py`
  - `dev/start_product_local.py`
  - `dev/clean_local_workspace.py`
- Product and demo workflows
  - `product/run_product_pilot_demo.py`
  - `product/product_readiness_gate.py`
  - `product/run_certify_demo.py`
- Validation and regression
  - `validation/ci_checks.py`
  - `validation/check_benchmark_drift.py`
  - `validation/check_open_benchmarks.py`
  - `validation/run_validation_harness.py`
  - `validation/validate_recent_research_examples.py`
  - `validation/compare_recent_research_benchmarks.py`
- Release and governance
  - `apply_branch_protection.py`
  - `refresh_repo_baselines.py`
  - `release/release_gate_check.py`
  - `release/build_release_gate_packet.py`
  - `release/refresh_release_gate_packet.py`
  - `release/sign_release_gate_packet.py`
  - `release/verify_release_gate_packet.py`
  - `release/verify_release_gate_packet_signature.py`
- PIC and tapeout operations
  - `run_corner_sweep_demo.py`
  - `build_pic_*`
  - `init_pic_*`
  - `refresh_pic_handoff_daily.py`
- Satellite and orbit lanes
  - `run_satellite_chain_demo.py`
  - `run_satellite_chain_sweep.py`
  - `run_satellite_chain_optuna.py`
  - `run_orbit_provider_parity.py`
  - `replay_satellite_chain_reports.py`

## Common Commands

```bash
python scripts/validation/ci_checks.py
python scripts/validation/run_validation_harness.py --output-root results/validation
python scripts/dev/start_product_local.py
python scripts/product/product_readiness_gate.py --spawn-api
python scripts/refresh_repo_baselines.py --all
```

If a script supports `--help`, prefer reading that output before reading the
script source.

## Maintenance Rule

If you add, rename, move, or remove a script:

- update this index in the same branch,
- update `README.md` if the script appears in user-facing examples,
- update `docs/dev/release_process.md` if release or evidence flow changed,
- update `CHANGELOG.md` when the change is externally visible.
