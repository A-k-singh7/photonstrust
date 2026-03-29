# Satellite QKD Realism Pack (Free-Space, Orbit, Finite-Key, and Evidence)

Date: 2026-02-14

This document is the satellite/free-space counterpart to:
- `16_qkd_deployment_realism_pack.md` (fiber)

Goal:
- make OrbitVerify + QKD claims scientifically defensible for satellite industry use
- upgrade the free-space physics layer in a way that is testable, reproducible, and
  compatible with the evidence bundle discipline

This is not "simulate everything with full atmospherics".
It is a staged realism pack with explicit applicability bounds.

---

## 0) Why Satellite QKD Needs Its Own Realism Pack

Satellite/free-space differs from fiber in the dominant error sources:
- background is often time-varying (day/night, moon, city lights)
- pointing and tracking errors dominate link margins
- turbulence causes fading and intermittency (outage is often the key metric)
- finite-key effects are unavoidable because passes are time-limited

So a "single average loss number" model is not enough for trustable outputs.

---

## 1) Current State in PhotonTrust (Anchor)

Current implementation:
- free-space efficiency model: `photonstrust/channels/free_space.py`
  - geometric efficiency
  - atmospheric transmission using extinction_db_per_km * distance_km * airmass (simplified)
  - pointing loss proxy
  - turbulence efficiency proxy
  - background_counts_cps as config input
- orbit mission templates and run surface exist (phases 11+)

This is a good start, but it needs realism upgrades and stronger artifact labeling.

---

## 2) Realism Pack Philosophy (Scientist-Grade, Not Overclaiming)

Rules:

1) Every upgraded model must declare:
- what it approximates
- where it is valid
- what inputs are required

2) Every satellite result must report:
- uncertainty and outage probability
- parameter sensitivity ranking (what dominates risk)

3) "Preview" and "Certification" must be separate:
- preview: fast, conservative heuristics
- certification: requires higher-fidelity or calibrated parameters, and emits stronger evidence artifacts

---

## 3) Model Upgrades (Stepwise, Testable)

### Upgrade A: Fix atmosphere path length (do not multiply by slant range)

Problem in naive models:
- atmospheric extinction should apply to the atmospheric segment of the path, not the full satellite distance

Proposed model:
- introduce `atmosphere_effective_thickness_km` (default ~10-20 km)
- compute atmospheric path length as:
  - `L_atm_km = atmosphere_effective_thickness_km * airmass(elevation)`
- then:
  - `loss_atm_db = extinction_db_per_km * L_atm_km`

Evidence fields to add:
- `channel_diag.atmosphere_effective_thickness_km`
- `channel_diag.atmosphere_path_km`
- `channel_diag.extinction_db_per_km`

Validation gates:
- monotonic: lower elevation -> higher atmospheric loss
- sensitivity: atmospheric loss should not explode just because satellite range increases

### Upgrade B: Background model (counts as physics, not a raw knob)

Current:
- `background_counts_cps` provided as config

Upgrade path:
- keep the knob as an override, but add a physics-based estimator:
  - `background_model = fixed | radiance_proxy`

Radiance-proxy inputs (minimal):
- telescope FOV
- optical filter bandwidth
- detector gate/window
- day/night flag
- site light pollution proxy (optional)

Outputs:
- background counts estimate with uncertainty bounds

Validation gates:
- day model predicts higher background than night model (all else equal)
- background scales with FOV and filter bandwidth

### Upgrade C: Turbulence as a fading distribution (outage modeling)

Current:
- `eta_turb = exp(-scintillation_index)` (single number)

Upgrade:
- treat turbulence as a random fading variable
- implement at least one fading distribution in v0.1:
  - lognormal (common in weak turbulence regimes)
  - or gamma-gamma (more general)

Outcome:
- instead of a single eta, we get a distribution of eta_turb
- compute:
  - expected key rate
  - outage probability vs a key-rate floor

Validation gates:
- higher scintillation -> higher outage probability
- certification mode requires reporting the assumed turbulence regime

### Upgrade D: Pointing/tracking as a distribution

Current:
- deterministic proxy `eta_point = exp(-(sigma/theta)^2)`

Upgrade:
- define `pointing_jitter` distribution and compute an outage-aware penalty
- include:
  - static bias error
  - dynamic jitter

Outputs:
- expected eta_point and P(eta_point < threshold)

Validation gates:
- increased jitter increases outage probability and decreases expected eta

### Upgrade E: Finite-key is mandatory for satellite passes

Reason:
- passes are limited-duration; block sizes are not infinite

Upgrade:
- require finite-key mode when `scenario.kind = orbit_pass` (or when pass duration < threshold)
- compute signals per pass:
  - rep_rate * pass_duration * duty_cycle * detection probability

Artifacts:
- report:
  - pass duration
  - effective signals per block
  - epsilon and PE fraction

---

## 4) Orbit Scenario Contract (What We Need in Inputs)

Minimum scenario fields:
- orbit pass geometry or precomputed `distance_km(t)` and `elevation_deg(t)`
- time window and sampling step
- day/night (or sun elevation) indicator
- station and payload apertures and optics parameters

Output requirement:
- time series of:
  - eta_total(t)
  - background(t)
  - expected key rate(t) (or per time bin)
- aggregated results:
  - total expected key bits per pass
  - outage probability
  - operating envelope

---

## 5) Evidence and Trust Artifacts (What Makes This "Industry-Trustable")

Every satellite QKD run must produce:

1) Assumptions table:
- what is modeled vs assumed
- which parameters are calibrated vs default

2) Applicability bounds:
- elevation range
- turbulence regime label
- background model regime label

3) Diagnostics:
- airmass and atmosphere path length
- pointing loss and turbulence loss decomposition
- uncertainty bands and outage probabilities

4) Provenance:
- config hash, seeds, dependency versions
- evidence bundle export (Phases 35-36)
- signing (Phase 40)

---

## 6) Validation Strategy (How We Avoid "Toy Model" Dismissal)

You do not need perfect agreement with a specific satellite mission.
You need:
- correct qualitative behavior
- correct scaling in validated envelopes
- literature-anchored regime checks

Benchmark anchors:
- classic satellite-to-ground demonstration (2017)
- modern constraint-focused analyses
- modern microsatellite demonstration (2025)

---

## 7) Phased Rollout Plan (Suggested)

Phase S1 (v0.1): Atmosphere path length correction + required artifact fields
- implement Upgrade A
- tests: monotonicity and non-exploding behavior vs range

Phase S2 (v0.2): Outage-aware turbulence and pointing distributions
- implement Upgrade C and D
- add outage probability fields to reliability cards

Phase S3 (v0.3): Background estimator
- implement Upgrade B with day/night modes

Phase S4 (v0.4): Satellite finite-key pass budgeting
- implement Upgrade E and enforce for orbit scenarios

Each phase must follow:
research -> plan -> build -> validation -> doc updates

---

## Source Index (Web-validated, 2026-02-14)

Satellite QKD anchors:
- Liao et al. (2017) Nature satellite-to-ground QKD, DOI: 10.1038/nature23655
- Bedington et al. (2017) Nature review, DOI: 10.1038/nature23675
- 2025 microsatellite-based real-time QKD (Nature), DOI: 10.1038/s41586-025-08739-z

Constraints and analysis examples:
- Finite key effects in satellite QKD (npj Quantum Information, 2022), DOI: 10.1038/s41534-022-00610-6
- Practical constraints in satellite QKD (Communications Physics, 2023), DOI: 10.1038/s42005-023-01190-0
