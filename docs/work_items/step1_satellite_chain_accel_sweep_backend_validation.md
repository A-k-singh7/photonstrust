# Step 1 Validation: Satellite Chain Acceleration and Sweep Backends

This note captures the Step 1 validation scope for the new acceleration and sweep backend paths.

## Covered Behaviors

- `accumulate_key_bits` NumPy path:
  - clips negative rates to zero
  - integrates deterministic total bits as `sum(key_rate_bps) * dt_s`
- `accumulate_key_bits` `auto` backend:
  - falls back to NumPy when JAX is unavailable
- `run_satellite_chain_sweep` local backend:
  - accepts minimal scenario config files
  - produces deterministic aggregate summary and report file
- `run_satellite_chain_sweep` Ray backend guard:
  - raises a clear runtime error when `ray` is not installed

## Targeted Test Command

```powershell
py -3 -m pytest -q tests/test_satellite_chain_accel.py tests/test_satellite_chain_sweep_backend.py
```

