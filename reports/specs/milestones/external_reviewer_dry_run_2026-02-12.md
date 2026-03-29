# External Reviewer Dry-Run

## Reviewer profile
- Org/team: PhotonTrust internal pilot panel (proxy for external evaluator flow)
- Role: Quantum networking engineer and platform integrator
- Familiarity level: Intermediate (QKD-aware, first-time PhotonTrust operator)

## Task script
- [x] Install and run one flagship scenario
- [x] Generate and inspect Reliability Card
- [ ] Compare two runs in UI
- [x] Interpret recommendation and uncertainty

## Findings
- Time to first successful run: `387.22s` (`py -3 -m photonstrust.cli run configs/quickstart/qkd_default.yml`) on maintainer workstation, 2026-02-12.
- Time to first quick smoke validation: `1.27s` (`py -3 -m photonstrust.cli run configs/quickstart/qkd_quick_smoke.yml --output results/smoke_quick`) on same workstation.
- Clarity issues: run completion latency is acceptable for engineering workflows but lacks incremental progress visibility for first-time operators.
- Trust concerns: no critical trust blockers found; card output includes uncertainty and outage-probability semantics in reviewed sample outputs.
- Feature requests: add optional progress milestones/logging in long scenario runs.

## Severity triage
- Critical: none.
- Major: missing guided UI compare walkthrough for non-maintainer reviewers.
- Minor: README onboarding could link directly to a two-run comparison flow.

## Go/No-go suggestion
- [ ] Go
- [x] Conditional go
- [ ] No-go

Conditions:
- complete one non-maintainer guided UI comparison dry-run before external announcement.

Follow-up completed after dry-run:
- Added quickstart smoke profile: `configs/quickstart/qkd_quick_smoke.yml`.
- Added explicit UI comparison steps in `README.md`.
