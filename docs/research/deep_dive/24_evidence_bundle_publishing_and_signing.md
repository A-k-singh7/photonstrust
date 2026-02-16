# Evidence Bundle Publishing + Signing (Phase 40 Deep Research)

Date: 2026-02-14

This document is an implementation-grade research spec for Phase 40:

- publish evidence bundles outside the repo as immutable artifacts, and
- make them tamper-evident via cryptographic signing and verifiable provenance.

It is designed to integrate with PhotonTrust's existing workflow surfaces:

- run registry + run linking (Phases 19-21)
- project approvals (Phase 22)
- evidence bundle export (Phase 35)
- evidence bundle attestation schemas (Phase 36)

The purpose is not security theater. The purpose is trust closure: a third party
can verify that a Reliability Card and its attached evidence bundle were produced
by a specific PhotonTrust version/config, and that artifacts were not modified
after export.

---

## 0) Terminology

Evidence bundle:
- a zip (or folder) export that contains:
  - run manifests and child workflow manifests,
  - referenced artifacts (JSON/YAML/plots/GDS/netlists/reports), and
  - a bundle manifest that lists hashes for all included files.

Signing:
- applying a digital signature to a blob (e.g., the bundle manifest or the zip)
  so a verifier can detect post-export modifications.

Attestation:
- structured, machine-readable statements about how something was produced.
  In practice, use an in-toto style statement with a predicate.

Supply chain integrity:
- assurance that the software used to generate artifacts is known (versioned),
  and that outputs correspond to recorded inputs.

---

## 1) Goals and Non-Goals

Goals (Phase 40):

1) Tamper-evident exports
- If any file in the bundle changes, verification fails.

2) Verifiable linkage: approval -> evidence bundle
- Project approvals should reference a signed bundle digest (or a signed manifest
  digest) so the "blessed" run is anchored to immutable evidence.

3) Works in both open-source and enterprise deployments
- Open-source: keyless signing option.
- Enterprise/on-prem: key-based signing without calling external services.

4) Minimal cryptographic surface area
- Do not invent crypto.
- Use existing tooling and well-documented formats.

Non-goals (Phase 40):

- Preventing a malicious maintainer from signing bad results.
  (Signing authenticates origin, not truth.)
- Solving all reproducibility issues (numerics, OS differences). The existing
  determinism and schema gates remain the first line.
- Shipping a complex PKI. Keep key management optional and pluggable.

---

## 2) Threat Model (Practical)

We care about these realistic failures:

1) Accidental mutation
- Someone unzips the bundle, edits a config, re-zips, and later claims it is the
  original evidence.

2) Post-hoc cherry-picking
- Someone swaps plots or summary tables in an exported pack to support a claim.

3) Artifact drift
- A card references a bundle but the bundle content changes over time.

We do not solve:

- A fully malicious signer who controls keys and publishes signatures.
  (This becomes governance: approvals + transparency + independent replay.)

---

## 3) What to Sign (Decision)

You have three practical signing options:

Option A (recommended): sign the bundle manifest

- Bundle export already produces a manifest with per-file hashes.
- Signing the manifest yields a small stable signature target.
- Verification becomes:
  - verify manifest signature
  - verify that every file hash matches the manifest

Option B: sign the entire zip

- Simple, but heavy. Any zip metadata re-ordering can break reproducible hashes
  unless you enforce deterministic zip creation.

Option C: sign each file

- Strong but operationally messy and slow.

Recommendation:

- Sign the manifest (Option A).
- Optionally also sign the zip if you need "single-blob" distribution.

---

## 4) Canonical Bundle Layout (Proposed)

Bundle root (conceptual):

```
bundle/
  bundle_manifest.json
  workflow_report.json
  runs/
    <run_id>/
      run_manifest.json
      artifacts/
        reliability_card.json
        report.html
        report.pdf
        ...
  signatures/
    bundle_manifest.sig
    bundle_manifest.attestation.json
```

Notes:

- `bundle_manifest.json` must include SHA-256 hashes of every file in the bundle
  except files under `signatures/` (or include them with a second-stage manifest).
- `workflow_report.json` (Phase 36) should already summarize and link child runs.

---

## 5) Manifest Design: Hashes + Identity + Replay Link

Minimum fields for `bundle_manifest.json`:

- bundle_format_version
- created_at
- photonstrust_version and commit (if available)
- root_run_id
- files[] with:
  - path
  - sha256
  - size_bytes
  - media_type (optional)

Additional fields that make verification and governance stronger:

- schema_versions:
  - reliability_card_schema
  - workflow_report_schema
  - run_manifest_schema

- environment_summary:
  - python_version
  - platform
  - core dependency versions (numpy/scipy/qutip/qiskit)
  - optional SBOM pointer

- provenance:
  - config_hash
  - seed(s)
  - command line that generated the run (or equivalent canonical form)

Rationale:
- Hashes give integrity.
- Identity fields make the bundle understandable without network access.
- Replay link fields allow external re-execution checks.

---

## 6) Signing Approaches

PhotonTrust should support two modes:

### 6.1 Keyless signing (open-source default)

