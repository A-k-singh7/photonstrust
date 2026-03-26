# Phase 44: QKD Fidelity Foundations (Implementation Plan)

Date: 2026-02-15

## Scope

Implement three foundational fixes:

1) Unify rate->probability mapping for noise clicks (Poisson arrivals)
2) Unify dead-time saturation model (non-paralyzable default)
3) Treat fiber polarization drift as visibility/misalignment penalty (QBER) rather than attenuation

## Files to change

### Shared helpers

- `photonstrust/photonstrust/qkd_protocols/common.py`
  - Update `per_pulse_prob_from_rate()` to use numerically stable `expm1`.
  - Add `apply_dead_time()` helper with selectable models:
    - `nonparalyzable` (default)
    - `paralyzable`
    - `legacy` (first-order)
  - Add `misalignment_error_with_visibility_factor()` helper to combine protocol visibility/misalignment with an external visibility factor.

### Direct-link QKD

- `photonstrust/photonstrust/qkd.py`
  - Replace `p_noise_base = noise_counts_cps * window_s` with Poisson mapping.
  - Clamp `p_false` to [0, 1].
  - Replace dead-time first-order correction with `apply_dead_time()`.
  - Remove polarization drift multiplication into `eta_channel` and instead fold it into misalignment/QBER.
  - Update `q_timing` attribution to use the difference vs a reference window (still a proxy, but consistent under Poisson mapping).

### Relay protocols

- `photonstrust/photonstrust/qkd_protocols/mdi_qkd.py`
  - Fold polarization drift into misalignment.
  - Replace dead-time first-order saturation with `apply_dead_time()`.

- `photonstrust/photonstrust/qkd_protocols/pm_qkd.py`
  - Fold polarization drift into misalignment.
  - Replace dead-time first-order saturation with `apply_dead_time()`.

### Schemas / registry

- `photonstrust/schemas/photonstrust.config.demo1.schema.json`
  - Add optional fields surfaced by runtime models:
    - `channel.polarization_coherence_length_km`
    - `detector.dead_time_model`
    - `protocol.misalignment_prob`, `protocol.optical_visibility`
    - `source.hom_visibility`, `source.indistinguishability`

- `photonstrust/schemas/photonstrust.reliability_card.v1.schema.json`
  - Add optional traceability fields to `inputs.source` and `inputs.protocol`:
    - source visibility proxies
    - protocol visibility/misalignment knobs

### Tests

- Update polarization semantics test:
  - `photonstrust/tests/test_completion_quality.py`

- Add Phase 44 semantics unit tests:
  - `photonstrust/tests/test_qkd_semantics.py`

- Canonical baselines:
  - Regenerate fixture via `py scripts/generate_phase41_canonical_baselines.py`.

## Validation gates

- `py -m pytest -q` must pass.
- New semantics tests must pass:
  - Poisson mapping matches `1 - exp(-lambda)`.
  - Dead-time output matches non-paralyzable formula.
  - Polarization coherence length increases QBER (misalignment) without changing attenuation/loss.
