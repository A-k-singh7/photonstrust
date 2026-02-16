# Phase 57: PDK/Foundry Interop Hardening (Research Brief)

Date: 2026-02-16

## Goal

Execute Phase 57 (W29-W32) by hardening PDK and foundry interop across PIC
layout and signoff workflows: formal PDK adapter contract, mandatory PDK
manifest evidence, sealed foundry DRC runner seam, and canonical golden chain
determinism coverage.

## Scope executed

### W29: PDK adapter contract

1. Added a typed adapter contract and capability matrix for portable PDK use.
2. Added adapter conformance validation and registry-backed adapter resolution.
3. Added schema-backed contract tests with toy manifest fixture coverage.

### W30: PDK manifest enforcement

1. Added `pdk_manifest.json` schema and API-level manifest resolution helpers.
2. Enforced manifest presence for certification mode in layout/signoff runs.
3. Emitted deterministic `pdk_manifest.json` artifacts for key PIC endpoints.

### W31: Foundry DRC sealed runner seam

1. Added a metadata-only sealed runner contract for proprietary foundry decks.
2. Added sealed summary schema and API endpoint integration.
3. Added no-leakage and schema coverage for sealed execution outputs.

### W32: Canonical golden chain fixture

1. Added canonical chain fixture for graph -> layout -> KLayout -> LVS-lite ->
   SPICE -> evidence.
2. Added deterministic regression test to lock chain behavior and ordering.
3. Validated fixture execution remains hermetic with mocked KLayout boundaries.

## Source anchors used

- `docs/upgrades/02_upgrade_ideas_pic_and_verification.md`
- `docs/research/deep_dive/28_drc_pdrc_lvs_evidence_pipeline.md`
- `docs/operations/365_day_plan/phase_57_w29_w32_pdk_foundry_interop_hardening.md`
