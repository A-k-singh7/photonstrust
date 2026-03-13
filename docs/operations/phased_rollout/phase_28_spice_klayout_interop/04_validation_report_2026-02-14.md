# Phase 28 - Validation Report (2026-02-14)

## Gates

### Python
- `py -m pytest -q`
  - Result: PASS (122 passed, 1 skipped)
- `py scripts/release/release_gate_check.py`
  - Result: PASS

### Web
- `cd web && npm run lint`
  - Result: PASS
- `cd web && npm run build`
  - Result: PASS

## Tool Availability Notes
- `ngspice` is not installed on PATH in this environment.
  - Runner behavior is validated via the missing-tool error path.
- KLayout is not installed on PATH in this environment.
  - Runner behavior is validated via the missing-tool error path.

## Functional Checks
- SPICE export artifacts are generated and schema-valid:
  - `netlist.sp`, `spice_map.json`, `spice_provenance.json`
- Export determinism check passes (ignoring timestamps).
