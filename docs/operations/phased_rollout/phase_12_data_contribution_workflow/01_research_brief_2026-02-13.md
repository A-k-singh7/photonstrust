# Research Brief

## Metadata
- Work item ID: PT-PHASE-12
- Title: Data contribution workflow v0.1 (academic + industry safe)
- Authors: PhotonTrust core team
- Date: 2026-02-13
- Related modules (planned/expected):
  - `schemas/photonstrust.measurement_bundle.v0.schema.json` (new)
  - `photonstrust/measurements/` (new; ingestion + validation)
  - `scripts/` (new; redaction scans + publish pack)

## 1) Problem and motivation
PhotonTrust's defensible moat depends on continuous ingestion of new evidence:
- measurement datasets used to calibrate compact models, and
- reproducible scenario artifacts that can be replayed and audited.

To support both academic openness and industry safety, PhotonTrust needs a
structured data contribution workflow that is:
- consent-driven (explicit share scope and restrictions),
- IP-safe (no accidental proprietary files),
- privacy-safe (no personal data leaks),
- reproducible (checksums, provenance, schema validation),
- automatable (local validation tools that run before publishing).

This phase defines and implements a minimal "measurement bundle" contract and
tooling to ingest, validate, and optionally publish artifact packs.

## 2) Research questions
- RQ1: What is the minimal dataset schema that supports calibration linkage
  without forcing one lab format?
- RQ2: How do we encode consent, IP classification, and export-control flags so
  they are machine-readable and enforced in tooling?
- RQ3: What local validation and redaction scans prevent the most common
  "oops" failures (keys, credentials, private keys, internal paths)?
- RQ4: How do we package artifacts for academic sharing so they align with
  reproducibility expectations (checksums, provenance, replay pointers)?

## 3) Method design (v0.1)

### 3.1 Measurement bundle manifest
Define a single JSON manifest (`measurement_bundle.json`) that declares:
- dataset identity and version,
- license and share level,
- provenance fields (non-personal, high level),
- list of data files with sha256 checksums and content types,
- links to related configs/calibration bundles/graphs (optional).

### 3.2 Registry ingestion
Provide an ingestion tool that:
- validates schema,
- verifies file hashes,
- copies the manifest and referenced files into a local registry under
  `datasets/measurements/open/<dataset_id>/`,
- updates an `index.json` for browsing and drift control.

### 3.3 Publish artifact pack (opt-in)
Provide a packaging tool that:
- runs redaction scans,
- produces a shareable "artifact pack" directory (and optional zip),
- records scan results and provenance in a pack manifest.

Publishing is explicit and opt-in; nothing is uploaded automatically.

### 3.4 Redaction and privacy checks
Implement conservative local scans that fail closed by default:
- detect private keys and common token formats in text files,
- block known sensitive filenames (e.g., `.env`, `id_rsa`, `*.pem`),
- require an explicit override flag to proceed if risks are detected.

## 4) Primary references (reporting + dataset governance anchors)
- FAIR principles (findable, accessible, interoperable, reusable metadata):
  https://doi.org/10.1038/sdata.2016.18
- Datasheets for Datasets (dataset provenance and use constraints):
  https://arxiv.org/abs/1803.09010
- ACM Artifact Review and Badging (reproducibility expectations for published artifacts):
  https://www.acm.org/publications/policies/artifact-review-and-badging-current

## 5) Acceptance criteria
- Measurement bundle schema exists and is validated in tests.
- Ingestion tool exists and maintains an on-disk open registry + index.
- Publish pack tool exists and runs redaction scans before packaging.
- Validation includes checks that secrets and sensitive files are rejected by default.
- `py -m pytest -q` and release gate pass.

## 6) Decision
- Decision: Proceed.

