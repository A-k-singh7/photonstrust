# Phase 40: Evidence Bundle Signing (Research Brief)

Date: 2026-02-14

## Goal

Make PhotonTrust evidence bundles tamper-evident outside the repository by
adding cryptographic signing and a verifier.

This phase builds on:
- Phase 35: evidence bundle export (zip)
- Phase 36: evidence bundle manifest schema contracts
- Phase 22: project approvals (append-only governance log)

The deliverable is not “security theater”. It is trust closure:
- if a bundle’s content changes post-export, verification fails
- approvals can reference immutable, verifiable evidence

## Threat model (pragmatic)

In scope:
- accidental mutation after export
- post-hoc cherry-picking (swapping plots/configs)
- evidence drift when bundles are copied/shared

Out of scope:
- malicious signer who controls signing keys (governance problem)

## Research decisions

1) Sign the manifest, not the whole zip
- The zip container can be re-packed in many ways.
- The manifest already enumerates file hashes.

2) Default signing mode: Ed25519 (offline, simple)
- works without network
- deterministic verification

3) Optional future mode: keyless signing (Sigstore)
- good for public/open artifacts with transparency logs
- higher operational complexity; defer unless needed

## Evidence artifact contract (v0.1)

- `bundle_manifest.json` remains the integrity index for evidence files.
- A detached signature artifact is added:
  - `signatures/bundle_manifest.ed25519.sig.json`

The signature covers a canonicalized JSON encoding of the manifest object.

## Primary anchors

- SLSA provenance model (integrity/provenance framing): https://slsa.dev/spec/v1.2/
- in-toto overview (attestable artifact concepts): https://in-toto.io/
- Sigstore (optional keyless pathway): https://www.sigstore.dev/
- NIST SSDF (secure software supply chain posture): https://doi.org/10.6028/NIST.SP.800-218

## Definition of done

- A CLI command signs a bundle and creates a signed zip including a detached signature file.
- A verifier:
  - recomputes file hashes vs manifest
  - verifies Ed25519 signature over canonical manifest bytes
- Tests demonstrate:
  - verify passes for a signed bundle
  - verify fails if any file referenced in the manifest is modified
