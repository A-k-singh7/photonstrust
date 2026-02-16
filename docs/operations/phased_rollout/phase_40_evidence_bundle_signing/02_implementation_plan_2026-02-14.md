# Phase 40: Evidence Bundle Signing (Implementation Plan)

Date: 2026-02-14

## Scope

Implement Ed25519 signing/verification for evidence bundle zips.

This phase does not yet:
- require server-side signing
- publish bundles to remote immutable storage
- integrate Sigstore keyless signing

## Files to change / add

Code:
- Add `photonstrust/evidence/bundle.py`
  - `sign_bundle_zip(...)`
  - `verify_bundle_zip(...)`
- Add `photonstrust/evidence/signing.py`
  - Ed25519 keygen + sign/verify helpers (optional dependency: cryptography)
- Update `photonstrust/cli.py`
  - add `photonstrust bundle keygen|sign|verify`

Schemas:
- Add `schemas/photonstrust.evidence_bundle_signature.v0.schema.json`
- Update `photonstrust/workflow/schema.py`
  - add `evidence_bundle_signature_schema_path()`

Tests:
- Add `tests/test_evidence_bundle_signature_schema.py`
  - export bundle via API, sign it, validate signature JSON against schema
- Add `tests/test_evidence_bundle_signing_verify.py`
  - sign bundle and verify; mutate README and ensure verification fails

Packaging:
- Update `pyproject.toml`
  - add `signing` extra
  - add `cryptography` to `dev` extra (tests require it)

## Artifact contract

The signed bundle zip includes:
- `<bundle_root>/bundle_manifest.json`
- `<bundle_root>/signatures/bundle_manifest.ed25519.sig.json`

The signature file includes:
- `manifest_canonical_sha256` (sha256 of canonical manifest bytes)
- `signature_b64` (Ed25519 signature)

## Acceptance tests (must pass)

1) Signing
- `photonstrust bundle sign <bundle.zip> --key <private.pem>` produces `<bundle>.signed.zip`
- signature file exists inside the signed zip

2) Verification
- `photonstrust bundle verify <bundle>.signed.zip --pubkey <public.pem> --require-signature` exits 0

3) Mutation detection
- modify any evidence file listed in the manifest -> verification fails

## Notes

- The signature covers canonicalized manifest bytes (sorted keys, compact JSON) so
  signature validity does not depend on pretty-print formatting.
