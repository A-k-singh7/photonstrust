# PhotonTrust Physics Core Open-Science Master Plan (2026-02-12)

This document is the execution specification for making PhotonTrust the most
trustable and broadly usable photonic verification engine across academic,
industrial, and satellite-oriented workflows.

It converts current research signals into concrete physics-engine development
work, benchmarking requirements, calibration policy, open-source governance, and
product integration requirements for drag-drop data collection and decision
support.

## 0. Current implementation status (as of 2026-02-14)

Completed phases (strict rollout protocol):
- Phase 01: Free-space/satellite channel foundation
  - `../operations/phased_rollout/phase_01_free_space_channel/`
- Phase 02: Stateful detector model (gating/saturation/afterpulse)
  - `../operations/phased_rollout/phase_02_detector_stateful_model/`
- Phase 03: Emitter transient mode + spectral diagnostics
  - `../operations/phased_rollout/phase_03_emitter_transient_mode/`
- Phase 04: Calibration diagnostics enforcement gates
  - `../operations/phased_rollout/phase_04_calibration_gates/`
- Phase 05: Reliability-card trust extensions (evidence tiers, diagnostics block)
  - `../operations/phased_rollout/phase_05_reliability_card_trust_extensions/`
- Phase 06: Performance acceleration and multi-fidelity execution
  - `../operations/phased_rollout/phase_06_multifidelity_performance/`
- Phase 07: Open benchmark ingestion and external reproducibility package
  - `../operations/phased_rollout/phase_07_open_benchmark_ingestion/`
- Phase 08: Component graph schema v0.1 + compiler (UI -> engine)
  - `../operations/phased_rollout/phase_08_graph_schema_compiler/`
- Phase 09: ChipVerify PIC component library v1 + netlist execution
  - `../operations/phased_rollout/phase_09_pic_component_library/`
- Phase 10: ChipVerify compact model import (Touchstone/S-parameters) + sweeps
  - `../operations/phased_rollout/phase_10_pic_compact_model_import/`
- Phase 11: OrbitVerify mission templates v1 (pass envelopes + metadata)
  - `../operations/phased_rollout/phase_11_orbit_mission_templates/`
- Phase 12: Data contribution workflow (academic + industry safe)
  - `../operations/phased_rollout/phase_12_data_contribution_workflow/`
- Phase 13: Web drag-drop MVP (managed service surface)
  - `../operations/phased_rollout/phase_13_web_drag_drop_mvp/`
- Phase 14: Trust panel v0.2 (parameter registry + units/ranges)
  - `../operations/phased_rollout/phase_14_trust_panel_param_registry/`
- Phase 15: Graph validation + structured diagnostics (params, ports, kind support)
  - `../operations/phased_rollout/phase_15_graph_validation_diagnostics/`
- Phase 16: OrbitVerify web runner v0.1 (config-first pass envelopes)
  - `../operations/phased_rollout/phase_16_orbit_web_runner/`
- Phase 17: OrbitVerify validation + diagnostics v0.1 (schema + validate endpoint)
  - `../operations/phased_rollout/phase_17_orbit_validation_diagnostics/`
- Phase 18: OrbitVerify evidence hardening v0.2 (availability envelope + standards anchors)
  - `../operations/phased_rollout/phase_18_orbit_availability_standards/`
- Phase 19: Run registry + artifact serving v0.1 (managed-service hardening, local dev)
  - `../operations/phased_rollout/phase_19_run_registry_artifact_serving/`
- Phase 20: Run browser + run diff v0.1 (managed-service hardening, local dev)
  - `../operations/phased_rollout/phase_20_run_browser_diff/`
- Phase 21: Run output summaries + output diff scope v0.1 (managed-service hardening, local dev)
  - `../operations/phased_rollout/phase_21_run_output_summary_diff/`
- Phase 22: Project registry + approvals v0.1 (managed-service governance, local dev)
  - `../operations/phased_rollout/phase_22_project_registry_approvals/`
- Phase 23: Performance DRC flagship hardening v0.2 (route-level layout feature extraction)
  - `../operations/phased_rollout/phase_23_performance_drc_layout_feature_extraction/`
- Phase 24: GDS-level layout feature extraction v0.2 (optional seam)
  - `../operations/phased_rollout/phase_24_gds_layout_feature_extraction/`
- Phase 25: Crosstalk calibration loop v0.1 (measurement bundles -> fit -> drift governance)
  - `../operations/phased_rollout/phase_25_crosstalk_calibration_loop/`
- Phase 26: PIC solver extensions v0.2 (ring resonator transfer; sweeps)
  - `../operations/phased_rollout/phase_26_pic_solver_extensions/`
