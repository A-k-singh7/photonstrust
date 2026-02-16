# Fundable Wedge: "Denial-Resistant" Demos + Moat Story (PhotonTrust)

Date: 2026-02-14

This document is the investor-and-customer-facing execution spec:
- what to demo
- why it is hard to dismiss
- what milestones prove defensibility

It is intentionally concrete and operational.

---

## 0) The Pitch (1 Sentence)

PhotonTrust is the verification and evidence layer for quantum links and photonic
chips: we turn simulations, layouts, and measurements into replayable, signed
evidence bundles and performance DRC gates that teams can trust in reviews,
tapeouts, and certification discussions.

---

## 1) The Problem (What Teams Actually Struggle With)

Engineering reality:
- PIC and QKD decisions are dominated by risk and uncertainty
- tooling exists, but trust closure is missing:
  - assumptions are implicit
  - results are hard to reproduce across environments
  - verification artifacts are not standardized
  - calibration datasets are private and scattered

So the pain is not "lack of solvers".
The pain is:
- inability to sign off quickly and defensibly.

---

## 2) Why This Is a Wedge (Not a Science Project)

You do not need to beat commercial solvers on physics depth to win.

You win by becoming:
- the gate that every design/run must pass
- the place evidence is stored, diffed, and approved

This is workflow + governance + verification as product.

---

## 3) The Three "Denial-Resistant" Demos (Ship These First)

Each demo must:
- be runnable end-to-end on a clean machine
- export a replayable evidence bundle
- show a meaningful failure mode and its fix

### Demo 1: Performance DRC for PIC Crosstalk (Layout-Aware)

Story:
"A designer routes two waveguides too close for too long. We detect it from
routes and/or GDS, quantify worst-case crosstalk vs wavelength, and output an
actionable constraint (min gap / max parallel length)."

Why it is denial-resistant:
- outputs are actionable engineering constraints
- diffs clearly show what changed (gap/length) and why risk changed

Artifacts:
- performance DRC report JSON/HTML
- extracted parallel-run segments (route-mode or GDS-mode)
- evidence bundle export

Repo anchors:
- Phase 23 (route feature extraction)
- Phase 24 (GDS extraction)

### Demo 2: "Layout -> KLayout Pack -> LVS-lite" Evidence Chain

Story:
"Our drag-drop graph emits a layout GDS, runs KLayout DRC-lite and extraction,
then runs LVS-lite to catch a connectivity bug."

Include a scripted bug:
- label typo or endpoint not snapped to port -> LVS-lite fails
- fix the label -> LVS-lite passes

Why it is denial-resistant:
- it proves you are not just simulating; you are verifying intent vs layout
- evidence pack includes tool logs and hashes

Repo anchors:
- Phase 30-32 (KLayout artifact pack)
- Phase 34 (workflow chaining)
- Phase 37 (GDS PATH correctness)

### Demo 3: Satellite QKD Reliability Card With Applicability Bounds

Story:
"Given a LEO downlink pass, we compute link efficiency, background, and expected
key rate with uncertainty. The output is a reliability card that explicitly
labels assumptions and applicability (day/night, elevation range, turbulence
model)."

Why it is denial-resistant:
- it is honest: it declares what is assumed vs modeled vs calibrated
- it produces an operating envelope, not a single number

Repo anchors:
- orbit/free-space channel models (phases 01, 11+)
- Phase 39 trust gates (determinism + airmass sanity)
- satellite realism pack (see `32_satellite_qkd_realism_pack.md`)

---

## 4) The "Moat" (What Is Hard to Copy)

Moat is not your first model.
Moat is what accumulates as you run the workflow.

Hard-to-copy assets:

1) Evidence pipeline and schemas
- stable contracts for artifacts across tools
- replayable bundles that are review-friendly

2) Calibration datasets and drift governance
- opt-in measurement bundles
- versioned benchmark packs
- drift checks in CI

3) Workflow adoption surface
- run registry + diffs + approvals
- append-only review history

4) Multi-fidelity trust gates
- analytic vs stochastic vs QuTiP/Qiskit cross-checks
- certification mode requires triangulation

This becomes a defensible platform over time.

---

## 5) Open-Core + Commercial Split (What to Open Source)

Open source (academia-friendly):
- physics core models (analytic + stochastic)
- schemas and evidence bundle tooling
- canonical benchmark packs (where licensing allows)
- non-NDA PDK adapters and open PDK demos

Commercial (what customers pay for):
- managed run registry at scale
- approvals, permissions, audit trails
- private PDK adapters (customer-installed)
- sealed runner infrastructure for external tools (foundry decks, vendor solvers)
- measurement ingestion + calibration services

This split avoids license traps while maximizing adoption.

---

## 6) Milestones That Make Funding Easy (Concrete)

Milestone A (4-6 weeks):
- Demo 1 + Demo 2 working end-to-end with evidence bundles
- At least one public PDK path used in the demo workflow
- A "replay bundle" exported and replayed on a second machine

Milestone B (8-12 weeks):
- One measurement bundle ingestion and calibration loop for a PIC metric
  (crosstalk or insertion loss surrogate)
- Drift governance and regression gates in CI

Milestone C (3-6 months):
- MDI-QKD and TF/PM-QKD preview surfaces shipped with strict applicability labels
- Satellite realism pack upgraded and benchmarked against at least one published regime
- Multi-fidelity triangulation tests in CI for canonical scenarios

Milestone D (6-12 months):
- 2-3 paying pilots (verification engagements or component generator engagements)
- at least one private PDK adapter deployment (on-prem or isolated)

---

## 7) What Not to Do (Common Startup Failure Modes)

Do not:
- claim "we simulate everything" (it is not credible and not necessary)
- start with full-chip inverse design
- hide applicability bounds (this will kill trust)
- build features that cannot export evidence packs

---

## 8) Supporting Sources (Landscape Anchors)

PIC tooling ecosystem:
- gdsfactory photonics paper: https://gdsfactory.github.io/photonics_paper/
- Ansys Lumerical: https://www.ansys.com/products/optics/ansys-lumerical
- Luceda IPKISS: https://www.lucedaphotonics.com/ipkiss

QKD satellite anchor example:
- 2025 microsatellite real-time QKD (Nature): DOI: 10.1038/s41586-025-08739-z
