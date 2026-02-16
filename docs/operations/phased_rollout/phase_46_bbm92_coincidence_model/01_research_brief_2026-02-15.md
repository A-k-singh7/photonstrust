# Phase 46: BBM92 Coincidence Model (Research Brief)

Date: 2026-02-15

## Goal

Replace the legacy direct-link BBM92/E91 model in `photonstrust.qkd` (which used an additive QBER error-budget proxy) with a coincidence-based analytical model that is closer to how entanglement-based QKD is actually evaluated:

- explicit coincidence probability per pulse/window (gain) rather than a proxy `p_pair + p_false`,
- explicit accidentals from multi-pair emission and Poisson noise in the coincidence window,
- QBER computed as a mixture of true-pair errors and accidental errors.

The output must remain deterministic, fast, and compatible with the existing Reliability Card surface.

## Model summary

### SPDC multi-pair statistics

For SPDC, model photon-pair number per pulse/window as a two-mode squeezed vacuum (thermal/geometric) distribution with mean pair number `mu`:

`P(n) = mu^n / (1 + mu)^(n+1)`.

### Threshold detection and coincidence definition

We assume threshold detection per window on each side, and define a coincidence as:

"at least one click on Alice AND at least one click on Bob".

Noise clicks are Poisson arrivals within the coincidence window.

### Closed-form coincidence probabilities

Let:

- `eta` be the per-photon end-to-end detection probability (collection/coupling * channel * PDE)
- `b = noise_counts_cps * window_s` be the Poisson mean of noise clicks per window (per side)

Then the total coincidence probability per window (gain) is:

`Q = 1 - 2*exp(-b)/(1 + mu*eta) + exp(-2b)/(1 + mu*(2*eta - eta^2))`.

Define "true" single-pair coincidences as events with no noise clicks and exactly one detected pair without extra detected photons. This yields:

`Q_true = exp(-2b) * [ mu*eta^2 / (1 + mu*(2*eta - eta^2))^2 ]`.

Accidentals:

`Q_acc = Q - Q_true`.

### QBER mixture

Let `e_vis = (1 - V_eff)/2` where `V_eff` is the effective visibility (misalignment/polarization visibility multiplied by an optional HOM/indistinguishability proxy).

Then:

`E = (e_vis*Q_true + 0.5*Q_acc) / Q`.

## References (conceptual anchors)

- Standard treatment of QKD with imperfect devices and coincidence counting is widely covered in QKD reviews; a canonical reference is:
  - Scarani et al., "The security of practical quantum key distribution", Rev. Mod. Phys. 81, 1301 (2009).

This phase implements the physics-consistent coincidence accounting; protocol-complete composable finite-key proofs remain out of scope.
