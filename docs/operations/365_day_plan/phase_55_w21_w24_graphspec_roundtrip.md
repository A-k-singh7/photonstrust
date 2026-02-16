# Phase 55 (W21-W24): GraphSpec Round-Trip Guarantees

Source anchors:
- `docs/research/deep_dive/27_drag_drop_component_ir_and_non_json_authoring.md`
- `docs/upgrades/02_upgrade_ideas_pic_and_verification.md`

### W21 (2026-07-06 to 2026-07-12) - `.ptg.toml` parser
- Work: Build GraphSpec parser and TOML-to-canonical-JSON compiler bridge.
- Artifacts: parser module + schema bindings + fixtures.
- Validation: compile path tests for TOML fixtures.
- Exit: TOML authoring is accepted end-to-end.

### W22 (2026-07-13 to 2026-07-19) - Deterministic formatter and hashing
- Work: Add `photonstrust fmt graphspec` and stable graph hash generation.
- Artifacts: formatter command, canonicalization tests.
- Validation: format idempotence tests.
- Exit: GraphSpec files are deterministic and review-friendly.

### W23 (2026-07-20 to 2026-07-26) - Typed ports and connection rules
- Work: Enforce typed port domains and invalid-connection blocking in UI and compiler.
- Artifacts: typed port schema, diagnostics enhancements.
- Validation: invalid connection test matrix.
- Exit: Engineering constraints enforced before simulation.

### W24 (2026-07-27 to 2026-08-02) - Round-trip guarantee
- Work: Guarantee JSON/TOML/UI round-trip without semantic drift.
- Artifacts: round-trip golden fixtures and docs.
- Validation: round-trip equivalence tests.
- Exit: Non-JSON authoring shipped with explicit no-drift guarantees.
