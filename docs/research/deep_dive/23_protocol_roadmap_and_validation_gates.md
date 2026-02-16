# Protocol Roadmap + Validation Gates (QKD + Quantum Networking)

Date: 2026-02-14

This document answers:
- What protocols should PhotonTrust implement next (and in what order)?
- What validation gates make each protocol "trustable" (not just implemented)?
- How do we avoid over-claiming when protocol security models differ?

This is written to be executable under the repo discipline:
research -> plan -> build -> validate -> doc updates
(`docs/research/deep_dive/15_research_to_build_protocol.md`).

---

## 0) Where We Are Today (Reality)

PhotonTrust currently has a QKD performance model centered on an
entanglement-based link abstraction in `photonstrust/qkd.py`:

- supports fiber and free-space channel models
- includes background + Raman coexistence hooks
- includes a simple finite-key penalty toggle
- produces breakdown terms for QBER contributions
- has sanity-gate tests including a PLOB bound test (Phase 39)

This is a strong base, but it is not yet "modern protocol coverage".

---

## 1) Protocol Taxonomy (What "Protocol" Means in This Repo)

To keep architecture clean, treat a protocol as a *contracted mapping*:

Inputs:
- source model (photon statistics / visibility)
- channel model (loss + background + turbulence/pointing if free-space)
- detector model (PDE, dark counts, dead time, jitter, afterpulsing)
- reconciliation/privacy parameters
- finite-key settings (block size, epsilon, PE fraction, etc.)

Outputs (must be stable and comparable):
- key rate (bps) with uncertainty and outage probability
- a QBER (or equivalent excess noise) breakdown
- explicit applicability bounds and evidence tier label

This contract must stay stable across protocol families so the UI and evidence
pipeline remains composable.

---

## 2) Priority Protocol Roadmap (High Leverage, Non-Optional)

### Tier A (must-have for credibility in 2026)

1) Decoy-state BB84 (prepare-and-measure)
- Why:
  - baseline of deployed QKD (and the literature benchmark ecosystem)
  - essential for fiber deployments and performance comparisons
- What changes:
  - new source model: weak coherent pulses (WCP) + decoy intensities
  - yields and error rates per photon number need estimation
- Validation gates:
  - rate scales correctly with transmittance in the asymptotic limit
  - known monotonicities: increasing loss decreases key rate, higher dark counts increases QBER
  - reproduce a small set of published regime curves (trend + envelope)

Anchor:
- Lo, Ma, Chen (2005) decoy-state QKD, Phys. Rev. A, DOI: 10.1103/PhysRevA.72.012326

2) MDI-QKD (measurement-device-independent)
- Why:
  - removes detector side-channel attacks by design
  - high scientific interest and practical security narrative
- What changes:
  - central measurement node model (BSM), two-channel symmetry/asymmetry
  - interference visibility becomes first-class
- Validation gates:
  - sanity: when you degrade BSM visibility, key rate falls and QBER rises
  - check limiting behavior: approaches decoy-BB84-like behavior only in idealized limits (do not over-promise)

Anchor:
- Lo, Curty, Qi (2012) MDI-QKD, Phys. Rev. Lett., DOI: 10.1103/PhysRevLett.108.130503

3) TF-QKD / PM-QKD family (single-photon interference, beats repeaterless scaling)
- Why:
  - modern, high-impact research direction
  - changes the "PLOB bound story" (you must handle this correctly)
- What changes:
  - dual-link model + central interference
  - phase tracking and reference frame error models
  - careful applicability flags: security proofs depend on assumptions
- Validation gates:
  - do NOT run a naive PLOB gate on TF/PM protocols; apply bounds correctly
  - validate internal scaling claims using protocol-specific theory checks

