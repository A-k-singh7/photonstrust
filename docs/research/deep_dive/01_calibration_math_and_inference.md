# Calibration Math and Inference

This document defines the calibration model in explicit mathematical and
engineering terms so implementation remains consistent across releases.

## Calibration objective
Given measurements `y` from hardware, infer parameter vector `theta` for
emitter, detector, and memory models, with uncertainty:

- Emitter parameters: `theta_e = {tau_rad, Fp, gamma_phi, g2_0, beta}`
- Detector parameters: `theta_d = {eta_det, dcr, sigma_j, p_ap, t_dead}`
- Memory parameters: `theta_m = {T1, T2, eta_store, eta_ret}`

Target output: posterior `p(theta | y)` with actionable summaries.

## Data model
### Measurement families
- Lifetime traces (time-resolved fluorescence)
- Correlation data for `g2(0)`
- HOM visibility proxies
- Detector click streams and jitter histograms
- Memory retrieval and coherence decay curves

### Observation schema requirements
- Each measurement must include unit metadata.
- Each measurement set must include acquisition context:
  - temperature, repetition rate, wavelength, detector settings.
- Every dataset must include a measurement hash for provenance.

## Probabilistic model
### Prior model
Use bounded, physically meaningful priors by default.

- `tau_rad ~ LogNormal(mu_tau, sigma_tau)`
- `Fp ~ LogNormal(mu_fp, sigma_fp)`
- `gamma_phi ~ HalfNormal(sigma_phi)`
- `g2_0 ~ Beta(alpha_g2, beta_g2)`
- `eta_det ~ Beta(alpha_eta, beta_eta)`
- `dcr ~ LogNormal(mu_dcr, sigma_dcr)`
- `T1, T2 ~ LogNormal(mu_T, sigma_T)`

### Likelihood examples
- Lifetime data:
  - `I(t) = A * exp(-t / tau_eff) + b`
  - Gaussian noise likelihood for calibrated detectors
- `g2(0)` counts:
  - Poisson or Negative Binomial likelihood depending on overdispersion
- Jitter histogram:
  - Gaussian mixture likelihood if asymmetry exists
- Memory fidelity vs wait:
  - `F(t) = 0.5 + 0.5 * exp(-t / T2_eff)` with Gaussian residuals

### Posterior
`p(theta | y) proportional p(y | theta) p(theta)`

Use NUTS/HMC when gradients are stable, else use robust MCMC (emcee) with
adaptive proposal scaling.

## Inference engine requirements
- Minimum posterior effective sample size (ESS): 500 per key parameter.
- Convergence diagnostic:
  - R-hat < 1.01 for all key parameters.
- Divergence threshold:
  - Fewer than 0.5% divergent transitions for HMC workflows.

## Posterior summary outputs
For each parameter:
- posterior mean, median
- standard deviation
- 5th, 50th, 95th quantiles
- ESS and R-hat

Store summaries in calibration artifacts and propagate to Reliability Cards.

## Model selection and mismatch handling
- If posterior predictive checks fail:
  - escalate likelihood complexity (mixture noise models)
  - inspect hidden confounders (temperature drift, detector saturation)
  - split calibration by device regime (low/high rate)

## Posterior predictive checks
- Simulate synthetic observables using posterior samples.
- Compare predicted distributions vs observed histograms.
- Require overlap score above threshold for acceptance.

## Engineering implementation checklist
- Add typed calibration result objects.
- Persist full posterior traces for reproducibility.
- Store random seeds and library versions.
- Add calibration report with diagnostics tables.

## Definition of done
- Calibration command outputs posterior summary and diagnostics.
- Posterior predictive checks pass for at least one benchmark per component.
- Reliability Card includes uncertainty intervals from posterior samples.


## Inline citations (web, verified 2026-02-12)
Applied to: calibration objective, probabilistic model, posterior diagnostics, and predictive checks.
- JCGM 100:2008 (GUM): https://www.bipm.org/en/doi/10.59161/JCGM100-2008E
- JCGM 101:2008 (Monte Carlo propagation supplement): https://www.bipm.org/en/doi/10.59161/jcgm101-2008
- JCGM 102:2011 (multi-output extension): https://www.bipm.org/fr/doi/10.59161/jcgm102-2011
- JCGM GUM-1:2023 (intro update): https://www.bipm.org/en/doi/10.59161/jcgmgum-1-2023
- Improved R-hat diagnostic (Vehtari et al.): https://arxiv.org/abs/1903.08008
- ArviZ diagnostics reference: https://python.arviz.org/en/stable/api/diagnostics.html
- Stan posterior predictive checks: https://mc-stan.org/docs/stan-users-guide/posterior-predictive-checks.html

