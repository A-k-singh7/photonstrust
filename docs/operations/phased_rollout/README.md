# PhotonTrust Strict Multi-Phase Rollout Protocol

This folder enforces a strict build discipline for physics-core development:

1. Research
2. Implementation plan
3. Build
4. Validation
5. Documentation updates

No phase is considered complete unless all required artifacts are present and
validation gates pass.

## Mandatory artifact contract per phase

Each phase folder must contain:
- `01_research_brief_YYYY-MM-DD.md`
- `02_implementation_plan_YYYY-MM-DD.md`
- `03_build_log_YYYY-MM-DD.md`
- `04_validation_report_YYYY-MM-DD.md`

Optional:
- notebooks, benchmark outputs, reviewer notes.

## Gate policy

A phase is approved only if:
- research brief is complete and linked to primary sources,
- implementation plan maps edits to specific files and tests,
- build log captures exactly what changed,
- validation report includes test evidence and decision,
- downstream docs were updated (`docs/research/*` and/or `README.md`).

## Rollout phases (active track)

- Phase 01: Free-space/satellite channel foundation
  - Folder: `phase_01_free_space_channel/`
  - Status: Complete
- Phase 02: Stateful detector model (gating/saturation/afterpulse)
  - Folder: `phase_02_detector_stateful_model/`
  - Status: Complete
- Phase 03: Emitter transient mode + spectral diagnostics
  - Folder: `phase_03_emitter_transient_mode/`
  - Status: Complete
- Phase 04: Calibration diagnostics enforcement gates
  - Folder: `phase_04_calibration_gates/`
  - Status: Complete
- Phase 05: Reliability-card trust extensions (evidence tiers, diagnostics block)
  - Folder: `phase_05_reliability_card_trust_extensions/`
  - Status: Complete
- Phase 06: Performance acceleration and multi-fidelity execution
  - Folder: `phase_06_multifidelity_performance/`
  - Status: Complete
- Phase 07: Open benchmark ingestion and external reproducibility package
  - Folder: `phase_07_open_benchmark_ingestion/`
  - Status: Complete
- Phase 08: Component graph schema v0.1 + compiler (UI -> engine)
  - Folder: `phase_08_graph_schema_compiler/`
  - Status: Complete
- Phase 09: ChipVerify PIC component library v1 + netlist execution
  - Folder: `phase_09_pic_component_library/`
  - Status: Complete
- Phase 10: ChipVerify compact model import (Touchstone/S-parameters) + sweeps
  - Folder: `phase_10_pic_compact_model_import/`
  - Status: Complete
- Phase 11: OrbitVerify mission templates v1 (pass envelopes + metadata)
  - Folder: `phase_11_orbit_mission_templates/`
  - Status: Complete
- Phase 12: Data contribution workflow (academic + industry safe)
  - Folder: `phase_12_data_contribution_workflow/`
  - Status: Complete
- Phase 13: Web drag-drop MVP (managed service surface)
  - Folder: `phase_13_web_drag_drop_mvp/`
  - Status: Complete
- Phase 14: Trust panel v0.2 (parameter registry + units/ranges)
  - Folder: `phase_14_trust_panel_param_registry/`
  - Status: Complete
- Phase 15: Graph validation + structured diagnostics (params, ports, kind support)
  - Folder: `phase_15_graph_validation_diagnostics/`
  - Status: Complete
- Phase 16: OrbitVerify web runner v0.1 (config-first pass envelopes)
  - Folder: `phase_16_orbit_web_runner/`
  - Status: Complete
- Phase 17: OrbitVerify validation + diagnostics v0.1 (schema + validate endpoint)
  - Folder: `phase_17_orbit_validation_diagnostics/`
  - Status: Complete
- Phase 18: OrbitVerify evidence hardening v0.2 (availability envelope + standards anchors)
  - Folder: `phase_18_orbit_availability_standards/`
  - Status: Complete
- Phase 19: Run registry + artifact serving v0.1 (managed-service hardening, local dev)
  - Folder: `phase_19_run_registry_artifact_serving/`
  - Status: Complete
- Phase 20: Run browser + run diff v0.1 (managed-service hardening, local dev)
  - Folder: `phase_20_run_browser_diff/`
  - Status: Complete
- Phase 21: Run output summaries + output diff scope v0.1 (managed-service hardening, local dev)
  - Folder: `phase_21_run_output_summary_diff/`
  - Status: Complete
