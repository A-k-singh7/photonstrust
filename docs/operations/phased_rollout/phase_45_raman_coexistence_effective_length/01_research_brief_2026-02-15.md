# Phase 45: Raman Coexistence Effective-Length Model (Research Brief)

Date: 2026-02-15

## Goal

Replace the unphysical "linear in distance" Raman coexistence term with an attenuation-aware analytic model that:

- remains calibration-friendly (single scalar coefficient),
- captures the correct saturating / diminishing-returns behavior with distance,
- differentiates co- vs counter-propagation via the underlying fiber-loss integrals,
- supports relay protocols by summing per-arm Raman contributions.

## Problem

The legacy Raman model scaled received Raman counts as:

`R ~ k * L * P * BW * Nch`

This implies unbounded linear growth in received Raman noise with fiber length `L`, which is not physically consistent when pump and Raman photons attenuate along the fiber.

## Model (analytic effective interaction length)

Let `L` be the fiber length, `z` the position along fiber measured from the classical launch point (`z=0`) to the receiver (`z=L`).

- Classical pump power decays as `P_p(z) = P_launch * exp(-a_p z)`.
- Raman photons generated at `z` attenuate to the receiver as `exp(-a_s * (L - z))`.

Assume a calibration coefficient `k` in units `cps/(km*mW*nm)` and filter bandwidth `BW` in nm.

### Co-propagation

Received Raman counts:

`R_rx = k * P_launch * BW * L_eff_co`

with:

`L_eff_co = exp(-a_s L) * (1 - exp(-(a_p - a_s) L)) / (a_p - a_s)`

and stable equal-loss limit (`a_p -> a_s`):

`L_eff_co = L * exp(-a_s L)`

### Counter-propagation (backscattered)

`L_eff_counter = (1 - exp(-(a_p + a_s) L)) / (a_p + a_s)`

and zero-loss limit (`a_p + a_s -> 0`):

`L_eff_counter = L`

### Attenuation units

The model uses power-attenuation coefficients in Np/km, derived from dB/km:

`a = (ln(10)/10) * alpha_db_per_km`

## Applicability / calibration notes

- The coefficient `k` remains deployment-specific and should be calibrated from measured background counts under a known WDM plan and filter bandwidth.
- Optional direction multipliers are retained as knobs to account for practical asymmetries (filtering, capture efficiency) beyond the minimal integral model.
