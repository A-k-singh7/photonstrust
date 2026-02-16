# Inverse Design Engine Architecture (Adjoint Optimization)

Date: 2026-02-13

This document specifies how to implement inverse-design optimization in a way
that is:
- reproducible,
- PDK-aware (manufacturing constraints are first-class),
- pluggable across EM backends (FDFD/FDTD),
- and compatible with PhotonTrust's evidence and release-gate discipline.

It is the technical companion to:
- `17_chip_inverse_design_and_open_pdk_strategy.md`
- `18_open_pdk_klayout_gdsfactory_playbook.md`

---

## 1) Design Goal (Product, Not Academic)

We are not trying to build a one-off inverse design demo.

We are trying to build a component generator that consistently produces:
- a layout,
- a compact model,
- and an evidence pack strong enough for design reviews and foundry discussions.

The engine must optimize *under constraints* (feature size, curvature, density),
and must export:
- "what was optimized",
- "under what assumptions",
- and "how robust is it across corners".

---

## 2) Problem Decomposition: Full Chip vs Hierarchical

Full chip topology optimization is typically intractable for a product workflow.

The correct decomposition is:
- Component inverse design:
  - optimize a small design region with defined ports and objectives.
- Circuit-level parameter optimization:
  - optimize tunable parameters of a composed circuit (ring tuning, phase
    shifter biases, heater power, etc).
- Chip-level placement and routing:
  - mostly a CAD/routing task, not EM topology optimization.

---

## 3) Core Concepts (Adjoint Method Summary)

Adjoint optimization in photonics typically takes the form:
- define objective function J(E, H, p) where p are design parameters,
- compute fields for the forward problem,
- compute fields for an adjoint problem,
- combine them to obtain gradients dJ/dp at a cost roughly comparable to two
  simulations per iteration, independent of the number of parameters p.

This is the reason adjoint methods dominate inverse design.

Reference architecture and practical considerations:
- SPINS paper:
  https://arxiv.org/abs/1910.04829

---

## 4) Backend Options and License Reality

### SPINS-B (research reference, GPL-3.0)
- https://github.com/stanfordnqp/spins-b
- https://spins-b.readthedocs.io/en/latest/introduction.html

Good for:
- understanding a mature inverse design architecture,
- comparing algorithmic choices.

Risk for product:
- GPL can constrain proprietary distribution.

### Meep adjoint (FDTD, GPL v2+)
- https://meep.readthedocs.io/en/latest/Python_Tutorials/Adjoint_Solver/
- https://meep.readthedocs.io/en/latest/License_and_Copyright/

Good for:
- physically richer 3D modeling,
- community credibility.

Risk:
- same copyleft considerations if shipping derivative works; also heavier compute.

### Ceviche (MIT, autograd-friendly)
- https://github.com/fancompute/ceviche

Good for:
- prototyping and educational pipelines,
- permissive licensing and clean Python integration.

Risk:
- scaling limitations for large 3D structures.

Decision rule:
- prototype with a permissive backend (Ceviche) to harden your product surface,
  evidence packs, and constraints.
- evaluate GPL backends as optional research plugins or internal services.
(Not legal advice.)

---

## 5) Engine Interfaces (What We Implement in PhotonTrust)

### 5.1 Data structures

`DesignRegion`:
- grid bounds (x, y, z)
- material bounds (eps_min, eps_max)
- feature constraints (min feature, min radius)
- symmetry constraints (optional)
- filters and projection policy

`Ports`:
- port definitions (position, width, mode order)
- normalization policy
- objective extraction (S-params, mode overlap, power in region)

`Objective`:
- scalar objective J
- optional multi-objective wrapper (weighted sum or Pareto exploration)

`Constraints`:
- fabrication constraints (min feature, minimum spacing)
- performance constraints (insertion loss max, crosstalk max)
- penalty functions (differentiable)

`CornerSet`:
- process corners (bias/etch/waveguide width)
- temperature corners
- wavelength sweep

`EvidencePack`:
- config hash and seed
- solver and discretization settings
- objective and constraints
- iteration trace (J(t), constraint violations)
- DRC results on final layout
- corner sweep results

### 5.2 Solver abstraction

Implement a base interface:

`solve_forward(design) -> fields, monitors`
`solve_adjoint(design, monitors) -> adjoint_fields`
`gradient(forward, adjoint) -> dJ/dp`

Backends implement these methods; PhotonTrust owns:
- reproducibility and provenance,
- constraints and filtering policy,
- evidence pack generation,
- and integration into component library.

---

## 6) Fabrication Constraints (You Must Implement Early)

Inverse design without manufacturing constraints produces junk.

Minimum constraints set (v1):
- minimum feature size via spatial filtering + projection:
  - density filter (convolution / Helmholtz filter)
  - threshold projection (tanh-like)
- enforce binarization schedule (beta continuation)
- enforce design region boundaries and port clearances

Additional constraints (v2):
- Manhattanization / angle constraints for specific processes
- minimum curvature for waveguides
- density/area constraints

Output must always include the constraint policy, not just final performance.

---

## 7) Robust Optimization and Yield

To make a design credible:
- optimize expected performance across corners, or
- optimize worst-case performance, or
- optimize nominal and report corner degradation with triggers.

Default policy:
- run corner sweep post-optimization,
- compute sensitivity ranking of parameters,
- store "robustness metrics" in evidence pack.

---

## 8) Integration into ChipVerify

### 8.1 Component library
Store final designs as:
- a component layout cell (GDS + param tags),
- a compact model (S-params, or fitted surrogate),
- and an evidence pack artifact.

### 8.2 Graph compiler
PIC graphs compile to:
- which component instances to place,
- their parameter values (including inverse-design variants),
- and routing topology.

---

## 9) Validation Gates (PhotonTrust-style)

Required invariants:
- deterministic replay for fixed seed and config hash.
- monotonic sanity:
  - tightening constraints should not improve objective magically.
- stability:
  - small discretization change should not flip "good vs bad" decision.

Benchmarking:
- at least one canonical component (e.g., 2x2 coupler) with published reference
  targets (not necessarily exact numeric match; trend match + envelope).

Release gating:
- inverse design engine changes must pass:
  - unit tests,
  - drift checks for benchmark components,
  - evidence pack schema validation.

---

## 10) Source index

- SPINS-B:
  https://github.com/stanfordnqp/spins-b
  https://spins-b.readthedocs.io/en/latest/introduction.html
- SPINS paper (architecture):
  https://arxiv.org/abs/1910.04829
- Meep adjoint solver:
  https://meep.readthedocs.io/en/latest/Python_Tutorials/Adjoint_Solver/
  https://meep.readthedocs.io/en/latest/License_and_Copyright/
- Ceviche:
  https://github.com/fancompute/ceviche

