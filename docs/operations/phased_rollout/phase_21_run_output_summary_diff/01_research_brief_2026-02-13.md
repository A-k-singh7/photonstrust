# Research Brief

## Metadata
- Work item ID: PT-PHASE-21
- Title: Run output summaries + output diff scope v0.1 (managed-service hardening, local dev)
- Authors: PhotonTrust core team
- Date: 2026-02-13
- Related modules (planned/expected):
  - `photonstrust/api/server.py`
  - `photonstrust/api/runs.py`
  - `photonstrust/orbit/pass_envelope.py`
  - `photonstrust/sweep.py`
  - `web/`

## 1) Problem and motivation

Phase 20 introduced a run browser and a run diff endpoint, but the diff is
input-only. For scientific and engineering review, input diffs alone are not
enough: reviewers need to see how the outputs changed (and whether the changes
are expected).

We need a minimal, stable "output summary" contract that:
- is safe to compute (does not re-run physics),
- is bounded (small enough for UI + API),
- is comparable (stable keys and units),
- supports domain-specific workflows for OrbitVerify and QKD link runs.

## 2) Key research questions

- RQ1: What output summary fields are universally useful across runs?
- RQ2: Should output summaries be computed at write-time (stored in the manifest)
  or computed on-demand (read artifacts and summarize)?
- RQ3: How do we keep summaries honest (no hidden heuristics, no overclaiming)?

## 3) Decision and approach

Decision (v0.1):
- Store a small `outputs_summary` block inside `run_manifest.json` at write-time
  for API-generated runs:
  - Orbit pass runs: per-case keys totals and key-rate envelope summary.
  - QKD runs: per-card key rate, QBER, and safe-use label.
- Extend `/v0/runs/diff` to support `scope=outputs_summary` in addition to
  `scope=input`.
- Extend the Runs UI to let users select diff scope.

Rationale:
- Write-time summary is deterministic and keeps diffs fast.
- Summary fields are derived from already-produced result artifacts (no new
  physics).

## 4) Acceptance criteria

- `POST /v0/orbit/pass/run` writes `outputs_summary` into the run manifest.
- `POST /v0/qkd/run` writes `outputs_summary` into the run manifest.
- `POST /v0/runs/diff` supports `scope=outputs_summary`.
- Web Runs mode supports selecting diff scope.
- Gates pass:
  - `py -m pytest -q`
  - `py scripts/release/release_gate_check.py`
  - `cd web && npm run lint`
  - `cd web && npm run build`

## 5) Non-goals

- No signed attestations or transparency log integration in v0.1.
- No domain-aware "result tolerance" semantics (e.g., statistical equivalence).
- No metric normalization across different run types.

## 6) Primary references (ecosystem anchors)

Run tracking + comparison patterns:
- MLflow Tracking (run listing, metrics, artifacts):
  https://mlflow.org/docs/latest/ml/tracking/
- Weights & Biases Artifacts (inputs/outputs to runs):
  https://docs.wandb.ai/guides/artifacts/

Provenance and attestation formats (future hardening track):
- SLSA provenance predicate (in-toto framework):
  https://slsa.dev/spec/v1.1/provenance
- in-toto Attestation Framework repository:
  https://github.com/in-toto/attestation
- Sigstore cosign attestation verification docs:
  https://docs.sigstore.dev/cosign/verifying/attestation/

