# Product and UX Strategy

This strategy supports both business wedges:
- `ChipVerify`: photonic chip/system verification
- `OrbitVerify`: satellite/space link verification

## Product surfaces

## 1) Engine and APIs (shared core)
- Keep the current Python engine as source of truth.
- Expose stable API endpoints for:
  - run creation,
  - run status/results,
  - card comparison,
  - provenance retrieval.

## 2) Streamlit (internal/reviewer surface)
- Keep Streamlit for internal QA, benchmark triage, and reviewer workflows.
- Do not make Streamlit the primary drag-drop builder.

## 3) Drag-drop web app (primary external UX)
- Introduce graph-based editor for components/topologies.
- Recommended stack: React + React Flow (`@xyflow/react`):
  https://reactflow.dev/
- Output of editor is machine-readable graph JSON that compiles into
  PhotonTrust scenario configs.

## Key UX flows

## Flow A: Build and run
1. User drags components onto canvas.
2. User connects components and sets parameters.
3. System validates graph and compiles scenario config.
4. User runs simulation and receives reliability card + recommendations.

## Flow B: Compare and decide
1. User selects baseline and candidate runs.
2. System shows deltas in key metrics + uncertainty overlap.
3. System highlights dominant error shifts and recommended next actions.

## Flow C: Audit and export
1. User opens provenance panel for any result.
2. System shows config hash, model version, calibration diagnostics.
3. User exports machine + human artifacts (JSON + HTML/PDF).

## UX quality requirements
- p95 graph edit to preview result: under 5 seconds.
- every chart has "why this changed" explanation metadata.
- no card export allowed if diagnostics gates fail.
- all external-facing decisions link back to provenance fields.

## Design-system rules
- Node cards must show trust level and data freshness.
- Side panel must separate:
  - model assumptions,
  - calibrated parameters,
  - policy/compliance tags.
- Comparison tables must default to uncertainty-aware ordering, not raw value
  sorting only.

## Adoption checklist
- short guided walkthroughs for three scenarios:
  - tape-out precheck,
  - detector trade study,
  - satellite pass rehearsal.
- quickstart in under 20 minutes from install to first card.
- pilot-ready templates and example projects.

## Related docs
- `10_roadmap_and_milestones.md`
- `12_web_research_update_2026-02-12.md`
- `13_business_expansion_and_build_plan_2026-02-12.md`
