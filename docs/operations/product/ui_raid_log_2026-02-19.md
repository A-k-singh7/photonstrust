# PhotonTrust UI Program RAID Log (2026-02-19)

This log tracks Risks, Assumptions, Issues, and Dependencies for the UI 8-week execution program.

## 1) RAID template

| ID | Type (`R`,`A`,`I`,`D`) | Title | Description | Owner role | Probability | Impact | Score | Mitigation or action | Due date | Status | Escalation trigger |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

## 2) Seeded entries

| ID | Type | Title | Description | Owner role | Probability | Impact | Score | Mitigation or action | Due date | Status | Escalation trigger |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R-01 | R | Over-polish before flow clarity | Visual polish displaces critical flow work before gates pass | Program Manager | Medium | High | 6 | Block polish stories until weekly flow gate passes | 2026-03-06 | Open | Any polish task enters week before flow gate |
| R-02 | R | Monolithic UI slows delivery | `App.jsx` complexity causes integration drag and defect leakage | Engineering Lead | High | High | 9 | Mandatory modular refactor in Week 3 exit criteria | 2026-03-13 | Open | Refactor incomplete by Week 3 Thursday |
| R-03 | R | Telemetry quality is insufficient | Missing or malformed events break KPI confidence | Telemetry Owner | Medium | High | 6 | Enforce schema validation and daily telemetry checks | 2026-03-06 | Open | Required-field completeness below 98% |
| R-04 | R | Demo fragility under unstable API | Investor demo fails when backend is degraded | Demo Owner | Medium | High | 6 | Implement deterministic fallback states and scripted data | 2026-04-10 | Open | Rehearsal failure in two consecutive runs |
| I-01 | I | KPI ownership not explicit | Metric ownership unclear across Product, Eng, QA | Program Manager | - | High | - | Assign KPI owner and backup in operating system doc | 2026-02-23 | Open | Missing owner in Monday scope lock |
| I-02 | I | Severity triage inconsistency | P0/P1 classification differs across teams | QA and Accessibility Lead | - | Medium | - | Publish severity rubric and examples in weekly runbook | 2026-02-25 | Open | Defect severity disputes older than 24 hours |
| D-01 | D | Stable backend contracts | UI work depends on consistent run and trust payloads | Engineering Lead | Medium | High | 6 | Add contract checks and fallback fixtures per route | 2026-03-04 | Open | API contract change without compatibility notice |
| D-02 | D | Copy and narrative signoff availability | Landing and demo quality depends on weekly copy approvals | UI Product Owner | Medium | Medium | 4 | Reserve weekly Wednesday copy review slot | Ongoing | Open | Two missed copy signoff windows |
| A-01 | A | Persona sample quality | Weekly participants represent target personas | UI Product Owner | Medium | Medium | 4 | Track persona mix and rebalance recruiting every Friday | Ongoing | Open | Persona match drops below 70% |
| A-02 | A | Test environment reproducibility | RC confidence assumes stable local and CI environments | QA and Accessibility Lead | Medium | High | 6 | Standardize smoke script and artifact capture for gate runs | 2026-04-17 | Open | RC smoke run cannot reproduce prior passing state |

## 3) Review protocol

- Update RAID at least twice per week (Monday scope lock and Friday gate review).
- Any item with score >= 6 requires named mitigation owner and due date.
- Any unresolved high-impact issue rolls into next-week de-scope decision.
