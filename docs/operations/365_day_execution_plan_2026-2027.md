# PhotonTrust 365-Day Execution Plan (2026-02-16 to 2027-02-14)

## 0) Starting point and operating rules

### Current baseline (as of 2026-02-16)
- Phase 49 cross-track integration closed and green.
- RC artifact pack updated and ready for external tagging.
- Day-0 pilot runbook rehearsed and passing.
- QuTiP parity lane exists but remains optional/non-blocking.

Primary anchors:
- `docs/operations/phased_rollout/phase_49_cross_track_integration/10_phase49_closeout_report_2026-02-16.md`
- `docs/operations/phased_rollout/phase_49_cross_track_integration/11_phase5_followthrough_report_2026-02-16.md`
- `docs/operations/phased_rollout/phase_49_cross_track_integration/13_day0_rehearsal_report_2026-02-16.md`
- `docs/results/phase5b_rc_artifact_pack_latest.json`

### Non-negotiable process (every week)
Each weekly scope must follow strict rollout protocol:
1. Research brief
2. Implementation plan
3. Build log
4. Validation report
5. Docs/changelog updates

Required file pattern per phase:
- `01_research_brief_YYYY-MM-DD.md`
- `02_implementation_plan_YYYY-MM-DD.md`
- `03_build_log_YYYY-MM-DD.md`
- `04_validation_report_YYYY-MM-DD.md`

Core gates to remain green continuously:

```bash
python -m pytest -q
python scripts/validation/ci_checks.py
python scripts/release/release_gate_check.py
python scripts/validation/run_validation_harness.py --output-root results/validation
```

### Ownership model
Use `docs/research/deep_dive/13_raci_matrix.md` for role assignment.

---

## 1) Phase map (13 phases x 4 weeks)

- Phase 50 (W1-W4): Quality/security foundation
- Phase 51 (W5-W8): Multi-fidelity backend foundation
- Phase 52 (W9-W12): Protocol expansion track
- Phase 53 (W13-W16): Satellite realism S1/S2
- Phase 54 (W17-W20): Satellite realism S3/S4 + pilot hardening
- Phase 55 (W21-W24): GraphSpec TOML + round-trip guarantees
- Phase 56 (W25-W28): DRC/PDRC/LVS expansion
- Phase 57 (W29-W32): PDK/foundry interop hardening
- Phase 58 (W33-W36): Inverse design Wave 3
- Phase 59 (W37-W40): Event kernel + external interop
- Phase 60 (W41-W44): Platform performance/security scale-up
- Phase 61 (W45-W48): Adoption and pilot conversion
- Phase 62 (W49-W52): GA release cycle

---

## 2) Week-by-week execution plan

## Phase 50 (W1-W4): Quality + security foundation
Source anchors:
- `docs/upgrades/03_upgrade_ideas_platform_quality_security.md`
- `docs/audit/03_configuration_validation.md`
- `docs/audit/04_ci_cd_improvements.md`
- `docs/audit/06_dependency_security.md`

### W01 (2026-02-16 to 2026-02-22) - Program lock and phase scaffolding
- Work: Open `phase_50_quality_security_foundation`, lock owner map, refresh risk register and gates.
- Artifacts: Phase 50 `01/02/03/04` docs, updated risk table in weekly ops notes.
- Validation: `python scripts/release/release_gate_check.py`
- Exit: No open owner gaps on release-critical workstreams.

### W02 (2026-02-23 to 2026-03-01) - CI matrix and coverage floor
- Work: Python version matrix, optional dependency lanes, coverage fail floor in CI.
- Artifacts: CI workflow updates, coverage config in `pyproject.toml`.
- Validation: `pytest -q --cov=photonstrust --cov-fail-under=70`
- Exit: CI matrix green with coverage enforcement.

### W03 (2026-03-02 to 2026-03-08) - Security baseline
- Work: Dependabot, pip-audit lane, deterministic frontend install policy, disclosure process.
- Artifacts: `.github/dependabot.yml`, `SECURITY.md`, security CI job.
- Validation: `pip-audit`
- Exit: Security scanning runs in CI and policy documented.

### W04 (2026-03-09 to 2026-03-15) - Config versioning + migration skeleton
- Work: Add `schema_version` governance for scenario configs, migration hooks, API strict validation.
- Artifacts: Config loader upgrades, migration notes, validation tests.
- Validation: `python -m photonstrust.cli run configs/product/pilot_day0_kickoff.yml --validate-only`
- Exit: Unsupported schema versions fail fast with migration guidance.

