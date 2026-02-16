# Phase 22 Research Brief: Project Registry + Approvals (v0.1)

## Metadata
- Work item ID: PT-PHASE-22
- Date: 2026-02-13
- Objective: Add project-level grouping and review approvals on top of the existing run registry/diff.

## Why This Phase Exists (trust + business)
PhotonTrust already has:
- a run registry (`GET /v0/runs`),
- immutable per-run manifests (`run_manifest.json`),
- served artifacts (`GET /v0/runs/{run_id}/artifact`), and
- bounded diffs (`POST /v0/runs/diff`, including `outputs_summary` scope).

What is missing for real teams (academic labs and companies) is governance:
- "Which runs belong to this project?"
- "Which run is approved as the current reference for a paper, design review, or customer report?"
- "Who approved it, when, and why?"

Without a project registry + approvals log, review workflows happen out-of-band (Slack/email),
which breaks traceability and weakens the trust moat.

## External Anchors (how real systems model this)

### MLflow: experiments, tracking, and registry governance
MLflow's ecosystem distinguishes:
- tracking (runs, artifacts, metadata), and
- registry/governance (promoting versions, adding metadata and review signals).

Primary anchors:
- MLflow Tracking (runs + artifacts):
  https://mlflow.org/docs/latest/ml/tracking/
- MLflow Model Registry (registry semantics and governance patterns):
  https://mlflow.org/docs/latest/ml/model-registry/

Relevance to PhotonTrust:
- "Project" in PhotonTrust should behave like an experiment namespace: grouping runs with shared intent.
- "Approval" should behave like registry promotion: an auditable state transition, not a silent overwrite.

### W&B: projects + artifacts as first-class collaboration primitives
W&B emphasizes projects and artifacts for sharing and comparing results across runs.

Primary anchor:
- W&B Artifacts:
  https://docs.wandb.ai/guides/artifacts/

Relevance to PhotonTrust:
- Approvals should reference a run and its artifact set, not just a metric snapshot.
- Small, stable "summary" diffs complement large artifact browsing.

### OpenLineage: event-style audit trails (runs as events with facets)
OpenLineage models lineage and auditability via events and metadata facets.

Primary anchor:
- OpenLineage documentation:
  https://openlineage.io/docs/

Relevance to PhotonTrust:
- An append-only, event-style log (JSONL) is a pragmatic v0.1 audit trail for approvals.

### Supply chain provenance: future cryptographic attestation path (not required in v0.1)
For higher assurance, the run manifest + outputs can be attested (in-toto/SLSA) and verified (Sigstore).

Primary anchors:
- SLSA provenance spec:
  https://slsa.dev/spec/v1.1/provenance
- in-toto attestation repository:
  https://github.com/in-toto/attestation
- Sigstore cosign attestations (verification):
  https://docs.sigstore.dev/cosign/verifying/attestation/

Relevance to PhotonTrust:
- Phase 22 should keep data structures compatible with future attestations (stable IDs, hashes, and append-only logs).

## Scope Constraints (v0.1)
- Local-dev, filesystem-backed implementation (no DB dependency).
- Strict input validation (project IDs) and path safety (no traversal).
- Minimal API surface for:
  - listing projects inferred from runs,
  - filtering runs by project,
  - recording approvals (append-only log),
  - listing approvals.

Non-goals for this phase:
- RBAC, org/user management, or OAuth.
- Cryptographic signing or remote transparency logs.
- Deletion/rewriting of approval history (keep append-only).
