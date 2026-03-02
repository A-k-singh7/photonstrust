# PhotonTrust
[![tapeout-gate](https://github.com/photonstrust/photonstrust/actions/workflows/tapeout-gate.yml/badge.svg?branch=main)](https://github.com/photonstrust/photonstrust/actions/workflows/tapeout-gate.yml)
[![cv-quick-verify](https://github.com/photonstrust/photonstrust/actions/workflows/cv-quick-verify.yml/badge.svg?branch=main)](https://github.com/photonstrust/photonstrust/actions/workflows/cv-quick-verify.yml)

PhotonTrust is an open-source digital twin and reliability card generator for
photonic quantum links. This MVP focuses on QKD key-rate realism across Near-IR,
O-band, and C-band configurations, including direct-link and relay-based
protocol-family surfaces.

## Quick start

```bash
pip install -e .
pip install -e .[qutip]
photonstrust run configs/demo1_default.yml
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
photonstrust run configs/demo11_orbit_pass_envelope.yml --output results/orbit_demo11
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
py scripts/run_api_server.py --reload
cd web
npm ci
npm run dev
```

Quick smoke run:

```bash
photonstrust run configs/demo1_quick_smoke.yml --output results/smoke_quick
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
photonstrust run configs/calibration_example.yml
photonstrust run configs/optimization_example.yml
```

`configs/calibration_example.yml` includes diagnostics quality gates that can
enforce calibration acceptance thresholds during CLI runs.

Benchmark datasets:

```bash
python -m photonstrust.datasets.generate datasets/benchmarks/metro_qkd.yml results/benchmarks/metro_qkd
python -m photonstrust.datasets.generate datasets/benchmarks/repeater_chain.yml results/benchmarks/repeater_chain
python -m photonstrust.datasets.generate datasets/benchmarks/teleportation_sla.yml results/benchmarks/teleportation
```

Streamlit dashboard:

```bash
pip install -e .[ui]
uvicorn photonstrust.api.server:app --host 127.0.0.1 --port 8000
streamlit run ui/app.py
```

Week 4 product packaging (single-command local start + pilot demo):

```bash
pip install -e .[api,ui]
python scripts/start_product_local.py
python scripts/run_product_pilot_demo.py --project-id pilot_demo_week4
python scripts/product_readiness_gate.py --spawn-api
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
photonstrust run configs/demo1_quick_smoke.yml --output results/compare_a
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

CI + tests:

```bash
pip install -e .[dev]
python scripts/ci_checks.py
```

Regression baselines + canonical validation harness:

```bash
python scripts/generate_baselines.py
python scripts/generate_phase41_canonical_baselines.py
pytest tests/test_regression_baselines.py tests/test_phase41_canonical_baselines.py tests/test_validation_harness.py
python scripts/check_benchmark_drift.py
python scripts/run_validation_harness.py --output-root results/validation
```

Open benchmarks (shareable bundles) + repro packs:

```bash
python scripts/check_open_benchmarks.py
python scripts/generate_repro_pack.py configs/demo1_quick_smoke.yml results/repro_pack_demo1_quick_smoke
python scripts/validate_recent_research_examples.py
python scripts/compare_recent_research_benchmarks.py
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
python scripts/release_gate_check.py
```

Production readiness (isolated + fail-closed):

```bash
python scripts/production_readiness_check.py --recreate-venv
```

This command bootstraps a repo-local isolated environment (`.venv.production`),
installs with `requirements/runtime.lock.txt` constraints, runs CI/release/runtime
checks (including strict QuTiP parity + strict Qiskit lane), and refreshes +
verifies the signed release gate packet artifacts.

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