## Phase 51 (W5-W8): Multi-fidelity backend foundation
Source anchors:
- `docs/research/deep_dive/26_physics_engine_multifidelity_quutip_qiskit_plan.md`
- `docs/operations/phased_rollout/phase_49_cross_track_integration/10_phase5a_qutip_parity_lane_report_2026-02-16.md`

### W05 (2026-03-16 to 2026-03-22) - Backend interface scaffolding
- Work: Add backend interface layer (`base`, `analytic`, `stochastic`) and multifidelity schema.
- Artifacts: Backend modules, deterministic backend tests, schema contract.
- Validation: `python -m pytest -q`
- Exit: Existing runs remain backward compatible under default backend.

### W06 (2026-03-23 to 2026-03-29) - QuTiP narrow target lane
- Work: Implement one QuTiP high-value target (memory or emitter) with explicit applicability reporting.
- Artifacts: `qutip_backend.py`, parity artifacts, fallback policy notes.
- Validation: `python scripts/run_qutip_parity_lane.py`
- Exit: Optional QuTiP lane stable and reproducible.

### W07 (2026-03-30 to 2026-04-05) - Qiskit repeater primitive lane
- Work: Add small-circuit repeater primitive templates and formula vs circuit cross-check tests.
- Artifacts: `qiskit_backend.py`, circuit template set, tests.
- Validation: optional dependency test lane for Qiskit.
- Exit: Qiskit lane produces deterministic cross-check outputs.

### W08 (2026-04-06 to 2026-04-12) - Multifidelity evidence integration
- Work: Include `multifidelity_report` in evidence bundles and trust panel surfaces.
- Artifacts: bundle schema update, UI trust section update.
- Validation: `python scripts/release/release_gate_check.py`
- Exit: Multifidelity results exported, schema-valid, and diffable.

## Phase 52 (W9-W12): Protocol expansion track
Source anchors:
- `docs/research/deep_dive/23_protocol_roadmap_and_validation_gates.md`
- `docs/research/deep_dive/03_protocol_validation_matrix.md`
- `docs/upgrades/01_upgrade_ideas_qkd_and_satellite.md`

### W09 (2026-04-13 to 2026-04-19) - Protocol module contract refactor
- Work: Split protocol logic into explicit protocol modules and dispatch interface.
- Artifacts: protocol base interface, migration notes, compatibility tests.
- Validation: regression baseline checks.
- Exit: Protocol selection explicit in config and artifacts.

### W10 (2026-04-20 to 2026-04-26) - Decoy BB84 v0.1
- Work: Implement decoy BB84 preview path with theory sanity and monotonicity gates.
- Artifacts: module + canonical scenario + benchmark test.
- Validation: QBER/rate bound tests and trend tests.
- Exit: Decoy BB84 available with applicability labels.

### W11 (2026-04-27 to 2026-05-03) - MDI-QKD v0.1
- Work: Implement MDI surface with visibility/asymmetry behavior checks.
- Artifacts: MDI protocol module, benchmark fixture, docs.
- Validation: MDI-specific validation matrix tests.
- Exit: MDI outputs integrated into reliability card pipeline.

### W12 (2026-05-04 to 2026-05-10) - TF/PM preview + bound gate update
- Work: Add TF/PM preview protocol surfaces and protocol-aware bound gate routing.
- Artifacts: TF/PM modules, gate routing tests, applicability docs.
- Validation: protocol matrix and bound-gate tests.
- Exit: No false PLOB-style failures for TF-family flows.

## Phase 53 (W13-W16): Satellite realism S1/S2
Source anchors:
- `docs/research/deep_dive/32_satellite_qkd_realism_pack.md`
- `docs/upgrades/01_upgrade_ideas_qkd_and_satellite.md`

### W13 (2026-05-11 to 2026-05-17) - Atmosphere path correction
- Work: Replace slant-range atmospheric loss assumption with effective atmospheric path model.
- Artifacts: free-space channel update + atmosphere diagnostics fields.
- Validation: low-elevation monotonic tests.
- Exit: Atmospheric behavior physically bounded across test envelopes.

### W14 (2026-05-18 to 2026-05-24) - Turbulence fading distribution
- Work: Add turbulence distribution model (lognormal/gamma-gamma preview).
- Artifacts: turbulence model layer + outage reporting fields.
- Validation: scintillation-to-outage trend checks.
- Exit: Satellite outputs include distribution-aware turbulence effects.

