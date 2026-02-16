# Pilot Readiness Packet v3 (Phase 61 W47/W48)

Use this packet for customer pilot kickoff, pilot-cycle governance, and pilot-to-paid conversion handoff.

v3 keeps prior realism guardrails and adds conversion-focused execution assets for external pilots:

- cycle outcome capture with explicit gate status and conversion risk flags
- external pilot gate logging for week-by-week accountability
- pilot-to-paid memo template for final executive decision packages
- support runbook handoff checklist for post-pilot operational continuity

## Contents

1. `01_pilot_intake_checklist.md` - pre-kickoff intake and go/no-go checks
2. `02_pilot_success_criteria_template.md` - success criteria to agree in week 0
3. `03_claim_boundaries_summary.md` - what PhotonTrust currently claims (and does not claim)
4. `04_day0_operator_runbook.md` - timeline, exact commands, hard acceptance gates, fallback actions
5. `05_external_pilot_cycle_outcome_template.md` - per-cycle outcome capture template
6. `06_external_pilot_gate_log_template.md` - gate decision ledger template for pilot cycles
7. `07_pilot_to_paid_conversion_memo_template.md` - final conversion recommendation memo template
8. `08_support_runbook_handoff_checklist.md` - support ownership handoff checklist
9. `pilot_cycle_01_outcome_example.md` - sample completed cycle artifact (placeholder)
10. `pilot_cycle_02_outcome_example.md` - sample completed cycle artifact (placeholder)

## W47/W48 usage guidance

### Week 47 (external pilot execution and control)

1. Kick off with `01_pilot_intake_checklist.md`, `02_pilot_success_criteria_template.md`, and `04_day0_operator_runbook.md`.
2. Open `06_external_pilot_gate_log_template.md` immediately and append gate decisions after each customer milestone.
3. Complete `05_external_pilot_cycle_outcome_template.md` at the end of each cycle (minimum: one entry per week).
4. Use `pilot_cycle_01_outcome_example.md` as a formatting reference for lightweight but decision-ready records.

### Week 48 (conversion package and handoff)

1. Consolidate cycle outcomes into `07_pilot_to_paid_conversion_memo_template.md`.
2. Confirm claim-safe language from `03_claim_boundaries_summary.md` before external conversion messaging.
3. Run `08_support_runbook_handoff_checklist.md` with support, customer success, and technical owner signoff.
4. Use `pilot_cycle_02_outcome_example.md` as a reference for closeout status framing.

## Completeness check

Run the packet checker before sharing externally:

```bash
py -3 scripts/check_pilot_packet.py
```

The checker exits non-zero if required packet files are missing.
