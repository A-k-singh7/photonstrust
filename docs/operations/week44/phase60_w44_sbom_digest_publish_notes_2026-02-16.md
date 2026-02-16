# Phase 60 W44 Operations Notes (SBOM + Immutable Publish by Digest)

Date: 2026-02-16

## Week focus

Complete supply-chain and immutability chain by embedding SBOM artifacts in
bundles and enabling digest-addressable publication and verification.

## Refreshed risk table

| Risk ID | Risk | Owner | Likelihood | Impact | Mitigation | Gate trigger | Status |
|---|---|---|---|---|---|---|---|
| P60-R13 | Evidence bundles lack dependency transparency | TL | Medium | Medium | Added CycloneDX SBOM artifact to bundle exports | SBOM artifact checks fail | Mitigated |
| P60-R14 | Published bundle references are mutable/path-based | SIM | Medium | High | Added publish-by-sha256 path and fetch-by-digest endpoint | Digest fetch tests fail | Mitigated |
| P60-R15 | Published artifacts cannot be integrity-reverified | QA | Low | High | Added verify-by-digest API backed by bundle verify engine | Verify endpoint tests fail | Mitigated |
| P60-R16 | Publish manifest drifts from contract | TL | Low | Medium | Added publish manifest schema + validation in publish path | Schema validation test fails | Mitigated |

## Owner map confirmation

Ownership remained aligned with phase governance and handoffs were clear.