### W15 (2026-05-25 to 2026-05-31) - Pointing distribution + outage
- Work: Add pointing bias/jitter distribution and outage semantics.
- Artifacts: pointing diagnostics, seeded reproducibility tests.
- Validation: jitter stress tests.
- Exit: Pointing risk is modeled as distribution, not single deterministic scalar.

### W16 (2026-06-01 to 2026-06-07) - Satellite trust labeling hardening
- Work: Enforce preview vs certification labeling and applicability bounds for Orbit outputs.
- Artifacts: reliability card and orbit report updates.
- Validation: orbit card schema checks.
- Exit: Satellite cards include explicit model regime and caveat fields.

## Phase 54 (W17-W20): Satellite realism S3/S4 + pilot hardening
Source anchors:
- `docs/research/deep_dive/32_satellite_qkd_realism_pack.md`
- `docs/operations/pilot_readiness_packet/*`

### W17 (2026-06-08 to 2026-06-14) - Background estimator
- Work: Add `radiance_proxy` background model with day/night and optics dependence.
- Artifacts: background model API + uncertainty fields.
- Validation: day-vs-night directional checks.
- Exit: Background defaults are physics-informed and override-able.

### W18 (2026-06-15 to 2026-06-21) - Finite-key pass budgeting
- Work: Enforce finite-key budgeting semantics for orbit-pass scenarios.
- Artifacts: pass-duration finite-key metrics and epsilon fields.
- Validation: pass-duration sensitivity tests.
- Exit: Orbit key claims tied to finite-pass constraints.

### W19 (2026-06-22 to 2026-06-28) - Satellite canonical benchmarks
- Work: Add canonical satellite scenarios and drift governance.
- Artifacts: canonical configs + baseline fixtures.
- Validation: `python scripts/validation/check_benchmark_drift.py`
- Exit: Satellite regimes covered by reproducible benchmark harness.

### W20 (2026-06-29 to 2026-07-05) - Pilot packet v2
- Work: Update intake/success criteria/claim boundaries/day-0 runbook for new satellite realism assumptions.
- Artifacts: refreshed `docs/operations/pilot_readiness_packet/*`.
- Validation: day-0 rehearsal rerun.
- Exit: Pilot packet synchronized with current model validity envelope.

## Phase 55 (W21-W24): GraphSpec TOML + round-trip guarantees
Source anchors:
- `docs/research/deep_dive/27_drag_drop_component_ir_and_non_json_authoring.md`
- `docs/upgrades/02_upgrade_ideas_pic_and_verification.md`

### W21 (2026-07-06 to 2026-07-12) - `.ptg.toml` parser
- Work: Build GraphSpec parser and TOML-to-canonical-JSON compiler bridge.
- Artifacts: parser module + schema bindings + fixtures.
- Validation: compile path tests for TOML fixtures.
- Exit: TOML authoring is accepted end-to-end.

### W22 (2026-07-13 to 2026-07-19) - Deterministic formatter and hashing
- Work: Add `photonstrust fmt graphspec` and stable graph hash generation.
- Artifacts: formatter command, canonicalization tests.
- Validation: format idempotence tests.
- Exit: GraphSpec files are deterministic and review-friendly.

### W23 (2026-07-20 to 2026-07-26) - Typed ports and connection rules
- Work: Enforce typed port domains and invalid-connection blocking in UI and compiler.
- Artifacts: typed port schema, diagnostics enhancements.
- Validation: invalid connection test matrix.
- Exit: Engineering constraints enforced before simulation.

### W24 (2026-07-27 to 2026-08-02) - Round-trip guarantee
- Work: Guarantee JSON/TOML/UI round-trip without semantic drift.
- Artifacts: round-trip golden fixtures and docs.
- Validation: round-trip equivalence tests.
- Exit: Non-JSON authoring shipped with explicit no-drift guarantees.

## Phase 56 (W25-W28): DRC/PDRC/LVS expansion
Source anchors:
- `docs/research/deep_dive/28_drc_pdrc_lvs_evidence_pipeline.md`
- `docs/research/deep_dive/30_klayout_gds_spice_end_to_end_workflow.md`
- `docs/operations/phased_rollout/phase_49_cross_track_integration/14_pic_upgrade_wave2_2026-02-16.md`

### W25 (2026-08-03 to 2026-08-09) - PDRC loss-budget checks
- Work: Extend PDRC with route-based loss checks (length, bends, crossings).
- Artifacts: new PDRC rules and report fields.
- Validation: proxy monotonicity tests.
- Exit: PDRC includes actionable loss-risk findings.