- Phase 27: PDK-aware layout hooks v0.1 (deterministic sidecars + LVS-lite + optional KLayout runner seam)
  - `../operations/phased_rollout/phase_27_pdk_layout_hooks/`
- Phase 28: SPICE + KLayout interop v0.1 (SPICE export + optional ngspice runner seam)
  - `../operations/phased_rollout/phase_28_spice_klayout_interop/`
- Phase 29: PIC layout + LVS-lite + SPICE v0.1 (API + web tabs integration)
  - `../operations/phased_rollout/phase_29_pic_layout_spice_api_web/`
- Phase 30: KLayout macro templates + run artifact pack contract v0.1 (EDA seam hardening)
  - `../operations/phased_rollout/phase_30_klayout_macros_artifact_pack/`
- Phase 31: KLayout artifact pack API + web integration v0.1 (managed workflow surface)
  - `../operations/phased_rollout/phase_31_klayout_pack_api_web/`
- Phase 32: KLayout pack run registry source selection v0.1 (Runs picker -> selected GDS)
  - `../operations/phased_rollout/phase_32_klayout_pack_run_registry_source/`
- Phase 33: Inverse design robustness + evidence pack v0.1 (schema contract + corner cases + coupler ratio primitive)
  - `../operations/phased_rollout/phase_33_invdesign_robustness_evidence_pack/`

Fast execution overlay (v1 -> v3, "Strongest Contender Path"):
- `../research/deep_dive/21_v1_to_v3_fast_execution_plan.md`

Latest completed phase:
- Phase 36: Evidence bundle attestation + schema contracts v0.1 (workflow report + bundle manifest)
  - `../operations/phased_rollout/phase_36_evidence_bundle_attestation_schemas/`

Planned next phase (draft):
- Phase 37 (planned): Evidence bundle publish + signing (project approvals integration)
  - Reference: `../research/deep_dive/21_v1_to_v3_fast_execution_plan.md`
  - Reference: `../research/15_platform_rollout_plan_2026-02-13.md`

## 1. Mission and positioning

PhotonTrust should be developed as a dual-purpose scientific platform. The core
physics engine must be open and academically inspectable, while the product
layer should provide managed collaboration, reproducibility workflows, and
decision-ready reporting for industrial teams. The defensible moat is not
closed code; the moat is high-integrity physics plus operational reliability at
scale.

The core mission is to map hardware parameters to network-level reliability
artifacts with uncertainty, diagnostics, and provenance that are strong enough
for publication review, engineering design reviews, and mission-go/no-go
decisions.

## 2. Current research signals and timing context

Recent literature and mission updates indicate that the expansion window is
immediate. For example, a Nature paper published on 2026-02-11 reports a large
integrated-photonic trusted-node TF-QKD network, which validates a strong
near-term demand for chip-to-network verification workflows:
https://www.nature.com/articles/s41586-026-08816-0

Free-space and hybrid quantum communications remain active research fronts
through 2025, including all-day free-space protocols and intermodal field-trial
work. Public satellite programs are maturing, with ESA positioning EAGLE-1 as a
satellite-based QKD system (public schedule statements have shifted over time;
use mission dates as "moving targets", not fixed truths):
https://connectivity.esa.int/projects/eagle-1

Canada is running QEYSSat as a satellite mission scoped to validate
satellite-ground QKD technologies:
https://www.asc-csa.gc.ca/eng/satellites/qeyssat/default.asp

Inference: the physics core must quickly support both terrestrial integrated
photonics and free-space/satellite channels with common uncertainty semantics.

## 3. Scientific principles for the physics core

The engine should follow five non-negotiable principles.

First, every externally consumable metric must carry uncertainty and
diagnostics, not only point estimates. Second, model behavior must be
falsifiable through benchmark scenarios tied to literature or field data.
Third, every output must be reproducible with immutable configuration hashes,
model version identifiers, and seed control. Fourth, model assumptions must be
machine-readable and exportable. Fifth, model release gates must be automated in
CI to prevent publication of unqualified artifacts.

## 4. Target architecture of the next-generation physics engine

The near-term architecture should preserve modularity and extend each layer.

The source and device layer should include emitter, detector, and memory models
that can run in preview and certification modes. The channel layer should handle
fiber and free-space/satellite paths with common interfaces. The protocol layer
should remain compatible with existing swap/purify/teleport flows while adding
security-focused protocol variants. The calibration layer should enforce MCMC
diagnostic thresholds before cards can be published. The reporting layer should
export both human-readable and machine-readable provenance bundles.

This can be implemented without breaking current module boundaries by extending
`photonstrust.physics`, `photonstrust.channels`, `photonstrust.calibrate`, and
`photonstrust.report`.

