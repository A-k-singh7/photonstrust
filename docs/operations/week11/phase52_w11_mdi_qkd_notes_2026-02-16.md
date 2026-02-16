# Phase 52 W11 Operations Notes (MDI-QKD v0.1)

Date: 2026-02-16

## Week focus

Keep MDI-QKD in the explicit protocol contract with strict applicability bounds
and explicit protocol metadata propagation to run artifacts.

## Refreshed risk table

| Risk ID | Risk | Owner | Likelihood | Impact | Mitigation | Gate trigger | Status |
|---|---|---|---|---|---|---|---|
| P52-R11 | MDI assumptions leak into unsupported channel models | QA | Medium | High | Enforced fiber-only applicability for MDI module | MDI applicability test fails on free-space | Mitigated |
| P52-R12 | MDI metadata is not explicit in run-level artifacts | DOC | Medium | Medium | Added `protocol_selected` manifest and summary fields | API run outputs miss protocol selection fields | Mitigated |
| P52-R13 | Contract refactor alters MDI output surface unexpectedly | SIM | Low | High | Retained MDI module implementation and validated regression suites | Relay protocol surface tests fail | Mitigated |
| P52-R14 | API summaries omit protocol gate context for reviewers | TL | Medium | Medium | Added `bound_gate_policy` block to QKD summary cards | API trust metadata tests fail | Mitigated |
| P52-R15 | Operational team over-trusts protocol without applicability context | TL | Low | Medium | Applicability status/reasons now first-class contract fields | Missing applicability in protocol contract tests | Mitigated |

## Owner map confirmation

MDI applicability governance, API protocol metadata propagation, and regression
gates remain explicitly owned with no accountable/responsible gaps.
