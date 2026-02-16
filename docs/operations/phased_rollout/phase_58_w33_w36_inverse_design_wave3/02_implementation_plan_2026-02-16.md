# Phase 58: Inverse Design Wave 3 (Implementation Plan)

Date: 2026-02-16

## Scope

Implement Phase 58 W33-W36 by strengthening inverse-design evidence contracts,
robustness analytics, plugin boundary metadata governance, and flagship
end-to-end workflow validation in certification mode.

## Owner map lock (release-critical workstreams)

Owner roles follow `docs/research/deep_dive/13_raci_matrix.md`.

| Workstream | Accountable | Responsible | Consulted | Backup |
|---|---|---|---|---|
| Certification evidence gates for inverse-design API/workflow | TL | SIM | QA | DOC |
| Robustness thresholds, worst-case metrics, and schema contract updates | TL | SIM | QA | DOC |
| External solver plugin policy boundary and parity testing | TL | SIM | QA | DOC |
| Flagship fixture + replay/signoff/bundle evidence regression | QA | SIM | TL | DOC |

## Implementation tasks

1. Add robustness-required and threshold evaluation in inverse-design core:
   - `photonstrust/invdesign/_robust.py`
   - `photonstrust/invdesign/mzi_phase.py`
   - `photonstrust/invdesign/coupler_ratio.py`
2. Add external solver plugin boundary metadata contract:
   - `photonstrust/invdesign/plugin_boundary.py`
   - `photonstrust/invdesign/__init__.py`
3. Enforce certification evidence gates and signoff passthrough in API:
   - `photonstrust/api/server.py`
4. Expand inverse-design report schema for new evidence fields:
   - `schemas/photonstrust.pic_invdesign_report.v0.schema.json`
5. Add Phase 58 regression tests and flagship fixture:
   - `tests/test_invdesign_robustness_metrics.py`
   - `tests/test_api_phase58_invdesign_wave3.py`
   - `tests/test_phase58_w36_flagship_invdesign_fixture.py`
   - `tests/fixtures/phase58_w36_flagship_invdesign_component_graph.json`
6. Complete strict rollout docs and weekly operations notes:
   - `docs/operations/week33/phase58_w33_invdesign_evidence_gates_notes_2026-02-16.md`
   - `docs/operations/week34/phase58_w34_robustness_knobs_notes_2026-02-16.md`
   - `docs/operations/week35/phase58_w35_external_solver_plugin_notes_2026-02-16.md`
   - `docs/operations/week35/phase58_w35_external_solver_plugin_policy_2026-02-16.md`
   - `docs/operations/week36/phase58_w36_flagship_fixture_notes_2026-02-16.md`
   - `docs/operations/week36/phase58_w33_w36_consolidated_ops_notes_2026-02-16.md`

## Acceptance gates

- Certification mode rejects incomplete inverse-design evidence artifacts.
- Inverse-design reports include worst-case robustness and threshold evidence.
- Plugin boundary emits policy-safe metadata and preserves artifact parity.
- Flagship fixture passes certification workflow with signoff evidence, replay,
  and bundle checks.
- Targeted tests, full test suite, drift check, release gate, CI checks, and
  validation harness all pass.
