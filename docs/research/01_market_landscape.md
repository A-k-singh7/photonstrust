# Market and Ecosystem Landscape

This document updates positioning for two business wedges:
- photonic chip verification workflows, and
- satellite quantum communication verification workflows.

## Ecosystem map (2026-02-12)

## Adjacent simulation and protocol tools
- NetSquid, SeQUeNCe, QuNetSim remain important references for network-level
  simulation.
- QuTiP and Qiskit are still core dependencies, but they are libraries, not
  end-to-end reliability decision products.

## Photonic design/manufacturing ecosystem
- Foundry/service ecosystem activity is strong (PDK, MPW, packaging/test
  workflows), e.g., AIM Photonics services:
  https://www.aimphotonics.com/services-workflow/
- EDA ecosystem direction is converging toward integrated PIC design + DRC/LVS
  + compact-model flows (Ansys/Luceda/Cadence signals):
  https://optics.ansys.com/hc/en-us/articles/360055701453-CML-Compiler-overview
  https://www.epda.org/Articles/258048/Luceda_Photonics_Cadence_Virtuoso.aspx
- Co-packaged optics standardization/implementation activity is ongoing in OIF
  (2024-2025 updates), reinforcing verification and interoperability demand:
  https://www.oiforum.com/technical-work/

## Satellite quantum and space ecosystem
- ESA EAGLE-1 and CSA QEYSSat indicate active public-sector demand for
  satellite QKD pathfinding:
  https://connectivity.esa.int/projects/eagle-1
  https://www.asc-csa.gc.ca/eng/satellites/qeyssat/default.asp
- EuroQCI frames long-term European deployment direction for secure quantum
  infrastructure:
  https://digital-strategy.ec.europa.eu/en/policies/european-quantum-communication-infrastructure-euroqci

## Where PhotonTrust fits

## Gap 1: verification-to-decision layer
- Existing stacks are strong for simulation and design, weaker for
  uncertainty-aware, reproducible, decision-ready reporting.
- PhotonTrust should own the "trusted decision artifact" layer:
  model assumptions -> calibrated outputs -> reliability card -> recommended
  next engineering action.

## Gap 2: cross-domain consistency
- Teams working on photonic chips and satellite links often use separate models
  and reporting habits.
- PhotonTrust can unify artifact quality across terrestrial and space contexts.

Inference: this cross-domain consistency is a defensible differentiator if card
schemas and uncertainty diagnostics are held constant across products.

## Priority customers and value proposition

## ChipVerify (near-term)
- Photonic design teams, foundry enablement, and quantum hardware labs.
- Value: faster design-review cycles and fewer late-stage validation surprises.

## OrbitVerify (expansion)
- Space systems teams and mission assurance groups.
- Value: mission scenario auditability and uncertainty-aware link readiness
  decisions.

## Research checklist
- Publish two benchmark packs:
  - chip verification benchmark pack (component + system metrics),
  - satellite pass benchmark pack (elevation/pointing/background regimes).
- Demonstrate one shared reliability schema across both packs.
- Run at least two external pilot studies before pricing finalization.

## Related docs
- `12_web_research_update_2026-02-12.md`
- `13_business_expansion_and_build_plan_2026-02-12.md`
