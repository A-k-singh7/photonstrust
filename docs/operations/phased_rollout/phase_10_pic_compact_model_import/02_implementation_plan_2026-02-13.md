# Implementation Plan

## Metadata
- Work item ID: PT-PHASE-10
- Title: ChipVerify compact model import (Touchstone/S-parameters) + wavelength sweeps
- Date: 2026-02-13

## 1) Deliverables

### 1.1 Touchstone ingestion (2-port)
- New module:
  - `photonstrust/components/pic/touchstone.py`
- New component kind:
  - `pic.touchstone_2port` in `photonstrust/components/pic/library.py`

Parameters (v1):
- `touchstone_path` (required): path to `.s2p`
- `forward` (optional, default `s21`): choose `s21` or `s12`
- `allow_extrapolation` (optional, default false): allow out-of-range evaluation

### 1.2 Sweep execution
- New function:
  - `photonstrust/pic/simulate.py::simulate_pic_netlist_sweep`
- Export from:
  - `photonstrust/pic/__init__.py`

### 1.3 CLI support
- Extend `photonstrust pic simulate`:
  - add `--wavelength-sweep-nm` (list of floats)
  - keep `--wavelength-nm` override behavior for single-point simulation

### 1.4 Tests and fixtures
- Add fixture Touchstone file(s):
  - `tests/fixtures/touchstone_demo.s2p`
- Add tests:
  - `tests/test_pic_touchstone_import.py`
  - `tests/test_pic_sweep.py`

## 2) Build steps (file mapping)

### Step A: Implement Touchstone parser (conservative subset)
- Parse header:
  - units (HZ/KHZ/MHZ/GHZ)
  - parameter type (S only)
  - format (RI/MA/DB)
  - reference impedance (optional capture)
- Parse data records:
  - 2-port ordering: S11, S21, S12, S22
- Enforce strictly increasing frequency grid.
- Provide deterministic interpolation of complex matrices.

### Step B: Add `pic.touchstone_2port` component kind
- Add component ports `in -> out`.
- Convert `wavelength_nm` to `freq_hz`.
- Map forward transmission:
  - default: S21
- Reject missing wavelength with explicit errors.
- Use absolute-path caching for stable behavior.

### Step C: Add sweep runner
- Implement `simulate_pic_netlist_sweep` by repeatedly calling
  `simulate_pic_netlist` with explicit wavelength overrides.
- Return a structured payload:
  - list of wavelengths
  - per-wavelength outputs

### Step D: Wire up CLI
- Add CLI argument parsing.
- Preserve backward compatibility:
  - existing `photonstrust pic simulate` usage remains valid.

## 3) Validation gates (must pass)
- Unit tests:
  - `py -m pytest -q`
- Release gate:
  - `py scripts/release_gate_check.py --output results/release_gate/phase10_release_gate_report.json`
- Manual smoke (optional but recommended):
  - run a sweep on a compiled PIC netlist:
    - `photonstrust pic simulate <netlist.json> --wavelength-sweep-nm 1540 1550 1560 --output results/pic/sweep_demo`

## 4) Non-goals (explicit)
- No full bidirectional S-parameter network solve in v1 (reflections ignored).
- No multiport Touchstone import in this phase.
- No automated compact-model calibration to measurements yet (planned).