### W26 (2026-08-10 to 2026-08-16) - Resonance and phase-shifter checks
- Work: Integrate resonance alignment and phase-range/power checks into signoff bundle.
- Artifacts: expanded PIC verification core outputs.
- Validation: `tests/test_pic_layout_verification_core.py`
- Exit: Multi-check signoff bundle pass/fail logic stable.

### W27 (2026-08-17 to 2026-08-23) - Reviewable violation outputs
- Work: Add violation coordinates/annotations for DRC/PDRC/LVS findings.
- Artifacts: enhanced artifact pack and run viewer support.
- Validation: reviewer walkthrough dry run.
- Exit: Violations are explainable and locatable without manual reverse engineering.

### W28 (2026-08-24 to 2026-08-30) - Violation diff semantics
- Work: Add new/resolved violation diff and changed-applicability diff.
- Artifacts: run diff API and UI updates.
- Validation: diff regression tests.
- Exit: Run comparison supports engineering signoff workflow.

## Phase 57 (W29-W32): PDK/foundry interop hardening
Source anchors:
- `docs/upgrades/02_upgrade_ideas_pic_and_verification.md`
- `docs/research/deep_dive/28_drc_pdrc_lvs_evidence_pipeline.md`

### W29 (2026-08-31 to 2026-09-06) - PDK adapter contract
- Work: Define adapter contract and capability matrix for public and toy PDKs.
- Artifacts: adapter interface + conformance tests.
- Validation: adapter test suite.
- Exit: Verification flow portable across PDK adapters.

### W30 (2026-09-07 to 2026-09-13) - PDK manifest enforcement
- Work: Include `pdk_manifest.json` in all layout/signoff runs and enforce in certification mode.
- Artifacts: manifest schema + bundle integration.
- Validation: certification run fails when manifest missing.
- Exit: PDK identity and rule context always present in evidence.

### W31 (2026-09-14 to 2026-09-20) - Foundry DRC sealed runner seam
- Work: Add sealed runner contract for proprietary decks (summary metadata only).
- Artifacts: runner interface + summary schema.
- Validation: mock runner integration tests.
- Exit: Enterprise DRC seam available without leaking proprietary decks.

### W32 (2026-09-21 to 2026-09-27) - Canonical golden chain fixture
- Work: Establish one full chain fixture: graph -> layout -> KLayout -> LVS-lite -> SPICE -> evidence.
- Artifacts: canonical fixture, runbook, optional CI lane.
- Validation: full chain determinism checks.
- Exit: Golden chain fixture locked as regression guardrail.

## Phase 58 (W33-W36): Inverse design Wave 3
Source anchors:
- `docs/research/deep_dive/19_inverse_design_engine_architecture.md`
- `docs/research/deep_dive/29_inverse_design_adjoint_strategy_licensing_and_evidence.md`

### W33 (2026-09-28 to 2026-10-04) - Mandatory inverse-design evidence gates
- Work: Certification mode requires complete inverse-design evidence artifacts.
- Artifacts: schema and gating updates.
- Validation: certification failure tests for incomplete evidence.
- Exit: Inverse-design claims are evidence-first.

### W34 (2026-10-05 to 2026-10-11) - Robust optimization knobs
- Work: Add fabrication corner robustness and worst-case reporting.
- Artifacts: robustness sweep outputs and thresholds.
- Validation: corner regression tests.
- Exit: Robustness becomes required, not optional.

### W35 (2026-10-12 to 2026-10-18) - External solver plugin boundary
- Work: Add plugin boundary for optional external/GPL solver paths.
- Artifacts: plugin runner seam and policy docs.
- Validation: plugin/no-plugin artifact parity checks.
- Exit: License-safe architecture with optional solver extensibility.

### W36 (2026-10-19 to 2026-10-25) - Flagship inverse-designed component
- Work: Deliver one flagship component end-to-end with robustness and signoff evidence.
- Artifacts: component package + evidence bundle.
- Validation: replay and signoff checks.
- Exit: Denial-resistant inverse-design demo fixture complete.

## Phase 59 (W37-W40): Event kernel and external interop
Source anchors:
- `docs/research/deep_dive/25_event_kernel_and_backend_interop.md`
- `docs/research/04_network_kernel_and_protocols.md`

### W37 (2026-10-26 to 2026-11-01) - Deterministic event ordering
- Work: Enforce total event ordering key and trace modes.
- Artifacts: trace schema and deterministic trace outputs.
- Validation: stable trace hash checks.
- Exit: Event kernel determinism contract formalized.

