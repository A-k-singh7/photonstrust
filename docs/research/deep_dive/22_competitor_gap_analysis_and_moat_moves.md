# Competitor Gap Analysis + "Moat Moves" (Non-Copying Plan)

Date: 2026-02-14

This document is a blunt competitive teardown with actionable, non-copying moves
for PhotonTrust. It covers:

- QKD / quantum network simulation competitors (NetSquid, SeQUeNCe, QuNetSim, SimulaQron, etc.)
- PIC design + verification tooling (gdsfactory, Nazca, SiEPIC Tools, KLayout, commercial EDA)
- What they do better
- What PhotonTrust should implement to beat them on trust, workflow integration, and adoption

The goal is not "copy features". The goal is to build a platform that is:

- denial-resistant in technical scrutiny (evidence packs + reproducibility)
- useful inside real engineering workflows (layout, DRC/LVS, compact models)
- scientifically defensible (bounded applicability + calibration + uncertainty)

---

## 0) Operating Principle: Non-Copying Competitive Learning

Allowed (good):
- learn generic workflow patterns (PCells, rule decks, netlists, evidence, CI gates)
- implement public physics models from papers/standards
- implement interoperable file formats and adapters (GDS, Touchstone, SPICE-like netlists)

Not allowed:
- copying code, UI assets, or proprietary rule decks
- using NDA PDK content in open-core

PhotonTrust advantage if executed well:
- competitors optimize for simulation/design power
- PhotonTrust optimizes for "trust closure" + "verification artifacts" that survive review

---

## 1) Competitor Map (What Space You Are Actually In)

PhotonTrust sits at the intersection of:

1) QKD link modeling and quantum-network simulation
2) PIC design tooling (layout generation, PDKs, compact models)
3) Verification tooling (DRC, LVS, performance checks, provenance/audit)
4) Managed workflow surface (author -> run -> diff -> approve -> replay)

That combination is uncommon. Most competitors sit in only one axis.

---

## 2) QKD / Quantum Network Simulation: What They Do Better

### 2.1 NetSquid (proprietary)

What they do better:
- mature discrete-event simulation kernel and scheduling
- established protocol examples and research community usage
- credible "network scale" story (many nodes, many events)

Where they are weak (for your wedge):
- they do not position around standardized evidence artifacts
- they do not integrate into PIC layout/PDK flows

PhotonTrust non-copying moat move:
- do not rebuild a NetSquid clone
- instead, define an "import trace -> reliability card" adapter surface:
  - ingest event traces or summary metrics
  - produce PhotonTrust reliability cards + evidence bundles
- position PhotonTrust as verification layer + governance layer for multi-fidelity backends

Source:
- NetSquid product site: https://netsquid.org/

### 2.2 SeQUeNCe (open source)

What they do better:
- open-source discrete-event quantum network simulation focus
- a research paper describing architecture and motivation

Where they are weak:
- no evidence pack standard
- no managed run registry/diff/approval workflow
- no PIC layout integration

PhotonTrust non-copying moat move:
- treat SeQUeNCe as a compatibility target:
  - add "SeQUeNCe result ingestion" contract
  - generate reliability card + provenance bundle
- offer "trust closure" as value:
  - deterministic replay, schema validation, release gates, signed evidence (Phase 40+)

Sources:
- SeQUeNCe paper (arXiv): https://arxiv.org/abs/2008.05119
- SeQUeNCe repo: https://github.com/sequence-toolbox/SeQUeNCe

### 2.3 QuNetSim / SimulaQron (open source, protocol-level emphasis)

What they do better:
- easy-to-read protocol examples and educational adoption
- lower barrier to entry for teaching and prototyping

Where they are weak:
- "physics realism" depth is typically shallower than discrete-event + hardware-calibrated models
- no systematic evidence artifacts + standards alignment

PhotonTrust non-copying moat move:
- explicitly support "education mode" and "certification mode" as separate profiles:
  - education mode: easy, explainable, quick plots
  - certification mode: strict assumptions table, applicability checks, reproducibility bundle, bounded uncertainty
- provide reference notebooks that reproduce known results with citations

Sources:
- QuNetSim paper (arXiv): https://arxiv.org/abs/1909.00124
- SimulaQron paper (arXiv): https://arxiv.org/abs/1605.04251
- Comparative / cross-validation survey (arXiv): https://arxiv.org/abs/2304.04844

---

## 3) PIC CAD + Verification Ecosystem: What They Do Better

### 3.1 Commercial PIC platforms (Ansys Lumerical, Synopsys/Keysight OSG, Luceda IPKISS)

