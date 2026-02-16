# Phase 52 W12 Operations Notes (TF/PM Preview + Bound-Gate Routing)

Date: 2026-02-16

## Week focus

Make bound-gate routing protocol-aware so TF/PM/MDI families avoid naive
direct-link PLOB-style gating while direct-link families retain that sanity gate.

## Refreshed risk table

| Risk ID | Risk | Owner | Likelihood | Impact | Mitigation | Gate trigger | Status |
|---|---|---|---|---|---|---|---|
| P52-R16 | TF/PM protocols are incorrectly evaluated with direct-link PLOB gate | TL | Medium | High | Added protocol gate policy (`apply` vs `skip`) in registry | Bound-routing tests fail for TF/PM | Mitigated |
| P52-R17 | MDI protocol is treated as direct-link in gate policy | QA | Medium | High | Marked relay-family protocols with `skip` policy and rationale | Gate policy tests fail for MDI | Mitigated |
| P52-R18 | Gate policy is not visible in API trust summaries | DOC | Medium | Medium | Added `bound_gate_policy` fields to QKD summary cards | API trust metadata test misses policy field | Mitigated |
| P52-R19 | Protocol selection ambiguity causes incorrect gate routing | SIM | Low | High | Canonicalized protocol names via registry resolution and explicit summary field | `protocol_selected` missing or mismatched in manifests | Mitigated |
| P52-R20 | Regression suite does not cover routing semantics | QA | Low | Medium | Added dedicated bound-routing tests and API consistency assertions | Targeted routing suite fails | Mitigated |

## Owner map confirmation

Bound-routing semantics, protocol-family trust metadata, and regression safety
coverage remain explicitly owned with no accountable/responsible gaps.
