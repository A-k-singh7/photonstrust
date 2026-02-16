# PhotonTrust Web Research Update (2026-02-12)

This document expands the existing PhotonTrust research bundle with web-validated references and implementation guidance as of February 12, 2026.

## Scope and method
- Scope: `00_overview.md` through `14_physics_core_open_science_master_plan_2026-02-12.md`.
- Method: prioritize primary sources only (official docs, standards bodies, and peer-reviewed or archival papers).
- Timestamp policy: include concrete dates where ecosystem or version information can drift.

## 00 Overview: ecosystem signals
PhotonTrust is entering an active but fragmented landscape. QuTiP and Qiskit both moved materially in 2025-2026, which supports the original strategy of staying modular rather than hard-coding to one release line. As of February 12, 2026, the QuTiP download page lists v5.2.3 (released 2026-01-26) and IBM's Qiskit API documentation publishes a 2.x line (for example, 2.3.0 release notes), so interface versioning and compatibility tests should be treated as first-class work, not cleanup.

Quantum networking architecture guidance has matured through RFC 9340 (March 2023), and newer QIRG drafts (November 2025) are expanding architecture tenets. This supports the existing plan to keep PhotonTrust's physics, control, and reporting planes explicitly separated.

## 01 Market and ecosystem landscape: validated updates
The competitive map remains accurate, but should explicitly include the newest SeQUeNCe activity and the relative positioning of QuNetSim as a higher-layer framework. NetSquid remains a heavily cited reference simulator in the literature, while SeQUeNCe is open and has current research momentum, including heterogeneous network simulations (2025 preprint activity).

Recommended positioning refinement:
- Keep "physics-calibrated reliability layer" as the core message.
- Differentiate against simulator-only tools by emphasizing decision outputs, uncertainty propagation, and reportable trust artifacts.
- Explicitly target interoperability with simulator ecosystems rather than replacement.

## 02 Architecture and interfaces: standards alignment
OpenQASM 3 should remain the default circuit/protocol representation for local and near-hardware control paths. For broader interoperability planning, define an optional export path to QIR (LLVM-based) for organizations with compiler-heavy workflows.

For network architecture semantics, map EventKernel concepts to RFC 9340 language:
- quantum data plane events (entanglement operations and per-pair control signals)
- classical/control plane messages (scheduling, routing, orchestration)

Interchange recommendations:
- Keep JSON schemas versioned with explicit semantic versions.
- Add provenance-compatible metadata fields compatible with CodeMeta and W3C PROV style lineage.

## 03 Physics models: implementation-grade upgrades
QuTiP-first remains the right default. QuTiP v5 family status and the qutip-qip split from core QuTiP should be reflected in dependency planning, because circuit/noise tooling may be packaged separately from core dynamics.

Model-level upgrades:
- Keep Jaynes-Cummings and Lindblad baselines, but define acceptable mismatch envelopes against measured data (not just visual fit).
- Record detector model assumptions alongside timing distributions and dark-count scaling laws in machine-readable config.
- Add explicit solver-policy docs for when to use `sesolve`, `mesolve`, and trajectory methods for the same scenario class.

## 04 Network kernel and protocol compiler: protocol-grounded additions
Protocol set is correct but should cite canonical references and modern network-layer practice:
- entanglement swapping and purification (BBPSSW/DEJMPS lineage)
- teleportation control flow
- MDI-QKD as a practical security-focused protocol family

Validation should include two external anchors:
- architectural consistency with RFC 9340 principles
- rate/distance sanity against repeaterless limits (PLOB bound) and repeater literature

## 05 Calibration and uncertainty: metrology baseline
Uncertainty reporting should align with JCGM GUM guidance and GUM Supplement Monte Carlo propagation principles. The existing Bayesian approach should add hard diagnostics gates:
- rank-normalized split R-hat threshold policy
- minimum effective sample size policy
- posterior predictive checks before publishing calibration bundles

