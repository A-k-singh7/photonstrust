# Calibration and Uncertainty

This document defines calibration workflows and uncertainty propagation.

## Calibration Inputs
- emitter: g2_0, lifetime, HOM proxy, brightness
- detector: dark counts, jitter histogram, PDE
- memory: T1, T2, retrieval efficiency

## Bayesian Inference
- Priors defined per component
- Likelihood based on measured observables
- Outputs: posterior mean, std, p5/p95

## Uncertainty Propagation
- Sample posterior parameters
- Recompute QKD/teleportation metrics
- Report confidence intervals on reliability card

## Active Experiment Design (optional)
- Choose next measurement to maximize information gain

## Quality Checklist
- Posterior summaries reproducible with seeds
- Confidence intervals included in reports
- Calibration configs stored in reproducibility bundle

## Web Research Extension (2026-02-12)
See `12_web_research_update_2026-02-12.md` section `05 Calibration and uncertainty: metrology baseline`.

