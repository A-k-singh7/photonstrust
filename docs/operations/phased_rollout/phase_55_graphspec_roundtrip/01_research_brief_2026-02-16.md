# Phase 55: GraphSpec TOML + Round-Trip Guarantees (Research Brief)

Date: 2026-02-16

## Goal

Execute Phase 55 (W21-W24) by adding GraphSpec TOML authoring support,
deterministic GraphSpec formatting and stable hashing, typed port-domain
connection enforcement, and explicit round-trip no-drift guarantees.

## Scope executed

### W21: `.ptg.toml` parser + compiler bridge

1. Added GraphSpec TOML parser and canonical graph normalization utilities.
2. Extended graph load paths to accept JSON and TOML consistently.
3. Added TOML fixture and TOML compile-path test coverage.

### W22: Deterministic formatter + stable hash

1. Added deterministic GraphSpec TOML formatter.
2. Added stable semantic graph hash based on canonicalized payloads.
3. Added CLI formatting command surface for check/write/output/hash workflows.

### W23: Typed ports + invalid connection blocking

1. Added typed port-domain metadata to backend kind registry (`port_domains`).
2. Enforced edge domain compatibility in PIC compiler and diagnostics.
3. Added web editor-side connection blocking for invalid PIC domain wiring.

### W24: Round-trip no-drift guarantee

1. Added canonicalization and round-trip idempotence tests.
2. Added JSON-vs-TOML demo fixture semantic equivalence test via stable hash.
3. Added week-level operations notes and strict rollout artifacts for Phase 55.

## Source anchors used

- `docs/research/deep_dive/27_drag_drop_component_ir_and_non_json_authoring.md`
- `docs/upgrades/02_upgrade_ideas_pic_and_verification.md`
- `docs/operations/365_day_plan/phase_55_w21_w24_graphspec_roundtrip.md`