- Phase 22: Project registry + approvals v0.1 (managed-service governance, local dev)
  - Folder: `phase_22_project_registry_approvals/`
  - Status: Complete
- Phase 23: Performance DRC flagship hardening v0.2 (route-level layout feature extraction)
  - Folder: `phase_23_performance_drc_layout_feature_extraction/`
  - Status: Complete
- Phase 24: GDS-level layout feature extraction v0.2 (optional seam)
  - Folder: `phase_24_gds_layout_feature_extraction/`
  - Status: Complete
- Phase 25: Crosstalk calibration loop v0.1 (measurement bundles -> fit -> drift governance)
  - Folder: `phase_25_crosstalk_calibration_loop/`
  - Status: Complete
- Phase 26: PIC circuit solver extensions v0.2 (ring resonator transfer; sweeps)
  - Folder: `phase_26_pic_solver_extensions/`
  - Status: Complete
- Phase 27: PDK-aware layout hooks v0.1 (deterministic sidecars + LVS-lite + optional KLayout runner seam)
  - Folder: `phase_27_pdk_layout_hooks/`
  - Status: Complete
- Phase 28: SPICE + KLayout interop v0.1 (SPICE export + optional ngspice runner seam)
  - Folder: `phase_28_spice_klayout_interop/`
  - Status: Complete
- Phase 29: PIC layout + LVS-lite + SPICE v0.1 (API + web tabs integration)
  - Folder: `phase_29_pic_layout_spice_api_web/`
  - Status: Complete
- Phase 30: KLayout macro templates + run artifact pack contract v0.1 (EDA seam hardening)
  - Folder: `phase_30_klayout_macros_artifact_pack/`
  - Status: Complete
- Phase 31: KLayout artifact pack API + web integration v0.1 (managed workflow surface)
  - Folder: `phase_31_klayout_pack_api_web/`
  - Status: Complete
- Phase 32: KLayout pack run registry source selection v0.1 (Runs picker -> selected GDS)
  - Folder: `phase_32_klayout_pack_run_registry_source/`
  - Status: Complete
- Phase 33: Inverse design robustness + evidence pack v0.1 (schema contract + corner cases + coupler ratio primitive)
  - Folder: `phase_33_invdesign_robustness_evidence_pack/`
  - Status: Complete
- Phase 34: Invdesign workflow chaining v0.1 (invdesign -> layout -> LVS-lite -> KLayout pack -> SPICE export)
  - Folder: `phase_34_invdesign_workflow_chaining/`
  - Status: Complete
- Phase 35: Workflow replay + evidence bundle export v0.1 (zip + replay + run linking UX)
  - Folder: `phase_35_workflow_replay_bundle_export/`
  - Status: Complete
- Phase 36: Evidence bundle attestation + schema contracts v0.1 (workflow report + bundle manifest)
  - Folder: `phase_36_evidence_bundle_attestation_schemas/`
  - Status: Complete
- Phase 37: GDS + KLayout pack enablement v0.1.1 (PATH emission + PDK-defaulted DRC-lite settings)
  - Folder: `phase_37_gds_klayout_pack_enablement/`
  - Status: Complete
- Phase 38: Config validation + CLI `--validate-only` v0.1.1 (fail-fast scenario validation; distance sweep stability)
  - Folder: `phase_38_config_validation_cli_validate_only/`
  - Status: Complete
- Phase 39: QKD physics trust gates v0.1.1 (PLOB sanity gate; seeded uncertainty; Kasten-Young airmass)
  - Folder: `phase_39_qkd_physics_trust_gates/`
  - Status: Complete
- Phase 40: Evidence bundle signing v0.1.2 (Ed25519 signing + verification; schema for signature artifact)
  - Folder: `phase_40_evidence_bundle_signing/`
  - Status: Complete
- Phase 41: QKD deployment realism pack (fiber) v0.1.3 (canonical presets + drift baselines + applicability notes)
  - Folder: `phase_41_qkd_deployment_realism_pack/`
  - Status: Complete
- Phase 42: Reliability card v1.1 (evidence tiers + operating envelope + standards anchors)
  - Folder: `phase_42_reliability_card_v1_1/`
  - Status: Complete
- Phase 43: MDI-QKD + TF/PM-QKD protocol surfaces (relay protocols + analytical models)
  - Folder: `phase_43_mdi_tf_pm_qkd_protocol_surfaces/`
  - Status: Complete
