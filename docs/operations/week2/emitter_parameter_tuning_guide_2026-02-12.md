# Emitter Parameter Tuning Guide - Week 2 (2026-02-12)

This guide documents how to tune emitter-cavity inputs for stable and
reproducible PhotonTrust outputs during M1.

## Scope
Applies to emitter-cavity source configs consumed by:
- `photonstrust.physics.emitter.get_emitter_stats`
- `photonstrust.qkd.compute_point`

## Tunable parameters
| Parameter | Meaning | Typical range | Notes |
| --- | --- | --- | --- |
| `radiative_lifetime_ns` | bare emitter lifetime | 0.3 to 5.0 | must be positive |
| `purcell_factor` | cavity-enhanced emission factor | 1 to 20 | higher increases emission probability |
| `dephasing_rate_per_ns` | coherence loss rate | 0 to 2 | higher generally reduces photon quality |
| `drive_strength` | cavity drive amplitude (QuTiP path) | 0.01 to 0.2 | keep small for stable steady-state behavior |
| `pulse_window_ns` | detection window length | 2x to 8x lifetime | too short loses counts; too long can increase noise |
| `g2_0` | multiphoton correlation proxy | 0 to 0.2 target | clamped to `[0, 1]` by model guardrails |
| `seed` | run-level deterministic seed tag | integer | used for reproducibility tracking |

## Recommended tuning workflow
1. Start from calibrated hardware priors or measured defaults.
2. Run analytic backend first to establish monotonic trends.
3. Sweep one parameter at a time while fixing all others.
4. Confirm expected trends:
   - `purcell_factor` up -> `emission_prob` up
   - `g2_0` up -> `p_multi` up -> key rate down
5. If QuTiP backend is used, compare against analytic trend direction.
6. Capture selected parameters in scenario config and keep `seed` stable.

## New diagnostics emitted by model
`get_emitter_stats` now returns a `diagnostics` block with:
- `lifetime_ns`
- `purcell_factor`
- `pulse_window_ns`
- `gamma_eff_per_ns`
- `window_over_lifetime`
- `dephasing_rate_per_ns`
- `drive_strength`

QuTiP backend adds:
- `gamma_per_ns`
- `kappa_per_ns`
- `n_photon_ss`

Operational use:
- treat `window_over_lifetime` outside roughly `2-8` as a review signal
- track `gamma_eff_per_ns` shifts when comparing runs
- keep `n_photon_ss` in a physically plausible regime for your setup

## Guardrails and fallback behavior
- Non-positive lifetime/purcell/window values are replaced by safe defaults
  with warnings.
- Non-finite or out-of-range `g2_0`/probabilities are clamped.
- If QuTiP backend is requested but unavailable, PhotonTrust falls back to
  analytic backend and records `fallback_reason`.

## Validation checklist for Week 2
- `tests/test_emitter_model.py` passes.
- Emitter output is deterministic for fixed source config + seed tag.
- Trend check (`purcell_factor` increase) passes.
- Invalid input stabilization checks pass.
- QKD path does not mutate source input parameters.

