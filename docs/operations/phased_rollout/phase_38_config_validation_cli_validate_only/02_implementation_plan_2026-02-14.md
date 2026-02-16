# Phase 38 - Config Validation + CLI `--validate-only` (v0.1.1) - Implementation Plan (2026-02-14)

## Scope

- Scenario config validation for scenario-based runs (`photonstrust run ...`)
- Numerically stable `distance_km` expansion

Non-goals:
- Pydantic migration (explicitly deferred; keep open-core lightweight)
- API server schema posture changes (graph validation remains its own track)

## Implementation Steps

### 1) Add scenario validation module

File:
- `photonstrust/photonstrust/validation.py` (new)

Contract:
- `validate_scenario(scenario) -> list[str]`
- `validate_scenarios_or_raise(scenarios) -> None` raising `ConfigValidationError`

### 2) Harden distance expansion

File:
- `photonstrust/photonstrust/config.py`

Changes:
- validate `step > 0`, finite `start/stop`, and `stop >= start`
- compute count using `round((stop-start)/step)` and `round()` emitted points to avoid drift

### 3) Add CLI validate-only mode + fail-fast validation

File:
- `photonstrust/photonstrust/cli.py`

Changes:
- add `photonstrust run --validate-only`
- validate scenarios immediately after `build_scenarios(config)` and before `run_scenarios(...)`
- on validation error: print a clear message and exit non-zero

### 4) Add tests

File:
- `photonstrust/tests/test_config_validation_and_distance_expand.py` (new)

Coverage:
- distance expansion includes stop and rejects invalid step
- validation flags out-of-range values and aggregates errors

## Validation Gates

Python:

```powershell
cd c:\Users\aksin\Desktop\Qutip+qskit projects\photonstrust
py -m pytest -q
py scripts\release_gate_check.py
```

Web:

```powershell
cd web
npm run lint
npm run build
```

Optional manual check:

```powershell
photonstrust run configs/demo1_quick_smoke.yml --validate-only
```

