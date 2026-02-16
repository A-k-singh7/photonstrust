# Emitter Validation Report - Week 2 (2026-02-12)

Status: completed

## Scope
Validation of emitter model hardening and deterministic behavior for:
- `photonstrust.physics.emitter`
- emitter use path in `photonstrust.qkd.compute_point`

## Validation checks
1. Deterministic output for fixed source config and seed tag.
2. Expected trend check:
   - higher `purcell_factor` increases `emission_prob`.
3. Input stabilization:
   - invalid lifetime/window are defaulted with warnings
   - out-of-range `g2_0` is clamped.
4. QKD path immutability:
   - emitter stats must not mutate source config (`g2_0` regression guard).

## Test evidence
Test file added:
- `tests/test_emitter_model.py`

Full suite run:
```bash
pytest -q
```

Observed result on `2026-02-12`:
- `11 passed`
- warnings limited to expected invalid-input warning paths in targeted test

## Code changes validated
- `photonstrust/physics/emitter.py`
  - diagnostics block added
  - input guardrails added
  - backend fallback metadata added
- `photonstrust/qkd.py`
  - removed source mutation from emitter stats ingestion path

## Exit decision
Week 2 emitter hardening exit criteria are met for current baseline.

