# Phase 52 (W9-W12): Protocol Expansion

Source anchors:
- `docs/research/deep_dive/23_protocol_roadmap_and_validation_gates.md`
- `docs/research/deep_dive/03_protocol_validation_matrix.md`
- `docs/upgrades/01_upgrade_ideas_qkd_and_satellite.md`

### W09 (2026-04-13 to 2026-04-19) - Protocol module contract refactor
- Work: Split protocol logic into explicit protocol modules and dispatch interface.
- Artifacts: protocol base interface, migration notes, compatibility tests.
- Validation: regression baseline checks.
- Exit: Protocol selection explicit in config and artifacts.

### W10 (2026-04-20 to 2026-04-26) - Decoy BB84 v0.1
- Work: Implement decoy BB84 preview path with theory sanity and monotonicity gates.
- Artifacts: module + canonical scenario + benchmark test.
- Validation: QBER/rate bound tests and trend tests.
- Exit: Decoy BB84 available with applicability labels.

### W11 (2026-04-27 to 2026-05-03) - MDI-QKD v0.1
- Work: Implement MDI surface with visibility/asymmetry behavior checks.
- Artifacts: MDI protocol module, benchmark fixture, docs.
- Validation: MDI-specific validation matrix tests.
- Exit: MDI outputs integrated into reliability card pipeline.

### W12 (2026-05-04 to 2026-05-10) - TF/PM preview + bound gate update
- Work: Add TF/PM preview protocol surfaces and protocol-aware bound gate routing.
- Artifacts: TF/PM modules, gate routing tests, applicability docs.
- Validation: protocol matrix and bound-gate tests.
- Exit: No false PLOB-style failures for TF-family flows.
