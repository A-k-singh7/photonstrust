# PhotonTrust Research Overview

This document frames the overall research and execution plan for making
PhotonTrust the widely adopted reliability layer for photonic quantum networks.
It sets the scope, success criteria, and the structure of the research bundle.

## Mission and Adoption Goal
- Mission: translate hardware physics into trusted network-level performance and
  a shareable Reliability Card standard.
- Adoption goal: become the default evaluation layer for QKD, repeaters, and
  teleportation in research, industry, and standards discussions.

## Research Outputs (this bundle)
1) Market and ecosystem landscape
2) Technical architecture and interfaces
3) Physics models and calibration strategy
4) Protocol compiler and network kernel plan
5) Optimization and decision outputs
6) Reliability Card standard and schema
7) Benchmark datasets and baselines
8) UX and product strategy
9) Roadmap and execution milestones
10) Risks, mitigations, and quality gates
11) Business expansion plan for photonic chip verification and satellite workflows
12) Physics-core open-science master plan and build backlog

## Success Criteria
Adoption is likely if all of the following are true:
- Reproducible results with deterministic seeds and calibrated parameters
- Clear reliability artifacts that are easy to compare and share
- Strong alignment with existing tools (QuTiP, Qiskit, NetSquid concepts)
- Trust by showing uncertainty bounds and error budgets
- Tooling that is fast enough for day-to-day engineering decisions

## How to Use This Research
- Use the docs in order for full context.
- Each document ends with a checklist for implementation or validation.
- Update the research as the codebase evolves to keep the spec and product
  in sync.
- Use `12_web_research_update_2026-02-12.md` for the source-backed expansion
  and standards alignment layer.

## Directory Map
- 00_overview.md
- 01_market_landscape.md
- 02_architecture_and_interfaces.md
- 03_physics_models.md
- 04_network_kernel_and_protocols.md
- 05_calibration_and_uncertainty.md
- 06_optimization_and_decisions.md
- 07_reliability_card_standard.md
- 08_benchmarks_and_datasets.md
- 09_product_and_ux.md
- 10_roadmap_and_milestones.md
- 11_risks_quality_and_governance.md
- 12_web_research_update_2026-02-12.md
- 13_business_expansion_and_build_plan_2026-02-12.md
- 14_physics_core_open_science_master_plan_2026-02-12.md
- 15_platform_rollout_plan_2026-02-13.md

## Deep-dive map
- `deep_dive/00_deep_dive_index.md` is the entry point for granular research.
- The deep-dive set expands the core plan into implementation-grade detail.
