# PhotonTrust UI Week 1 Owner Plan (2026-02-23 to 2026-03-01)

This plan executes Week 1 of `docs/operations/ui_8_week_execution_board_2026-02-19.md` with explicit ownership and daily checkpoints.

## Week 1 objective

Make the app structure explain the product clearly before any deep interaction.

## Owner roster

| Workstream | Accountable owner role | Responsible owner role | Consulted | Output artifact |
| --- | --- | --- | --- | --- |
| IA and route model freeze | UI Product Owner | Engineering Lead | Program Manager | IA labels and route map |
| App-shell implementation | Engineering Lead | Frontend Engineer | QA/A11y Lead | New top-level nav in `web/src/App.jsx` |
| Landing narrative workspace | UI Product Owner | Frontend Engineer | Demo Owner | Start-here workspace and quick actions |
| Copy system baseline | UI Product Owner | UX Writer or Design Owner | Engineering Lead | Centralized copy labels in `web/src/features/shell/copy.js` |
| Token and style baseline | Engineering Lead | Frontend Engineer | QA/A11y Lead | Week 1 shell and layout CSS |
| Comprehension test operations | Program Manager | UX Research Owner | UI Product Owner | Friday comprehension test scorecard |

## Daily execution plan (owner-by-owner)

### Monday (scope lock)

- UI Product Owner: freeze labels `Build`, `Run`, `Validate`, `Compare`, `Certify`, `Export`.
- Engineering Lead: freeze route mapping from product stages to existing workspace modes.
- Program Manager: publish Week 1 acceptance checklist and RAID updates.

### Tuesday (implementation)

- Frontend Engineer: ship stage navigation shell and top-level routing state.
- Frontend Engineer: ship landing workspace with start-here quick actions.
- QA/A11y Lead: review keyboard and focus behavior for nav and landing actions.

### Wednesday (implementation and copy pass)

- UI Product Owner: complete copy quality pass for helper text and empty states.
- Frontend Engineer: integrate copy dictionary and update labels in UI.
- Engineering Lead: verify no dead-end routes in primary nav.

### Thursday (hardening)

- QA/A11y Lead: responsive pass for desktop, laptop, and tablet breakpoints.
- Frontend Engineer: fix discovered empty-state and layout defects.
- Program Manager: prep Friday comprehension test protocol and participant list.

### Friday (validation)

- UX Research Owner: run 5-person comprehension test.
- Program Manager: produce Week 1 scorecard and gate recommendation.
- Executive Sponsor: record `GO`, `GO-WITH-CONDITIONS`, or `NO-GO` for Week 2.

## Week 1 acceptance checklist

- [ ] New top-level nav model is visible and operational.
- [ ] Landing workspace explains product value and has clear start actions.
- [ ] No dead-end screens in primary nav.
- [ ] At least 80% of test users can explain product value in one sentence after 60 seconds.

## Risks and mitigations specific to Week 1

- Risk: technical mode labels leak into first-time UX and reduce clarity.
  - Mitigation: keep stage nav as primary and technical mode as secondary control.
- Risk: landing copy remains too technical for investor persona.
  - Mitigation: Wednesday copy pass must include investor readability check.
- Risk: responsive polish slips due implementation concentration in one file.
  - Mitigation: run Thursday viewport checklist before Friday validation.
