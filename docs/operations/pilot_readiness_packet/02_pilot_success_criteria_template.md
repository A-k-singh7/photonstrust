# Pilot Success Criteria Template

**Customer:** ____________________  
**Pilot ID:** ____________________  
**Kickoff date:** ____________________  
**Final review date:** ____________________

## 1) Pilot objective (1 sentence)

> __________________________________________

## 2) Scope in / out

### In scope
- __________________________________________
- __________________________________________

### Out of scope
- __________________________________________
- __________________________________________

## 3) Success metrics (must be measurable)

| Metric | Baseline | Target | Measurement method | Owner | Review date |
|---|---:|---:|---|---|---|
| Time-to-decision (days) | ____ | ____ | kickoff-to-decision log | ____ | ____ |
| Reproducibility rate (%) | ____ | ____ | rerun same config, compare artifacts | ____ | ____ |
| Report acceptance (Y/N) | ____ | ____ | stakeholder signoff on reliability outputs | ____ | ____ |
| Validation pass rate (%) | ____ | ____ | `scripts/run_validation_harness.py` summary | ____ | ____ |
| Day vs night background direction | ____ | ____ | radiance-proxy check (`day > night`) | ____ | ____ |
| Orbit finite-key sensitivity | ____ | ____ | pass-duration budget comparison report | ____ | ____ |
| Benchmark drift status (satellite canonicals) | ____ | ____ | `scripts/check_benchmark_drift.py` | ____ | ____ |

## 4) Mandatory acceptance gates

- [ ] Reliability card v1.1 produced for agreed scenarios.
- [ ] Evidence quality tier explicitly stated on every delivered card.
- [ ] Operating envelope and applicability notes included.
- [ ] Orbit-pass outputs include finite-key budgeting fields and epsilon ledger fields.
- [ ] Radiance-proxy assumptions are explicit (day/night + optics inputs) when model is used.
- [ ] Re-run reproducibility demonstrated on agreed environment.
- [ ] Final review completed with decision memo (go/iterate/no-go).

## 5) Data + evidence deliverables

- [ ] Config set used in pilot
- [ ] Run outputs (cards, summaries, plots)
- [ ] Validation harness output folder
- [ ] Benchmark drift report output (including satellite canonical cases)
- [ ] Optional repro/artifact pack (if requested)

## 6) Risk log (top 3)

1. Risk: ____________________ | Owner: ____________________ | Mitigation date: ____________________
2. Risk: ____________________ | Owner: ____________________ | Mitigation date: ____________________
3. Risk: ____________________ | Owner: ____________________ | Mitigation date: ____________________

## 7) Final pilot decision rubric

- **Success:** all mandatory gates pass + metrics meet target or approved variance.
- **Conditional success:** gates pass, one metric misses target with corrective plan.
- **No-go:** any mandatory gate fails or unresolved critical blocker remains.

**Customer approver:** ____________________  
**PhotonTrust approver:** ____________________  
**Signoff date:** ____________________
