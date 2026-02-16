# PhotonTrust Business Expansion and Build Plan (2026-02-12)

This plan expands PhotonTrust from "photonic quantum link reliability cards" into
an execution platform for:
- photonic chip verification workflows, and
- satellite/space quantum link verification workflows.

The strategy below is source-backed and mapped to the current repository
architecture.

## 1) Strategic direction

## Core thesis
- Keep one scientific engine, ship two product surfaces.
- Surface A: `PhotonTrust ChipVerify` for photonic chip/system teams.
- Surface B: `PhotonTrust OrbitVerify` for satellite/space link teams.

Inference: one shared engine lowers R&D cost and keeps model trust consistent
across terrestrial and space deployments.

## Why now (evidence snapshot)
- AIM Photonics service stack includes process design kits (PDKs), MPW shuttles,
  and packaging/test enablement, indicating active PIC design-to-test demand:
  https://www.aimphotonics.com/services-workflow/
- Integrated photonics is already scaling into operational trusted-node
  deployments (signal for chip-to-network verification demand):
  https://www.nature.com/articles/s41586-026-08816-0
- OIF has active 2024-2025 implementation agreements for co-packaged optics,
  showing packaging/interoperability pressure in photonic systems:
  https://www.oiforum.com/technical-work/
- Europe is funding satellite QKD infrastructure (EAGLE-1 / EuroQCI), and ESA
  frames EAGLE-1 as Europe's first satellite-based QKD system:
  https://connectivity.esa.int/projects/eagle-1
- Canada is running QEYSSat to validate satellite-ground QKD technologies:
  https://www.asc-csa.gc.ca/eng/satellites/qeyssat/default.asp
- Quantum/space regulatory and qualification requirements are explicit and
  tightening (EAR updates, ITAR spacecraft controls, FCC deorbit rule):
  https://www.ecfr.gov/current/title-15/subtitle-B/chapter-VII/subchapter-C/part-774
  https://www.ecfr.io/Title-22/Section-121.1
  https://www.fcc.gov/document/fcc-adopts-new-5-year-rule-deorbiting-satellites-0

## 2) Product model and customer wedges

## Wedge 1 (first revenue): ChipVerify
- Buyer: photonic design teams, foundry enablement teams, advanced packaging
  groups, quantum hardware labs.
- Primary pain:
  - hard handoff from PIC design to system-level performance/risk metrics,
  - weak uncertainty/provenance in current analysis reports,
  - expensive iteration from lab failures discovered late.
- Product promise:
  - drag-drop component graph -> calibrated simulation -> reliability card +
    design-risk deltas for next tape-out iteration.

## Wedge 2 (expansion): OrbitVerify
- Buyer: satellite quantum comm programs, space systems primes, national labs.
- Primary pain:
  - free-space/space channel uncertainty not tracked consistently across teams,
  - ground-to-sat experiment assumptions fragmented in docs/spreadsheets,
  - compliance evidence and mission assurance artifacts are difficult to audit.
- Product promise:
  - mission graph + environmental assumptions -> uncertainty-aware link
    reliability reports and decision triggers.

## 3) Physics engine work: where to invest first

Current engine status (from repo): deterministic and modular but still MVP-level
for space-grade and foundry-grade verification.

## Priority P0 (0-12 weeks)
- Emitter model upgrades (`photonstrust/physics/emitter.py`)
  - move beyond steady-state-only `g2_0` estimation to pulse-resolved dynamics.
  - add explicit linewidth/spectral purity outputs and mismatch penalties.
- Detector model upgrades (`photonstrust/physics/detector.py`)
  - add gated-window mode, saturation effects, and detector state machine for
    afterpulse/dead-time coupling.
- Memory model upgrades (`photonstrust/physics/memory.py`)
  - separate amplitude damping and pure dephasing uncertainty outputs.
  - emit confidence diagnostics, not only scalar variance.
- Channel layer extension (`photonstrust/channels/`)
  - add free-space/satellite channel model with pointing loss, turbulence proxy,
    atmospheric loss by elevation, and daylight/background terms.
- Fiber QKD deployment realism pack (`photonstrust/qkd.py`, `photonstrust/channels/`)
  - add coexistence noise (Raman + background) parameterization for deployed fiber.
  - add misalignment/visibility QBER floor term.
  - add finite-key mode (non-asymptotic penalty) for decision-grade reporting.
  - spec: `deep_dive/16_qkd_deployment_realism_pack.md`
