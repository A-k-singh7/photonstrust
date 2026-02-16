# Memory and Detector Validation Report - Week 3 (2026-02-12)

Status: completed

## Scope
Validation of:
- memory decay and retrieval behavior (`photonstrust.physics.memory`)
- detector stochastic realism and bounds (`photonstrust.physics.detector`)

## Model updates validated
- `photonstrust/physics/memory.py`
  - retrieval probability now decays with wait-time (`T1` term)
  - probability and timescale guardrails added
  - diagnostics block added to `MemoryStats`
- `photonstrust/physics/detector.py`
  - probability/non-negative guardrails for detector parameters
  - deterministic-seed behavior preserved

## Test evidence
New test coverage:
- `tests/test_memory_detector_invariants.py`

Key invariants covered:
1. memory fidelity monotonicity vs wait time
2. memory retrieval monotonic decay vs wait time
3. detector click bounds and false-click bounds in `[0, 1]`
4. detector click-rate monotonicity vs PDE (fixed seed)
5. dead-time effect reduces click rate
6. deterministic repeatability for fixed seed

Suite result on `2026-02-12`:
```bash
pytest -q
```
- `16 passed`

## Exit criteria check
- Fidelity decay monotonicity: verified.
- Detector bounds and realism checks: verified.

Week 3 exit criteria are met for current baseline.