This turns calibration from "fit + intervals" into auditable statistical evidence.

## 06 Optimization and decisions: objective hardening
Optimization outputs should be benchmarked against known physical/economic limits, not only internal baselines. Recommended updates:
- Use repeaterless bounds as no-repeater baseline checks.
- Add protocol search mode using Bayesian optimization for large combinatorial protocol spaces.
- Publish objective tradeoffs as Pareto fronts with uncertainty-aware dominance flags.

Decision artifact policy:
- every recommendation must include confidence and top sensitivity contributors
- every recommendation must include "what would change this decision" triggers

## 07 Reliability Card standard: documentation maturity
The Reliability Card concept should borrow proven reporting patterns:
- Model Cards (model behavior/context reporting)
- Datasheets for Datasets (data provenance/use constraints)
- FAIR principles (findable, accessible, interoperable, reusable metadata)
- ACM artifact badging logic (artifact availability and result validation levels)

Practical extension fields for v1.1:
- evidence_quality_tier
- benchmark_coverage
- calibration_diagnostics (R-hat/ESS/PPC status)
- reproducibility_artifact_uri (immutable archive pointer)
- software_supply_chain_attestation (signature/provenance status)

## 08 Benchmarks and datasets: governance and drift control
Benchmark suite should include governance mechanics, not only scenarios.

Recommended controls:
- scenario versioning with immutable IDs
- baseline lock windows per release
- drift alarms when summary metrics move beyond tolerance without code/schema change justification
- metadata minimums aligned to FAIR and software metadata standards (for build/run reproducibility)

Add "reference result classes":
- physics-faithful reference
- toy/fast approximation reference
- stress/failure-case reference

## 09 Product and UX: current platform signals
Streamlit has materially expanded capabilities in 2025-2026 (including rapid UI feature growth and ongoing release cadence). Keep Streamlit, but design for a thin UI layer with a strict engine boundary so UI churn does not leak into scientific core logic.

Product flow upgrades:
- run cards should expose reliability label plus evidence depth
- every chart should have a direct "open provenance" action
- export bundle should include machine-readable card JSON plus human-readable PDF/HTML

## 10 Roadmap and milestones: externalized gates
Roadmap phases should include externally anchored gates rather than only internal completion:
- standards alignment gate (RFC 9340 / QKD standards mapping complete)
- calibration quality gate (diagnostics thresholds met across flagship scenarios)
- benchmark governance gate (drift and versioning process operational)
- release integrity gate (signed artifacts and provenance checks)

This de-risks the program for external adoption and review.

## 11 Risks, quality, and governance: expanded risk controls
Cyber and software integrity controls should be explicitly tied to established frameworks:
- NIST CSF 2.0 for governance and operational risk lifecycle
- NIST SSDF guidance trajectory for secure development practice baselines
- SLSA provenance maturity targets for build integrity
- Sigstore/cosign verification paths for release artifacts

Quantum-security context should acknowledge operational coexistence with PQC migration planning (NIST FIPS 203/204/205 and SP 800-227 context), especially for organizations deciding between or combining QKD and PQC approaches.

## 12 Business expansion: photonic chip verification wedge
The most credible near-term business wedge is photonic design verification with
decision-grade reporting, not raw simulation as a standalone deliverable.

Signals supporting this:
- AIM Photonics explicitly frames a workflow that includes PDK, MPW, packaging,
  and test services.
- OIF shows active implementation-agreement output for co-packaged optics in
  2024-2025, reinforcing near-term interoperability and validation pressure.
- EDA ecosystem activity indicates integrated PIC workflows (layout, compact
  models, and verification connectivity), but there is still room for
  uncertainty-aware cross-layer decision artifacts.
- Compact Model Libraries (CML) remain a common way to integrate photonic device
  compact models into system-level simulation and EDA workflows (Ansys/Luceda),
  which suggests PhotonTrust should treat "component compact models + uncertainty"
  as a first-class interface, not an afterthought.
