# Phase 54 W17 Operations Notes (Background Estimator)

Date: 2026-02-16

## Week focus

Add radiance-proxy background estimation with day/night and optics dependence,
while preserving fixed-background override compatibility.

## Refreshed risk table

| Risk ID | Risk | Owner | Likelihood | Impact | Mitigation | Gate trigger | Status |
|---|---|---|---|---|---|---|---|
| P54-R1 | Day/night directionality regresses | QA | Medium | High | Added directional tests (`day > night`) | Radiance direction tests fail | Mitigated |
| P54-R2 | Optics dependence is not reflected in background estimates | SIM | Medium | High | Added FOV/filter/gate scaling in radiance proxy | Optics scaling tests fail | Mitigated |
| P54-R3 | Background uncertainty fields are missing from orbit outputs | DOC | Medium | Medium | Added uncertainty block in point outputs and summaries | Orbit schema/test misses uncertainty fields | Mitigated |
| P54-R4 | Fixed-model users lose backward compatibility | TL | Low | High | Kept `background_model=fixed` default and sample override path | Existing orbit configs fail | Mitigated |
| P54-R5 | Satellite decomposition omits background provenance | SIM | Low | Medium | Added model/day-night fields in channel decomposition | Channel diagnostics tests fail | Mitigated |

## Owner map confirmation

Background-model realism, compatibility defaults, and diagnostics surfacing
remain explicitly owned with no accountable/responsible gaps.
