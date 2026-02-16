# Research Brief

## Metadata
- Work item ID: PT-PHASE-09
- Title: ChipVerify PIC component library v1 + netlist execution (chain + DAG)
- Authors: PhotonTrust core team
- Date: 2026-02-13
- Related modules (planned/expected):
  - `photonstrust/components/pic/` (new)
  - `photonstrust/pic/` (new)
  - `photonstrust/graph/compiler.py` (PIC netlist compilation)
  - `schemas/photonstrust.graph.v0_1.schema.json` (edge port extensions)

## 1) Problem and motivation
PhotonTrust has a graph schema and compiler (Phase 08), but ChipVerify requires
an executable PIC "physics core" that turns compiled netlists into:
- loss budgets (fast, explainable), and
- interference-aware forward simulation (for couplers/MZIs),
with explicit assumptions and deterministic behavior.

This phase establishes a minimal, open-source PIC component model library and a
netlist simulator that is usable by:
- academic teams (transparent and reproducible), and
- product workflows (drag-drop preview that can scale to "managed runs").

## 2) Research questions
- RQ1: What minimal set of PIC primitives covers the highest-leverage early
  verification workflows (I/O coupling + waveguides + phase control +
  split/combination)?
- RQ2: What composition math should v1 use to support interference while
  remaining simple enough to audit and unit-test?
- RQ3: How do we design the interface so we can later import and compose
  foundry/EDA compact models (e.g., S-parameters/Touchstone or CML-wrapped
  models) without breaking the schema/contracts?
- RQ4: What are the non-negotiable "trust behaviors" for v1 (determinism,
  explicit assumptions, bounded outputs, regression fixtures)?

## 3) Method design (v1)

### 3.1 Component model interface (forward matrices)
Use a simple forward-only component interface:
- each component exposes declared input/output ports, and
- a forward propagation matrix `M` mapping complex input amplitudes to complex
  output amplitudes.

For 2-port elements, `M` is 1x1 (scalar complex transmission). For couplers,
`M` is 2x2.

This matches common frequency-domain circuit simulation practice and is
compatible with future S-parameter composition (planned).

### 3.2 Solver strategy: two solvers, same netlist
Provide two solvers because they serve different user needs:
- Chain solver: detect a simple 2-port chain and compute total loss in dB as a
  sum of per-component losses (fast "budget" view).
- DAG solver: a feed-forward solver that propagates complex amplitudes along a
  deterministic topological order; supports interference by allowing multiport
  mixing nodes (e.g., couplers).

The DAG solver is explicitly unidirectional in v1:
- no back-reflections,
- no cycles/feedback loops (resonator loops are rejected).

### 3.3 Port-aware edges
PIC graphs require explicit port connectivity (e.g., coupler `out1/out2`).
Therefore Phase 09 extends the graph edge schema and compiler to support
optional:
- `from_port` (default: `out`)
- `to_port` (default: `in`)

### 3.4 Trust and scope boundaries
This phase is a v1 foundation; it is not a foundry-grade simulator.
Non-negotiables:
- explicit assumptions in outputs,
- deterministic outputs for identical inputs,
- unit tests for invariants (loss accounting, interference routing),
- clear "not modeled" statements (reflections, resonator feedback, dispersion).

## 4) Primary references (ecosystem anchors)
These sources are used as "workflow reality checks" (not copied implementations):
- Ansys Lumerical CML Compiler overview (compact model libraries, calibration,
  statistical/yield style workflows): https://optics.ansys.com/hc/en-us/articles/360055701453-CML-Compiler-overview
- SAX photonic circuit simulator (S-matrix approach; differentiable/JAX-based):
  https://flaport.github.io/sax/
- gdsfactory (open PIC flow, netlists and simulation interfaces):
  https://github.com/gdsfactory/gdsfactory
- SiEPIC-Tools (KLayout-integrated photonics workflow; netlists and simulation):
  https://github.com/SiEPIC/SiEPIC-Tools
- scikit-rf (Touchstone/S-parameter manipulation in Python; future import path):
  https://scikit-rf.readthedocs.io/

## 5) Acceptance criteria
- PIC component library exists and is unit-tested:
  - waveguide, grating/edge coupler, phase shifter, coupler (2x2).
- PIC simulation module exists:
  - chain solver returns correct total loss in dB for a chain.
  - DAG solver routes power correctly in a canonical MZI test.
- Graph schema/compiler supports `from_port`/`to_port` for PIC edges.
- CLI supports PIC netlist simulation:
  - `photonstrust pic simulate <compiled_netlist.json> --output <dir>`
- Full `pytest` suite passes; release gate passes.

## 6) Decision
- Decision: Proceed.
