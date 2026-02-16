# Phase 27 - Validation Report (2026-02-14)

## Gates

### Python
- `py -m pytest -q`
  - Result: PASS (122 passed, 1 skipped)
- `py scripts/release_gate_check.py`
  - Result: PASS

### Web
- `cd web && npm run lint`
  - Result: PASS
- `cd web && npm run build`
  - Result: PASS

## Functional Checks
- Layout builder emits deterministic artifacts:
  - `ports.json`
  - `routes.json`
  - `layout_provenance.json`
  - optional `layout.gds` when `gdstk` is installed
- LVS-lite report:
  - detects missing edges and dangling endpoints
  - passes when layout sidecars match expected connectivity

## Environment Notes
- This environment does not have KLayout or ngspice on PATH.
- `gdstk` is optional; tests are designed to pass with or without it.