What they do better:
- deep EM solvers and production-grade compact model flows
- statistical compact model workflows (CML) and system-level simulation surfaces
- strong foundry integration (real PDKs, real decks, real sign-off expectations)

Where they are weak (opportunity):
- closed ecosystems and expensive tooling
- limited openness for academic reproducibility and community benchmarking
- do not natively produce open, machine-verifiable evidence bundles suitable for audit + CI

PhotonTrust non-copying moat move:
- do NOT claim you replace these tools
- claim you sit adjacent as a verification/evidence layer:
  - import compact models / S-parameters
  - run performance DRC gates
  - export an evidence bundle that can be attached to design reviews / tapeout packages
- provide a "tool-agnostic evidence pack" that works with:
  - KLayout for open flows
  - vendor solvers for certification mode (via optional runners / adapters)

Sources:
- Ansys Lumerical page (INTERCONNECT + CML compiler mentioned): https://www.ansys.com/products/optics/ansys-lumerical
- Luceda IPKISS: https://www.lucedaphotonics.com/ipkiss
- Synopsys Optical Solutions page (OptoCompiler/OptSim and Keysight acquisition note): https://www.synopsys.com/photonic-solutions.html

### 3.2 gdsfactory (open source)

What they do better:
- strong open-source community momentum in PIC layout automation
- clean python-first composability (PCells, routing, packaging)
- explicit interoperability story with KLayout and multiple open PDKs
- they highlight a YAML-based design flow for declarative design composition

Where they are weak (your wedge):
- not oriented around "trust artifacts" (evidence tiers, calibration governance, signed bundles)
- not oriented around QKD or satellite link verification

PhotonTrust non-copying moat move:
- embrace gdsfactory as a layout backend target, not a competitor
- provide:
  - stable IR + schema contracts for extracted features and performance DRC
  - evidence packs that wrap gdsfactory outputs into reviewable, replayable artifacts
  - a managed run registry/diff for layout + verification results

Source:
- gdsfactory photonics paper: https://gdsfactory.github.io/photonics_paper/

### 3.3 Nazca (open source, AGPL)

What they do better:
- established PIC PCell and routing workflow (python-based)
- user familiarity in some PIC communities

Key constraint for PhotonTrust:
- Nazca is AGPL-3.0 (copyleft), which changes product-architecture choices if you embed or derivative-link it.

PhotonTrust non-copying moat move:
- do not embed Nazca into the commercial surface
- if you want compatibility, do it as:
  - optional import/export (file-based) adapter, or
  - an external plugin runner boundary
- build PhotonTrust-native component graph / layout pipeline with:
  - permissive licensing for core (so industry adoption is not blocked)
  - explicit evidence and reproducibility baked in

Sources:
- Nazca license (AGPL-3.0): https://github.com/nickersonm/nazca-design/blob/master/LICENSE.txt
- Nazca project site: https://nazca-design.org/

### 3.4 SiEPIC Tools (KLayout plugin ecosystem)

What they do better:
- KLayout-integrated tooling aimed at a full photonics workflow
- close relationship to the SiEPIC / EBeam ecosystem and academic community

Where they are weak (your wedge):
- "trust artifact" and managed evidence pack story is not the focus
- cross-domain integration (PIC <-> QKD/satellite) is not their lane

PhotonTrust non-copying moat move:
- treat SiEPIC Tools as a compatibility and collaboration opportunity:
  - adopt shared conventions (port labels, layer conventions) where public
  - provide evidence pack wrappers around KLayout runs (already in Phases 30-32)
  - focus on performance DRC + provenance and make it easy to attach to papers and design reviews

Source:
- SiEPIC Tools repo: https://github.com/SiEPIC/SiEPIC-Tools

---

## 4) What You Must Beat Them On (If You Want "Most Trustable")

Competitors win on solver depth and legacy.
PhotonTrust must win on trust closure and workflow correctness.

You beat them by shipping these as non-negotiable:

1) Deterministic replay at scale
- stable seeds, stable ordering, stable schema versions
- evidence bundles that allow third parties to replay and verify

2) Explicit applicability bounds (no over-claiming)
- every result labeled as:
  - analytic vs calibrated vs measured
  - education vs preview vs certification mode
- warnings and hard failures when outside validated envelopes

3) Multi-fidelity cross-checks (model triangulation)
- analytic model must be cross-checked against:
  - a Monte Carlo / stochastic model
  - a higher-fidelity backend (QuTiP/Qiskit or external solver)
