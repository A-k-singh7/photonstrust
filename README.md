# PhotonTrust
[![tapeout-gate](https://github.com/photonstrust/photonstrust/actions/workflows/tapeout-gate.yml/badge.svg?branch=main)](https://github.com/photonstrust/photonstrust/actions/workflows/tapeout-gate.yml)
[![cv-quick-verify](https://github.com/photonstrust/photonstrust/actions/workflows/cv-quick-verify.yml/badge.svg?branch=main)](https://github.com/photonstrust/photonstrust/actions/workflows/cv-quick-verify.yml)

PhotonTrust is an open-source digital twin and reliability card generator for
photonic quantum links. This MVP focuses on QKD key-rate realism across Near-IR,
O-band, and C-band configurations, including direct-link and relay-based
protocol-family surfaces.

## Choose Your Path

- CLI or library user: start with the quick start below, then see
  `configs/README.md` and `examples/README.md`.
- Product UI user: use the React-first product surface in `web/` via
  `scripts/dev/start_product_local.py`.
- Contributor or maintainer: read `CONTRIBUTING.md`, `docs/README.md`, and
  `scripts/README.md` first.

## Repository Layout

- `photonstrust/` - core Python package and APIs
- `web/` - React/Vite product surface
- `ui/` - legacy Streamlit surface
- `configs/` - runnable scenario and validation configs
- `graphs/` - graph compiler inputs for QKD and PIC flows
- `examples/` - small Python and notebook examples
- `scripts/` - validation, release, demo, and maintainer automation
- `docs/` - research, operations, templates, and work-item indexes
- `schemas/` - JSON schemas for run outputs and governance artifacts
- `results/` - generated outputs and selected checked-in evidence artifacts
- `open_source/` - separately managed public extracts

## Community Files

- `CONTRIBUTING.md`
- `CODE_OF_CONDUCT.md`
- `SUPPORT.md`
- `SECURITY.md`
- `CHANGELOG.md`
- `CITATION.cff`

## Quick start

```bash
pip install -e .
pip install -e .[qutip]
photonstrust run configs/quickstart/qkd_default.yml
```

Other demos:

```bash
photonstrust run configs/demo2_repeater_spacing.yml
photonstrust run configs/demo3_heralding_comparison.yml
photonstrust run configs/demo3_teleportation.yml
photonstrust run configs/demo4_source_benchmark.yml
photonstrust run configs/demo5_satellite_downlink.yml
photonstrust run configs/demo6_transient_emitter.yml
photonstrust run configs/demo7_multifidelity_preview.yml
photonstrust run configs/demo7_multifidelity_certification.yml
photonstrust run configs/quickstart/orbit_pass_envelope.yml --output results/orbit_demo11
```

Graph compiler / GraphSpec authoring (JSON or `.ptg.toml` -> engine config/netlist):

```bash
photonstrust graph compile graphs/demo8_qkd_link_graph.json --output results/graphs_demo
photonstrust graph compile graphs/demo8_qkd_link_graph.ptg.toml --output results/graphs_demo
photonstrust run results/graphs_demo/demo8_qkd_link/compiled_config.yml --output results/graphs_demo/demo8_qkd_link/run_outputs
photonstrust graph compile graphs/demo8_pic_circuit_graph.json --output results/graphs_demo
photonstrust pic simulate results/graphs_demo/demo8_pic_circuit/compiled_netlist.json --output results/graphs_demo/demo8_pic_circuit/pic_outputs
photonstrust pic simulate results/graphs_demo/demo8_pic_circuit/compiled_netlist.json --wavelength-sweep-nm 1540 1550 1560 --output results/graphs_demo/demo8_pic_circuit/pic_sweep_outputs
photonstrust fmt graphspec graphs/demo8_qkd_link_graph.ptg.toml --check --print-hash
```

Web drag-drop editor (Phase 13 MVP, local dev):

```bash
pip install -e .[api]
py scripts/dev/run_api_server.py --reload
cd web
npm ci
npm run dev
```

Quick smoke run:

```bash
photonstrust run configs/quickstart/qkd_quick_smoke.yml --output results/smoke_quick
```

Matrix sweeps:

```bash
photonstrust run configs/demo1_matrix_full.yml
photonstrust run configs/demo1_matrix_realistic.yml
photonstrust run configs/demo1_matrix_high_end.yml
photonstrust run configs/demo1_matrix_low_cost.yml
```

Calibration and optimization:

```bash
photonstrust run configs/research/calibration_example.yml
photonstrust run configs/research/optimization_example.yml
```

`configs/research/calibration_example.yml` includes diagnostics quality gates that can
enforce calibration acceptance thresholds during CLI runs.

Benchmark datasets:

```bash
python -m photonstrust.datasets.generate datasets/benchmarks/metro_qkd.yml results/benchmarks/metro_qkd
python -m photonstrust.datasets.generate datasets/benchmarks/repeater_chain.yml results/benchmarks/repeater_chain
python -m photonstrust.datasets.generate datasets/benchmarks/teleportation_sla.yml results/benchmarks/teleportation
```

React-first product surface (recommended local dev):

```bash
pip install -e .[api]
cd web
npm ci
cd ..
py scripts/dev/start_product_local.py
```

This launches the FastAPI backend plus the React/Vite product shell. Useful flags:

- `--web-port 5174` if `5173` is already in use
- `--surface streamlit` to launch the legacy Streamlit surface instead of React

Streamlit dashboard:

```bash
pip install -e .[ui]
uvicorn photonstrust.api.server:app --host 127.0.0.1 --port 8000
streamlit run ui/app.py
```

Product packaging (single-command local start + pilot demo):

```bash
pip install -e .[api]
cd web && npm ci && cd ..
python scripts/dev/start_product_local.py
python scripts/product/run_product_pilot_demo.py --project-id pilot_demo_week4
python scripts/product/product_readiness_gate.py --spawn-api
```

Quickstart runbook:

- `docs/operations/product/10_minute_quickstart_2026-02-18.md`

UI run-builder walkthrough:

1. Open `Run Builder` tab.
2. Click `Check API health`.
3. Click `Run Golden Path Demo` (recommended).
4. Confirm `Decision Summary` and `Time to first value`.
5. Export a deterministic `Run Profile (Export / Import)` JSON for reuse.

Run profile reuse:

- `Run Profile (Export / Import)` allows downloading/importing exact builder settings.
- Saved profiles are written under `results/ui_profiles/*.json`.

Error recovery hints:

- API failures in Run Builder are categorized (connectivity, validation, auth scope, backend failure)
  and shown with direct recovery guidance.

UI comparison walkthrough:

```bash
photonstrust run configs/quickstart/qkd_quick_smoke.yml --output results/compare_a
photonstrust run configs/demo1_nir_795.yml --output results/compare_b
streamlit run ui/app.py
```

In `Run Registry`, set `Results directory` to `results`, select at least two
runs, and verify delta metrics appear.

Baseline decision workflow:

- In `Run Registry`, set `Project ID for baseline promotion`.
- Promote a selected run as baseline.
- Select a candidate run and review recommendation (`promote` or `hold`) before
  promoting candidate baseline.
- Baseline state persists in `results/ui_product_state/state.json`.

UI telemetry events are written to:

`results/ui_metrics/events.jsonl`

PDF reports:

```bash
pip install -e .[pdf]
```

Full-fidelity backends:

```bash
pip install -e .[qutip,qiskit]
```

QuTiP parity lane:

```bash
pip install -e .[dev,qutip]
python scripts/run_qutip_parity_lane.py
```

Artifacts are written to `results/qutip_parity/` (`.json` + `.md`).
Use `--strict` to enforce parity thresholds as a fail-closed gate.

Day-60 orbit provider parity lane (skyfield vs poliastro, optional orekit reference):

```bash
python scripts/run_orbit_provider_parity.py \
  configs/satellite/eagle1_analog_berlin.yml \
  configs/satellite/eagle1_analog_snspd.yml \
  --output-dir results/orbit_provider_parity

python scripts/run_orbit_provider_parity.py \
  configs/satellite/micius_analog.yml \
  --include-orekit \
  --strict \
  --output-dir results/orbit_provider_parity_strict
```

The parity lane writes JSON artifacts to the output dir and prints a compact JSON summary on stdout.

Day-90 deterministic distributed + optimizer lanes:

```bash
pip install -e .[dev,optuna,ray]

python scripts/run_satellite_chain_sweep.py \
  configs/satellite/eagle1_analog_berlin.yml \
  configs/satellite/eagle1_analog_snspd.yml \
  --backend local \
  --max-workers 1 \
  --seed 42 \
  --max-retries 1 \
  --output-root results/satellite_chain_sweep

python scripts/run_satellite_chain_optuna.py \
  configs/satellite/eagle1_analog_berlin.yml \
  --n-trials 8 \
  --seed 42 \
  --output-dir results/satellite_chain_optuna \
  --tracking-mode local_json

python scripts/replay_satellite_chain_reports.py \
  --sweep-report results/satellite_chain_sweep/satellite_chain_sweep.json \
  --optuna-report results/satellite_chain_optuna/satellite_chain_optuna_report.json

python scripts/release/release_gate_check.py --quick
```

Optional MLflow and Prefect lanes:

```bash
pip install -e .[dev,optuna,mlflow,prefect]

python scripts/run_satellite_chain_optuna.py \
  configs/satellite/eagle1_analog_berlin.yml \
  --n-trials 5 \
  --seed 42 \
  --tracking-mode mlflow

python scripts/run_prefect_flow.py --flow satellite --mode local --output-dir results/prefect_local
python scripts/run_prefect_flow.py --flow satellite --mode prefect --output-dir results/prefect_prefect
```

CI + tests:

```bash
pip install -e .[dev]
python scripts/validation/ci_checks.py
```

Day-30 integrity baseline (lint/hooks/runtime-contract checks + DVC stages):

```bash
pip install -e .[dev,dvc]
pre-commit install
pre-commit run --all-files
python scripts/check_model_metadata_contract.py
python scripts/check_hardcoded_physics_constants.py
dvc repro rc_baseline_lock open_benchmark_index
```

Regression baselines + canonical validation harness:

```bash
python scripts/generate_baselines.py
python scripts/generate_phase41_canonical_baselines.py
pytest tests/test_regression_baselines.py tests/test_phase41_canonical_baselines.py tests/test_validation_harness.py
python scripts/validation/check_benchmark_drift.py
python scripts/validation/run_validation_harness.py --output-root results/validation
```

Open benchmarks (shareable bundles) + repro packs:

```bash
python scripts/validation/check_open_benchmarks.py
python scripts/generate_repro_pack.py configs/quickstart/qkd_quick_smoke.yml results/repro_pack_demo1_quick_smoke
python scripts/validation/validate_recent_research_examples.py
python scripts/validation/compare_recent_research_benchmarks.py
```

Measurement bundles (ingestion + opt-in artifact packs):

```bash
python scripts/ingest_measurement_bundle.py tests/fixtures/measurement_bundle_demo/measurement_bundle.json --open-root results/measurements_open_demo
python scripts/publish_artifact_pack.py tests/fixtures/measurement_bundle_demo/measurement_bundle.json results/artifact_pack_demo
```

Golden report snapshots:

```bash
python scripts/generate_golden_report.py
pytest tests/test_golden_report.py
```

Release gate:

```bash
python scripts/release/release_gate_check.py
```

Production readiness (isolated + fail-closed):

```bash
python scripts/production_readiness_check.py --recreate-venv
```

This command bootstraps a repo-local isolated environment (`.venv.production`),
installs with `requirements/runtime.lock.txt` constraints, runs CI/release/runtime
checks (including strict QuTiP parity + strict Qiskit lane), and refreshes +
verifies the signed release gate packet artifacts.

PIC foundry readiness preflight automation:

```bash
python scripts/init_pic_gate_b_measurement_templates.py --root datasets/measurements/private --rc-id rc_missing_data_2026_03_03 --force
python scripts/build_pic_gate_b_packet.py --run-dir results/pic_readiness/run_pkg --release-candidate rc_missing_data_2026_03_03 --open-root results/pic_readiness/measurements_open --artifact-root results/pic_readiness/artifact_packs --b1-bundle datasets/measurements/private/rc_missing_data_2026_03_03/b1_insertion_loss/measurement_bundle.json --b2-bundle datasets/measurements/private/rc_missing_data_2026_03_03/b2_resonance/measurement_bundle.json --b4-bundle datasets/measurements/private/rc_missing_data_2026_03_03/b4_delay_rc/measurement_bundle.json --output results/pic_readiness/gate_b/packet_missing_data_seeded_2026-03-03.json --overwrite-ingest
python scripts/build_pic_c_d5_packet.py --corner-report results/corner_sweep/demo_qkd_transmitter/pic_corner_sweep.json --tapeout-gate-report results/pic_readiness/tapeout_gate_report.json --decision-packet results/pic_readiness/day10_decision_packet.json --decision-packet results/pic_readiness/day10_decision_packet_repeat.json --decision-packet results/pic_readiness/day10_decision_packet_third.json --output results/pic_readiness/process_repro/pic_c_d5_packet_2026-03-03.json
python scripts/init_pic_claim_evidence_matrix.py --output results/pic_readiness/governance/claim_evidence_matrix_2026-03-03.json --release-candidate rc_missing_data_2026_03_03 --force
python scripts/init_pic_gate_e_metrics_templates.py --output-dir results/pic_readiness/governance --release-candidate rc_missing_data_2026_03_03 --force
python scripts/build_pic_gate_e_packet.py --claim-matrix results/pic_readiness/governance/claim_evidence_matrix_2026-03-03.json --ci-history-json results/pic_readiness/governance/ci_history_metrics_2026-03-03.json --triage-metrics-json results/pic_readiness/governance/triage_metrics_2026-03-03.json --output results/pic_readiness/governance/pic_gate_e_packet_2026-03-03.json --e2-min-runs 3 --e2-sla-seconds 600
python scripts/build_pic_readiness_scorecard.py --tapeout-gate results/pic_readiness/tapeout_gate_report.json --gate-b results/pic_readiness/gate_b/packet_missing_data_seeded_2026-03-03.json --gate-cd5 results/pic_readiness/process_repro/pic_c_d5_packet_2026-03-03.json --gate-e results/pic_readiness/governance/pic_gate_e_packet_2026-03-03.json --output results/pic_readiness/scorecard/pic_readiness_scorecard_2026-03-03.json
python scripts/build_pic_preflight_policy_packet.py --output results/pic_readiness/policy/pic_preflight_policy_packet_2026-03-03.json --run-id pic_preflight_2026-03-03
python scripts/release/sign_release_gate_packet.py --packet results/pic_readiness/policy/pic_preflight_policy_packet_2026-03-03.json --signature-output results/pic_readiness/policy/pic_preflight_policy_packet_2026-03-03.ed25519.sig.json --private-key results/pic_readiness/policy/pic_preflight_policy_packet_2026-03-03.private.pem --public-key results/pic_readiness/policy/pic_preflight_policy_packet_2026-03-03.public.pem --generate-keypair --key-id pic_preflight_policy_packet_2026-03-03
python scripts/release/verify_release_gate_packet_signature.py --packet results/pic_readiness/policy/pic_preflight_policy_packet_2026-03-03.json --signature results/pic_readiness/policy/pic_preflight_policy_packet_2026-03-03.ed25519.sig.json --public-key results/pic_readiness/policy/pic_preflight_policy_packet_2026-03-03.public.pem
python scripts/build_pic_external_data_manifest.py --gate-b results/pic_readiness/gate_b/packet_missing_data_seeded_2026-03-03.json --gate-e results/pic_readiness/governance/pic_gate_e_packet_2026-03-03.json --rc-id rc_next --output results/pic_readiness/handoff/pic_required_external_data_manifest_2026-03-03.json
python scripts/build_pic_integration_task_board.py --manifest results/pic_readiness/handoff/pic_required_external_data_manifest_2026-03-03.json --output-json results/pic_readiness/handoff/pic_integration_task_board_in_progress_2026-03-03.json --output-csv results/pic_readiness/handoff/pic_integration_task_board_in_progress_2026-03-03.csv --default-status in_progress --start-date 2026-03-03 --target-step-days 2
python scripts/refresh_pic_handoff_daily.py --gate-b results/pic_readiness/gate_b/packet_missing_data_seeded_2026-03-03.json --gate-e results/pic_readiness/governance/pic_gate_e_packet_2026-03-03.json --rc-id rc_next --manifest-output results/pic_readiness/handoff/pic_required_external_data_manifest_2026-03-03.json --task-board-json results/pic_readiness/handoff/pic_integration_task_board_in_progress_2026-03-03.json --task-board-csv results/pic_readiness/handoff/pic_integration_task_board_in_progress_2026-03-03.csv --task-status in_progress --start-date 2026-03-03 --target-step-days 2
```

Reliability card spec:

See `reports/specs/reliability_card_v1.md`.

Release notes:

See `reports/specs/release_notes_v0.1.0.md` and `CHANGELOG.md`.

Research plan:

See `docs/research/00_overview.md` for the full research bundle.

For granular execution detail, use `docs/research/deep_dive/00_deep_dive_index.md`.
For delivery operations, use `docs/research/deep_dive/12_execution_program_24_weeks.md`.
Default operating protocol: `docs/research/deep_dive/15_research_to_build_protocol.md`.

Recent phased rollout completions (see `docs/operations/phased_rollout/README.md`):
- Phase 37: GDS + KLayout pack enablement (PATH emission + PDK-defaulted DRC-lite settings)
- Phase 38: Config validation + CLI `--validate-only`
- Phase 39: QKD physics trust gates (PLOB sanity; seeded uncertainty; Kasten-Young airmass)
- Phase 40: Evidence bundle signing (Ed25519 signing + verification; signature artifact schema)
- Phase 41: Fiber QKD deployment realism pack (canonical presets + drift baselines + applicability notes)
- Phase 42: Reliability card v1.1 (evidence tiers + operating envelope + standards anchors)
- Phase 43: MDI-QKD + TF/PM-QKD protocol surfaces (analytical models + dispatch)
- Phase 44: QKD fidelity foundations (Poisson noise, dead time model, polarization-as-visibility)
- Phase 45: Raman coexistence effective-length model (attenuation-aware Raman counts)
- Phase 46: BBM92 coincidence model (multi-pair + coincidence accidentals)
Week 1 kickoff artifacts: `docs/operations/week1/`.
Program completion report: `docs/operations/program_completion_report_2026-02-12.md`.
Milestone acceptance bundle: `reports/specs/milestones/`.
Contribution workflow is defined in `CONTRIBUTING.md`.

Outputs are written to `results/` by default.

Each run writes a `run_registry.json` at the results root for UI browsing.

The demo configs set `physics_backend: qutip` for emitter-cavity sources. If
QuTiP is not installed, PhotonTrust falls back to the analytic model.
