# Implementation Plan

## Metadata
- Work item ID: PT-PHASE-09
- Title: ChipVerify PIC component library v1 + netlist execution (chain + DAG)
- Date: 2026-02-13
- Owner: PhotonTrust core team

## 1) Deliverables

### 1.1 Code
- PIC component library:
  - `photonstrust/components/pic/library.py`
  - `photonstrust/components/pic/__init__.py`
  - `photonstrust/components/__init__.py`
- PIC netlist simulation:
  - `photonstrust/pic/simulate.py`
  - `photonstrust/pic/__init__.py`

### 1.2 Schema + compiler
- Extend edge schema to support optional ports:
  - `schemas/photonstrust.graph.v0_1.schema.json`
- Ensure compiler preserves/defaults ports:
  - `photonstrust/graph/compiler.py`

### 1.3 CLI
- Add PIC netlist simulation CLI command:
  - `photonstrust/cli.py`
  - `photonstrust pic simulate <compiled_netlist.json> --output <dir>`

### 1.4 Tests
- Add unit tests covering:
  - chain solver loss accounting,
  - DAG solver interference routing (MZI),
  - schema validation changes are backward-compatible.
- Primary file:
  - `tests/test_pic_simulation.py`

### 1.5 Documentation updates (required by rollout protocol)
- Add Phase 09 rollout folder (this folder) and complete artifacts.
- Update:
  - `docs/operations/phased_rollout/README.md`
  - `docs/operations/README.md`
  - `docs/research/14_physics_core_open_science_master_plan_2026-02-12.md`
  - `docs/research/15_platform_rollout_plan_2026-02-13.md`
  - `docs/research/03_physics_models.md`
  - `docs/research/02_architecture_and_interfaces.md`
  - `README.md`

## 2) Detailed build steps (file mapping)

### Step A: PIC component library
- Implement a minimal set of component kinds:
  - `pic.waveguide`: length/loss and optional phase from `phase_rad` or `n_eff`.
  - `pic.grating_coupler` / `pic.edge_coupler`: insertion loss.
  - `pic.phase_shifter`: explicit phase shift and optional insertion loss.
  - `pic.coupler`: unidirectional symmetric 2x2 mixing matrix with coupling ratio.
  - `pic.ring`: placeholder 2-port insertion-loss element (filter physics deferred).

Implementation:
- `photonstrust/components/pic/library.py`

### Step B: PIC netlist simulation
Implement two solvers with shared netlist input:
- `simulate_chain`: detect 2-port chain with default `out -> in` edges and compute:
  - per-component loss,
  - total transmission `eta_total`,
  - `total_loss_db`.
- `simulate_dag`: propagate complex amplitudes along topological order:
  - reject cycles,
  - allow multiport nodes via `component_forward_matrix`,
  - allow explicit `circuit.inputs` / `circuit.outputs`, with auto-detection when
    unambiguous.

Implementation:
- `photonstrust/pic/simulate.py`

### Step C: Schema + compiler port support
Extend graph edge schema to allow optional:
- `from_port` and `to_port`.

Compiler behavior:
- default ports are `out` and `in` if not specified.
- emitted PIC netlist edges always contain `from_port`/`to_port`.

Implementation:
- `schemas/photonstrust.graph.v0_1.schema.json`
- `photonstrust/graph/compiler.py`

### Step D: CLI command
Add:
- `photonstrust pic simulate <netlist.json> --output <dir> [--wavelength-nm ...]`

Output:
- `pic_results.json` including:
  - chain solver summary (if applicable),
  - DAG solver outputs (external port powers),
  - assumptions block.

Implementation:
- `photonstrust/cli.py`

### Step E: Tests
Add tests that enforce:
- loss budgets add in dB for chains,
- MZI routes power between outputs depending on phase difference.

Implementation:
- `tests/test_pic_simulation.py`

## 3) Validation gates (must pass)
- Unit tests:
  - `py -m pytest -q`
- Release gate:
  - `py scripts/release/release_gate_check.py --output results/release_gate/phase09_release_gate_report.json`
- Manual smoke:
  - compile demo PIC graph:
    - `photonstrust graph compile graphs/demo8_pic_circuit_graph.json --output results/graphs`
  - simulate compiled netlist:
    - `photonstrust pic simulate results/graphs/demo8_pic_circuit/compiled_netlist.json --output results/pic/demo8_pic_circuit`

## 4) Non-goals (explicit)
- No bidirectional scattering / reflections in v1.
- No resonator feedback loops (cycles rejected).
- No wavelength sweep engine or dispersion model beyond a placeholder
  phase-from-`n_eff` hook.
- No Touchstone import in Phase 09 (planned next: Phase 09b/Phase 10+).

