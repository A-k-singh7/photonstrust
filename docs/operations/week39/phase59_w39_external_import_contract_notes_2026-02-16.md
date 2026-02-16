# Phase 59 W39 Operations Notes (External Simulation Import Contract)

Date: 2026-02-16

## Week focus

Define external simulator contract and provide a vendor-neutral import path that
produces reliability-card artifacts in the run registry.

## Refreshed risk table

| Risk ID | Risk | Owner | Likelihood | Impact | Mitigation | Gate trigger | Status |
|---|---|---|---|---|---|---|---|
| P59-R9 | External result payloads are inconsistent across vendors | TL | Medium | High | Added schema contract for `external_sim_result` | Import schema validation fails | Mitigated |
| P59-R10 | Imported runs cannot enter trust/evidence workflow | SIM | Medium | High | Added import endpoint writing manifest + reliability card | Missing card artifact in imported run | Mitigated |
| P59-R11 | Imported metric bounds are not sanity-checked | QA | Low | High | Added schema bounds for QBER/fidelity ranges | Invalid payload unexpectedly accepted | Mitigated |
| P59-R12 | Interop ingest bypasses project governance | TL | Low | Medium | Import endpoint validates project_id and writes run manifest | Project integrity tests fail | Mitigated |

## Owner map confirmation

Ownership mapping remained stable and explicitly documented with no unresolved
role ambiguity.