- Calibration hardening (`photonstrust/calibrate/`)
  - hierarchical calibration bundles (device-level + lot-level priors).
  - enforce diagnostics gates (R-hat, ESS, posterior predictive checks).

## Priority P1 (3-6 months)
- Component library for chip verification:
  - ring resonator, MZI, coupler, phase shifter, detector, grating coupler.
  - each component gets a parameter schema + validation tests.
- Event kernel realism:
  - deterministic retry/timeout semantics for operational mission flow.
  - fault injection for link outages and detector blinding windows.
- Protocol coverage:
  - explicit MDI-QKD and satellite key-relay templates.

## Priority P2 (6-12 months)
- GPU/parallel acceleration path for ensemble simulations.
- Surrogate model caching for interactive drag-drop previews.
- Scenario certification mode:
  - immutable signed artifacts with provenance references.

## Physics quality gates (must pass before external pilots)
- deterministic replay for fixed seed + config hash.
- reference benchmark agreement within declared tolerance envelopes.
- uncertainty diagnostics published on every external card.
- coexistence/finite-key sanity: monotonicity tests and explicit reporting of assumptions.

## 4) Drag-drop product architecture

## Frontend
- Build a dedicated web client for graph editing (keep Streamlit for internal
  analysis/reviewer flows).
- Candidate stack: React + React Flow (`@xyflow/react`) for node/edge editing:
  https://reactflow.dev/

## Execution pipeline
1. User builds topology graph (chip or satellite profile).
2. Graph compiler maps nodes/edges to `ScenarioConfig`.
3. Backend runs engine (`physics`, `events`, `protocols`, `calibrate`).
4. Reliability cards + decision report + provenance bundle are generated.
5. UI supports run-to-run diff and sensitivity drill-down.

## Boundary policy
- UI is a thin client. Scientific decisions stay in versioned backend modules.
- every UI action emits machine-readable config deltas.

## 5) Compliance and standards track

## Commercial photonic track
- PDK and tapeout-aligned flows:
  - AIM Photonics workflow: PDK + MPW + packaging/test ecosystem.
  - EDA integration signals from Ansys/Luceda/Cadence ecosystem.
- Reliability references:
  - MIL-STD-883 remains a major microelectronics reliability baseline
    (Rev L listed June 27, 2025):
    https://landandmaritimeapps.dla.mil/Downloads/MilSpecDocs/MIL-STD-883L.pdf

## Space/satellite track
- Architecture/mission context:
  - ESA EAGLE-1 and CSA QEYSSat mission programs.
- Qualification references:
  - ECSS standards framework:
    https://ecss.nl/home/ecss-a-single-set-of-european-cooperation-for-space-standardization-standards/
  - NASA EEE guidance (EEE-INST-002 metadata):
    https://nepp.nasa.gov/DocUploads/07B18CD6-83A8-4281-8FF7-6EA421A97954/EEE-INST-002_Add1.pdf
- Export and control awareness:
  - EAR Part 774 (current page shows amendments through January 7, 2026).
  - ITAR/USML Category XV includes spacecraft and related articles.
- Operational policy:
  - FCC 5-year deorbit rule for satellites in low Earth orbit.

Inference: OrbitVerify must include a compliance evidence mode from day one to
be viable for government/defense-adjacent pilots.

## 6) Business model

## Offer tiers
- Open core (`PhotonTrust OSS`):
  - local simulations, baseline reliability cards, public schemas.
- Team (`ChipVerify Team`):
  - managed runs, shared projects, benchmark governance, API access.
- Enterprise/Gov (`OrbitVerify Secure`):
  - on-prem or isolated deployment, signed artifacts, audit workflows,
    compliance report bundles.

## Services layer
- paid onboarding: model calibration against customer hardware data.
- paid verification engagements: pre-tapeout and pre-mission design reviews.

## Pricing motion (recommended)
- Start with annual license + professional services.
- Move to usage-based compute add-on once workload is predictable.

## 7) Concrete build roadmap (18 months)

## Phase A: Foundation (Month 0-3)
- Deliverables:
  - free-space channel MVP
  - detector gating/saturation model
  - graph schema v0.1 for drag-drop
  - first customer-facing "ChipVerify alpha" CLI + report flow
- Gate:
  - 3 internal benchmark scenarios with stable uncertainty outputs.