## 5. Physics-engine development priorities

## Priority block P0 (0-12 weeks)

The first priority is free-space/satellite channel modeling. This unlocks
OrbitVerify and forces the engine to handle background noise and pointing-loss
regimes that do not appear in fiber-only assumptions.

The second priority is detector realism. The current stochastic model should be
upgraded to stateful behavior for gated operation, dead-time recovery,
afterpulse memory, and saturation rolloff.

The third priority is emitter transient behavior. The model should add a
pulse-resolved mode that complements current steady-state outputs and exposes
spectral-quality indicators that influence link-level fidelity.

The fourth priority is calibration diagnostics enforcement. Reliability cards
must include hard pass/fail diagnostics fields (R-hat, ESS, posterior
predictive checks) for all calibrated models.

## Priority block P1 (3-6 months)

The core should support photonic component-level verification interfaces for
ring resonators, MZI meshes, couplers, phase shifters, and chip I/O coupling
chains. Component parameter schemas and invariants should be validated in CI.

Protocol integration should expand to include MDI-QKD profile templates for
security-centered deployments.

## Priority block P2 (6-12 months)

Introduce multi-fidelity execution. Preview mode should target rapid interactive
feedback for drag-drop editing, while certification mode should run fuller
physics and stricter diagnostics.

Add surrogate caching paths only after fidelity envelopes are validated.

## 6. Free-space/satellite model specification

The free-space channel model should include geometric spreading,
atmospheric-extinction effects, pointing jitter penalties, turbulence
attenuation proxy terms, and background count contributions to false heralds.
The model should export decomposed loss terms for error-budget accounting.

The minimum required outputs are channel transmission efficiency, effective
channel loss in dB, and metadata for each loss contributor. The minimum required
inputs are elevation angle, aperture sizes or beam divergence assumptions,
pointing jitter, atmospheric extinction coefficient, and background count rate.

The model should default to conservative values and keep all assumptions
explicit in exported artifacts.

## 7. Detector realism specification

Detector modeling should move from scalar probability assumptions to a temporal
state machine where the detector is explicitly in ready, dead-time, and recovery
states. Gated mode should support configurable gate width and repetition.
Afterpulsing should be conditioned on prior clicks and decay with delay.
Saturation should reduce effective detection probability at high event rates.

This layer should output both event-level and aggregate metrics, including
effective PDE under load, false-click components, and confidence intervals.

## 8. Emitter and memory modeling specification

Emitter development should add transient solver paths and expose output fields
for linewidth proxies and mode mismatch penalties that directly propagate into
pair probability and fidelity estimates.

Memory modeling should separate amplitude damping and phase decoherence effects
in reported diagnostics. The reliability card should carry these contributors as
separate uncertainty channels so decision-makers can prioritize hardware
improvements appropriately.

## 9. Calibration and uncertainty policy

Calibration should remain Bayesian and become gate-driven. No external card
should be published unless diagnostics pass pre-declared thresholds. Suggested
minimum policy is split R-hat near 1 with narrow tolerance, effective sample
size above defined per-parameter minima, and posterior predictive checks passing
scenario-specific acceptance tests.

All calibration bundles should include metadata linking raw measurements to
model versions and prior definitions.

## 10. Benchmarking and validation framework

Benchmarking should be structured into three classes: physics-faithful
benchmarks, fast-approximation benchmarks, and stress/failure benchmarks.
Each class should have immutable scenario IDs and baseline lock windows.

Every major release should require drift analysis with explicit approval for any
threshold exceedance. External reference anchors should include peer-reviewed
and field-trial publications where possible.

## 11. Open-source strategy for academia

The open-source core should include physics, channels, calibration, and event
kernel modules plus benchmark definitions and reproducibility scripts. Academic
users should be able to reproduce published PhotonTrust cards locally from
public artifacts.

A contributor workflow should require machine-readable benchmark submissions
with provenance metadata. New model proposals should include hypothesis,
validation strategy, and failure-mode documentation.

A lightweight technical steering process should govern breaking changes to model
interfaces and schema contracts.

## 12. Drag-drop service strategy for data collection

The drag-drop surface should not own scientific logic. It should produce graph
JSON payloads that compile into versioned scenario configurations executed by
backend services.

Each user action should be logged as structured parameter deltas so that design
evolution can be studied and transformed into benchmark candidates. This enables
continuous ingestion of real-world research configurations from academic and
industry usage.

The managed service should provide collaboration and orchestration, while model
transparency remains anchored in the open core.

## 13. Quality gates and release criteria