- Open-source PIC ecosystems (gdsfactory, SiEPIC-Tools) show that "design flows"
  are becoming programmable and composable, which aligns with PhotonTrust's
  planned drag-drop graph compilation approach.

Inference: positioning PhotonTrust as a reliability/evidence layer on top of
existing design ecosystems is lower-friction than replacing design tools.

## 13 Business expansion: satellite and space industry wedge
Satellite quantum infrastructure is transitioning from concept to programs with
explicit public mission objectives.

Evidence:
- ESA positions EAGLE-1 as Europe's first satellite-based QKD system.
- CSA QEYSSat is mission-scoped to validate satellite-ground QKD technologies.
- EU EuroQCI policy pages describe a strategic deployment path for secure
  quantum communications infrastructure.
- ITU-R publishes recommendations directly relevant to terrestrial free-space
  optical (FSO) links (P.1814/P.1817). These recommendations help anchor
  propagation assumptions and provide a standards-aligned baseline for portions
  of the free-space channel model.
- Turbulence/scintillation modeling commonly uses log-normal and Gamma-Gamma
  distributions; the Gamma-Gamma parameterization in the canonical 2001 paper by
  Al-Habash et al. is a practical reference anchor for implementing a configurable
  turbulence proxy in the engine.

Inference: a mission-rehearsal and verification surface ("OrbitVerify") is a
plausible expansion track once free-space channel models and policy metadata are
production-ready.

## 14 Physics engine implications from current codebase
Current modules provide a strong baseline but show clear scaling gaps for chip
and satellite verification:
- `emitter.py`: steady-state emphasis; needs transient pulse-mode outputs.
- `detector.py`: stochastic model present; needs gated and saturation behavior.
- `memory.py`: decay path present; needs diagnostics-first calibration policy.
- `channels/`: terrestrial-first; needs free-space/satellite channel models.

Recommended order:
1. free-space channel model + tests,
2. detector gating/saturation upgrade,
3. transient emitter extensions,
4. calibration diagnostics enforcement.

## 15 Product and UX implications: drag-drop systems engineering
Current Streamlit layer is suitable for registry/comparison workflows but not
for full graph-authoring UX at scale.

Recommended architecture:
- keep Streamlit for reviewer/internal analysis,
- add dedicated graph frontend using React Flow (`@xyflow/react`),
- compile graph JSON into existing PhotonTrust scenario contracts.

This keeps scientific logic in backend modules while unlocking interactive
workflow design.

## 16 Compliance implications for commercialization
For the satellite wedge, compliance handling must be productized rather than
ad hoc documentation:
- EAR/ITAR tagging for scenario artifacts and customer deployments.
- FCC mission-policy context fields where orbital operations are relevant.
- Qualification references for space hardware evidence packs (ECSS, NASA EEE,
  MIL-STD-883 lineages).

## Recommended next build cycle (pragmatic)
1. Add a `research_evidence/` folder with machine-readable source manifest and retrieval date.
2. Add Reliability Card v1.1 fields for diagnostics and provenance status.
3. Add calibration CI checks for R-hat/ESS/PPC thresholds.
4. Add benchmark drift checks to CI with explicit override workflow.
5. Add free-space/satellite channel module with benchmark scenarios.
6. Add drag-drop graph schema + compiler API contract.
7. Add compliance metadata fields (EAR/ITAR/FCC references) in card exports.
8. Add signed release artifact verification in CI/CD.

## Source index