### W38 (2026-11-02 to 2026-11-08) - Protocol step logs
- Work: Export protocol step logs and optional QASM artifacts.
- Artifacts: `protocol_steps` artifacts in run bundles.
- Validation: schema + replay linkage tests.
- Exit: Protocol behavior auditable at step level.

### W39 (2026-11-09 to 2026-11-15) - External simulation import contract
- Work: Define and implement external simulator result import.
- Artifacts: interop schema and importer path.
- Validation: imported result to card flow.
- Exit: Vendor-neutral ingest path operational.

### W40 (2026-11-16 to 2026-11-22) - Interop-aware run diff
- Work: Add native-vs-imported comparison surfaces in run browser and diff APIs.
- Artifacts: diff and visualization updates.
- Validation: interop diff tests.
- Exit: Cross-tool comparison available for reviewers.

## Phase 60 (W41-W44): Platform performance and security scale-up
Source anchors:
- `docs/audit/05_performance_bottlenecks.md`
- `docs/upgrades/03_upgrade_ideas_platform_quality_security.md`
- `docs/research/deep_dive/07_security_privacy_and_compliance.md`

### W41 (2026-11-23 to 2026-11-29) - Async compute and compile caching
- Work: Add background job model and config-hash compile cache.
- Artifacts: async endpoints, job status artifacts.
- Validation: API load smoke tests.
- Exit: Long-running compute no longer blocks API.

### W42 (2026-11-30 to 2026-12-06) - Uncertainty parallelization and detector fast path
- Work: Parallelize uncertainty sampling and add vectorized detector path.
- Artifacts: performance changes with determinism safeguards.
- Validation: runtime and numeric parity tests.
- Exit: Runtime targets improved with reproducible outputs.

### W43 (2026-12-07 to 2026-12-13) - AuthN/AuthZ hardening
- Work: Add role-based auth for runs/artifacts/approvals.
- Artifacts: auth middleware, role model, tests.
- Validation: 401/403/role tests.
- Exit: Governance surfaces permissioned and auditable.

### W44 (2026-12-14 to 2026-12-20) - SBOM and immutable publish by digest
- Work: Add SBOM generation and immutable content-digest publication path.
- Artifacts: SBOM outputs and manifest pointers.
- Validation: fetch-by-digest verify tests.
- Exit: Supply-chain and artifact immutability chain complete.

## Phase 61 (W45-W48): Adoption and pilot conversion
Source anchors:
- `docs/research/deep_dive/08_adoption_and_distribution_strategy.md`
- `docs/audit/09_packaging_improvements.md`
- `docs/operations/pilot_readiness_packet/*`

### W45 (2026-12-21 to 2026-12-27) - Packaging/docs readiness
- Work: Finalize `CITATION.cff`, docs structure, templates, adoption docs.
- Artifacts: package metadata and onboarding docs.
- Validation: clean-environment quickstart timing.
- Exit: Public adoption package coherent and complete.

### W46 (2026-12-28 to 2027-01-03) - Benchmark and repro pack refresh
- Work: Refresh open benchmarks and reproducibility packs.
- Artifacts: updated open benchmark index and repro bundles.
- Validation: `python scripts/validation/check_open_benchmarks.py`
- Exit: External reproducibility path current and stable.

### W47 (2027-01-04 to 2027-01-10) - External pilot cycles
- Work: Run two external pilot cycles using formal intake/success/gate templates.
- Artifacts: pilot outcome packets and gate logs.
- Validation: mandatory pilot acceptance gates.
- Exit: Two pilots complete with decision classification.

### W48 (2027-01-11 to 2027-01-17) - Pilot-to-paid conversion package
- Work: Convert pilot outputs into recurring product and service package inputs.
- Artifacts: conversion memo and support runbook updates.
- Validation: internal signoff (TL + QA + DOC).
- Exit: Sales-engineering handoff package approved.

## Phase 62 (W49-W52): GA release cycle
Source anchors:
- `docs/research/deep_dive/10_operational_readiness_and_release_gates.md`
- `docs/research/deep_dive/14_milestone_acceptance_templates.md`
- `docs/research/deep_dive/12_execution_program_24_weeks.md`

### W49 (2027-01-18 to 2027-01-24) - RC freeze and baseline lock
- Work: Freeze RC, regenerate fixtures, and lock validation manifests.
- Artifacts: frozen baseline hashes and RC validation bundle.
- Validation: full test + harness run.
- Exit: RC baseline set locked.

