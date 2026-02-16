# Phase 52 W10 Operations Notes (Decoy BB84 v0.1)

Date: 2026-02-16

## Week focus

Stabilize Decoy BB84 under the protocol contract surface with explicit
selection, compatibility aliases, and regression-backed behavior checks.

## Refreshed risk table

| Risk ID | Risk | Owner | Likelihood | Impact | Mitigation | Gate trigger | Status |
|---|---|---|---|---|---|---|---|
| P52-R6 | Decoy BB84 selection is inconsistent across aliases | QA | Medium | Medium | Registry maps BB84 aliases to canonical `bb84_decoy` | Alias-resolution tests fail | Mitigated |
| P52-R7 | Protocol-specific behavior regresses during dispatch refactor | SIM | Medium | High | Preserved module implementation and added registry compatibility tests | Decoy BB84 trend tests fail | Mitigated |
| P52-R8 | Applicability labels for protocol modules are missing from contract | DOC | Medium | Medium | Protocol contract now includes applicability object | Contract tests fail to return applicability status | Mitigated |
| P52-R9 | Artifact metadata obscures selected protocol family | TL | Low | High | Added explicit `protocol_selected` fields in run manifest/summary | API run manifest lacks explicit protocol selection | Mitigated |
| P52-R10 | Regression coverage misses protocol integration paths | QA | Low | Medium | Included API + protocol regression tests in targeted gate | Targeted gate failures in protocol/API tests | Mitigated |

## Owner map confirmation

Decoy BB84 protocol selection, applicability labeling, and artifact-surface
explicitness remain explicitly owned with no accountable/responsible gaps.