## Phase B: Design platform beta (Month 4-8)
- Deliverables:
  - React Flow-based graph editor (alpha)
  - component library v1 (chip + link primitives)
  - scenario diff and provenance panel
  - calibration diagnostics integrated in CI
- Gate:
  - 2 external design partners run end-to-end and reproduce outputs.

## Phase C: Satellite vertical pilot (Month 9-14)
- Deliverables:
  - OrbitVerify profile pack (ground station, orbital pass templates,
    atmosphere/pointing assumptions)
  - compliance evidence bundle v1 (EAR/ITAR/FCC mapping fields)
  - mission rehearsal report templates
- Gate:
  - 1 satellite pilot partner signs off on report utility for design reviews.

## Phase D: Scale and standardize (Month 15-18)
- Deliverables:
  - reliability card v2 with chip + orbit extensions
  - signed artifact pipeline and release attestation
  - enterprise deployment docs + SLOs
- Gate:
  - 3 paid customers, repeatable onboarding playbook, sub-2-week pilot setup.

## 8) Operating metrics

## Product metrics
- time from graph edit to result card (p95).
- percentage of runs with complete uncertainty diagnostics.
- scenario reproducibility pass rate across environments.

## Business metrics
- pilot-to-paid conversion rate.
- average time to first trusted decision report.
- annual recurring revenue split: license vs services.

## Quality metrics
- benchmark drift events per release.
- model validation pass rate against calibration datasets.
- percentage of releases with signed provenance bundle.

## 9) Immediate execution plan (next 6 weeks)

1. Lock product requirements for ChipVerify alpha and OrbitVerify profile
   boundaries.
2. Create component schema registry (`components/*.json`) for drag-drop nodes.
3. Implement free-space channel module and tests.
4. Add calibration diagnostics policy checks in CI.
5. Build minimal graph compiler API (graph JSON -> existing ScenarioConfig).
6. Run two "design review rehearsal" cases and generate decision reports.

## 10) Source index (primary-first)

### Ecosystem, tooling, and product stack
- AIM Photonics workflow/services: https://www.aimphotonics.com/services-workflow/
- Ansys photonic flow (compact models/CML workflow anchor): https://optics.ansys.com/hc/en-us/articles/360055701453-CML-Compiler-overview
- Luceda-Cadence integration signal: https://www.epda.org/Articles/258048/Luceda_Photonics_Cadence_Virtuoso.aspx
- gdsfactory (open-source PIC automation): https://gdsfactory.github.io/gdsfactory/
- OIF technical work and implementation agreements: https://www.oiforum.com/technical-work/
- React Flow docs: https://reactflow.dev/

### Satellite and quantum comm programs
- ESA EAGLE-1: https://connectivity.esa.int/projects/eagle-1
- CSA QEYSSat: https://www.asc-csa.gc.ca/eng/satellites/qeyssat/default.asp
- EU EuroQCI policy page: https://digital-strategy.ec.europa.eu/en/policies/european-quantum-communication-infrastructure-euroqci
- Satellite QKD (Micius, Nature 2017): https://www.nature.com/articles/nature23655

### Standards, qualification, and compliance
- MIL-STD-883 Rev L listing/PDF: https://landandmaritimeapps.dla.mil/Programs/MilSpec/listdocs.aspx?BasicDoc=MIL-STD-883
- ECSS standards framework: https://ecss.nl/home/ecss-a-single-set-of-european-cooperation-for-space-standardization-standards/
- NASA EEE-INST-002 Addendum 1 metadata/PDF: https://nepp.nasa.gov/DocUploads/07B18CD6-83A8-4281-8FF7-6EA421A97954/EEE-INST-002_Add1.pdf
- EAR Part 774 (eCFR): https://www.ecfr.gov/current/title-15/subtitle-B/chapter-VII/subchapter-C/part-774
- ITAR/USML text reference: https://www.ecfr.io/Title-22/Section-121.1
- FCC 5-year deorbit rule release: https://www.fcc.gov/document/fcc-adopts-new-5-year-rule-deorbiting-satellites-0

### Core quantum software cadence
- QuTiP download/releases: https://qutip.org/download.html
- Qiskit release notes 2.x: https://quantum.cloud.ibm.com/docs/en/api/qiskit/release-notes/2.3
- Streamlit release notes: https://docs.streamlit.io/develop/quick-reference/release-notes