### W50 (2027-01-25 to 2027-01-31) - External reviewer dry run
- Work: Execute dry-run template and triage findings.
- Artifacts: reviewer report and severity closure plan.
- Validation: no critical unresolved findings.
- Exit: External reviewer go/conditional-go status achieved.

### W51 (2027-02-01 to 2027-02-07) - Final release gate package
- Work: Complete milestone acceptance templates and final release notes.
- Artifacts: release gate packet and signed approvals.
- Validation: `python scripts/release/release_gate_check.py`
- Exit: release gate PASS with approver signoff.

### W52 (2027-02-08 to 2027-02-14) - GA publish and next-cycle handoff
- Work: Publish GA, run post-release review, and stage Phase 63+ backlog.
- Artifacts: GA release bundle, postmortem, next-cycle queue.
- Validation: GA artifact verification and replay sample.
- Exit: GA approved and post-GA planning opened.

---

## 3) Quarter control checkpoints

- End Q1 (Week 13): Quality/security/config + multifidelity foundations complete.
- End Q2 (Week 26): Protocol expansion and satellite realism core complete; PDRC expansion active.
- End Q3 (Week 39): GraphSpec, PDK interop, inverse design wave 3, and event-kernel interop complete.
- End Q4 (Week 52): Platform scale-up, pilot conversion, and GA release complete.

---

## 4) Weekly KPI set

Trust:
- Calibration diagnostics pass rate.
- Multi-fidelity agreement pass rate on canonical scenarios.

Reproducibility:
- Replay pass rate by scenario class.
- Evidence verification success rate.

Performance:
- p95 preview latency.
- full uncertainty runtime per flagship scenario.

Adoption:
- pilot time-to-first-card.
- pilot acceptance-gate pass rate.
- pilot-to-paid conversion rate.

Quality:
- benchmark drift incidents per release.
- release gate pass consistency.

---

## 5) Source corpus used for this plan

- `docs/operations/phased_rollout/README.md`
- `docs/operations/phased_rollout/FAST_EXECUTION_OVERLAY.md`
- `docs/operations/phased_rollout/phase_49_cross_track_integration/10_phase49_closeout_report_2026-02-16.md`
- `docs/operations/phased_rollout/phase_49_cross_track_integration/11_phase5_followthrough_report_2026-02-16.md`
- `docs/operations/phased_rollout/phase_49_cross_track_integration/13_day0_rehearsal_report_2026-02-16.md`
- `docs/research/10_roadmap_and_milestones.md`
- `docs/research/14_physics_core_open_science_master_plan_2026-02-12.md`
- `docs/research/15_platform_rollout_plan_2026-02-13.md`
- `docs/research/16_web_research_update_2026-02-13.md`
- `docs/research/deep_dive/12_execution_program_24_weeks.md`
- `docs/research/deep_dive/14_milestone_acceptance_templates.md`
- `docs/research/deep_dive/21_v1_to_v3_fast_execution_plan.md`
- `docs/research/deep_dive/23_protocol_roadmap_and_validation_gates.md`
- `docs/research/deep_dive/24_evidence_bundle_publishing_and_signing.md`
- `docs/research/deep_dive/25_event_kernel_and_backend_interop.md`
- `docs/research/deep_dive/26_physics_engine_multifidelity_quutip_qiskit_plan.md`
- `docs/research/deep_dive/27_drag_drop_component_ir_and_non_json_authoring.md`
- `docs/research/deep_dive/28_drc_pdrc_lvs_evidence_pipeline.md`
- `docs/research/deep_dive/29_inverse_design_adjoint_strategy_licensing_and_evidence.md`
- `docs/research/deep_dive/30_klayout_gds_spice_end_to_end_workflow.md`
- `docs/research/deep_dive/32_satellite_qkd_realism_pack.md`
- `docs/upgrades/01_upgrade_ideas_qkd_and_satellite.md`
- `docs/upgrades/02_upgrade_ideas_pic_and_verification.md`
- `docs/upgrades/03_upgrade_ideas_platform_quality_security.md`
- `docs/audit/00_audit_index.md`
- `docs/audit/03_configuration_validation.md`
- `docs/audit/04_ci_cd_improvements.md`
- `docs/audit/05_performance_bottlenecks.md`
- `docs/audit/06_dependency_security.md`
- `docs/audit/07_code_quality.md`
- `docs/audit/08_reliability_card_v1_1.md`
- `docs/audit/09_packaging_improvements.md`