- enforce "triangulation tests" in CI for canonical scenarios

4) Evidence packs + signing
- artifacts: inputs, configs, environment, hashes, logs, plots, reports
- signatures and verification commands (Phase 40 target)

5) Verification in the loop (performance DRC)
- checks tied to layout features, not just netlist assumptions
- show "actionable constraints" (min gap, max parallel length, etc.)

---

## 5) Concrete "Moat Moves" (Buildable, Non-Copying)

### Moat Move A: Standardized Evidence Packs Across Domains

What this means:
- same evidence-bundle format supports:
  - QKD link verification
  - satellite pass verification
  - PIC layout and performance DRC

Why it wins:
- it becomes a "required attachment" in reviews and audits

Implementation hooks you already have:
- evidence bundle export and schemas (Phases 35-36)
- KLayout run artifact pack (Phases 30-32)
- run registry + diff + approvals (Phases 19-22)

Next incremental work:
- Phase 40 signing/publishing and verification command

### Moat Move B: Performance DRC as the Entry Wedge

This is the wedge described in `21_v1_to_v3_fast_execution_plan.md`.

Make it unbeatable by:
- shipping both:
  - fast "route-mode" checks (Phase 23 implemented)
  - GDS-based checks (Phase 24 implemented; Phase 37 PATH emission for KLayout pack)
- showing calibration loops with measurement bundles

### Moat Move C: "Graph IR" That Can Compile to Multiple Worlds

One graph IR should compile to:
- PIC simulation (S-matrix / compact model)
- PIC layout (GDS)
- KLayout verification runs (artifact pack)
- SPICE export (Phase 28)
- QKD protocol simulation (link budgets + finite-key modes)
- satellite mission scenarios (OrbitVerify)

This is how you avoid being boxed into any single competitor lane.

### Moat Move D: Data Flywheel With Safe Contribution

Offer opt-in measurement bundles that:
- are schema-validated
- can be redacted
- can be used to calibrate models

Then publish:
- curated open benchmark packs
- drift governance and versioning

This becomes "scientific credibility + moat".

---

## 6) Next Implementation Slices (Mapped to Your Existing Phases)

Already implemented (anchors):
- PIC verification chain: Phases 27-37
- performance DRC route extraction: Phase 23
- run registry + diff + approvals: Phases 19-22
- evidence bundles: Phases 35-36
- QKD trust gates: Phase 39

Next best steps to outcompete without copying:

1) Phase 40: signed evidence bundles (tamper-evident exports)
2) Phase 41: QKD deployment realism pack (fiber) and publish canonical benchmark configs
3) Phase 43: modern protocol surfaces (MDI-QKD, TF/PM-QKD) with strict applicability bounds
4) Add a non-JSON authoring layer:
   - TOML/YAML graph spec (UI still drag-drop)
   - CLI compile + format + schema validate
5) Add multi-fidelity backend surfaces:
   - QuTiP/Qiskit optional backends for cross-checks and education-grade high-fidelity runs

---

## 7) "Undeniable" Startup Funding Angle (Summary)

The defensible pitch is:

"We are the verification and evidence layer for quantum links and photonic chips.
We make performance claims audit-ready by producing replayable, signed evidence
bundles and performance DRC gates tied to layout features. We are open-core for
academia and offer a managed control plane for industry."

This is hard to copy because it is:
- a workflow + governance product
- a dataset + calibration flywheel
- and an interoperability layer across toolchains

---

## Source Index (Web-validated, 2026-02-14)

Quantum network simulation:
- NetSquid: https://netsquid.org/
- SeQUeNCe paper: https://arxiv.org/abs/2008.05119
- SeQUeNCe repo: https://github.com/sequence-toolbox/SeQUeNCe
- QuNetSim paper: https://arxiv.org/abs/1909.00124
- SimulaQron paper: https://arxiv.org/abs/1605.04251
- Cross-validation/survey: https://arxiv.org/abs/2304.04844

PIC CAD / verification:
- gdsfactory photonics paper: https://gdsfactory.github.io/photonics_paper/
- Nazca license: https://github.com/nickersonm/nazca-design/blob/master/LICENSE.txt
- Nazca site: https://nazca-design.org/
- SiEPIC Tools repo: https://github.com/SiEPIC/SiEPIC-Tools
- Luceda IPKISS: https://www.lucedaphotonics.com/ipkiss
- Ansys Lumerical: https://www.ansys.com/products/optics/ansys-lumerical
- Synopsys photonic solutions: https://www.synopsys.com/photonic-solutions.html

