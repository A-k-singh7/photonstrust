# Phase 44: QKD Fidelity Foundations (Research Brief)

Date: 2026-02-15

## Goal

Increase baseline physics fidelity and internal consistency of QKD evaluation across direct-link and relay protocol families by:

- using a single, bounded mapping from count rates to per-window click probabilities (Poisson arrivals),
- using a detector dead-time throughput model that matches the stochastic detector backend semantics,
- treating fiber polarization drift as a visibility/misalignment effect (QBER) rather than as channel attenuation.

This phase intentionally targets "foundations" changes that are:

- low-risk to implement,
- analytically tractable,
- testable with deterministic unit tests,
- reusable across BBM92/E91 and relay protocols (MDI/PM/TF).

## Why these changes matter

### A) Rate -> probability semantics

Direct-link BBM92 previously used a linear approximation for noise clicks:

`p_noise ~= noise_counts_cps * window_s`

This is only valid for small `lambda = noise_counts_cps * window_s` and can become unphysical (`p_noise > 1`) at large windows or high backgrounds.

Relay protocol modules already used Poisson arrivals.

Target: unify all protocols to use:

`p_noise = 1 - exp(-lambda)`

with a numerically stable implementation for small `lambda`.

### B) Dead-time saturation model

The code previously used a first-order dead-time correction:

`r_out ~= r_in * max(0, 1 - r_in * tau)`

This is a small-signal approximation and collapses to zero at `r_in * tau >= 1`.

The stochastic detector backend implements non-paralyzable event filtering (reject clicks inside the dead-time interval), so the analytic models should match a non-paralyzable throughput law by default:

`r_out = r_in / (1 + r_in * tau)`

Optionally, we keep a paralyzable form available:

`r_out = r_in * exp(-r_in * tau)`

### C) Polarization drift should not be modeled as attenuation

Fiber polarization drift/mismatch primarily reduces interference visibility (and therefore increases misalignment/QBER) rather than acting like absorption loss. Modeling it as attenuation incorrectly reduces herald/event rates without increasing QBER, and mixes concepts (loss vs mode overlap).

Target: interpret the existing polarization drift factor `exp(-distance / coherence_length)` as a visibility multiplier and fold it into the protocol misalignment term.

## References / anchors

This phase implements standard detection and link-modeling conventions:

- Poisson arrivals: probability of at least one count in a window is `1 - exp(-rate * window)`.
- Dead-time throughput:
  - non-paralyzable counter model: `r_out = r_in / (1 + r_in * tau)`
  - paralyzable counter model: `r_out = r_in * exp(-r_in * tau)`

No protocol security proof changes are made in this phase; it strictly improves the physical consistency of noise and detector saturation semantics.