Use Sigstore for developer-friendly signing that integrates with transparency
logs.

Practical shape:

- obtain an ephemeral identity (OIDC) when signing
- produce a signature + certificate chain that a verifier can check

Pros:
- no key distribution
- strong public audit trail if you use transparency logging

Cons:
- requires network access
- enterprise/on-prem may not allow external calls

### 6.2 Key-based signing (enterprise/on-prem default)

Use a customer-managed key stored and used in their environment.

Pros:
- offline
- aligns with regulated environments

Cons:
- key management is their problem; PhotonTrust must make it easy but not own it

---

## 7) Attestation: What to Claim (and What Not to Claim)

The signature authenticates the manifest.
The attestation explains what the manifest corresponds to.

Proposed attestation statement claims:

- subject: bundle_manifest.json (sha256)
- predicateType: one of
  - "photonstrust.evidence_bundle.publish.v0"
  - or a standard predicate if you adopt an in-toto/SLSA predicate form

Predicate should include:

- root_run_id
- root_config_hash
- evidence_bundle_version
- code identity:
  - photonstrust package version
  - git commit (if known)
- generation command / mode:
  - preview vs certification
  - flags controlling determinism

Explicitly do NOT claim:

- that results are correct
- that models are validated

Those claims live in:
- the Reliability Card evidence tier fields
- benchmark coverage section
- calibration diagnostics section

---

## 8) Verification Procedure (What a Skeptical Reviewer Does)

The verifier should be able to run:

1) Verify integrity (hash-only)
- recompute SHA-256 hashes for all files in the bundle
- compare to `bundle_manifest.json`

2) Verify signature (if present)
- verify signature over the manifest

3) Verify schema validity
- validate `workflow_report.json`, `run_manifest.json`, and `reliability_card.json`
  against the pinned schemas

4) Replay (optional but powerful)
- run the replay command using the included config(s) and seeds
- compare key metrics within tolerance

This four-step ladder is important:
- integrity + signature detect tampering
- schema validity detects structural corruption
- replay detects "it runs but produces different results"

---

## 9) Integration With Project Approvals (Critical for Trust Closure)

Approvals should point to the signed bundle digest.

Recommendation:

- When a run is approved in Phase 22 workflow, capture:
  - bundle_manifest_sha256
  - signature artifact path(s)
  - signer identity (keyless subject or key id)

Approval object should be append-only and include:
- what was approved (run id)
- what evidence bundle was approved (manifest digest)
- when it was approved
- who approved

This enables:
- audit trail
- reproducible claims in papers and design reviews

---

## 10) Publishing Strategy (Immutable Storage)

Publishing means: the signed bundle is stored at a stable, immutable URI.

Recommended tiers:

Tier 1 (local-only):
- `results/<run>/evidence_bundle.zip`

Tier 2 (team):
- object storage (S3-compatible / artifact registry)
- store by content digest:
  - `evidence/sha256/<digest>.zip`
  - `evidence/sha256/<digest>.manifest.json`

Tier 3 (public benchmarks):
- publish open benchmark evidence bundles to a public bucket or release assets
- include signature and verification instructions

Design rule:
- publish by digest, not by mutable name

---

## 11) Implementation Slices (Mapping to Existing Repo Surfaces)

Phase 35 already exports bundles.
Phase 36 already provides schema contracts.

Phase 40 should add:

1) A signer abstraction
- local key-based signer
- optional Sigstore signer

2) CLI commands (conceptual)

```
photonstrust evidence bundle export <run_id> --output <path>
photonstrust evidence bundle sign <bundle_path> --mode keyless|key --key <path>
photonstrust evidence bundle verify <bundle_path> [--require-signature]
photonstrust evidence bundle publish <bundle_path> --dest <uri>
```

3) API hooks
- `POST /v0/evidence/bundle/sign`
- `POST /v0/evidence/bundle/verify`
- `POST /v0/evidence/bundle/publish`

4) Web UI integration
- show "Signed" status on run detail page
- show "Verified" status (last verified timestamp + tool)
- allow attaching signed bundle to an approval

---

## 12) Validation Gates (Definition of Done)

Functional:

- Mutating any file in the bundle causes verification failure.
- Missing file causes verification failure.
- Extra unexpected file causes either:
  - verification failure, or
  - explicit "unaccounted" error (choose strict by default).

Signature:

- `--require-signature` fails if signature is absent.
- Signature verification fails on modified manifest.

Determinism support:

- Verification does not require re-running the physics engine.
- Replay is optional and documented as separate, slower check.

Governance:

- Approvals can reference a specific signed manifest digest.

---

## 13) Source Index (Web-validated anchors)

- SLSA specification v1.2: https://slsa.dev/spec/v1.2/
- in-toto overview: https://in-toto.io/
- in-toto Attestation Framework (reference): https://github.com/in-toto/attestation
- Sigstore project: https://www.sigstore.dev/
- cosign verification docs (signature + attestation verification): https://docs.sigstore.dev/cosign/
- NIST SSDF (SP 800-218): https://doi.org/10.6028/NIST.SP.800-218
