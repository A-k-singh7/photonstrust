# PhotonTrust Web Research Update (ChipVerify + OrbitVerify) (2026-02-13)

This document extends `12_web_research_update_2026-02-12.md` with additional
web-validated anchors focused on:
- photonic integrated circuit (PIC) verification workflows (ChipVerify), and
- space/free-space optical communications standards and mission signals
  (OrbitVerify),
plus QKD network standards signals relevant to interoperability and trust.

This update is written to directly inform physics-engine priorities and the
platform's "trust artifacts" (benchmarks, provenance, reproducibility packs).

## Scope and method
- Timestamp: 2026-02-13
- Sources: prioritize primary sources (standards bodies, official org pages,
  tool documentation) and widely used reference tooling documentation.
- Use: these are not copied implementations; they are alignment anchors so the
  engine matches how real teams model, calibrate, and verify.

---

## 1) ChipVerify: PIC verification ecosystem (what real flows look like)

### 1.1 Compact models and calibration are core, not optional
Ansys/Lumerical positions Compact Model Libraries (CML) as a workflow for PIC
design/simulation, including calibration against measurement data and model
packaging for reuse. This reinforces that PhotonTrust's differentiator should
be "compact models with explicit uncertainty + evidence + provenance", not
geometry-level EM simulation.

Primary anchor:
- Ansys Lumerical: CML Compiler overview:
  https://optics.ansys.com/hc/en-us/articles/360055701453-CML-Compiler-overview

Implication for PhotonTrust:
- treat "calibration + testbenches + statistical variation" as a first-class
  product surface, not a future add-on.

### 1.2 S-matrix / S-parameter style circuit simulation is a natural interface
Open tooling increasingly represents PIC circuit blocks as S-matrices and
composes them across a circuit graph.

Primary anchors:
- SAX: S-matrix based photonic circuit simulator (JAX/autograd oriented):
  https://flaport.github.io/sax/
- scikit-rf (Touchstone + network composition utilities; widely used in RF):
  https://scikit-rf.readthedocs.io/

Implication for PhotonTrust:
- add a stable "S-parameter import + composition" contract for ChipVerify
  so foundry/EDA models can be wrapped as black boxes with declared validity
  ranges and uncertainty tags.

### 1.3 Open design/verification flows are programmable and composable
gdsfactory positions itself as a programmable PIC design/verification flow and
exposes simulation interfaces (including circuit simulation integration), which
aligns with PhotonTrust's "graph compile -> engine execution" strategy.

Primary anchor:
- gdsfactory docs hub:
  https://gdsfactory.github.io/gdsfactory/

Implication for PhotonTrust:
- integrate with open PIC workflows through:
  - a netlist interchange format,
  - optional PDK-aware parameter presets,
  - a "results + reliability card" export that can be attached to PR reviews
    or design reviews.

### 1.4 Layout-aware netlists and LVS-like thinking exist in photonics tooling
SiEPIC-Tools (KLayout ecosystem) is a strong signal that photonics teams want
layout-aware netlists and verification loops (layout vs schematic expectations)
inside their day-to-day tools.

Primary anchor:
- SiEPIC-Tools documentation:
  https://siepic-tools.readthedocs.io/

Implication for PhotonTrust:
- define "evidence hooks" that can attach:
  - the source of a netlist (graph auth vs extracted from layout),
  - the extraction tool version,
  - mismatch summaries (connectivity deltas, parameter deltas),
into the provenance bundle.

---

## 2) OrbitVerify: space/free-space optical comm (standards and mission signals)

### 2.1 Free-space optical links have standards anchors for parts of the model
ITU-R publishes recommendations used to design terrestrial free-space optical
links, including propagation effects and availability framing. These documents
are directly useful to anchor baseline assumptions and to justify which
contributors are included in a model decomposition.

Primary anchors:
- ITU-R P.1814: prediction methods for attenuation for terrestrial FSO links:
  https://www.itu.int/rec/R-REC-P.1814/en
- ITU-R P.1817: prediction methods for availability of terrestrial FSO links:
  https://www.itu.int/rec/R-REC-P.1817/en

Implication for PhotonTrust:
- OrbitVerify should export decomposed loss terms with a direct mapping to
  standards-anchored contributor categories where applicable.

### 2.2 Space optical comm is real and operational, with explicit constraints
NASA's LCRD materials emphasize:
- high-rate optical links (vs RF),
- operational constraints (cloud blockage),
- multiple ground station operations.

Primary anchors:
- NASA LCRD overview:
  https://www.nasa.gov/mission/laser-communications-relay-demonstration-lcrd/
- NASA "About LCRD":
  https://www.nasa.gov/mission/laser-communications-relay-demonstration-lcrd/about-lcrd/
- NASA LCRD key info (launch date and operational summary):
  https://www.nasa.gov/mission/laser-communications-relay-demonstration-lcrd/key-info/

Implication for PhotonTrust:
- OrbitVerify must not stop at a single "channel loss number".
- Availability and operational envelopes (weather/clouds, elevation, pointing)
  must be first-class scenario semantics, and surfaced in artifacts.

### 2.3 Space optical comm has formal publications for physical layer framing
CCSDS publishes optical communications specifications (including experimental
specifications) that can anchor model assumptions and interface expectations.

Primary anchor:
- CCSDS 141.11-O-1 (Optical High Data Rate Communication - 1064 nm),
  PDF publication:
  https://public.ccsds.org/Pubs/141x11o1.pdf

