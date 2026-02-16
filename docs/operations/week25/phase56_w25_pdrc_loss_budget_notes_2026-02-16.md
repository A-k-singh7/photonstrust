# Phase 56 W25 Operations Notes (PDRC Loss-Budget Checks)

Date: 2026-02-16

## Week focus

Extend performance DRC with route-level loss-budget analysis and actionable
findings that can be consumed by signoff reviewers.

## Refreshed risk table

| Risk ID | Risk | Owner | Likelihood | Impact | Mitigation | Gate trigger | Status |
|---|---|---|---|---|---|---|---|
| P56-R1 | Route-loss proxy terms undercount bend/crossing effects | SIM | Medium | High | Added explicit propagation/bend/crossing components and total aggregation | Loss-budget regression tests fail | Mitigated |
| P56-R2 | Loss budgets vary by caller and become non-comparable | TL | Medium | Medium | Added request-level defaults and explicit budget fields in outputs | Schema/consumer validation fails | Mitigated |
| P56-R3 | Violations are not triage-friendly for reviewers | QA | Medium | High | Added `violations_annotated` and `violation_summary` with blocking counts | Reviewer dry-run cannot classify outcomes | Mitigated |
| P56-R4 | HTML report omits route-loss detail needed for signoff | DOC | Low | Medium | Expanded performance DRC report with loss-budget and violation sections | Report snapshot/visual review fails | Mitigated |
| P56-R5 | New PDRC outputs break compatibility with schema clients | TL | Low | High | Extended schema with optional additive fields and regression tests | Schema tests fail | Mitigated |

## Owner map confirmation

PDRC analytics, report surfacing, and schema compatibility ownership remains
explicit with no accountable/responsible gaps.
