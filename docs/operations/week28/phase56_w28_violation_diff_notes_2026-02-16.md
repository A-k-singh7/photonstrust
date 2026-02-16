# Phase 56 W28 Operations Notes (Violation Diff Semantics)

Date: 2026-02-16

## Week focus

Add semantic violation comparison in run diff API and UI to support engineering
signoff workflows with clear new/resolved/applicability-changed classification.

## Refreshed risk table

| Risk ID | Risk | Owner | Likelihood | Impact | Mitigation | Gate trigger | Status |
|---|---|---|---|---|---|---|---|
| P56-R16 | Violation comparisons rely on brittle raw JSON path diffs | SIM | Medium | High | Added semantic bucket diff (`new`, `resolved`, `applicability_changed`) | Diff regression tests fail | Mitigated |
| P56-R17 | API emits semantic diff when evidence is incomplete | TL | Medium | Medium | Enabled semantic diff only when both sides expose violation arrays | API optional-path tests fail | Mitigated |
| P56-R18 | UI does not expose semantic diff in reviewer flow | DOC | Medium | Medium | Added run-diff panel section with counts and sample entries | UI review checklist fails | Mitigated |
| P56-R19 | Semantic matching logic misclassifies applicability changes | QA | Low | High | Added focused API tests for changed applicability paths | Targeted API tests fail | Mitigated |
| P56-R20 | New diff fields break existing output consumers | TL | Low | High | Kept `violation_diff` optional and additive under existing `diff` object | Consumer/schema checks fail | Mitigated |

## Owner map confirmation

Diff semantics, API contract stability, and reviewer UX ownership remain explicit
with no accountable/responsible gaps.
