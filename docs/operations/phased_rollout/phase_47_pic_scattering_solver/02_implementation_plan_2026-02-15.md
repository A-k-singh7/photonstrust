# Phase 47 Implementation Plan: PIC Scattering-Network Solver

## Deliverables

- Add a bidirectional scattering solver for `pic_circuit` netlists.
- Allow cycles in the graph compiler when `circuit.solver = 'scattering'`.
- Extend the PIC component library with `component_scattering_matrix()`.
- Add unit tests covering:
  - Touchstone reflection propagation.
  - A simple feedback cycle producing a multi-pass gain consistent with the linear model.

## Code Changes

1. PIC component library: scattering matrices

- File: `photonstrust/photonstrust/components/pic/library.py`
- Add:
  - `component_all_ports(kind)`
  - `component_scattering_matrix(kind, params, wavelength_nm)`
- Behavior:
  - Native 2-port components: `S11=S22=0`, `S21=S12=t` where `t` is the existing forward scalar amplitude.
  - `pic.coupler`: build a 4-port reflectionless reciprocal scattering matrix from the existing 2x2 forward mixing matrix.
  - `pic.touchstone_2port`: return the full 2x2 S matrix evaluated at the wavelength.

2. PIC simulator: scattering solve

- File: `photonstrust/photonstrust/pic/simulate.py`
- Add `simulate_scattering(...)` implementing `(I - S C) b = S a_ext`.
- Update `simulate_pic_netlist(...)` to:
  - Always run chain solver.
  - Run DAG solver but report non-applicability if it fails (e.g., due to cycles).
  - Run scattering solver when `circuit.solver` is one of: `scattering`, `scattering_network`, `bidirectional_scattering`.

3. Graph compiler: cycle gating

- File: `photonstrust/photonstrust/graph/compiler.py`
- Keep default behavior (reject cycles).
- If topological sort fails due to a cycle and `circuit.solver='scattering'`, allow compilation and mark `topology.is_dag=false`.

## Tests

- Update: `photonstrust/tests/test_graph_compiler.py`
  - Add a test that cycles are allowed when `circuit.solver='scattering'`.

- Update: `photonstrust/tests/test_pic_simulation.py`
  - Add scattering solver tests for reflection and feedback cycles.

- Add fixtures:
  - `photonstrust/tests/fixtures/touchstone_reflective.s2p`
  - `photonstrust/tests/fixtures/touchstone_bidir.s2p`

## Validation Gates

- Run: `py -m pytest -q`
- Ensure no regressions to forward-only solver behavior.
