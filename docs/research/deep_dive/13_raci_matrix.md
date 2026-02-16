# PhotonTrust RACI Matrix

This document assigns ownership across major workstreams.

Legend:
- R = Responsible (executes)
- A = Accountable (final owner)
- C = Consulted
- I = Informed

Roles:
- TL (Technical Lead)
- PHY (Physics Engineer)
- SIM (Simulation Engineer)
- PROT (Protocol Engineer)
- CAL (Calibration Engineer)
- OPT (Optimization Engineer)
- UX (UI/Product Engineer)
- QA (Quality Engineer)
- DOC (Docs/DevEx)

## Workstream RACI

| Workstream | TL | PHY | SIM | PROT | CAL | OPT | UX | QA | DOC |
|---|---|---|---|---|---|---|---|---|---|
| Architecture and API contracts | A | C | R | C | C | C | I | C | R |
| Emitter model quality | C | A/R | C | I | C | I | I | C | I |
| Memory model quality | C | A/R | C | I | C | I | I | C | I |
| Detector stochastic model | C | C | A/R | I | C | I | I | C | I |
| Event kernel and scheduling | C | I | A/R | C | I | I | I | C | I |
| Channel realism | C | C | A/R | I | I | I | I | C | I |
| Protocol circuits (Qiskit) | C | I | C | A/R | I | I | I | C | I |
| Protocol-event integration | C | I | R | A | I | I | I | C | I |
| QKD scenario quality | A | R | R | C | C | C | I | C | I |
| Repeater optimization | C | C | C | I | C | A/R | I | C | I |
| Teleportation scenario quality | C | C | R | A/R | I | I | I | C | I |
| Source benchmarking | C | A/R | C | I | C | I | I | C | I |
| Calibration inference | C | C | I | I | A/R | I | I | C | I |
| Uncertainty propagation | C | C | R | I | A/R | C | I | C | I |
| Reliability Card schema and renderers | A | C | C | I | C | C | R | C | R |
| Benchmark suite governance | A | C | C | C | C | C | I | R | R |
| CI and regression baselines | I | I | C | I | C | I | I | A/R | I |
| Streamlit UI and run registry UX | I | I | C | I | I | C | A/R | C | C |
| Release notes and changelog | A | I | I | I | I | I | C | C | R |
| External adoption and onboarding | A | C | I | C | I | C | R | I | R |

## Decision authority map
- Architecture-breaking changes: TL approval required.
- Schema version changes: TL + QA + DOC approval required.
- Baseline updates: QA approval required with rationale in changelog.
- Release gate pass/fail: TL and QA co-sign.

## Escalation model
- Critical correctness issue: escalate to TL within 24 hours.
- Reproducibility failure in CI: QA can block merges.
- Performance regression above threshold: SIM and TL joint triage.

## Review cadence
- Weekly owner report by each accountable role.
- Monthly RACI refresh to reflect staffing and scope shifts.

## Definition of done
- Every workstream has explicit A and at least one R.
- No release-critical stream has ambiguous ownership.


## Inline citations (web, verified 2026-02-12)
Applied to: decision authority, escalation ownership, and governance accountability structure.
- GitHub CODEOWNERS and review ownership: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners
- GitHub issue/PR templates for standardized intake: https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/about-issue-and-pull-request-templates
- GitHub contributor guideline placement and behavior: https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/setting-guidelines-for-repository-contributors?apiVersion=2022-11-28
- NIST CSF 2.0 (governance and risk communication): https://doi.org/10.6028/NIST.CSWP.29
- OpenSSF Scorecard as measurable repository hygiene signal: https://scorecard.dev/

