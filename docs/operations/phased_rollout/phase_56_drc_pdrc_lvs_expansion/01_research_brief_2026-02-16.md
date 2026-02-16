# Phase 56: DRC/PDRC/LVS Expansion (Research Brief)

Date: 2026-02-16

## Goal

Execute Phase 56 (W25-W28) by expanding PDRC/LVS outputs for engineering
signoff: route loss-budget analysis, signoff-bundle integration, reviewable
violation annotations, and semantic violation diffing in API/UI run compare.

## Scope executed

### W25: PDRC route loss-budget checks

1. Extended performance DRC to compute per-route proxy loss metrics (length,
   bends, crossings, propagation and aggregate route loss).
2. Added request-side loss-budget settings with defaults and risk grading.
3. Exposed actionable violations and summary fields in report outputs.

### W26: Signoff integration in LVS-lite

1. Integrated optional `signoff_bundle` verification into `pic_lvs_lite` flow.
2. Propagated signoff pass/fail/count fields into report summaries.
3. Extended LVS outputs with annotated violations and blocking counts.

### W27: Reviewable violation outputs

1. Standardized annotated violation surfaces for DRC/PDRC/LVS results.
2. Added structured summary objects (`violation_summary`, `blocking_violations`)
   to support reviewer triage.
3. Extended HTML performance DRC report sections for loss-budget findings.

### W28: Violation diff semantics

1. Added semantic violation diff function (`new`, `resolved`,
   `applicability_changed`) for run comparison.
2. Extended `/v0/runs/diff` output for `scope in {"outputs_summary", "all"}`
   when violation arrays are available on both runs.
3. Added UI run-diff panel rendering for compact violation-semantic summaries.

## Source anchors used

- `docs/research/deep_dive/28_drc_pdrc_lvs_evidence_pipeline.md`
- `docs/research/deep_dive/30_klayout_gds_spice_end_to_end_workflow.md`
- `docs/operations/365_day_plan/phase_56_w25_w28_drc_pdrc_lvs_expansion.md`
