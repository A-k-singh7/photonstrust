# Phase 56 (W25-W28): DRC/PDRC/LVS Expansion

Source anchors:
- `docs/research/deep_dive/28_drc_pdrc_lvs_evidence_pipeline.md`
- `docs/research/deep_dive/30_klayout_gds_spice_end_to_end_workflow.md`
- `docs/operations/phased_rollout/phase_49_cross_track_integration/14_pic_upgrade_wave2_2026-02-16.md`

### W25 (2026-08-03 to 2026-08-09) - PDRC loss-budget checks
- Work: Extend PDRC with route-based loss checks (length, bends, crossings).
- Artifacts: new PDRC rules and report fields.
- Validation: proxy monotonicity tests.
- Exit: PDRC includes actionable loss-risk findings.

### W26 (2026-08-10 to 2026-08-16) - Resonance and phase-shifter checks
- Work: Integrate resonance alignment and phase-range/power checks into signoff bundle.
- Artifacts: expanded PIC verification core outputs.
- Validation: `tests/test_pic_layout_verification_core.py`
- Exit: Multi-check signoff bundle pass/fail logic stable.

### W27 (2026-08-17 to 2026-08-23) - Reviewable violation outputs
- Work: Add violation coordinates/annotations for DRC/PDRC/LVS findings.
- Artifacts: enhanced artifact pack and run viewer support.
- Validation: reviewer walkthrough dry run.
- Exit: Violations are explainable and locatable without manual reverse engineering.

### W28 (2026-08-24 to 2026-08-30) - Violation diff semantics
- Work: Add new/resolved violation diff and changed-applicability diff.
- Artifacts: run diff API and UI updates.
- Validation: diff regression tests.
- Exit: Run comparison supports engineering signoff workflow.
