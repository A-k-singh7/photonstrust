# Phase 52: Protocol Dispatch Migration Notes

Date: 2026-02-16

## What changed

- QKD protocol routing moved from inline conditionals in `photonstrust/qkd.py`
  to registry-driven dispatch in `photonstrust/qkd_protocols/registry.py`.
- Protocol metadata is now represented by an explicit contract:
  - `QKDProtocolModule`
  - `ProtocolApplicability`

## Backward compatibility

- Existing protocol names and aliases remain supported (`BBM92`, `E91`, `BB84`,
  `MDI_QKD`, `PM_QKD`, `TF_QKD`, etc.).
- Missing protocol name still defaults to BBM92 semantics.
- Unknown protocol names still fail fast with `ValueError`.

## New explicit metadata surfaces

- QKD run manifest now carries:
  - `input.protocol_selected`
  - `outputs_summary.qkd.protocol_selected`
- QKD card summaries now carry:
  - `bound_gate_policy.plob_repeaterless_bound` (`apply`/`skip`)
  - `bound_gate_policy.rationale`

## Why this migration is important

- Keeps protocol expansion modular and testable.
- Prevents accidental gate misuse (notably naive PLOB gating for relay-family
  protocols).
- Enables future protocol modules to plug into a stable dispatch/applicability
  contract without modifying core `compute_point` branching logic.