### Core quantum tools and simulator ecosystem
- QuTiP releases (v5.2.3, January 26, 2026): https://qutip.org/download.html
- QuTiP documentation hub: https://qutip.org/documentation
- QuTiP benchmark pages: https://qutip.org/qutip-benchmark
- qutip-qip separation and package guidance: https://github.com/qutip/qutip-qip
- Qiskit releases (2.x line): https://github.com/Qiskit/qiskit/releases
- Qiskit release notes (2.3): https://quantum.cloud.ibm.com/docs/en/api/qiskit/release-notes/2.3
- Qiskit primitives guide: https://qiskit.org/documentation/guides/primitives.html
- Qiskit transpiler stages: https://qiskit.org/documentation/guides/transpiler-stages.html
- NetSquid paper (Communications Physics, 2021): https://www.nature.com/articles/s42005-021-00647-8
- SeQUeNCe paper: https://arxiv.org/abs/2009.12000
- SeQUeNCe project page: https://www.anl.gov/sequence-simulator-of-quantum-network-communication
- QuNetSim paper summary: https://tqe.ieee.org/2021/06/25/qunetsim-a-software-framework-for-quantum-networks/
- QuNetSim repository: https://github.com/tqsd/QuNetSim

### Architecture and interface standards
- RFC 9340 (Architectural Principles for a Quantum Internet): https://www.rfc-editor.org/info/rfc9340
- IETF draft (quantum-native architecture tenets, 2025): https://www.ietf.org/archive/id/draft-cacciapuoti-qirg-quantum-native-architecture-00.html
- OpenQASM live specification: https://openqasm.com/
- OpenQASM 3 paper: https://arxiv.org/abs/2104.14722
- QIR specification repository: https://github.com/qir-alliance/qir-spec

### Protocol, physics, and optimization references
- Teleportation (Bennett et al., 1993): https://doi.org/10.1103/PhysRevLett.70.1895
- Entanglement purification (BBPSSW, 1996): https://doi.org/10.1103/PhysRevLett.76.722
- Quantum privacy amplification / DEJMPS lineage (1996): https://doi.org/10.1103/PhysRevLett.77.2818
- Quantum repeater baseline (Briegel et al., 1998): https://doi.org/10.1103/PhysRevLett.81.5932
- MDI-QKD (Lo et al., 2012): https://doi.org/10.1103/PhysRevLett.108.130503
- PLOB repeaterless bound (2017): https://www.nature.com/articles/ncomms15043
- Integrated photonic trusted-node TF-QKD network (Nature, 2026-02-11): https://www.nature.com/articles/s41586-026-08816-0
- Twin-field QKD over 1002 km fiber (2023): https://doi.org/10.1103/PhysRevLett.130.210801
- Bayesian optimization for repeater protocols (2025 preprint): https://arxiv.org/abs/2502.02208
- Link-layer protocol for quantum networks: https://arxiv.org/abs/1903.09778

### Calibration, uncertainty, and diagnostics
- JCGM 100 GUM (measurement uncertainty): https://www.bipm.org/doi/10.59161/JCGM100-2008E
- JCGM guide family overview (incl. Monte Carlo supplement): https://www.iso.org/sites/JCGM/GUM-introduction.htm
- Improved R-hat paper: https://arxiv.org/abs/1903.08008
- ArviZ diagnostics documentation: https://python.arviz.org/en/stable/api/diagnostics.html
- Stan posterior predictive checks: https://mc-stan.org/docs/stan-users-guide/posterior-predictive-checks.html

### Reliability reporting, data governance, and reproducibility
- Model Cards: https://arxiv.org/abs/1810.03993
- Datasheets for Datasets: https://arxiv.org/abs/1803.09010
- FAIR principles: https://doi.org/10.1038/sdata.2016.18
- ACM artifact review and badging v1.1: https://www.acm.org/publications/policies/artifact-review-and-badging-current
- CodeMeta project: https://codemeta.github.io/