Anchors:
- Lucamarini et al. (2018) TF-QKD, Nature, DOI: 10.1038/s41586-018-0066-6
- Ma et al. (2018) PM-QKD, Phys. Rev. X, DOI: 10.1103/PhysRevX.8.031043
- Wang et al. (2018) SNS TF-QKD proposal, Phys. Rev. Lett., DOI: 10.1103/PhysRevLett.121.190502
- Fang et al. (2020) SNS protocol details, Phys. Rev. A, DOI: 10.1103/PhysRevA.101.042304

Notes:
- SNS is included here because it is often the practical pathway in TF-family discussions.

### Tier B (strategic expansion)

4) CV-QKD (continuous-variable QKD)
- Why:
  - strong research and commercialization activity; different hardware stack
  - attractive for metropolitan deployments
- What changes:
  - replace QBER-centric reporting with excess noise, SNR, reconciliation efficiency
  - homodyne/heterodyne detection models
- Validation gates:
  - validate against known formulas for coherent-state CV-QKD and known security regimes
  - strict applicability bounds (trusted noise, calibration assumptions)

Anchors:
- Grosshans, Grangier (2002) CV-QKD coherent states, Phys. Rev. Lett., DOI: 10.1103/PhysRevLett.88.057902
- Grosshans et al. (2003) CV-QKD in Nature, DOI: 10.1038/nature01289

5) QKD network-layer protocols (beyond a single link)
- Examples:
  - entanglement swapping
  - purification
  - teleportation / entanglement distribution scheduling
- Why:
  - needed for "quantum internet" discussions and repeater planning
- Caution:
  - do not try to compete with a full network simulator immediately
  - build a verification layer and interop adapters first

Anchors:
- RFC 9340 (Quantum Internet architectural principles): https://www.rfc-editor.org/info/rfc9340
- SeQUeNCe paper: https://arxiv.org/abs/2008.05119

---

## 3) Protocol Interface Proposal (Implementation Contract)

Create a stable interface and move protocol logic out of `photonstrust/qkd.py`
into protocol modules.

Recommended structure:
- `photonstrust/protocols/qkd/`
  - `base.py` (Protocol interface + result schema mapping)
  - `bb84_decoy.py`
  - `mdi.py`
  - `tf.py` (and/or `pm.py`, `sns.py`)
  - `cv.py`

Proposed protocol interface (conceptual):
- `evaluate_point(scenario, distance_km, runtime_overrides) -> QKDResultLike`
- `applicability(scenario) -> {status: pass/warn/fail, reasons: [...]}`
- `theory_checks(scenario) -> list[CheckResult]` (internal sanity gates)

Why:
- protocol selection becomes explicit and testable
- each protocol can define which global gates apply (e.g., PLOB gate)

---

## 4) Validation Gates: What Makes a Protocol "Trustable"

### Gate class 1: Theory sanity bounds (fast, deterministic)

Examples:
- QBER must be in [0, 0.5]
- key rate must be >= 0
- monotonic trends in controlled perturbations:
  - more loss -> lower key rate
  - higher dark counts -> higher QBER / lower key rate
  - lower optical visibility -> higher misalignment contribution

These are unit-test gates (CI).

### Gate class 2: Bound-based checks (protocol-specific)

PLOB bound:
- applies to repeaterless direct-transmission secret-key capacity of a pure-loss channel
- SHOULD be a gate for protocols that claim repeaterless direct link behavior
- MUST NOT be naively applied to TF-family protocols that change the architecture

Anchor:
- Pirandola et al. (2017) PLOB bound, Nature Communications, DOI: 10.1038/ncomms15043

### Gate class 3: Literature regime reproduction (benchmark suites)

For each protocol family:
- select a small set of published experimental regimes
- reproduce trend + order-of-magnitude behavior, not exact device-specific numbers
- store these as canonical benchmark configs and lock regression tolerances

Example anchor regime:
- Boaron et al. (2018) long-distance fiber QKD benchmark, DOI: 10.1103/PhysRevLett.121.190502

### Gate class 4: Evidence tiering and applicability labeling (artifact-level)

