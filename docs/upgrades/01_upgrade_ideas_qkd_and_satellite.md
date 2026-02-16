# Upgrade Ideas: QKD + Satellite (Physics + Protocols + Trust Gates)

Date: 2026-02-14

This file is the consolidated upgrade map for:
- QKD protocol expansion
- fiber deployment realism
- satellite/free-space realism
- multi-fidelity cross-checks (QuTiP/Qiskit) as trust gates

If you only read one QKD document for "what to do next", read this.

Operating flow for any item in this map (non-negotiable):
- Research brief (PhD-grade): cite primary anchors, define applicability bounds.
- Implementation plan: list exact files/schemas/tests and acceptance gates.
- Build: implement the smallest viable slice.
- Validate: run tests and add at least one regression/benchmark fixture.
- Docs: update this map + relevant deep-dive docs.

Deep research companions (full details):
- Fiber realism: `../research/deep_dive/16_qkd_deployment_realism_pack.md`
- Protocol roadmap + gates: `../research/deep_dive/23_protocol_roadmap_and_validation_gates.md`
- Satellite realism: `../research/deep_dive/32_satellite_qkd_realism_pack.md`
- Evidence signing: `../research/deep_dive/24_evidence_bundle_publishing_and_signing.md`

---

## P0 (Next)

### [DONE] UPG-QKD-001: Evidence bundle signing and verification (Phase 40)

Why:
- makes exported results tamper-evident outside the repo
- enables approvals to anchor to immutable evidence (audit trail)

Deliver:
- sign `bundle_manifest.json` (recommended)
- `photonstrust evidence bundle verify` fails on any modification
- approvals reference signed manifest digest

Risk if ignored:
- exported evidence bundles can be edited post-hoc (plots/configs swapped) with no detection
- approvals can "bless" mutable artifacts (breaks audit trail)

Minimal viable slice:
- sign the manifest (not the full zip)
- verification ladder:
  - verify signature over manifest
  - re-hash files and compare to manifest

Validation gates:
- mutate any bundled file -> verification fails
- remove/rename a file -> verification fails
- `--require-signature` fails when signature missing

Sources:
- `../research/deep_dive/24_evidence_bundle_publishing_and_signing.md`
- `../operations/phased_rollout/FAST_EXECUTION_OVERLAY.md`
- `../audit/08_reliability_card_v1_1.md`
- Implementation: `../operations/phased_rollout/phase_40_evidence_bundle_signing/`

### UPG-QKD-002: Reliability Card v1.1 implementation (Phase 42)

Why:
- turns "trust" into structured fields: evidence tier, operating envelope, benchmarks, standards alignment

Deliver:
- `schemas/reliability_card_v1_1.schema.json`
- generator populates v1.1 fields
- card validate/diff CLI

Risk if ignored:
- "trust" remains prose-only; comparisons and gates remain ad-hoc

Minimal viable slice:
- implement v1.1 as additive fields over v1.0 (keep v1.0 readers working)
- auto-populate: evidence tier, operating envelope, benchmark coverage, provenance

Validation gates:
- jsonschema validation for v1.1 cards in CI
- at least 3 run types produce v1.1 cards (fiber QKD, orbit pass, PIC workflow)

Sources:
- `../audit/08_reliability_card_v1_1.md`
- `../research/deep_dive/06_reliability_card_v1_1_draft.md`

### [DONE] UPG-QKD-003: Fiber QKD deployment realism pack implementation (Phase 41)

Why:
- prevents over-claiming for deployed fiber (coexistence, misalignment floor, finite-key regimes)

Deliver (minimum):
- canonical presets in `configs/canonical/`
- benchmark coverage + drift governance
- explicit applicability bounds in artifacts

Risk if ignored:
- deployed fiber claims are dismissed as "lab-only"/"asymptotic-only"

Minimal viable slice:
- standardize config extensions: coexistence (Raman/background), misalignment/visibility floor, finite-key mode
- add canonical metro/long-haul/coexistence presets

Validation gates:
- backward compatibility: existing configs unchanged when new fields absent
- monotonicity: higher background/power/misalignment/stricter finite-key => lower secure key

Sources:
- `../research/deep_dive/16_qkd_deployment_realism_pack.md`
- `../audit/01_physics_model_assumptions.md` (finite-key and benchmark anchors)
- Implementation: `../operations/phased_rollout/phase_41_qkd_deployment_realism_pack/`

### UPG-QKD-004: Protocol expansion scaffolding + decoy BB84 v0.1 (Phase 43 part A)

Why:
- decoy-state BB84 is the baseline for deployed QKD comparisons

Deliver:
- `photonstrust/protocols/qkd/` module surface with a protocol interface
- decoy BB84 rate model (preview mode first)
- theory sanity gates + 1-2 literature regime checks (trend/envelope)

Risk if ignored:
- PhotonTrust remains narrow vs deployed QKD benchmark ecosystem

Minimal viable slice:
- implement asymptotic decoy BB84 (signal + weak decoy + vacuum)
- keep strict applicability metadata: asymptotic vs finite-key

Validation gates:
- sanity: QBER in [0, 0.5], key rate >= 0
- trends: loss/background up => key rate down

Primary anchors:
- Lo, Ma, Chen (2005) decoy-state QKD: https://doi.org/10.1103/PhysRevA.72.012326

Sources:
- `../research/deep_dive/23_protocol_roadmap_and_validation_gates.md`
- `../audit/10_competitive_positioning.md`

---

## P1 (Planned)

### UPG-QKD-010: MDI-QKD v0.1 (Phase 43 part B)

Why:
- modern protocol family with strong security narrative (detector side-channel removal)