Implication for PhotonTrust:
- where OrbitVerify targets optical comm mission rehearsal, keep a pathway to
  align assumptions and metadata with CCSDS concepts (physical layer/coding
  framing, parameter tables, and reproducibility).

---

## 3) QKD interoperability and standards signals (trust + integration)

### 3.1 Network-level QKD framing exists in ITU-T
ITU-T has published recommendation(s) on networks supporting QKD.

Primary anchor:
- ITU-T Y.3800 (Overview on networks supporting quantum key distribution):
  https://www.itu.int/rec/T-REC-Y.3800/en

Implication for PhotonTrust:
- reliability cards and artifacts should be able to state:
  - what network assumptions are being made (trusted nodes, key management),
  - what interface semantics are assumed for integration.

### 3.2 ETSI provides QKD interface deliverables
ETSI ISG QKD publishes QKD interface deliverables; GS QKD 004 is a common anchor
for interface framing.

Primary anchors:
- ETSI ISG QKD landing page:
  https://www.etsi.org/committee/qkd
- ETSI GS QKD 004 deliverable PDF (Interface specification):
  https://www.etsi.org/deliver/etsi_gs/QKD/001_099/004/02.01.01_60/gs_qkd004v020101p.pdf

Implication for PhotonTrust:
- add a "standards mapping" metadata block in artifacts so customers and
  academics can reason about integration alignment explicitly (even if PhotonTrust
  is not a standards implementation).

---

## 4) Build implications for PhotonTrust (actionable physics-core roadmap)

PhotonTrust now has PIC v0.1 execution (Phase 09). The next major credibility
step for ChipVerify is to adopt a first-class S-parameter/Touchstone import
surface and wavelength sweep semantics, then expand ring/resonator physics with
feedback-aware solvers.

Recommended ChipVerify physics-engine extensions (ordered):
1. Touchstone ingestion (S-parameter import with provenance + validity ranges).
2. Frequency/wavelength sweeps (vectorized evaluation with caching).
3. Ring resonator transfer functions (all-pass/add-drop; parameterized by
   coupling/Q/FSR; validated against reference curves).
4. Statistical yield and sensitivity analysis (Monte Carlo + error budget
   decomposition), modeled after compact-model ecosystem expectations.

Recommended OrbitVerify physics-engine extensions (ordered):
1. Mission envelope schema (pass templates with time segmentation).
2. Availability envelope modeling (cloud/weather and day/night background).
3. Standards-anchored contributor decomposition (ITU-R categories where
   applicable; CCSDS metadata hooks for space optical framing).

Platform-level trust moats (cross-domain):
1. Reproducibility packs for all public benchmark bundles.
2. Benchmark drift governance for both ChipVerify and OrbitVerify scenario sets.
3. Evidence tiers enforced in reliability cards (preview vs certification).

---

## 5) Related implementation status (as of 2026-02-13)
- Phase 09 implemented PIC v0.1:
  - `docs/operations/phased_rollout/phase_09_pic_component_library/`
- Phase 10 implemented Touchstone import + wavelength sweeps (PIC v0.1 extension):
  - `docs/operations/phased_rollout/phase_10_pic_compact_model_import/`
- Phase 11 implemented OrbitVerify mission templates (pass envelopes + metadata):
  - `docs/operations/phased_rollout/phase_11_orbit_mission_templates/`
- Phase 12 implemented measurement bundle ingestion + artifact pack publishing:
  - `docs/operations/phased_rollout/phase_12_data_contribution_workflow/`
- Phase 13 implemented web drag-drop MVP (React Flow editor + local API):
  - `docs/operations/phased_rollout/phase_13_web_drag_drop_mvp/`
- Phase 14 implemented trust panel v0.2 (parameter registry + units/ranges):
  - `docs/operations/phased_rollout/phase_14_trust_panel_param_registry/`
- Phase 15 implemented graph validation + structured diagnostics (params, ports):
  - `docs/operations/phased_rollout/phase_15_graph_validation_diagnostics/`
- Phase 16 implemented OrbitVerify web runner v0.1 (config-first pass envelopes):
  - `docs/operations/phased_rollout/phase_16_orbit_web_runner/`
- Phase 17 implemented OrbitVerify validation + diagnostics v0.1 (schema + validate endpoint):
  - `docs/operations/phased_rollout/phase_17_orbit_validation_diagnostics/`
- Phase 18 implemented OrbitVerify evidence hardening v0.2 (availability envelope + standards anchors):
  - `docs/operations/phased_rollout/phase_18_orbit_availability_standards/`
- Phase 19 implemented run registry + artifact serving v0.1 (managed-service hardening, local dev):
  - `docs/operations/phased_rollout/phase_19_run_registry_artifact_serving/`
- Phase 20 implemented run browser + run diff v0.1 (managed-service hardening, local dev):
  - `docs/operations/phased_rollout/phase_20_run_browser_diff/`
- Phase 21 implemented run output summaries + output diff scope v0.1 (managed-service hardening, local dev):
  - `docs/operations/phased_rollout/phase_21_run_output_summary_diff/`
- Phase 22 implemented project registry + approvals v0.1 (managed-service governance, local dev):
  - `docs/operations/phased_rollout/phase_22_project_registry_approvals/`
- Platform build plan:
  - `15_platform_rollout_plan_2026-02-13.md`
