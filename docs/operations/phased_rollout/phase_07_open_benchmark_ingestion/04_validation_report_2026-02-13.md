# Validation Report

## Metadata
- Work item ID: PT-PHASE-07
- Date: 2026-02-13
- Reviewer: Internal QA

## Status
- Completed (validation gates passed).

## 1) Test evidence
- Full suite: `py -m pytest -q` -> `51 passed`
- Schema validation:
  - `tests/test_schema_validation.py` validates:
    - `schemas/photonstrust.benchmark_bundle.v0.schema.json`
    - `schemas/photonstrust.repro_pack_manifest.v0.schema.json`
- Ingestion and repro pack tests:
  - `tests/test_benchmark_ingestion.py` -> PASS
  - `tests/test_repro_pack_generation.py` -> PASS

## 2) Script-level validation
- Open benchmark drift check:
  - `py scripts/validation/check_open_benchmarks.py` -> PASS
- Release gate:
  - `py scripts/release/release_gate_check.py --output results/release_gate/phase07_release_gate_report.json` -> PASS

## 3) Repro pack replay (manual)
- Generated:
  - `py scripts/generate_repro_pack.py configs/demo1_quick_smoke.yml results/repro_pack_demo1_quick_smoke`
- Replayed + verified:
  - `powershell -ExecutionPolicy Bypass -File results/repro_pack_demo1_quick_smoke/run.ps1` -> PASS

## 4) Acceptance criteria check
- Benchmark bundles are schema-validated: PASS
- Open benchmark ingestion registry exists and is machine-readable: PASS
- Drift check is automatable and CI-capable: PASS
- External reproducibility pack generator exists and runs end-to-end: PASS

## 5) Known limitations (v0)
- Only `kind: qkd_sweep` is supported by the benchmark runner.
- No signed provenance/attestation in v0 (planned future work).

