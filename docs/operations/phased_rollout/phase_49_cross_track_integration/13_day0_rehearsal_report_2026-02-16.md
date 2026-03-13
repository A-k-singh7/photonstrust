# Day-0 Rehearsal Report (Pilot Runbook)

**Date:** 2026-02-16  
**Status:** ✅ PASS (all runbook gates G0–G4)

---

## Rehearsal execution

Run label:
- `day0_rehearsal_20260216T082905Z`

Artifacts:
- Pack dir: `results/demo_pack/day0_rehearsal_20260216T082905Z`
- Reliability card: `results/demo_pack/day0_rehearsal_20260216T082905Z/run/pilot_day0_c1550_phase2e_demo/c_1550/reliability_card.json`
- Harness summary: `results/validation/20260216T082947Z/summary.json`
- Rehearsal summary record: `results/day0_rehearsal/last_rehearsal_summary.json`

---

## Gate results

- **G0** config validate-only (`configs/product/pilot_day0_kickoff.yml`): PASS
- **G1** day-0 demo pack generation + required artifacts present: PASS
- **G2** reliability card schema v1.1 validation: PASS
- **G3** trust metadata + safe-use label checks: PASS
- **G4** validation harness replay (`ok=true`): PASS

---

## Outcome

Pilot day-0 operator flow is confirmed executable end-to-end in the current environment and is ready for live kickoff usage.
