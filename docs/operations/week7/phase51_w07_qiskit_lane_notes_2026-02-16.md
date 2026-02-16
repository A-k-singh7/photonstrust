# Phase 51 W07 Operations Notes (Qiskit Repeater Primitive Lane)

Date: 2026-02-16

## Week focus

Add an optional Qiskit backend lane for repeater primitive cross-checking with
deterministic formula-vs-circuit parity.

## Refreshed risk table

| Risk ID | Risk | Owner | Likelihood | Impact | Mitigation | Gate trigger | Status |
|---|---|---|---|---|---|---|---|
| P51-R11 | Qiskit lane introduces mandatory dependency pressure in core runtime | TL | Medium | High | Keep lane optional and isolated in resolver + backend wrapper | Core suite fails without Qiskit | Mitigated |
| P51-R12 | Repeater primitive cross-check is non-deterministic across environments | QA | Medium | High | Use statevector deterministic probability path and fixed formula target | Formula-vs-circuit delta drifts in tests | Mitigated |
| P51-R13 | Protocol compiler lacks explicit template hook for repeater primitive checks | SIM | Medium | Medium | Added dedicated protocol compiler branch with explicit comparison payload | Compiler rejects repeater primitive profile | Mitigated |
| P51-R14 | Provenance for optional Qiskit lane is insufficient for audit | DOC | Low | Medium | Added `qiskit_available`/`qiskit_version` provenance fields | Provenance tests fail or fields missing | Mitigated |
| P51-R15 | Backend resolver contract drifts as new backend is added | QA | Low | Medium | Extended backend interface tests for resolver/available backend list | Interface tests fail on backend registry mismatch | Mitigated |

## Owner map confirmation

Qiskit optional-lane implementation, deterministic cross-check logic, and
backend contract governance remain explicitly owned with no accountable/
responsible gaps.
