# Phase 38 - Config Validation + CLI `--validate-only` (v0.1.1) - Validation Report (2026-02-14)

## Gates

Python tests:

```powershell
cd c:\Users\aksin\Desktop\Qutip+qskit projects\photonstrust
py -m pytest -q
```

Result:
- `139 passed, 2 skipped`

Release gate:

```powershell
py scripts\release_gate_check.py
```

Result:
- `Release gate: PASS`

Web:

```powershell
cd web
npm run lint
npm run build
```

Result:
- `lint`: PASS
- `build`: PASS

## Manual CLI Check (Optional)

```powershell
photonstrust run configs/demo1_quick_smoke.yml --validate-only
```

Expected:
- exits successfully after validation and prints a small JSON payload indicating the scenario count.

## Decision

Phase 38 is **approved**.

