# Phase 57 W30 Operations Notes (PDK Manifest Enforcement)

Date: 2026-02-16

## Week focus

Enforce deterministic `pdk_manifest.json` evidence in layout/signoff pipelines,
including certification-mode fail-fast behavior when manifest context is absent.

## Refreshed risk table

| Risk ID | Risk | Owner | Likelihood | Impact | Mitigation | Gate trigger | Status |
|---|---|---|---|---|---|---|---|
| P57-R6 | Runs omit PDK identity evidence in artifacts | TL | Medium | High | Added `photonstrust.pdk_manifest.v0` schema and endpoint emission | Manifest schema/API tests fail | Mitigated |
| P57-R7 | Certification mode silently accepts missing manifest | TL | Medium | High | Added explicit certification-mode guardrails in API handlers | Certification negative-path tests fail | Mitigated |
| P57-R8 | Manifest generation varies by endpoint | SIM | Medium | Medium | Centralized manifest resolution helper logic in API server | Endpoint contract tests fail | Mitigated |
| P57-R9 | Added manifest artifacts leak unstable optional fields | QA | Low | Medium | Kept manifest contract minimal, deterministic, and schema-validated | Determinism/schema tests fail | Mitigated |
| P57-R10 | API changes regress legacy clients | TL | Low | High | Added manifest as additive artifact and kept existing response contracts | Optional API regression tests fail | Mitigated |

## Owner map confirmation

Manifest governance, certification enforcement, and API compatibility ownership
remain explicitly mapped with no accountability gaps.
