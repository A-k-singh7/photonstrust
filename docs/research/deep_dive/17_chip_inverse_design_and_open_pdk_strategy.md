# Chip Inverse Design + Open PDK Strategy (Discussion Doc)

Date: 2026-02-13

This document integrates the current PhotonTrust plan (ChipVerify + OrbitVerify)
with a realistic path to "inverse-design optimized chips" using open-source
tooling and publicly available PDKs, while keeping the end-state compatible
with real foundry PDKs under NDA.

The intent is to answer the core question from this thread:
"What if we make the whole chip inverse-design optimized?" and turn it into a
buildable, denial-resistant product plan.

---

## 0) Bottom Line (Critical View)

"Optimize the whole chip" with topology optimization is not the right first
product target.

The practical, startup-viable target is:
- inverse design for a curated library of high-leverage components
  (couplers, splitters, wavelength mux/demux, mode converters, grating couplers),
- circuit/chip assembly using a PDK-aware layout framework,
- verification and evidence artifacts (reliability cards + provenance) that make
  performance claims hard to dismiss.

This approach gives you:
- real differentiation (device quality + evidence),
- manageable compute cost,
- compatibility with foundry design rules,
- a path to manufacturing (MPW) without pretending you can "copy a foundry".

---

## 1) What "Open-Source Foundries I Can Copy" Actually Means

You cannot ethically or legally "copy a foundry process".

What you can do is:
- use publicly available PDKs (or "public PDKs") as your development target,
- learn the structure of manufacturable design rules, layers, and validation,
- build a toolchain that can swap in a foundry PDK later (often under NDA).

Public/no-NDA PDKs that are relevant for a photonics startup include:
- CORNERSTONE Photonics PDK via `cspdk` (gdsfactory integration).
  - https://github.com/gdsfactory/cspdk
  - https://pypi.org/project/cspdk/
- VTT photonics PDK (open-source gdsfactory PDK for VTT 3 um SOI).
  - https://github.com/gdsfactory/vtt
  - https://gdsfactory.github.io/vtt/
- Luxtelligence GlobalFoundries photonics PDK (open-source gdsfactory PDK).
  - https://github.com/gdsfactory/luxtelligence
- SiEPIC EBeam PDK (KLayout-based PDK used in the SiEPIC ecosystem).
  - https://siepic.ubc.ca/ebeam-pdk/

GDSFactory also maintains an explicit list of "Open-Source PDKs (No NDA
Required)" including the photonics PDKs above (and several non-photonic ones).
- https://github.com/gdsfactory/gdsfactory

For "open foundry" style *electronics* processes, there are fully open PDKs
that can be used to study the workflow mechanics (not photonics), for example:
- SkyWater SKY130 open PDK and its KLayout integration.
  - https://github.com/efabless/sky130_klayout_pdk
- IHP Open PDK (130nm BiCMOS, Apache 2.0).
  - https://github.com/IHP-GmbH/IHP-Open-PDK

These are useful as references for:
- PDK packaging,
- DRC/LVS deck structure,
- reproducible install flows.

---

## 2) Inverse Design: SPINS-B and Alternatives

### 2.1 SPINS-B (Stanford NQP Lab)

SPINS-B is the open-source version of the SPINS framework for gradient-based
(adjoint) photonic optimization developed in the Vuckovic group.
- https://github.com/stanfordnqp/spins-b
- https://spins-b.readthedocs.io/en/latest/introduction.html

Key practical implications:
- SPINS-B is GPL-3.0. If you ship a product that is a derivative work of SPINS-B,
  you will likely be forced into a copyleft distribution posture. Treat this as
  a product-architecture constraint, not a footnote. (Not legal advice.)
- The architecture is documented in the SPINS paper:
  "Nanophotonic Inverse Design with SPINS: Software Architecture and Practical
  Considerations."
  - https://arxiv.org/abs/1910.04829

SPINS-B is already the "startup story" case study:
the creators launched SPINS Photonics Inc for commercialization.
- https://spinsphotonics.com/

SPINS also has a related multi-GPU FDFD solver server (`maxwell-b`) intended to
run alongside SPINS-B for larger problems.
- https://github.com/stanfordnqp/maxwell-b

### 2.2 Meep adjoint (FDTD)

Meep includes an adjoint solver module for gradient computation with respect to
permittivity grids and can be used for topology optimization/inverse design.
- https://meep.readthedocs.io/en/latest/Python_Tutorials/Adjoint_Solver/

Meep is GPL v2 or later, and its docs clarify how the GPL applies to user-written
Python/Scheme control files vs linked binaries.
- https://meep.readthedocs.io/en/latest/License_and_Copyright/

### 2.3 Ceviche (autograd-friendly FDFD/FDTD)

Ceviche provides differentiable EM solvers in numpy/scipy compatible with autograd
and is MIT licensed.
- https://github.com/fancompute/ceviche

This is attractive for a startup because:
- permissive license,
- easy integration with Python optimization libraries,
- straightforward to prototype and publish reproducible notebooks.

Tradeoff:
- performance limits on large 3D problems relative to specialized GPU solvers.

---

## 3) Reality Check: Why "Whole Chip Topology Optimization" Is a Trap

The full-chip inverse-design dream fails fast on:
- problem size (3D EM over full die is not tractable for interactive design),
- manufacturing constraints (min feature, density, etch rules, stitching),
- system constraints (electrical routing, thermal tuning, packaging),
- verification burden (DRC/LVS/schematic consistency across a giant freeform
  geometry),
