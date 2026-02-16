# Phase 55 W23 Operations Notes (Typed Ports + Connection Rules)

Date: 2026-02-16

## Week focus

Enforce typed port domains for PIC graph edges in compiler, diagnostics, and
web editor connection workflows.

## Refreshed risk table

| Risk ID | Risk | Owner | Likelihood | Impact | Mitigation | Gate trigger | Status |
|---|---|---|---|---|---|---|---|
| P55-R11 | Invalid port-domain edges reach simulation pipeline | TL | Medium | High | Compiler now rejects domain mismatch and edge-kind/domain mismatch | PIC compile tests fail to block invalid edges | Mitigated |
| P55-R12 | UI allows invalid wiring that backend later rejects | SIM | Medium | High | Added UI-side connection blocking with domain checks | Manual/UI validation shows invalid edge acceptance | Mitigated |
| P55-R13 | Diagnostics omit domain-specific failure reasons | QA | Medium | Medium | Added `edge.port_domain` and `edge.kind_domain` diagnostics codes | Diagnostic test matrix misses domain errors | Mitigated |
| P55-R14 | Registry contract lacks typed-port metadata | TL | Low | Medium | Added `port_domains` metadata to backend kind registry entries | Registry consumers cannot infer port domains | Mitigated |
| P55-R15 | QKD/control graph behavior regresses under typed-port changes | QA | Low | High | Scoped strict domain blocking to PIC connection path in UI | QKD graph editor behavior regression | Mitigated |

## Owner map confirmation

Connection-policy enforcement, diagnostics clarity, and registry metadata
governance remain explicitly owned with no accountable/responsible gaps.