- Phase 44: QKD fidelity foundations (Poisson noise, dead time model, polarization-as-visibility)
  - Folder: `phase_44_qkd_fidelity_foundations/`
  - Status: Complete
- Phase 45: Raman coexistence effective-length model (attenuation-aware Raman counts)
  - Folder: `phase_45_raman_coexistence_effective_length/`
  - Status: Complete
- Phase 46: BBM92 coincidence model (SPDC multi-pair + Poisson noise coincidence accounting)
  - Folder: `phase_46_bbm92_coincidence_model/`
  - Status: Complete
- Phase 47: PIC scattering-network solver v0.2 (bidirectional ports + reflections + cycles)
  - Folder: `phase_47_pic_scattering_solver/`
  - Status: Complete
- Phase 48: PIC scattering realism pack v0.3 (edge propagation + native reflections + Touchstone N-port)
  - Folder: `phase_48_pic_scattering_realism_pack/`
  - Status: Complete
- Phase 50: Quality/security foundation (365-day plan kickoff)
  - Folder: `phase_50_quality_security_foundation/`
  - Status: Complete (W01-W04 implemented 2026-02-16)
- Phase 51: Multi-fidelity backend foundation (365-day plan continuation)
  - Folder: `phase_51_multifidelity_backend_foundation/`
  - Status: Complete (W05-W08 implemented 2026-02-16)
- Phase 52: Protocol expansion (365-day plan continuation)
  - Folder: `phase_52_protocol_expansion/`
  - Status: Complete (W09-W12 implemented 2026-02-16)
- Phase 53: Satellite realism S1/S2 (365-day plan continuation)
  - Folder: `phase_53_satellite_realism_s1_s2/`
  - Status: Complete (W13-W16 implemented 2026-02-16)
- Phase 54: Satellite S3/S4 + pilot hardening (365-day plan continuation)
  - Folder: `phase_54_satellite_s3_s4_pilot_hardening/`
  - Status: Complete (W17-W20 implemented 2026-02-16)
- Phase 55: GraphSpec TOML + round-trip guarantees (365-day plan continuation)
  - Folder: `phase_55_graphspec_roundtrip/`
  - Status: Complete (W21-W24 implemented 2026-02-16)
- Phase 56: DRC/PDRC/LVS expansion (365-day plan continuation)
  - Folder: `phase_56_drc_pdrc_lvs_expansion/`
  - Status: Complete (W25-W28 implemented 2026-02-16)
- Phase 57: PDK/Foundry interop hardening (365-day plan continuation)
  - Folder: `phase_57_w29_w32_pdk_foundry_interop_hardening/`
  - Status: Complete (W29-W32 implemented 2026-02-16)
- Phase 58: Inverse design wave 3 (365-day plan continuation)
  - Folder: `phase_58_w33_w36_inverse_design_wave3/`
  - Status: Complete (W33-W36 implemented 2026-02-16)
- Phase 59: Event kernel and external interop (365-day plan continuation)
  - Folder: `phase_59_w37_w40_event_kernel_external_interop/`
  - Status: Complete (W37-W40 implemented 2026-02-16)
- Phase 60: Platform performance and security scale-up (365-day plan continuation)
  - Folder: `phase_60_w41_w44_platform_perf_security_scaleup/`
  - Status: Complete (W41-W44 implemented 2026-02-16)
- Phase 61: Adoption and pilot conversion (365-day plan continuation)
  - Folder: `phase_61_w45_w48_adoption_pilot_conversion/`
  - Status: Complete (W45-W48 implemented 2026-02-16)
- Phase 62: GA release cycle (365-day plan continuation)
  - Folder: `phase_62_w49_w52_ga_release_cycle/`
  - Status: Complete (W49-W52 implemented 2026-02-16)

## Planned phases (draft)

These are the next increments for the v2/v3 fast execution overlay:
- `../../research/deep_dive/21_v1_to_v3_fast_execution_plan.md`
- `../../research/15_platform_rollout_plan_2026-02-13.md`
- `FAST_EXECUTION_OVERLAY.md` (mapping to phases + acceptance tests)

Draft list:
  (no draft phases currently tracked here)

## Process note

This protocol implements the strategy in:
- `../../research/14_physics_core_open_science_master_plan_2026-02-12.md`
- Fast execution overlay (v1 -> v3, "Strongest Contender Path"):
  - `../../research/deep_dive/21_v1_to_v3_fast_execution_plan.md`
