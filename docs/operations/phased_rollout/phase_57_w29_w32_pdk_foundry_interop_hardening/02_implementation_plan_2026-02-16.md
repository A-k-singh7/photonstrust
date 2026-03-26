# Phase 57: PDK/Foundry Interop Hardening (Implementation Plan)

Date: 2026-02-16

## Scope

Implement Phase 57 W29-W32 by hardening PDK/foundry interop for deterministic
engineering signoff workflows: adapter contract portability, enforced PDK
manifest evidence, sealed foundry DRC integration seam, and canonical chain
determinism fixtures.

## Owner map lock (release-critical workstreams)

Owner roles follow `docs/research/deep_dive/13_raci_matrix.md`.

| Workstream | Accountable | Responsible | Consulted | Backup |
|---|---|---|---|---|
| PDK adapter contract and capability matrix | TL | SIM | QA | DOC |
| API-level PDK manifest enforcement and artifact emission | TL | SIM | QA | DOC |
| Foundry DRC sealed runner contract and no-leakage schema | TL | SIM | QA | DOC |
| Canonical golden chain fixture and determinism regression | QA | SIM | TL | DOC |

## Implementation tasks

1. Add adapter contract + capability matrix surfaces:
   - `photonstrust/pdk/adapters.py`
   - `photonstrust/pdk/registry.py`
   - `schemas/photonstrust.pdk_adapter_contract.v0.schema.json`
2. Enforce and emit `pdk_manifest.json` across layout/signoff APIs:
   - `photonstrust/api/server.py`
   - `schemas/photonstrust.pdk_manifest.v0.schema.json`
3. Add sealed foundry DRC seam and schema:
   - `photonstrust/layout/pic/foundry_drc_sealed.py`
   - `schemas/photonstrust.pic_foundry_drc_sealed_summary.v0.schema.json`
4. Add deterministic golden chain fixture and tests:
   - `tests/fixtures/phase57_w32_canonical_pic_chain_graph.json`
   - `tests/test_golden_chain_fixture.py`
5. Complete strict rollout docs and weekly operations notes:
   - `docs/operations/week29/phase57_w29_pdk_adapter_contract_notes_2026-02-16.md`
   - `docs/operations/week30/phase57_w30_pdk_manifest_enforcement_notes_2026-02-16.md`
   - `docs/operations/week31/phase57_w31_foundry_drc_sealed_runner_notes_2026-02-16.md`
   - `docs/operations/week32/phase57_w32_canonical_golden_chain_notes_2026-02-16.md`
   - `docs/operations/week32/phase57_w29_w32_consolidated_ops_notes_2026-02-16.md`

## Acceptance gates

- Adapter validation passes for registry and toy PDK contract surfaces.
- Certification-mode flows fail fast when `pdk_manifest` is missing.
- Sealed foundry DRC outputs include only approved summary metadata fields.
- Canonical chain fixture remains deterministic across repeated executions.
- Targeted tests, full test suite, drift check, release gate, CI checks, and
  validation harness all pass.
