# Uncertainty Propagation and Reporting

This document specifies uncertainty propagation from calibrated parameters to
network metrics and reliability labels.

## Objective
Convert parameter uncertainty into uncertainty on:
- key rate
- fidelity
- throughput
- outage probability

## Input uncertainty sources
- calibration posterior uncertainty
- measurement uncertainty in fiber loss, jitter, dark count
- model structure uncertainty (optional scenario branching)

## Propagation strategy
### Primary path: posterior Monte Carlo
1. Sample `theta^(i)` from posterior.
2. Run scenario simulation with deterministic seed offset.
3. Collect metric outputs `m^(i)`.
4. Compute credible intervals and risk metrics.

### Secondary path: local sensitivity approximation
- For rapid UI previews, use local Jacobian around posterior mean.
- Mark these outputs as approximate in UI/report metadata.

## Confidence/credible interval policy
- Use central 90% interval by default (`p5`, `p95`).
- For operational risk, also report `p1` and `p99` where available.

## Outage probability semantics
Define outage for each use-case explicitly.

- QKD outage:
  - `R_key < R_target` OR `QBER > QBER_max`
- Repeater outage:
  - throughput below SLA threshold
- Teleportation outage:
  - fidelity below SLA threshold

Report `P(outage)` estimated from posterior runs.

## Error budget attribution under uncertainty
- Compute contribution distribution for each error source.
- Report dominant source as mode of posterior source ranking.
- Include uncertainty bar for source fractions.

## Reliability Card mapping
- Add uncertainty panel fields:
  - metric mean
  - metric p5/p95
  - outage probability
- Add confidence badge:
  - low / medium / high confidence based on interval width.

## Performance constraints
- Minimum posterior samples for final reports: 500
- Minimum for quick interactive mode: 100
- Cache intermediate physics components by parameter hash.

## Validation checklist
- Synthetic recovery test: known uncertainty in, recovered uncertainty out.
- Seed reproducibility test for uncertainty summaries.
- Interval monotonicity sanity test across distance sweep.

## Definition of done
- All flagship demos include uncertainty bounds and outage probability.
- Reliability Cards show interval fields consistently.
- Uncertainty mode documented in CLI and UI.


## Inline citations (web, verified 2026-02-12)
Applied to: uncertainty source modeling, Monte Carlo propagation, interval policy, and reporting semantics.
- JCGM 100:2008 (GUM): https://www.bipm.org/en/doi/10.59161/JCGM100-2008E
- JCGM 101:2008 (Monte Carlo propagation): https://www.bipm.org/en/doi/10.59161/jcgm101-2008
- JCGM 102:2011 (multivariate outputs): https://www.bipm.org/fr/doi/10.59161/jcgm102-2011
- JCGM 106:2012 (uncertainty in conformity assessment): https://www.bipm.org/en/doi/10.59161/jcgm106-2012
- FAIR data principles (Scientific Data): https://doi.org/10.1038/sdata.2016.18
- ArviZ diagnostics: https://python.arviz.org/en/stable/api/diagnostics.html