A release should fail if any of the following conditions are not met: schema
validation, deterministic replay checks, benchmark drift policy checks,
calibration diagnostics policy checks, and provenance completeness checks.

For externally shared cards, signed artifact attestation should be required once
the supply-chain workflow is in place.

## 14. Detailed implementation backlog (first build tranche)

## Tranche A (immediate, 2-4 weeks)

1. Add `photonstrust/channels/free_space.py` with deterministic functions for
   geometric efficiency, atmospheric transmittance, pointing penalty, and total
   channel efficiency with diagnostics payload.
2. Extend `photonstrust/qkd.py` to support `channel.model` values `fiber` and
   `free_space` while preserving backward compatibility for existing configs.
3. Extend `photonstrust/config.py` channel defaults to include model-aware
   defaults for free-space parameters.
4. Add tests:
   `tests/test_free_space_channel.py` for channel invariants and
   `tests/test_qkd_free_space.py` for end-to-end behavior.
5. Add one scenario config:
   `configs/demo5_satellite_downlink.yml`.

## Tranche B (next, 4-8 weeks)

1. Upgrade `photonstrust/physics/detector.py` with a temporal state model.
2. Add gated operation fields and saturation tests.
3. Extend report output with detector diagnostics decomposition.
4. Add CI checks for detector invariant envelopes.

## Tranche C (next, 8-12 weeks)

1. Extend `photonstrust/physics/emitter.py` transient mode support.
2. Extend `photonstrust/physics/memory.py` decomposition diagnostics.
3. Add calibration diagnostic policy enforcement in
   `photonstrust/calibrate/bayes.py`.
4. Expand reliability schema with calibration diagnostics and evidence tier
   fields.

## 15. Data model additions for trust

Reliability cards should be extended with the fields
`evidence_quality_tier`, `calibration_diagnostics`,
`benchmark_coverage`, and `reproducibility_artifact_uri`.

Evidence tiers should have explicit semantics:
`simulated_only`, `calibrated_lab`, and `field_validated`.

## 16. Research ingestion pipeline

PhotonTrust should add a structured research-ingestion path where new papers and
field reports are converted into benchmark candidate records. Each record should
include measurement context, parameter mapping confidence, and known limitations.

This allows continuous model stress testing against live literature and enables
academic users to contribute domain-specific benchmark packs.

## 17. Metrics for scientific dominance

The lead indicators should include benchmark reproducibility rate, percentage of
cards with complete diagnostics, drift incidents per release, and time from
external result publication to benchmark ingestion.

Business indicators should include pilot-to-paid conversion and time-to-first
trusted decision report, but scientific credibility metrics should remain the
primary control variables.

## 18. Immediate start protocol

Execution should begin with Tranche A now. Free-space channel support is the
correct starting point because it unlocks the satellite roadmap, stress-tests
detector false-count modeling, and creates a high-value benchmark axis without
rewriting the whole stack.

Rollout governance is now tracked under:
`../operations/phased_rollout/README.md`, with per-phase research/plan/build/
validation artifacts required before phase closure.

Current implementation status (as of 2026-02-14):
- See `../operations/phased_rollout/README.md` for the authoritative list and per-phase artifacts.

## 19. Source references (web-validated)

- Nature integrated photonic TF-QKD network (published 2026-02-11):
  https://www.nature.com/articles/s41586-026-10152-z
- EPJ QT intermodal quantum communication field trial (2025):
  https://link.springer.com/article/10.1140/epjqt/s40507-025-00306-9
- npj Quantum Information all-day free-space QKD protocol (2025):
  https://www.nature.com/articles/s41534-025-01085-y
- Free-space TF-QKD preprint (2025):
  https://arxiv.org/abs/2503.17744
- Atmospheric FSO analysis (2025):
  https://link.springer.com/article/10.1007/s11082-025-08505-5
- ESA EAGLE-1 mission page:
  https://www.esa.int/Applications/Connectivity_and_Secure_Communications/Eagle-1
- CSA QEYSSat mission page:
  https://www.asc-csa.gc.ca/eng/satellites/qeyssat.asp
- EuroQCI policy page:
  https://digital-strategy.ec.europa.eu/en/policies/european-quantum-communication-infrastructure-euroqci
- QuTiP release line:
  https://qutip.org/download.html
- Qiskit release notes 2.3:
  https://quantum.cloud.ibm.com/docs/en/api/qiskit/release-notes/2.3
- Bayesian optimization for repeater protocols (2025):
  https://arxiv.org/abs/2502.02208
- FAIR principles:
  https://doi.org/10.1038/sdata.2016.18
- W3C PROV overview:
  https://www.w3.org/TR/prov-overview/
- CodeMeta:
  https://codemeta.github.io/
