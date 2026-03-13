# Benchmarks and Datasets

This document defines benchmark scenarios and dataset generation rules.

## Benchmark Scenarios
- Metro QKD (20-80 km)
- Repeater chain (200-600 km)
- Teleportation SLA (50-200 km)
- Source benchmarking (short link)

## Dataset Schema
- scenario_id, config, results, metadata
- metadata includes seed and version

## Baselines
- Toy noise vs physics-twin outputs
- Regression baselines stored in tests/fixtures

## Open benchmarks (Phase 07)

PhotonTrust distinguishes between:
- regression baselines (developer guardrails under `tests/fixtures/`), and
- open benchmarks (shareable, schema-validated benchmark bundles under
  `datasets/benchmarks/open/`).

### Benchmark bundle format (v0)
- JSON schema:
  - `schemas/photonstrust.benchmark_bundle.v0.schema.json`
- Registry location:
  - `datasets/benchmarks/open/<benchmark_id>/benchmark_bundle.json`
  - `datasets/benchmarks/open/index.json` (machine-readable index)
- Drift check script:
  - `scripts/validation/check_open_benchmarks.py`

The bundle carries:
- the scenario config (as a config dict),
- expected key-rate curves per scenario/band (with tolerances), and
- optional environment requirements metadata.

Seeded open benchmark included in-repo:
- `datasets/benchmarks/open/open_demo_qkd_analytic_001/`

### External ingestion
Open benchmark bundles can be ingested into the registry using:
- `photonstrust.benchmarks.ingest_bundle_file(...)`

## External reproducibility packs (Phase 07)

Repro packs are a distribution-friendly artifact that combine:
- config input (`config.yml`)
- expected curves (`benchmark_bundle.json`)
- reference outputs (`reference_outputs/`)
- environment capture (`env/pip_freeze.txt`)
- replay scripts (`run.ps1`, `run.sh`) and verification helper (`verify.py`)

Generator:
- `scripts/generate_repro_pack.py <config.yml> <output_dir>`

Manifest schema:
- `schemas/photonstrust.repro_pack_manifest.v0.schema.json`

## Measurement bundles (Phase 12)

PhotonTrust also supports ingesting measurement datasets in a structured,
consent-aware way to support calibration and academic reproducibility.

### Measurement bundle format (v0)
- JSON schema:
  - `schemas/photonstrust.measurement_bundle.v0.schema.json`
- Registry location:
  - `datasets/measurements/open/<dataset_id>/measurement_bundle.json`
  - `datasets/measurements/open/index.json` (registry index)
- Ingestion script:
  - `python scripts/ingest_measurement_bundle.py <measurement_bundle.json>`

### Artifact pack publishing (opt-in, local)
- Artifact pack manifest schema:
  - `schemas/photonstrust.artifact_pack_manifest.v0.schema.json`
- Publisher script (runs conservative redaction scans before packaging):
  - `python scripts/publish_artifact_pack.py <measurement_bundle.json> <output_dir>`

## Quality Checklist
- Dataset entries reproducible
- run_registry.json built for UI

## Web Research Extension (2026-02-12)
See `12_web_research_update_2026-02-12.md` section `08 Benchmarks and datasets: governance and drift control`.

