# Research Brief

## Metadata
- Work item ID: PT-PHASE-07
- Title: Open benchmark ingestion and external reproducibility package
- Authors: PhotonTrust core team
- Date: 2026-02-13
- Related modules (expected):
  - `photonstrust/datasets/`
  - `scripts/validation/check_benchmark_drift.py`
  - `scripts/release/release_gate_check.py`
  - report/provenance exports (`photonstrust/report.py`, `photonstrust/sweep.py`)

## 1) Problem and motivation
PhotonTrust's trust moat depends on the ability for third parties to:
- validate that benchmark claims are stable (drift controlled), and
- reproduce results from an exported artifact bundle without private context.

Today, PhotonTrust has baseline drift checks, but the system is not yet designed
to:
- ingest external benchmark result bundles (from literature, labs, or partner
  tooling), and
- produce a standardized "repro pack" that is sufficient for independent replay
  and audit.

This limits academic adoption (reproducibility expectations) and slows
industrial pilots (audit evidence requirements).

## 2) Research questions and hypotheses
- RQ1: What is the minimal public benchmark artifact format that supports drift
  checks, provenance, and versioned scenario semantics?
- RQ2: What is the minimal reproducibility pack that lets an external reviewer
  rerun a scenario and validate outputs, without requiring the managed service?
- RQ3: How do we separate "public/open benchmarks" from "customer-private
  evidence bundles" without leaking IP?

Hypotheses:
- H1: A machine-readable benchmark manifest + strict schema validation is enough
  to make benchmark ingestion safe and automatable.
- H2: A small, standardized repro pack (config + pins + replay script + expected
  outputs) is enough to support external verification without complex tooling.

## 3) Related work (conceptual anchors)
- FAIR principles for metadata and reuse.
- ACM artifact badging levels for availability and result validation.
- Software supply chain provenance concepts (SLSA/Sigstore) for artifact
  integrity, as a future extension.

## 4) Method design (proposed)

### 4.1 Benchmark ingestion surface
- Define a benchmark bundle format:
  - `benchmark_manifest.json` with:
    - `scenario_id`, scenario config, expected outputs, tolerances,
    - engine version constraints, schema versions,
    - optional citation metadata (paper, DOI, lab notebook ref).
- Validate against JSON schema and store under a versioned folder:
  - `benchmarks/open/<benchmark_id>/...`

### 4.2 External reproducibility pack
- Define a pack layout:
  - `repro_pack/`
  - `repro_pack/README.md` (how to replay)
  - `repro_pack/config.yml`
  - `repro_pack/expected/` (expected outputs and tolerances)
  - `repro_pack/env/` (pinned requirements or lockfile)
  - `repro_pack/run.ps1` and `repro_pack/run.sh` (portable replay entrypoints)
  - `repro_pack/provenance.json` (hashes, versions, seeds)

## 5) Risk and failure analysis
- Risk: accidentally ingesting untrusted or malformed benchmarks leads to false
  confidence or unstable CI.
  - Mitigation: strict schema validation, version constraints, and explicit
    "evidence tier" labeling.
- Risk: reproducibility packs leak sensitive customer information.
  - Mitigation: separate "open" and "private" pack modes; a redaction step and
    allow-list metadata policy.

## 6) Acceptance criteria
- Benchmark bundles validate against schema and can be compared against engine
  outputs with declared tolerances.
- Repro pack can be executed on a clean machine to regenerate outputs within
  tolerance (documented procedure).
- CI gates can run "open benchmark" drift checks deterministically.
- No breaking change to existing configs and result formats.

## 7) Decision
- Decision: Planned (phase initiated).
- Next step: implementation plan + build execution.

