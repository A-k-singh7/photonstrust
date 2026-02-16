# Phase 48 Implementation Plan: PIC Scattering Realism Pack v0.3

## Deliverables

1) Edge propagation in both solvers

- Extend graph schema and compiler to preserve `edges[].params`.
- Apply edge transfer in:
  - DAG solver (multiply along each incoming edge)
  - scattering solver (use weighted `C` matrix entries)

2) Native reflections and non-reciprocal 2-port

- Extend `component_scattering_matrix` for native 2-port elements to support:
  - `return_loss_db` / reflection phase
  - per-port overrides (`return_loss_in_db`, `return_loss_out_db`)
- Add `pic.isolator_2port` kind (non-reciprocal `S21 != S12`).

3) Touchstone N-port

- Replace the 2-port-only parser with an N-port `.sNp` parser.
- Add `pic.touchstone_nport` kind with dynamic ports (p1..pN, split into in/out).

## Code Changes

- Graph schema:
  - `schemas/photonstrust.graph.v0_1.schema.json` add optional `edges[].params`.

- Compiler:
  - `photonstrust/photonstrust/graph/compiler.py` preserve `edge.params` in compiled netlists.

- PIC simulator:
  - `photonstrust/photonstrust/pic/simulate.py`
    - `_edge_transfer(...)` computes `g` from edge params
    - DAG solver multiplies contributions by `g`
    - scattering solver sets `C[i,j] = g`
    - pass node params into `component_ports/component_all_ports`

- PIC component library:
  - `photonstrust/photonstrust/components/pic/library.py`
    - `component_ports(kind, params)` supports dynamic ports for `pic.touchstone_nport`
    - reflections + isolator logic in `component_scattering_matrix`
    - add `_matrix_touchstone_nport` and `pic.touchstone_nport` kind

- Touchstone parser:
  - `photonstrust/photonstrust/components/pic/touchstone.py`
    - `parse_touchstone_nport`, `load_touchstone_nport`, generalized interpolation

- Registry + diagnostics:
  - `photonstrust/photonstrust/registry/kinds.py` add `pic.isolator_2port` and `pic.touchstone_nport`, and `return_loss_db` params on native 2-ports
  - `photonstrust/photonstrust/graph/diagnostics.py` add `array` param type support

- PIC layout / SPICE / LVS-lite
  - Pass node params into `component_ports` where needed:
    - `photonstrust/photonstrust/layout/pic/build_layout.py`
    - `photonstrust/photonstrust/spice/export.py`
    - `photonstrust/photonstrust/verification/lvs_lite.py`

## Tests

- Edge propagation:
  - `photonstrust/tests/test_pic_simulation.py` adds edge loss and edge phase tests
  - `photonstrust/tests/test_schema_validation.py` verifies schema accepts `edges[].params`

- Native reflections + isolator:
  - `photonstrust/tests/test_pic_simulation.py` adds reflection/isolator scattering tests

- Touchstone N-port:
  - `photonstrust/tests/test_pic_touchstone_import.py` adds `.s4p` import test
  - New fixture: `photonstrust/tests/fixtures/touchstone_demo_4port.s4p`

## Validation Gate

- `py -m pytest -q`