Every protocol result must declare:
- evidence tier:
  - Tier 0: theory-only (no calibration)
  - Tier 1: calibrated on synthetic solver sweeps
  - Tier 2: calibrated on measurement bundles
  - Tier 3: measurement-validated regime (explicitly cited datasets)
- applicability bounds:
  - wavelength, loss regime, background regime, tracking assumptions, etc.

This is how you prevent reputational failure from over-claiming.

---

## 5) Satellite and Free-Space Protocol Reality (You Must Treat Separately)

Free-space QKD is not "fiber with different loss".
It has day/night, background, pointing, turbulence, and orbital geometry.

Protocol roadmap (satellite relevance):
- decoy-state BB84 is common in satellite-to-ground discussions
- TF-family and MDI variants are research-active but operationally complex

Validation gates (satellite-specific):
- explicit background model assumptions (day/night, spectral filtering)
- pointing loss and tracking model flagged as assumed vs measured
- turbulence regime labeling (weak/strong) and model selection

Modern anchors (examples, not exhaustive):
- Liao et al. (2017) satellite-to-ground QKD, DOI: 10.1038/nature23655
- Bedington et al. (2017) satellite QKD review, DOI: 10.1038/nature23675
- 2025 microsatellite-based real-time QKD (Nature), DOI: 10.1038/s41586-025-08739-z

Note:
- implement a "free-space realism pack" as a separate deep-dive and phased rollout item
  (see `32_satellite_qkd_realism_pack.md` in this doc set).

---

## 6) Acceptance Checklist (Definition of Done per Protocol)

For each new protocol module:

1) Implementation:
- protocol selection is explicit in config and in output artifacts
- outputs match the global QKD result contract (key rate + uncertainty + breakdown)

2) Tests:
- theory sanity tests (bounds + monotonicity)
- at least one literature regime benchmark test (trend check)
- determinism tests (seed + config hash) for uncertainty runs

3) Evidence:
- artifacts include:
  - assumptions table
  - applicability flags and warnings
  - provenance hashes

4) Documentation:
- protocol doc page: model equations, parameters, defaults, and applicability
- a "quickstart reproducible figure" notebook or CLI recipe

---

## 7) Execution Plan (Phased Rollout Alignment)

Suggested next phases after Phase 39:

- Phase 40: signing/publishing evidence bundles
- Phase 41: QKD deployment realism pack (fiber) consolidated into canonical presets
- Phase 43: protocol expansion:
  - MDI-QKD v0.1 (preview/certification split)
  - TF/PM-QKD v0.1 (clearly labeled as preview until calibrated/benchmarked)

Then:
- CV-QKD as a separate phase (do not mix it into the same acceptance gates)

---

## Source Index (Web-validated, 2026-02-14)

Protocol anchors:
- Decoy-state QKD (Lo, Ma, Chen 2005), DOI: 10.1103/PhysRevA.72.012326
- MDI-QKD (Lo, Curty, Qi 2012), DOI: 10.1103/PhysRevLett.108.130503
- TF-QKD (Lucamarini et al. 2018), DOI: 10.1038/s41586-018-0066-6
- PM-QKD (Ma et al. 2018), DOI: 10.1103/PhysRevX.8.031043
- SNS TF-QKD (Wang et al. 2018), DOI: 10.1103/PhysRevLett.121.190502
- SNS details (Fang et al. 2020), DOI: 10.1103/PhysRevA.101.042304
- PLOB bound (Pirandola et al. 2017), DOI: 10.1038/ncomms15043

CV-QKD anchors:
- Grosshans, Grangier 2002, DOI: 10.1103/PhysRevLett.88.057902
- Grosshans et al. 2003, DOI: 10.1038/nature01289

Satellite anchors:
- Liao et al. 2017, DOI: 10.1038/nature23655
- Bedington et al. 2017, DOI: 10.1038/nature23675
- 2025 microsatellite real-time QKD (Nature), DOI: 10.1038/s41586-025-08739-z
