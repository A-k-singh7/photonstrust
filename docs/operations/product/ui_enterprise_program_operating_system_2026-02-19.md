# PhotonTrust UI Enterprise Program Operating System (2026-02-19)

This document operationalizes `docs/operations/ui_8_week_execution_board_2026-02-19.md` so the 8-week program can run with enterprise-level governance, quality control, and decision discipline.

## 1) Governance Model

### 1.1 Role ownership

| Role | Primary accountability | Decision rights | Backup role |
| --- | --- | --- | --- |
| Executive Sponsor | Outcome accountability, cross-team unblock, resource guardrails | Final tie-break on scope/time tradeoffs | Program Manager |
| Program Manager (DRI) | Weekly plan integrity, cadence facilitation, escalation routing | Accept/reject Monday scope lock readiness | UI Product Owner |
| UI Product Owner | Requirements quality, acceptance criteria, persona outcomes | Approve requirement changes within locked week | Engineering Lead |
| Engineering Lead (Web) | Architecture and implementation quality, technical sequencing | Approve implementation approach and technical debt tradeoffs | Senior Frontend IC |
| QA and Accessibility Lead | Test strategy, severity triage, accessibility coverage | Weekly quality gate recommendation (`GO`, `NO-GO`) | Program Manager |
| Telemetry Owner | Event schema, KPI quality, data integrity | Metric source-of-truth and Friday scorecard signoff | Engineering Lead |
| Demo Narrative Owner | Demo-mode script, proof screens, investor narrative quality | Demo readiness signoff | UI Product Owner |

### 1.2 Governance rules

- Every deliverable has exactly one accountable owner.
- No new work enters an active week without approved change control.
- If Friday gate fails, de-scope protocol is mandatory before next Monday scope lock.
- P0 escalation SLA is 4 hours; scope-change SLA is 24 hours.

## 2) Weekly Operating Cadence

| Day | Operating focus | Mandatory outputs |
| --- | --- | --- |
| Monday | Scope lock, acceptance criteria freeze, dependency check | Signed weekly plan and updated RAID log |
| Tuesday | Primary build execution | Midday implementation checkpoint |
| Wednesday | Build completion plus UX copy pass | Content and interaction quality pass |
| Thursday | QA, accessibility, responsive, edge-state hardening | Defect triage with P0/P1 closure plan |
| Friday | Usability run, KPI scorecard, demo rehearsal, reprioritization | Gate decision and next-week carryover/de-scope memo |

## 3) Quality Gates

| Gate | When | Entry criteria | Exit criteria | Owner |
| --- | --- | --- | --- | --- |
| G1 Scope Lock | Monday 09:00 | Backlog prioritized with draft acceptance criteria | Scope frozen and each item has accountable owner | Program Manager |
| G2 Build Complete | Thursday 12:00 | Planned stories implemented for active week | No unresolved merge blockers; telemetry hooks in place | Engineering Lead |
| G3 Quality Pass | Thursday 17:00 | Functional, accessibility, responsive checks executed | Zero open P0 and max two time-bound P1 | QA and Accessibility Lead |
| G4 KPI Validity | Friday 11:00 | Weekly telemetry extracted from `results/ui_metrics/events.jsonl` | KPI calculations reproducible and signed off | Telemetry Owner |
| G5 Weekly Steering | Friday 14:00 | G1-G4 evidence packet complete | Decision recorded (`GO`, `GO-WITH-CONDITIONS`, `NO-GO`) | Executive Sponsor |

## 4) RACI by Workstream

| Workstream | Exec Sponsor | Program Manager | UI Product Owner | Engineering Lead | QA/A11y Lead | Telemetry Owner | Demo Owner |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Week 1 IA and product narrative | I | C | A | R | C | I | C |
| Week 2 guided time-to-value flow | I | C | A | R | C | C | I |
| Week 3 graph studio modularization | I | C | C | A/R | C | I | I |
| Week 4 results decision UX | I | C | A | R | C | C | C |
| Week 5 trust and certification UX | C | C | A | R | C | C | C |
| Week 6 team workflow and compare lab | I | C | A | R | C | C | I |
| Week 7 pitch mode and proof screens | C | C | C | R | C | C | A |
| Week 8 hardening and RC readiness | I | C | C | R | A | C | I |
| KPI instrumentation and scorecard | I | C | C | R | C | A | I |

Legend: `R` Responsible, `A` Accountable, `C` Consulted, `I` Informed.

## 5) Change Control and De-Scope Protocol

### 5.1 Change classes

| Class | Definition | Approval path |
| --- | --- | --- |
| C1 minor | No KPI impact and <= 0.5 day effort shift | Program Manager plus Engineering Lead |
| C2 material | Potential KPI or schedule impact within active week | UI Product Owner plus Program Manager plus Engineering Lead |
| C3 major | Cross-week impact, target risk, or scope expansion | Executive Sponsor steering decision |

### 5.2 Change request minimum payload

- `change_id`
- `requested_by`
- `affected_week`
- `reason`
- `impact_on_kpis`
- `effort_delta`
- `options_considered`
- `recommended_option`
- `approval_record`

### 5.3 Mandatory de-scope triggers

- Open P0 defect after Thursday 17:00.
- Two or more north-star KPI breaches in weekly scorecard.
- Required telemetry data quality below 98% completeness.
- Critical dependency unresolved past agreed SLA.

### 5.4 De-scope decision sequence

1. Rank backlog by KPI contribution, risk reduction, and demo criticality.
2. Remove lowest-ranked work that does not protect KPI or risk posture.
3. Tag carryover items with `carryover_reason` and `re_entry_condition`.
4. Publish de-scope memo within 2 hours of Friday gate decision.

## 6) Weekly Program Artifacts

Each week must produce all artifacts below:

- Scorecard: `docs/operations/product/ui_weekly_scorecard_template_2026Q1.yaml`.
- Decision packet: `docs/operations/product/ui_weekly_decision_packet_template_2026-02-19.md`.
- RAID updates: `docs/operations/product/ui_raid_log_2026-02-19.md`.
- Gap/backlog status refresh: `docs/operations/product/ui_execution_gap_backlog_2026-02-19.md`.
- Telemetry source data: `results/ui_metrics/events.jsonl`.