### Security, compliance, and deployment governance
- NIST CSF 2.0: https://doi.org/10.6028/NIST.CSWP.29
- NIST SP 800-218 Rev.1 draft (SSDF update): https://csrc.nist.gov/pubs/sp/800/218/r1/ipd
- SLSA v1.0 notes: https://slsa.dev/spec/v1.0/whats-new
- Sigstore/cosign verification docs: https://docs.sigstore.dev/cosign/verifying/verify/
- NIST PQC FIPS announcement (203/204/205): https://www.nist.gov/news-events/news/2024/08/announcing-approval-three-federal-information-processing-standards-fips
- NIST SP 800-227 (KEM recommendations, final 2025): https://www.nist.gov/publications/nist-special-publication-800-227-recommendations-key-encapsulation-mechanisms
- ITU-T Y.3800 (QKDN overview): https://www.itu.int/rec/T-REC-Y.3800/
- ETSI QKD 016 press release: https://www.etsi.org/newsroom/press-releases/2222-etsi-releases-world-first-protection-profile-for-quantum-key-distribution
- ETSI GS QKD 016 (Protection Profile): https://www.etsi.org/deliver/etsi_gs/QKD/001_099/016/01.01.01_60/gs_QKD016v010101p.pdf
- ISO/IEC 23837-1:2023 (QKD security requirements): https://www.iso.org/standard/77097.html

### Product and UX references
- Streamlit release notes (latest + archived years): https://docs.streamlit.io/develop/quick-reference/release-notes
- React Flow documentation: https://reactflow.dev/

### Photonic design and packaging ecosystem
- AIM Photonics services workflow: https://www.aimphotonics.com/services-workflow/
- Ansys photonic automation workflow article:
  https://optics.ansys.com/hc/en-us/articles/360055701453-CML-Compiler-overview
- Ansys Compact Model Library (CML) overview (CML Compiler):
  https://optics.ansys.com/hc/en-us/articles/360055701453-CML-Compiler-overview
- Luceda Photonic Compact Model Library (CML):
  https://academy.lucedaphotonics.com/docs/ipkiss/4.0/real_cml.html
- Luceda-Cadence Virtuoso integration note:
  https://www.epda.org/Articles/258048/Luceda_Photonics_Cadence_Virtuoso.aspx
- gdsfactory docs and ecosystem:
  https://gdsfactory.github.io/gdsfactory/
  https://github.com/gdsfactory/gdsfactory
- SiEPIC-Tools (KLayout-based silicon photonics design ecosystem):
  https://siepic-tools.readthedocs.io/
  https://github.com/SiEPIC/SiEPIC-Tools
- OIF technical work and implementation agreements:
  https://www.oiforum.com/technical-work/

### Free-space optical propagation and turbulence references
- ITU-R P.1814 (Terrestrial FSO attenuation): https://www.itu.int/rec/R-REC-P.1814/en
- ITU-R P.1817 (FSO availability/reliability): https://www.itu.int/rec/R-REC-P.1817/en
- Gamma-Gamma turbulence model parameterization (Al-Habash et al., 2001):
  https://stars.library.ucf.edu/facultybib2000/3934/

### Satellite programs and policy references
- ESA EAGLE-1 project page: https://connectivity.esa.int/projects/eagle-1
- CSA QEYSSat project page: https://www.asc-csa.gc.ca/eng/satellites/qeyssat/default.asp
- EU EuroQCI policy page:
  https://digital-strategy.ec.europa.eu/en/policies/european-quantum-communication-infrastructure-euroqci
- FCC 5-year deorbit rule release:
  https://www.fcc.gov/document/fcc-adopts-new-5-year-rule-deorbiting-satellites-0
- EAR Part 774 eCFR page:
  https://www.ecfr.gov/current/title-15/subtitle-B/chapter-VII/subchapter-C/part-774
- ITAR/USML reference text:
  https://www.ecfr.io/Title-22/Section-121.1
- ECSS standards framework:
  https://ecss.nl/home/ecss-a-single-set-of-european-cooperation-for-space-standardization-standards/
- NASA EEE-INST-002 addendum metadata/PDF:
  https://nepp.nasa.gov/DocUploads/07B18CD6-83A8-4281-8FF7-6EA421A97954/EEE-INST-002_Add1.pdf
- MIL-STD-883 listdocs:
  https://landandmaritimeapps.dla.mil/Programs/MilSpec/listdocs.aspx?BasicDoc=MIL-STD-883
