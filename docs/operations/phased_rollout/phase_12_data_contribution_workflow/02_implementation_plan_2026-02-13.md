# Implementation Plan

## Metadata
- Work item ID: PT-PHASE-12
- Title: Data contribution workflow v0.1 (academic + industry safe)
- Date: 2026-02-13

## 1) Deliverables

### 1.1 Schemas
- Measurement bundle schema:
  - `schemas/photonstrust.measurement_bundle.v0.schema.json`
- Publish pack manifest schema (minimal):
  - `schemas/photonstrust.artifact_pack_manifest.v0.schema.json`

### 1.2 Code: measurements registry + ingestion
- Add module(s):
  - `photonstrust/measurements/__init__.py`
  - `photonstrust/measurements/ingest.py`
  - `photonstrust/measurements/schema.py`
  - `photonstrust/measurements/redaction.py`

### 1.3 Scripts (local tooling)
- Add:
  - `scripts/ingest_measurement_bundle.py <bundle.json>`
  - `scripts/publish_artifact_pack.py <bundle.json> <output_dir>`

### 1.4 Test fixtures + tests
- Add fixtures:
  - `tests/fixtures/measurement_bundle_demo/measurement_bundle.json`
  - `tests/fixtures/measurement_bundle_demo/data/demo_measurements.csv`
  - `tests/fixtures/measurement_bundle_bad_secret/measurement_bundle.json`
  - `tests/fixtures/measurement_bundle_bad_secret/data/leak.txt` (contains a secret-like token pattern)
- Add tests:
  - `tests/test_measurement_ingestion.py`
  - `tests/test_redaction_scan.py`

### 1.5 Documentation updates
- Add Phase 12 rollout artifacts (this folder).
- Update:
  - `docs/research/15_platform_rollout_plan_2026-02-13.md`
  - `docs/research/14_physics_core_open_science_master_plan_2026-02-12.md`
  - `docs/research/08_benchmarks_and_datasets.md`
  - `docs/operations/phased_rollout/README.md`
  - `docs/operations/README.md`

## 2) Measurement bundle contract (v0.1)

### Minimal fields
- `schema_version`: string ("0")
- `dataset_id`: string (stable ID)
- `kind`: string (e.g., `pic_component_measurements`, `free_space_measurements`)
- `title`: string
- `created_at`: RFC3339 date-time string
- `license`: string (SPDX identifier preferred)
- `share_level`: enum (`private`, `internal`, `public`)
- `restrictions`: object with boolean flags (e.g., `contains_personal_data`, `contains_export_controlled`)
- `files`: list of file entries:
  - `path` (relative path inside bundle folder)
  - `sha256`
  - `content_type` (e.g., `text/csv`)
  - `description` (optional)
- Optional linkage:
  - `links.calibration_bundle_id`
  - `links.graph_id`
  - `links.config_hash`

### Ingestion rules
- validate schema
- verify every file exists and sha256 matches
- copy bundle into `datasets/measurements/open/<dataset_id>/`
- upsert registry index at `datasets/measurements/open/index.json`

## 3) Publish pack contract (v0.1)
Artifact pack is an opt-in shareable directory (and optional zip) that includes:
- the measurement bundle manifest,
- referenced data files,
- a pack manifest with scan results and provenance.

## 4) Redaction/secret scan rules (v0.1)
- Blocklist filenames:
  - `.env`, `id_rsa`, `*.pem`, `*.p12`, `*.key`
- Text scan patterns (conservative subset):
  - `BEGIN PRIVATE KEY`
  - AWS access key ID pattern `AKIA[0-9A-Z]{16}`
  - GitHub token prefix `ghp_`
- Fail closed by default; require explicit `--allow-risk` to override.

## 5) Validation gates
- Unit tests:
  - `py -m pytest -q`
- Release gate:
  - `py scripts/release_gate_check.py --output results/release_gate/phase12_release_gate_report.json`
- Manual smoke:
  - `python scripts/ingest_measurement_bundle.py tests/fixtures/measurement_bundle_demo/measurement_bundle.json`
  - `python scripts/publish_artifact_pack.py tests/fixtures/measurement_bundle_demo/measurement_bundle.json results/artifact_pack_demo`

## 6) Non-goals (explicit)
- No remote upload service in v0.1.
- No automated anonymization transforms in v0.1 (only scans and policy flags).
- No full dataset governance workflow UI (planned).