Deliver:
- MDI-QKD preview surface with strict applicability warnings
- tests: visibility monotonicity, asymmetry behavior, sanity bounds

Risk if ignored:
- security narrative remains "trusted detectors" only; harder to position against modern protocol expectations

Primary anchors:
- Lo, Curty, Qi (2012) MDI-QKD: https://doi.org/10.1103/PhysRevLett.108.130503

Sources:
- `../research/deep_dive/23_protocol_roadmap_and_validation_gates.md`

### UPG-QKD-011: TF/PM-QKD preview surface (Phase 43 part C)

Why:
- research-active; changes the scaling story, so PhotonTrust must handle it correctly

Deliver:
- TF/PM module surfaces marked preview unless benchmarked/calibrated
- update "PLOB gate" logic so it does not create false positives for TF-family protocols

Risk if ignored:
- high reputational risk: incorrect "beats PLOB" comparisons or invalid sanity gates

Primary anchors:
- Lucamarini et al. (2018) TF-QKD: https://doi.org/10.1038/s41586-018-0066-6
- Ma et al. (2018) PM-QKD: https://doi.org/10.1103/PhysRevX.8.031043

Sources:
- `../research/deep_dive/23_protocol_roadmap_and_validation_gates.md`
- `../audit/01_physics_model_assumptions.md` (PLOB sanity gate)

### UPG-QKD-012: QuTiP/Qiskit multi-fidelity triangulation tests (Phase TBD)

Why:
- scientific defensibility: conclusions consistent across models

Deliver:
- backend scaffolding + optional dependency groups
- at least one QuTiP cross-check target (memory decoherence curve or emitter visibility model)
- at least one Qiskit cross-check target (repeater primitive circuit)
- `multifidelity_report.json` artifact included in evidence bundles

Sources:
- `../research/deep_dive/26_physics_engine_multifidelity_quutip_qiskit_plan.md`
- `../research/deep_dive/25_event_kernel_and_backend_interop.md`
- `../audit/01_physics_model_assumptions.md` (QuTiP fallback should become explicit)

---

## Satellite/Free-Space Realism Pack (Separate Track)

Guiding principle:
- Free-space/satellite is not "fiber with different loss". The dominant terms are
  background, pointing/tracking, turbulence fading, and finite-pass constraints.

### UPG-SAT-001: Atmosphere path length correction (Phase SAT-1)

Why:
- naive extinction * distance_km incorrectly penalizes the full slant range

Deliver:
- replace `distance_km` in atmospheric loss with an atmosphere-path model:
  - `L_atm_km = atmosphere_effective_thickness_km * airmass(elevation)`
- add diagnostics and tests (monotonic + non-exploding vs range)

Risk if ignored:
- atmospheric loss incorrectly scales with satellite slant range, distorting elevation/range sensitivities

Validation gates:
- lower elevation increases atmospheric loss (existing low-elevation warnings remain)
- at fixed elevation, increasing satellite range must not explode atmospheric loss

Primary anchors:
- Kasten & Young (1989) airmass: https://doi.org/10.1364/AO.28.004735

Sources:
- `../research/deep_dive/32_satellite_qkd_realism_pack.md`
- `../audit/01_physics_model_assumptions.md`

### UPG-SAT-002: Outage-aware pointing + turbulence distributions (Phase SAT-2)

Why:
- satellite links are dominated by fading and intermittency; outage probability is often the KPI

Deliver:
- turbulence fading distribution (lognormal or gamma-gamma) and outage computation
- pointing jitter distribution and outage computation
- explicit regime labeling in artifacts (preview vs certification)

Validation gates:
- increasing pointing jitter and/or scintillation must increase outage probability
- seeded determinism for outage metrics (replayable CIs)

Primary anchors:
- Al-Habash et al. (2001) Gamma-Gamma turbulence: https://doi.org/10.1117/1.1386641

Source:
- `../research/deep_dive/32_satellite_qkd_realism_pack.md`

### UPG-SAT-003: Background estimator (Phase SAT-3)

Why:
- background is not a constant knob; it depends on FOV, filters, gating, day/night, site radiance

Deliver:
- minimal radiance-proxy model with uncertainty bands
- clear override path for measured background

Validation gates:
- derived background scales with FOV and filter bandwidth
- derived day regime produces higher background than night regime (directional check)

Source:
- `../research/deep_dive/32_satellite_qkd_realism_pack.md`

### UPG-SAT-004: Finite-key budgeting for passes (Phase SAT-4)

Why:
- finite pass duration makes finite-key mandatory for satellite claims

Deliver:
- compute signals per pass and enforce finite-key mode in orbit scenarios

Validation gates:
- shorter pass duration reduces secure key superlinearly when finite-key enabled
- artifacts report keys/pass and expected keys/pass (availability-weighted)

Primary anchors:
- Tomamichel et al. (2012) finite-key: https://doi.org/10.1038/ncomms1631

Source:
- `../research/deep_dive/32_satellite_qkd_realism_pack.md`

---

## Small Physics Fixes (Fast Wins, Should Be Scheduled)

These are small but credibility-improving fixes from the audit:

- UPG-QKD-SMALL-01: dephasing parameter renaming/documentation (avoid unit ambiguity)
- UPG-QKD-SMALL-02: afterpulse jitter ratio -> configurable param
- UPG-QKD-SMALL-03: wavelength-dependent PDE option
- UPG-QKD-SMALL-04: QuTiP fallback requires explicit `require_backend` option
- UPG-QKD-SMALL-05: document QBER independence assumption (and optionally add correlation term extension)

Source:
- `../audit/01_physics_model_assumptions.md`
