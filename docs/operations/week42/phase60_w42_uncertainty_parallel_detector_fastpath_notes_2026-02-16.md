# Phase 60 W42 Operations Notes (Uncertainty Parallelization + Detector Fast Path)

Date: 2026-02-16

## Week focus

Improve runtime while preserving deterministic outputs by parallelizing
uncertainty sampling and adding a safe detector fast path.

## Refreshed risk table

| Risk ID | Risk | Owner | Likelihood | Impact | Mitigation | Gate trigger | Status |
|---|---|---|---|---|---|---|---|
| P60-R5 | Parallel uncertainty changes numeric outputs | TL | Medium | High | Seed-per-sample contract + sample-index stable aggregation | Worker invariance tests fail | Mitigated |
| P60-R6 | Parallel execution introduces non-reproducible ordering effects | SIM | Medium | High | Deterministic seed schedule and sorted aggregation | Reproducibility tests fail | Mitigated |
| P60-R7 | Detector optimization changes baseline semantics | QA | Low | High | Legacy fallback + explicit fast/legacy path diagnostics | Detector parity tests fail | Mitigated |
| P60-R8 | Fast path incorrectly runs under afterpulse conditions | TL | Low | Medium | Guarded fast-path eligibility + force-legacy escape hatch | Path-selection tests fail | Mitigated |

## Owner map confirmation

Roles and handoffs remained consistent with the phase implementation plan.
