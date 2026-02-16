# Phase 56: DRC/PDRC/LVS Expansion (Implementation Plan)

Date: 2026-02-16

## Scope

Implement Phase 56 W25-W28 by expanding DRC/PDRC/LVS verification outputs for
signoff workflows: route loss-budget checks, signoff-bundle integration,
reviewable violation annotations, and semantic violation diff support.

## Owner map lock (release-critical workstreams)

Owner roles follow `docs/research/deep_dive/13_raci_matrix.md`.

| Workstream | Accountable | Responsible | Consulted | Backup |
|---|---|---|---|---|
| PDRC route loss-budget checks and report schema expansion | TL | SIM | QA | DOC |
| LVS-lite signoff bundle integration and summary governance | TL | SIM | QA | DOC |
| Reviewable violation annotations across DRC/PDRC/LVS outputs | QA | SIM | TL | DOC |
| API/UI violation semantic diff integration and regression tests | TL | SIM | QA | DOC |

## Implementation tasks

1. Extend performance DRC route analysis and report outputs:
   - `photonstrust/verification/performance_drc.py`
   - `photonstrust/reporting/performance_drc_report.py`
   - `schemas/photonstrust.performance_drc.v0.schema.json`
2. Expand LVS-lite signoff and violation surfaces:
   - `photonstrust/verification/lvs_lite.py`
   - `schemas/photonstrust.pic_lvs_lite.v0.schema.json`
3. Add semantic violation diff output in API and render in web run diff:
   - `photonstrust/api/diff.py`
   - `photonstrust/api/server.py`
   - `web/src/App.jsx`
4. Add and update regression coverage:
   - `tests/test_performance_drc_loss_budget.py`
   - `tests/test_performance_drc_schema.py`
   - `tests/test_pic_layout_build_and_lvs_lite.py`
   - `tests/test_api_server_optional.py`
5. Complete strict rollout docs and weekly operations notes:
   - `docs/operations/week25/phase56_w25_pdrc_loss_budget_notes_2026-02-16.md`
   - `docs/operations/week26/phase56_w26_lvs_signoff_notes_2026-02-16.md`
   - `docs/operations/week27/phase56_w27_reviewable_violations_notes_2026-02-16.md`
   - `docs/operations/week28/phase56_w28_violation_diff_notes_2026-02-16.md`

## Acceptance gates

- PDRC reports include route-level loss-budget metrics and actionable findings.
- LVS-lite reports include optional signoff-bundle outcomes and blocking counts.
- Run diff API emits semantic violation buckets where both sides provide
  violation arrays.
- Web run diff displays violation semantic summaries for reviewer workflows.
- Targeted tests, full test suite, drift check, release gate, CI checks, and
  validation harness all pass.
