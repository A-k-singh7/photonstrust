# Phase 60 W41 Operations Notes (Async Compute + Compile Cache)

Date: 2026-02-16

## Week focus

Remove API blocking behavior for long-running QKD runs and reduce repeated
compile overhead with deterministic cache keys.

## Refreshed risk table

| Risk ID | Risk | Owner | Likelihood | Impact | Mitigation | Gate trigger | Status |
|---|---|---|---|---|---|---|---|
| P60-R1 | Long-running QKD calls block API responsiveness | TL | Medium | High | Added async job queue + status polling endpoints | Async lifecycle tests fail | Mitigated |
| P60-R2 | Cached compile output becomes non-deterministic | SIM | Medium | High | Added stable graph+schema cache key and deterministic payload reuse | Determinism regression tests fail | Mitigated |
| P60-R3 | Async job results lose artifact traceability | QA | Low | High | Added job result linkage to run_id + artifact_relpaths | Missing job/result artifacts | Mitigated |
| P60-R4 | Invalid status filters destabilize job listing | TL | Low | Medium | Explicit status validation and 400 responses | API status filter tests fail | Mitigated |

## Owner map confirmation

Owner map stayed aligned with `docs/research/deep_dive/13_raci_matrix.md` and
no accountability gaps were identified.
