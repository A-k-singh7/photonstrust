# Phase 55 W21 Operations Notes (GraphSpec TOML Parser)

Date: 2026-02-16

## Week focus

Add `.ptg.toml` parsing and TOML-to-canonical-JSON loading so GraphSpec inputs
are accepted by the compile path with deterministic normalization.

## Refreshed risk table

| Risk ID | Risk | Owner | Likelihood | Impact | Mitigation | Gate trigger | Status |
|---|---|---|---|---|---|---|---|
| P55-R1 | TOML authoring path diverges from JSON compile path | TL | Medium | High | Added shared loader (`load_graph_file`) and canonicalization path for JSON/TOML | TOML compile tests fail | Mitigated |
| P55-R2 | Null-vs-missing semantics create hidden drift | SIM | Medium | High | Canonicalization drops null dict entries before hashing/formatting | Round-trip hash mismatch | Mitigated |
| P55-R3 | Unstable node/edge ordering harms reproducibility | QA | Medium | Medium | Added deterministic canonical ordering for nodes/edges | Idempotence tests fail | Mitigated |
| P55-R4 | Backward compatibility regression for JSON graphs | TL | Low | High | Kept JSON loader behavior and added TOML as additive input format | Existing graph tests fail | Mitigated |
| P55-R5 | Parser rejects valid GraphSpec TOML fixtures | QA | Low | Medium | Added fixture compile-path test and demo `.ptg.toml` artifact | TOML fixture compile fails | Mitigated |

## Owner map confirmation

Parser correctness, canonicalization semantics, and compatibility safeguards
remain explicitly owned with no accountable/responsible gaps.
