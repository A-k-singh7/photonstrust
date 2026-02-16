# Research Brief

## Metadata
- Work item ID: PT-PHASE-10
- Title: ChipVerify compact model import (Touchstone/S-parameters) + wavelength sweeps
- Authors: PhotonTrust core team
- Date: 2026-02-13
- Related modules (planned/expected):
  - `photonstrust/components/pic/touchstone.py` (new)
  - `photonstrust/components/pic/library.py` (new component kind)
  - `photonstrust/pic/simulate.py` (sweep execution)
  - `photonstrust/cli.py` (CLI flags)

## 1) Problem and motivation
ChipVerify cannot be "most applicable" without supporting the reality that many
teams already have validated compact models represented as S-parameters (often
in Touchstone format). To integrate with foundry/EDA/measurement flows, the
engine needs:
- a stable way to import 2-port compact models,
- deterministic evaluation at a chosen wavelength/frequency, and
- sweep execution to inspect response curves and to validate models.

This phase adds a conservative, unit-tested Touchstone (S2P) ingestion path for
2-port models and a wavelength sweep runner built on the existing PIC netlist
simulation.

## 2) Research questions
- RQ1: What minimal subset of Touchstone should be supported in v1 so the engine
  remains deterministic and auditable?
- RQ2: How should an imported S-parameter model map into PhotonTrust's v1
  forward-only PIC solver (which does not model reflections)?
- RQ3: What provenance and validation behavior is required so imported models
  are "trustable" (range checks, deterministic interpolation, explicit errors)?
- RQ4: What sweep output structure is useful for both academic inspection and
  product workflows (drag-drop preview and report exports)?

## 3) Method design (v1)

### 3.1 Minimal Touchstone support policy
Support a conservative subset:
- 2-port networks only (S2P)
- parameter type: S
- data formats: RI, MA, DB
- frequency units: HZ, KHZ, MHZ, GHZ

Everything else is rejected with explicit errors (no silent best-effort parsing).

### 3.2 Mapping S-parameters into the forward solver
PhotonTrust PIC v1 is unidirectional. Therefore:
- imported models are mapped to a scalar forward transmission `t` (complex),
- default mapping uses S21 (port 1 -> port 2),
- reverse or reflective behavior is not used in v1 (tracked limitation).

### 3.3 Deterministic interpolation
Evaluate imported S-parameters at a target wavelength by:
- converting wavelength to frequency, and
- deterministic linear interpolation in the complex plane within the Touchstone
  frequency grid.

Out-of-range evaluation fails unless explicitly enabled via an
`allow_extrapolation` flag.

### 3.4 Sweep execution
Add a "sweep runner" that runs the existing PIC netlist simulator across a list
of wavelengths and returns:
- per-wavelength chain solver output (if applicable),
- per-wavelength DAG solver outputs.

## 4) Primary references (ecosystem anchors)
- scikit-rf documentation (Touchstone and network composition reference tooling):
  https://scikit-rf.readthedocs.io/
- SAX (S-matrix based photonic circuit simulation signal):
  https://flaport.github.io/sax/
- Ansys CML Compiler overview (compact model workflow anchor):
  https://optics.ansys.com/hc/en-us/articles/360055701453-CML-Compiler-overview

## 5) Acceptance criteria
- New component kind exists:
  - `pic.touchstone_2port` with `touchstone_path` parameter
- Touchstone parser is unit-tested with fixtures.
- Sweep runner exists:
  - `simulate_pic_netlist_sweep(...)`
- CLI supports sweep mode:
  - `photonstrust pic simulate ... --wavelength-sweep-nm <nm1> <nm2> ...`
- Full `pytest` suite passes and release gate passes.

## 6) Decision
- Decision: Proceed.

