# Phase 52: Protocol Expansion (Research Brief)

Date: 2026-02-16

## Goal

Execute Phase 52 (W09-W12) by hardening protocol dispatch contracts, keeping
protocol selection explicit in run artifacts, and adding protocol-aware bound
gate routing to avoid false assertions for relay-family protocols.

## Scope executed

### W09: Protocol module contract refactor

1. Added explicit protocol module contract and registry-based dispatch.
2. Moved `compute_point` protocol routing from inline conditional logic to
   protocol module resolution.
3. Added migration note documenting old-to-new dispatch surface.

### W10: Decoy BB84 v0.1 hardening

1. Kept decoy BB84 implementation as canonical module in protocol registry.
2. Added applicability labels through protocol-module applicability contract.
3. Added protocol registry tests that validate alias and selection behavior.

### W11: MDI-QKD v0.1 hardening

1. Bound MDI selection to explicit module contract with fiber-only
   applicability checks.
2. Added API output assertions confirming protocol metadata remains explicit in
   run summaries and manifests.

### W12: TF/PM preview + bound gate routing update

1. Added protocol gate policy routing (`apply` vs `skip`) for repeaterless bound
   checks by protocol family.
2. Added tests ensuring TF/PM/MDI routes skip naive direct-link PLOB gate
   assertions.
3. Surfaced protocol selection and gate policy in QKD run outputs summaries.

## Source anchors used

- `docs/research/deep_dive/23_protocol_roadmap_and_validation_gates.md`
- `docs/research/deep_dive/03_protocol_validation_matrix.md`
- `docs/upgrades/01_upgrade_ideas_qkd_and_satellite.md`
