# Phase 29 - Validation Report (2026-02-14)

## Gates

### Python
- `py -m pytest -q`
  - Result: PASS (124 passed, 1 skipped)
- `py scripts/release/release_gate_check.py`
  - Result: PASS

### Web
- `cd web && npm run lint`
  - Result: PASS
- `cd web && npm run build`
  - Result: PASS

## Functional Validation
- API endpoints return run IDs and write manifests + artifacts:
  - layout build: ports/routes/provenance (+ optional GDS)
  - LVS-lite: mismatch report
  - SPICE export: netlist + mapping + provenance
- Web UI tabs surface artifact links and manifest links for review.

## Tool Availability Notes
- KLayout/ngspice remain optional external tools. This phase does not require them to be installed.
