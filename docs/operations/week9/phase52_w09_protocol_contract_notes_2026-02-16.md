# Phase 52 W09 Operations Notes (Protocol Module Contract Refactor)

Date: 2026-02-16

## Week focus

Replace inline protocol branching with explicit protocol module contract and
registry dispatch to support scalable protocol expansion.

## Refreshed risk table

| Risk ID | Risk | Owner | Likelihood | Impact | Mitigation | Gate trigger | Status |
|---|---|---|---|---|---|---|---|
| P52-R1 | Protocol growth causes fragile branching logic in core QKD engine | TL | Medium | High | Introduced registry-driven protocol dispatch contract | Registry resolution tests fail | Mitigated |
| P52-R2 | Protocol alias handling diverges across modules | QA | Medium | Medium | Centralized normalization + module resolution in registry | Alias resolution tests fail | Mitigated |
| P52-R3 | Applicability assumptions remain implicit and untestable | SIM | Medium | High | Added explicit applicability contract (`pass/warn/fail`) | Applicability tests fail for relay protocols | Mitigated |
| P52-R4 | Migration breaks legacy protocol defaults | QA | Low | High | Kept default empty-name dispatch to BBM92 | Unknown/legacy protocol tests fail | Mitigated |
| P52-R5 | Future protocol additions require core-engine edits | TL | Medium | Medium | Encapsulated protocol selection in module registry | New protocol cannot be added without touching `qkd.py` | Mitigated |

## Owner map confirmation

Dispatch contract refactor, compatibility handling, and migration safety gates
remain explicitly owned with no accountable/responsible gaps.
