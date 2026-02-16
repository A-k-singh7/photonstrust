# External Pilot Gate Log Template

Use this as the running gate ledger for the external pilot.

**Customer:** ____________________  
**Pilot ID:** ____________________  
**Packet owner:** ____________________

## Gate log

| Date | Week/Cycle | Gate ID | Gate description | Decision (PASS/HOLD/FAIL) | Owner | Replay date | Evidence path | Notes |
|---|---|---|---|---|---|---|---|---|
| ____ | ____ | G0 | Pre-run readiness and config validation | ____ | ____ | ____ | ____ | ____ |
| ____ | ____ | G1 | Artifact generation and manifest presence | ____ | ____ | ____ | ____ | ____ |
| ____ | ____ | G2 | Reliability card schema and trust fields | ____ | ____ | ____ | ____ | ____ |
| ____ | ____ | G3 | Validation harness replay in target environment | ____ | ____ | ____ | ____ | ____ |
| ____ | ____ | G4 | Drift governance and canonical benchmark check | ____ | ____ | ____ | ____ | ____ |

## Decision rules

- PASS: gate criteria met with evidence attached.
- HOLD: temporary blocker; replay planned and dated.
- FAIL: not acceptable for current cycle close; escalate to pilot owner.

## Escalation record

| Date | Trigger | Escalated to | Action | Resolution date | Status |
|---|---|---|---|---|---|
| ____ | ____ | ____ | ____ | ____ | ____ |

## Weekly close checklist

- [ ] All gate rows for the week are filled.
- [ ] Each HOLD/FAIL entry has owner and replay date.
- [ ] Evidence links are valid and accessible.
- [ ] Cycle outcome document references this log.
