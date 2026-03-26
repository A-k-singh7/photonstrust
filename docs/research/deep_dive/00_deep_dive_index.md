# PhotonTrust Deep-Dive Research Index

This folder expands the core research docs into implementation-grade detail.
Use this index as the primary navigation map for execution.

## How to use this deep-dive set
- Read in order for a full program-level picture.
- Use each document's checklists as acceptance gates.
- Treat every section labeled "Definition of done" as release criteria.
- Cross-check with `../12_web_research_update_2026-02-12.md` for external
  standards, current toolchain status, and source-backed updates.
- If you want a short "what should we upgrade next?" list, start with:
  - `../../upgrades/README.md`

## Deep-dive documents
1. `01_calibration_math_and_inference.md`
   - Statistical model assumptions, priors, likelihoods, posterior diagnostics.
2. `02_uncertainty_propagation_and_reporting.md`
   - Monte Carlo design, confidence construction, outage semantics.
3. `03_protocol_validation_matrix.md`
   - Protocol-by-protocol correctness tests and regression criteria.
4. `04_benchmark_suite_governance.md`
   - Dataset governance, versioning, benchmark lifecycle.
5. `05_performance_engineering_plan.md`
   - Runtime profile targets, acceleration strategy, scalability plan.
6. `06_reliability_card_v1_1_draft.md`
   - Next iteration of card semantics and interoperability fields.
7. `07_security_privacy_and_compliance.md`
   - Security posture, integrity checks, controlled artifact sharing.
8. `08_adoption_and_distribution_strategy.md`
   - Open-source growth, standards pathway, enterprise onboarding.
9. `09_community_operating_model.md`
   - Maintainer workflow, governance, issue triage, release rituals.
10. `10_operational_readiness_and_release_gates.md`
    - Program-level quality gates before v1.0 publication.
11. `11_experiment_playbooks.md`
    - Reproducible playbooks for flagship scenarios and paper-ready figures.
12. `12_execution_program_24_weeks.md`
    - Week-by-week execution plan with role-level deliverables.
13. `13_raci_matrix.md`
    - Owner and accountability matrix for all major workstreams.
14. `14_milestone_acceptance_templates.md`
    - Ready-to-use acceptance templates for milestones and release gates.
15. `15_research_to_build_protocol.md`
    - Mandatory operating protocol: research -> plan -> build/test -> docs.
16. `16_qkd_deployment_realism_pack.md`
    - Fiber QKD realism extensions: coexistence (Raman/background), misalignment QBER floor, finite-key penalty, and reporting gates.
17. `17_chip_inverse_design_and_open_pdk_strategy.md`
    - Discussion doc: why full-chip inverse design is a trap, and the buildable path (component inverse design + evidence + PDK integration).
18. `18_open_pdk_klayout_gdsfactory_playbook.md`
    - Practical guide: open/public PDK targets, KLayout DRC workflows, and gdsfactory integration for ChipVerify.
19. `19_inverse_design_engine_architecture.md`
    - Technical spec: adjoint optimization engine interfaces, constraints, backend options, and validation gates.
20. `20_startup_strategy_chip_inverse_design_and_verification.md`
    - Startup strategy: wedge, moat, and commercialization plan for inverse design + verification.
21. `21_v1_to_v3_fast_execution_plan.md`
    - Execution-grade roadmap: v1 -> v3 fast path (performance DRC + data loop + inverse design + UI control plane).
22. `22_competitor_gap_analysis_and_moat_moves.md`
    - Competitor map (QKD simulators + PIC CAD) and non-copying implementation moves to win on trust + workflow integration.
23. `23_protocol_roadmap_and_validation_gates.md`
    - Protocol expansion roadmap (decoy BB84, MDI-QKD, TF/PM-QKD, CV-QKD) + validation gates and applicability labeling.
24. `24_evidence_bundle_publishing_and_signing.md`
    - Evidence bundle publishing + cryptographic signing plan (Sigstore/in-toto/SLSA) with approval integration.
25. `25_event_kernel_and_backend_interop.md`
    - Event kernel determinism + scalability + protocol-step logging; interop adapters for external simulators.
26. `26_physics_engine_multifidelity_quutip_qiskit_plan.md`
    - Multi-fidelity physics plan: analytic + stochastic + QuTiP/Qiskit cross-checks, determinism, and evidence artifacts.
27. `27_drag_drop_component_ir_and_non_json_authoring.md`
    - Drag-drop evolution to component-level engineering UX; non-JSON authoring (TOML GraphSpec) with round-trip guarantees.
28. `28_drc_pdrc_lvs_evidence_pipeline.md`
    - Full DRC/PDRC/LVS-lite verification pipeline spec and evidence pack requirements (KLayout + CI + UI).
29. `29_inverse_design_adjoint_strategy_licensing_and_evidence.md`
    - Adjoint/inverse design decision rules, licensing strategy, and "evidence pack" definition of done.
30. `30_klayout_gds_spice_end_to_end_workflow.md`
    - End-to-end PIC chain runbook: layout -> GDS -> KLayout pack -> LVS-lite -> SPICE export -> evidence bundle.
31. `31_fundable_wedge_and_denial_resistant_demos.md`
    - Investor-grade demo plan and moat story (performance DRC, KLayout chain, satellite reliability cards).
32. `32_satellite_qkd_realism_pack.md`
    - Satellite/free-space realism pack: atmosphere path length, background, pointing/turbulence distributions, finite-key, and evidence fields.
33. `33_foundry_pdk_specifications_research.md`
    - Comprehensive research report: published specs, design rules, layer stacks, and component parameters for six major photonics foundry PDKs (SiEPIC, AIM, IMEC, GF 45CLO, Ligentec AN800, LioniX TriPleX). Includes cross-platform comparisons and PDK manifest mapping guidance.

## Execution sequence recommendation
- Wave 1: 01, 02, 03 (scientific integrity)
- Wave 2: 04, 05, 06 (product and benchmark quality)
- Wave 3: 07, 08, 09 (adoption and governance)
- Wave 4: 10, 11 (release completion and publication)
- Wave 5: 12, 13, 14 (program operations and release execution)
- Wave 6: 15 (operating discipline and auditability)

## Program checkpoints
- Checkpoint A: Posterior calibration and uncertainty reporting validated
- Checkpoint B: Benchmark suite stable and CI-backed
- Checkpoint C: Reliability Card spec frozen for external reviewers
- Checkpoint D: Public release candidate with docs, UI, and run registry

## Inline citations (web, verified 2026-02-12)
Applied to: execution sequence rationale, architecture assumptions, and ecosystem stability.
- RFC 9340: Architectural Principles for a Quantum Internet (March 2023): https://www.rfc-editor.org/info/rfc9340
- IETF QIRG draft (November 2025): https://www.ietf.org/archive/id/draft-cacciapuoti-qirg-quantum-native-architecture-00.html
- QuTiP latest releases (v5.2.3 listed on January 26, 2026): https://qutip.org/download.html
- Qiskit SDK 2.2 release notes (IBM Quantum docs): https://quantum.cloud.ibm.com/docs/en/api/qiskit/release-notes/2.2
- Streamlit release notes (v1.54.0, February 4, 2026): https://docs.streamlit.io/develop/quick-reference/release-notes

