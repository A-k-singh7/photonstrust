# Phase 56 W27 Operations Notes (Reviewable Violation Outputs)

Date: 2026-02-16

## Week focus

Standardize violation annotations and summary counters across DRC/PDRC/LVS so
reviewers can localize and classify findings without manual reverse engineering.

## Refreshed risk table

| Risk ID | Risk | Owner | Likelihood | Impact | Mitigation | Gate trigger | Status |
|---|---|---|---|---|---|---|---|
| P56-R11 | Violation payload structure diverges across verification tools | TL | Medium | High | Normalized `violations_annotated` and summary field naming | Cross-tool contract tests fail | Mitigated |
| P56-R12 | Blocking vs advisory classification is inconsistent | SIM | Medium | High | Added explicit blocking counters and status derivation based on severity | Reviewer signoff mismatch | Mitigated |
| P56-R13 | Violation context is insufficient for remediation | QA | Medium | Medium | Added route- and signoff-aware details in annotated violation records | Dry-run remediation review fails | Mitigated |
| P56-R14 | Reporting surfaces omit fields present in raw outputs | DOC | Low | Medium | Updated HTML report sections to mirror structured findings | Report review checklist fails | Mitigated |
| P56-R15 | Additive fields regress existing parsers in strict mode | TL | Low | High | Kept new fields optional and validated with schema regression tests | Schema compatibility tests fail | Mitigated |

## Owner map confirmation

Violation model standardization, reviewer usability, and compatibility controls
remain explicitly owned with no accountability gaps.
