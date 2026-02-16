# Phase 33 - Inverse Design Robustness + Evidence Pack - Research Brief

## Metadata
- Work item ID: PT-PHASE-33
- Date: 2026-02-14
- Scope: Extend PhotonTrust inverse-design from a single v0 "phase tuning" primitive to a small family of deterministic synthesis primitives with (1) explicit robustness/corner evaluation and (2) a schema-validated evidence pack contract.

## Problem Statement
PhotonTrust already exposes inverse design as a managed-service action (`/v0/pic/invdesign/mzi_phase`) and stores the outputs as a run with served artifacts. However, the current inverse-design surface is not yet "decision-grade" because:
- the report payload is not schema-validated (contract drift risk),
- robustness is not first-class (no explicit corners / wavelength worst-case objective),
- the report does not standardize what constitutes an "evidence pack" across inverse-design kinds.

This blocks trustworthy scaling because reviewers cannot reliably compare:
- objective definition (mean vs worst-case),
- corner set and applicability bounds,
- which parameters were optimized vs held fixed,
- or whether "robustness" was actually evaluated.

## Research Findings (What "Real" PIC Inverse Design Needs)
Inverse design in photonics is commonly framed as an optimization problem where:
- objectives span multiple wavelengths and often multiple operating/corner cases, and
- gradients are obtained efficiently via adjoint methods (for EM solvers).

Key practical requirements that show up repeatedly in successful PIC inverse-design workflows:
- Multi-objective / multi-wavelength formulations (e.g., "minimax" or worst-case across a wavelength set).
  - Meep's adjoint solver documentation explicitly discusses minimax formulations for multi-frequency design. (https://meep.readthedocs.io/en/latest/Python_Tutorials/Adjoint_Solver/)
- Fabrication robustness: treat etch/width/temperature variations as explicit "cases" and optimize for mean or worst-case across cases.
- Manufacturability constraints for shape/topology optimization (minimum feature size, smoothing/filtering, and binarization/projection schedules).
- Clear solver provenance and determinism posture (seed control, bounded steps, explicit tolerances).

Open and widely used research-grade toolchains that inform a plugin strategy:
- Meep adjoint solver (adjoint-based EM optimization): https://meep.readthedocs.io/en/latest/Python_Tutorials/Adjoint_Solver/
- Ceviche (MIT license; FDFD + adjoint): https://github.com/fancompute/ceviche
- Lumopt (MIT license; gradient-based photonic inverse design): https://github.com/chriskeraly/lumopt
- SPINS-B (GPL license; powerful but license-sensitive for commercial bundling): https://github.com/stanfordnqp/spins-b
  - License: https://github.com/stanfordnqp/spins-b/blob/master/LICENSE

Emerging research direction:
- Generative/diffusion approaches can reduce search time by combining learned priors with gradient guidance.
  - Example: "AdjointDiffusion" (published 2026): https://pubs.acs.org/doi/10.1021/acsphotonics.5c00993

## Implications For PhotonTrust Architecture
PhotonTrust should treat inverse design as a "trusted contract surface", not a single algorithm.

Concrete implication:
- Define a schema-validated inverse-design report contract that can be produced by:
  - deterministic "compact-model inversion" (fast, always available, interactive),
  - optional EM backends (adjoint solvers) as plugins (future phases),
  - and hybrid approaches (e.g., learned priors + robust evaluation).

Crucially, robustness must be part of the contract:
- an inverse-design run should carry the exact case set and aggregation rules used for the objective,
- and should export a small per-case evaluation table (so reviewers can see worst-case behavior).

## Trust + Safety Constraints
- Inverse-design artifacts must be auditable and diffable:
  - objective definition and aggregators must be stored in the report (not implicit in code).
- Avoid license traps:
  - GPL solvers can be supported as optional plugins, but the open-core and managed-service defaults must remain permissive and tool-independent.
- Keep "preview vs certification" semantics honest:
  - v0/v1 primitives based on compact models are not EM signoff; they must be labeled as synthesis aids with explicit applicability bounds.

## Outcome (Phase 33)
PhotonTrust inverse design becomes a stable, extensible subsystem:
- multiple synthesis primitives share a common evidence pack schema,
- every run can include optional robustness/corner evaluation with explicit aggregation rules,
- and future EM/adjoint plugins can be added without breaking the managed-service contract.

