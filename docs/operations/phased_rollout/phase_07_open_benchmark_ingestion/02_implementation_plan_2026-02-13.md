# Implementation Plan

## Metadata
- Work item ID: PT-PHASE-07
- Scope owner: Benchmarking + reproducibility
- Target milestone: Open benchmark ingestion + repro pack v0.1

## 1) Scope and non-scope

In scope:
- Add a versioned benchmark bundle format + schema validation.
- Add an ingestion workflow for open benchmark bundles.
- Add an external reproducibility pack generator for a single scenario run.
- Add CI-capable checks for open benchmark drift with tolerances.

Out of scope (later phases):
- Signed provenance (Sigstore/cosign) for artifact packs.
- Full multi-tool benchmark import (NetSquid/SeQUeNCe direct adapters).
- Hosted public benchmark registry service.

## 2) Design decisions (v0.1)
- Benchmark bundle is JSON-first and schema-validated.
- Benchmark tolerance is explicit per metric (relative + absolute).
- Repro pack is filesystem-based and runnable without network dependencies.
- Public/open bundles are stored separately from customer/private bundles.

## 3) File-level build plan

### Step 1: Schema definitions
- Add:
  - `schemas/photonstrust.benchmark_bundle.v0.schema.json`
  - `schemas/photonstrust.repro_pack_manifest.v0.schema.json`
- Tests:
  - extend `tests/test_schema_validation.py` to validate the new schemas.

### Step 2: Benchmark ingestion module
- Add new module:
  - `photonstrust/benchmarks/ingest.py`
  - `photonstrust/benchmarks/__init__.py`
- Responsibilities:
  - validate bundle against schema
  - copy bundle into `datasets/benchmarks/open/<id>/`
  - write an `index.json` registry of known open benchmarks
- Tests:
  - `tests/test_benchmark_ingestion.py`

### Step 3: Open benchmark runner + drift checks
- Add:
  - `scripts/validation/check_open_benchmarks.py` (runs all open benchmarks; fails on drift)
- Integrate:
  - add this as an optional check in `scripts/release/release_gate_check.py`
    (initially non-blocking, then promote to blocking once seeded).
- Tests:
  - minimal fixture benchmark bundle and deterministic comparison tests.

### Step 4: External repro pack generator
- Add:
  - `scripts/generate_repro_pack.py`
- Behavior:
  - input: config path + output dir
  - output: repro pack layout with pins, replay script(s), provenance,
    and expected outputs/tolerances.
- Tests:
  - `tests/test_repro_pack_generation.py` validates structure + manifest fields.

### Step 5: Documentation
- Update research docs:
  - `docs/research/08_benchmarks_and_datasets.md`
  - `docs/research/07_reliability_card_standard.md` (artifact URIs and tiers)
  - `docs/research/15_platform_rollout_plan_2026-02-13.md` (link Phase 07 outputs)
- Add a user-facing doc:
  - `docs/operations/phased_rollout/phase_07_open_benchmark_ingestion/`

## 4) Validation plan
- Unit tests:
  - benchmark bundle schema validation passes/fails as expected.
  - ingestion writes stable registry output.
  - repro pack generator produces complete pack with deterministic hashes.
- Integration checks:
  - run a repro pack and compare to expected outputs within tolerance.
  - open benchmark drift script passes on baseline fixtures.

## 5) Done criteria
- [x] New schemas added and validated in tests
- [x] Ingestion path implemented + unit tests
- [x] Open benchmark drift script implemented + wired into release gates
- [x] Repro pack generator implemented + unit tests
- [x] Phase 07 build + validation reports completed
