# Phase 26 — PIC Solver Extensions (Rings v0.2)

## Metadata
- Work item ID: PT-PHASE-26
- Date: 2026-02-13
- Scope: Make `pic.ring` non-placeholder by adding a wavelength-dependent 2-port ring resonator response model suitable for sweeps and compact-model-style inspection.

## Problem Statement
PhotonTrust’s PIC simulator can already:
- run wavelength sweeps,
- compose simple feed-forward components (2-port chains, DAG mixing).

But `pic.ring` is currently a placeholder treated as lumped insertion loss, which blocks:
- filter response demos,
- ring-based verification checks,
- and credibility for photonics workflows.

## Scientific/Model Choice (v0.2)
Implement a **single-bus all-pass ring resonator** as a 2-port element with a closed-form complex transfer function.

Definitions:
- `r` = self-coupling amplitude (0..1)
- `kappa` = power coupling ratio (0..1), `r = sqrt(1 - kappa)`
- `a` = round-trip amplitude transmission (0..1), derived from propagation loss
- `phi(λ)` = round-trip phase

Through transfer (common all-pass form):
```
H(λ) = (r - a * exp(-j*phi)) / (1 - r*a*exp(-j*phi))
```

This yields resonance notches when coupling/loss align (near critical coupling).

## Practical Constraints
- We keep the simulator forward-only; the ring is modeled as a lumped 2-port response (no explicit feedback loops).
- This is compatible with the existing chain solver and DAG solver.
- Parameters remain physically interpretable and simple:
  - `radius_um` or `round_trip_length_um`
  - `n_eff`
  - `loss_db_per_cm`
  - `coupling_ratio`

## Exit Criteria
- `pic.ring` produces a wavelength-dependent complex transfer when provided resonator params.
- A sweep test demonstrates a resonance notch (non-flat transmission vs wavelength).
- Backwards compatibility: legacy `insertion_loss_db`-only ring remains supported.
- Gates pass.

