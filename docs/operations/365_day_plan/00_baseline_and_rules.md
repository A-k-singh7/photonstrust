# Baseline and Operating Rules

### Current baseline (as of 2026-02-16)
- Phase 49 cross-track integration closed and green.
- RC artifact pack updated and ready for external tagging.
- Day-0 pilot runbook rehearsed and passing.
- QuTiP parity lane exists but remains optional/non-blocking.

Primary anchors:
- `docs/operations/phased_rollout/phase_49_cross_track_integration/10_phase49_closeout_report_2026-02-16.md`
- `docs/operations/phased_rollout/phase_49_cross_track_integration/11_phase5_followthrough_report_2026-02-16.md`
- `docs/operations/phased_rollout/phase_49_cross_track_integration/13_day0_rehearsal_report_2026-02-16.md`
- `docs/results/phase5b_rc_artifact_pack_latest.json`

### Non-negotiable process (every week)
Each weekly scope must follow strict rollout protocol:
1. Research brief
2. Implementation plan
3. Build log
4. Validation report
5. Docs/changelog updates

Required file pattern per phase:
- `01_research_brief_YYYY-MM-DD.md`
- `02_implementation_plan_YYYY-MM-DD.md`
- `03_build_log_YYYY-MM-DD.md`
- `04_validation_report_YYYY-MM-DD.md`

Core gates to remain green continuously:

```bash
python -m pytest -q
python scripts/ci_checks.py
python scripts/release_gate_check.py
python scripts/run_validation_harness.py --output-root results/validation
```

### Ownership model
Use `docs/research/deep_dive/13_raci_matrix.md` for role assignment.

---
