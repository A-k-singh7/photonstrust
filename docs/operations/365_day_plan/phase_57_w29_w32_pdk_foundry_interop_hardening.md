# Phase 57 (W29-W32): PDK/Foundry Interop Hardening

Source anchors:
- `docs/upgrades/02_upgrade_ideas_pic_and_verification.md`
- `docs/research/deep_dive/28_drc_pdrc_lvs_evidence_pipeline.md`

### W29 (2026-08-31 to 2026-09-06) - PDK adapter contract
- Work: Define adapter contract and capability matrix for public and toy PDKs.
- Artifacts: adapter interface + conformance tests.
- Validation: adapter test suite.
- Exit: Verification flow portable across PDK adapters.

### W30 (2026-09-07 to 2026-09-13) - PDK manifest enforcement
- Work: Include `pdk_manifest.json` in all layout/signoff runs and enforce in certification mode.
- Artifacts: manifest schema + bundle integration.
- Validation: certification run fails when manifest missing.
- Exit: PDK identity and rule context always present in evidence.

### W31 (2026-09-14 to 2026-09-20) - Foundry DRC sealed runner seam
- Work: Add sealed runner contract for proprietary decks (summary metadata only).
- Artifacts: runner interface + summary schema.
- Validation: mock runner integration tests.
- Exit: Enterprise DRC seam available without leaking proprietary decks.

### W32 (2026-09-21 to 2026-09-27) - Canonical golden chain fixture
- Work: Establish one full chain fixture: graph -> layout -> KLayout -> LVS-lite -> SPICE -> evidence.
- Artifacts: canonical fixture, runbook, optional CI lane.
- Validation: full chain determinism checks.
- Exit: Golden chain fixture locked as regression guardrail.
