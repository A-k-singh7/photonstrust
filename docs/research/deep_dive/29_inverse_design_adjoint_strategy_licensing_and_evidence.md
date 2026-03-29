# Adjoint Method vs Inverse Design vs "Optimization": What to Build (Scientist/Engineer View)

Date: 2026-02-14

This document answers your direct question:
"If adjoint method will be better or inverse design etc."

It also turns that answer into an implementation and evidence strategy that:
- does not trap PhotonTrust in compute cost and brittle designs
- does not trap the product in license incompatibilities
- produces artifacts that are credible in design reviews and funding discussions

This doc complements:
- `17_chip_inverse_design_and_open_pdk_strategy.md`
- `19_inverse_design_engine_architecture.md`

---

## 0) Bottom Line (Pragmatic)

Adjoint methods are the right engine for gradient-based photonic inverse design.

But:
- inverse design is not a product by itself
- inverse-designed devices are often brittle without constraints and robustness
- full-chip topology optimization is a trap for a startup

So the correct product scope is:
- component-level inverse design (couplers/crossings/mode converters/gratings)
- strict manufacturing constraints and robustness sweeps as gates
- evidence pack export + DRC/LVS-lite integration

---

## 1) Terminology (Stop Ambiguity)

Parameter optimization:
- optimize a low-dimensional parameter set (lengths, gaps, radii, heater powers)
- fast and often sufficient for circuits

Inverse design (topology optimization):
- optimize a high-dimensional spatial design region (epsilon grid / pixels)
- uses filters/projection and an EM solver

Adjoint method:
- a way to compute gradients efficiently for inverse design
- cost ~ 2 simulations per iteration, not proportional to parameter count

So:
- adjoint method is the method
- inverse design is the task

---

## 2) What You Should Use Where (Decision Table)

Use parameter optimization when:
- the design is already a known topology
- you are tuning rings/MZIs/couplers in a PDK library
- you want yield/corner sweeps to be cheap

Use adjoint inverse design when:
- you need a new geometry class (compact footprint, broadband, tolerant)
- performance depends on sub-wavelength structure within a constrained region
- you can afford the solver cost for a component

Do NOT use inverse design for:
- whole chips
- routing
- anything where the main risk is packaging/electrical/thermal integration

This aligns with `17_chip_inverse_design_and_open_pdk_strategy.md`.

---

## 3) The Real Success Condition: Robustness + Evidence

An inverse-designed block is useless if:
- it only works at one wavelength
- it only works at nominal fabrication
- it cannot pass DRC
- it cannot be reproduced

So the "Definition of Done" is not "objective improved".
It is:
- DRC-clean layout
- corner robustness report
- replayable optimization artifacts (config + seeds + solver settings)
- integration into circuit simulation as a compact model (or surrogate)

This is how it becomes "undeniable" to investors and design partners.

---

## 4) Manufacturing Constraints (Must Be First-Class)

Minimum required constraints:
- min feature size and min spacing enforced via filtering + projection
- port clearance constraints
- binarization schedule and convergence criteria
- layer mapping and export rules for GDS

Robustness constraints:
- multi-corner objective (expected or worst-case)
- wavelength sweep objective terms
- temperature sensitivity reporting (even if not in objective initially)

Output artifacts must include:
- all constraint settings
- convergence traces
- corner sweep results

---

## 5) Solver Backends: What to Learn From (Without Product Lock-In)

### 5.1 SPINS-B (GPL-3.0)

Value:
- mature architecture and engineering lessons

Risk:
- GPL-3.0 is a product-architecture constraint (not legal advice)
- treat as a research reference or an optional plugin runner

Sources:
- SPINS-B repo: https://github.com/stanfordnqp/spins-b
- SPINS paper (architecture): https://arxiv.org/abs/1910.04829

### 5.2 Meep adjoint (GPL v2+)

Value:
- credible FDTD adjoint solver
- community recognition

Risk:
- copyleft considerations for distribution (not legal advice)
- heavier runtime cost

Source:
- Meep adjoint tutorial: https://meep.readthedocs.io/en/latest/Python_Tutorials/Adjoint_Solver/

### 5.3 Ceviche (MIT) and Lumopt (MIT)

Value:
- permissive licenses
- good for prototype and education-grade reference implementations

Limits:
- scaling limits for large 3D designs

Sources:
- Ceviche: https://github.com/fancompute/ceviche
- Lumopt: https://github.com/chriskeraly/lumopt

### 5.4 Product posture recommendation

For PhotonTrust open-core + commercial service:
- keep core inverse design surfaces permissive and backend-agnostic
- treat GPL solvers as optional external runners
- start with a permissive backend for the product surface (proof-of-work)

---

## 6) Evidence Pack Spec for Inverse Design (Undeniable Deliverable)

Every inverse design run MUST export:

Inputs:
- design region definition
- objectives and weights
- constraints and filters
- PDK binding and layer map
- seed(s) and solver settings

Execution:
- backend identity and version
- iteration logs and convergence traces

Outputs:
- final GDS cell(s)
- extracted port definitions
- compact model or surrogate fit (with fit error metrics)
- robustness sweep results (corners, wavelength, temperature if available)
- DRC-lite pass (and optional full DRC runner seam)
- LVS-lite connectivity report (ports and nets consistent)

This maps directly into:
- evidence bundle export (Phases 35-36)
- KLayout artifact packs (Phases 30-32)
- workflow chaining (Phase 34)

---

## 7) Acceptance Criteria (Definition of Done)

Inverse design is "real" in PhotonTrust when:

1) You have at least 1 flagship block:
- e.g., a directional coupler variant or crossing
- exported as GDS with evidence

2) It is robust:
- corner sweep shows bounded degradation
- the worst-case metrics are reported, not hidden

3) It is manufacturable:
- DRC-lite passes
- a path to foundry DRC runner exists (enterprise seam)

4) It is replayable:
- a third party can re-run and reproduce the geometry and key metrics

5) It is usable in circuit flow:
- a compact model exists and can be composed in PIC simulation

---

## 8) Implementation Slice Plan (Do This in Order)

Slice A: harden the evidence + constraints surface
- enforce required fields in invdesign schema
- add deterministic "fmt" and canonicalization of invdesign configs

Slice B: pick 1 component family and ship it end-to-end
- coupler ratio / splitter family is a good first "undeniable" primitive

Slice C: add robustness as a gate
- fail certification mode if robustness sweep is missing

Slice D: add external solver runner seam (optional)
- isolates licenses and tool installs

---

## Source Index (Web-validated, 2026-02-14)

- SPINS paper: https://arxiv.org/abs/1910.04829
- SPINS-B: https://github.com/stanfordnqp/spins-b
- Meep adjoint: https://meep.readthedocs.io/en/latest/Python_Tutorials/Adjoint_Solver/
- Ceviche: https://github.com/fancompute/ceviche
- Lumopt: https://github.com/chriskeraly/lumopt
