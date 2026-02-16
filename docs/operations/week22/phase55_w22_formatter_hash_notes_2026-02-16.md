# Phase 55 W22 Operations Notes (Formatter + Stable Hash)

Date: 2026-02-16

## Week focus

Ship deterministic GraphSpec formatting and stable semantic hashing so
GraphSpec artifacts are review-friendly and idempotent.

## Refreshed risk table

| Risk ID | Risk | Owner | Likelihood | Impact | Mitigation | Gate trigger | Status |
|---|---|---|---|---|---|---|---|
| P55-R6 | Formatting output is non-idempotent | QA | Medium | High | Added deterministic key ordering and canonical TOML serializer | `fmt --check` returns changed on already-formatted file | Mitigated |
| P55-R7 | Hash varies across semantically equivalent JSON/TOML graphs | SIM | Medium | High | Stable hash computed from canonicalized graph payload | JSON/TOML equivalence test fails | Mitigated |
| P55-R8 | CLI formatter behavior unclear for CI workflows | DOC | Medium | Medium | Added `--check`, `--write`, `--output`, `--print-hash` options | CI formatting gate cannot be expressed | Mitigated |
| P55-R9 | Formatter introduces unsupported TOML encodings | TL | Low | Medium | Explicit TOML value handling and finite-float guardrails | Formatter raises type errors on known fixtures | Mitigated |
| P55-R10 | Compile provenance hash drifts from GraphSpec semantics | TL | Low | Medium | Compiler artifact provenance switched to stable semantic hash | Compile output hash differs for equivalent inputs | Mitigated |

## Owner map confirmation

Formatter determinism, hashing policy, and CLI ergonomics remain explicitly
owned with no accountable/responsible gaps.