- local minima and brittleness (optimization produces designs that are hard to
  tune and yield across process corners).

What *does* work:
- optimize individual building blocks with strong constraints and port-based
  figures of merit,
- then assemble chips using those blocks plus standard PDK routing,
- run yield/robustness optimization across process corners at the component and
  circuit level.

---

## 4) How This Fits PhotonTrust (Architecture Alignment)

PhotonTrust already has:
- a strict multi-phase rollout protocol for high-integrity physics work:
  `docs/operations/phased_rollout/README.md`
- a graph schema + compiler foundation (Phase 08) enabling UI -> engine configs:
  `docs/operations/phased_rollout/phase_08_graph_schema_compiler/`
- a platform expansion plan that explicitly targets ChipVerify and OrbitVerify:
  `docs/research/15_platform_rollout_plan_2026-02-13.md`

The missing bridge is:
turning PIC graphs into manufacturable layout + simulation + evidence.

Recommended module-level expansion (engine stays source of truth):
- `photonstrust/components/pic/`
  - deterministic component compact models and uncertainty envelopes
- `photonstrust/layout/`
  - gdsfactory-powered layout generation from compiled graph specs
- `photonstrust/invdesign/`
  - inverse design tasks (problem definitions, constraints, solvers backend)
- `photonstrust/verification/`
  - DRC/LVS invocation hooks, connectivity checks, report extraction
- `photonstrust/report/`
  - extend Reliability Cards with "device evidence packs" for PIC blocks

The core "trust moat" stays consistent:
calibration + uncertainty + diagnostics + provenance + drift governance.

---

## 5) Buildable Product: "Foundry-Ready Inverse-Designed Component Generator"

### What you ship (MVP)
- A component generator that produces:
  - GDS layout for a component family (e.g., directional coupler, grating coupler),
  - a compact model / S-parameter-like representation for circuit sims,
  - an evidence bundle: solver config, seeds, optimization hyperparameters,
    constraints, DRC status, and benchmark plots.
- A chip assembly flow that:
  - instantiates those components plus standard PDK routes,
  - produces a chip-level netlist and a "chip evidence card".

### Why this is denial-resistant
Skeptics can dismiss "pretty field plots".
They struggle to dismiss:
- DRC-clean layouts,
- reproducible optimization scripts,
- explicit constraints and yield corners,
- measured-vs-sim comparisons (once you have lab data),
- error budget and sensitivity breakdown.

---

## 6) Implementation Strategy (Streamlined Plan)

### Phase 1: Public PDK integration (no NDA)
Goal: prove that PhotonTrust can generate and validate manufacturable PIC layouts.

Deliverables:
- pick one public photonics PDK target: CORNERSTONE, VTT, or Luxtelligence
  (start with whichever has the cleanest install path for your environment).
- implement "layout export" and "connectivity/LVS-lite" checks.
- generate 5 reference components and route them into a tiny chip.

Gate:
- deterministic replay of layout generation and verification steps.

### Phase 2: Inverse design for 1-2 critical components
Goal: show adjoint optimization actually creates better-than-hand designs in your
chosen PDK constraints.

Deliverables:
- choose an EM backend:
  - fast prototype: Ceviche,
  - deeper photonics inverse design: Meep adjoint,
  - evaluate SPINS-B as research reference, but treat GPL as a strategic constraint.
- implement:
  - design region parameterization,
  - minimum feature enforcement,
  - port-based objective (S-parameters / mode overlap).

Gate:
- monotonicity sanity checks and regression baselines for the inverse-designed
  component.

### Phase 3: Robustness and yield
Goal: prevent "one-off fragile design" failure.

Deliverables:
- process corner sweep (width/etch/bias proxies),
- temperature and wavelength sweep,
- sensitivity map and worst-case performance claim.

Gate:
- "robust performance" report required for external demos.

### Phase 4: Tie back into PhotonTrust Reliability Cards
Goal: unify chip-level performance with network-level reliability decisions.

Deliverables:
- extend Reliability Cards to include:
  - component evidence tier (simulated/calibrated/measured),
  - process corner robustness metrics,
  - solver provenance and optimization hyperparameters.

---

## 7) Startup Reality: Can You Build a Startup Around This?

Yes, but not by "copying foundries".

The credible wedge is:
- deliver inverse-designed, foundry-ready component IP plus evidence packs,
- sell time-to-tapeout acceleration and fewer lab iterations,
- charge for enterprise workflows (managed runs, collaboration, audit trails),
  and for calibration against customer measurement data.

Your moat is:
- the component library plus the evidence/verification pipeline and datasets,
- not the existence of an adjoint optimizer.

Competitive reality to internalize:
- SPINS Photonics is already pursuing the "inverse design platform" lane.
  You should not compete on "we can do adjoint optimization".
  You compete on:
  - verification + trust artifacts,
  - PDK integration breadth,
  - reproducibility and yield robustness,
  - integration with system/network-level decisions (PhotonTrust's unique angle).

---

## 8) Required Next Documents (This Thread's Deliverables)

This discussion doc is not enough to build. It needs two companion documents:
- Playbook: Open PDK + KLayout + gdsfactory integration and validation steps.
- Technical spec: Inverse design engine architecture (parameterization,
  constraints, solver abstraction, reproducibility).

See:
- `18_open_pdk_klayout_gdsfactory_playbook.md`
- `19_inverse_design_engine_architecture.md`
- `16_qkd_deployment_realism_pack.md` (fiber QKD realism additions)

