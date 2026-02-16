# 07 - Code Quality Findings

---

## Research Anchors (Language/Runtime References)

- Python `warnings` module (consistent warning behavior): https://docs.python.org/3/library/warnings.html
- PEP 8 (style conventions): https://peps.python.org/pep-0008/
- Python typing (module index, TypedDict, etc.): https://docs.python.org/3/library/typing.html

## Finding 1: Duplicated validation helpers

**Locations:**
- `photonstrust/physics/emitter.py`: `_clamp_zero_one()`, `_positive()`
- `photonstrust/physics/detector.py`: `_clamp_probability()`, `_non_negative()`
- `photonstrust/channels/free_space.py`: `_clamp()`
- `photonstrust/utils.py`: `clamp()`

**Issue:** Four modules define overlapping clamp/validate functions with
slightly different signatures and behavior (some warn, some silently clamp).

**Correction:** Consolidate into `photonstrust/utils.py`:

```python
# photonstrust/utils.py

import warnings

def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))

def clamp_probability(value: float, name: str = "", warn_on_clip: bool = False) -> float:
    """Clamp to [0, 1] with optional warning."""
    v = float(value)
    if v < 0.0 or v > 1.0:
        if warn_on_clip and name:
            warnings.warn(f"{name} clipped from {v} to [{0.0}, {1.0}]")
    return max(0.0, min(1.0, v))

def positive(value: float, default: float, name: str = "") -> float:
    """Ensure positive value, falling back to default."""
    v = float(value)
    if v <= 0.0:
        if name:
            warnings.warn(f"{name} must be > 0, using default {default}")
        return float(default)
    return v

def non_negative(value: float, name: str = "") -> float:
    """Ensure non-negative value."""
    v = float(value)
    if v < 0.0:
        if name:
            warnings.warn(f"{name} must be >= 0, clamping to 0")
        return 0.0
    return v
```

Then update imports in each module:

```python
# emitter.py
from photonstrust.utils import clamp_probability as _clamp_zero_one, positive as _positive

# detector.py
from photonstrust.utils import clamp_probability as _clamp_probability, non_negative as _non_negative
```

---

## Finding 2: Broad exception catching in API server

**Location:** `photonstrust/api/server.py`

**Issue:** `except Exception` catches everything including `KeyboardInterrupt`,
`SystemExit`, and programming errors. This hides bugs and may leak internal
details in error messages.

**Correction:**

1. Define a custom exception hierarchy:

```python
# photonstrust/errors.py

class PhotonTrustError(Exception):
    """Base exception for all PhotonTrust errors."""
    pass

class ConfigError(PhotonTrustError):
    """Invalid configuration."""
    pass

class PhysicsError(PhotonTrustError):
    """Physics model computation error."""
    pass

class ValidationError(PhotonTrustError):
    """Schema or parameter validation error."""
    pass
```

2. Catch specific exceptions in API endpoints:

```python
from photonstrust.errors import PhotonTrustError

@app.post("/api/run")
async def run(config: dict):
    try:
        result = _execute(config)
        return result
    except PhotonTrustError as e:
        raise HTTPException(400, detail=str(e))
    except Exception as e:
        # Log the full traceback internally
        logger.exception("Unexpected error in /api/run")
        raise HTTPException(500, detail="Internal server error")
```

---

## Finding 3: Missing type hints on public functions

**Locations:**
- `qkd.py`: `compute_sweep()` returns `dict` (should be typed)
- `config.py`: `build_scenarios()` returns `list[dict]` (should be typed)
- `sweep.py`: Most functions lack annotations

**Correction:** Add return type annotations to public API functions:

```python
# qkd.py
def compute_sweep(scenario: dict, include_uncertainty: bool = True) -> dict:
    """Returns {"results": list[QKDResult], "uncertainty": dict|None, "performance": dict}"""

# config.py
def build_scenarios(config: dict) -> list[dict]:
    """Returns list of expanded scenario dicts ready for compute_sweep()."""
```

For v0.2, use the TypedDict definitions from doc 03.

---

## Finding 4: `_expand_distance()` duplicated logic

**Location:** `photonstrust/config.py:49-56`

```python
def _expand_distance(distance):
    if isinstance(distance, (int, float)):
        return [float(distance)]
    start = float(distance["start"])
    stop = float(distance["stop"])
    step = float(distance["step"])
    count = int((stop - start) / step) + 1
    return [start + i * step for i in range(count)]
```

**Issue:** This manual range expansion can accumulate floating-point drift.
For `start=0, stop=100, step=10`, the last element may be 99.99999... instead
of 100.0 due to float arithmetic.

**Correction:** Use `numpy.linspace` or round to step precision:

```python
def _expand_distance(distance):
    if isinstance(distance, (int, float)):
        return [float(distance)]
    start = float(distance["start"])
    stop = float(distance["stop"])
    step = float(distance["step"])
    if step <= 0:
        raise ValueError(f"distance_km step must be > 0, got {step}")
    count = int(round((stop - start) / step)) + 1
    return [round(start + i * step, 10) for i in range(count)]
```

**Implemented (v0.1.1):** `_expand_distance` was updated to validate inputs and round emitted distances
(see `docs/operations/phased_rollout/phase_38_config_validation_cli_validate_only/`).

---

## Finding 5: Inconsistent warning usage

**Issue:** Only 3 modules use `warnings.warn()` (emitter, detector, memory).
Other modules silently clamp values. Users have no way to know their inputs
were modified.

**Correction:** Add warnings when values are auto-corrected:

```python
# channels/free_space.py
def total_free_space_efficiency(...):
    distance_km = max(0.0, float(distance_km))
    if float(distance_km_raw) < 0:
        warnings.warn(f"distance_km={distance_km_raw} clamped to 0.0")
```

Apply consistently across all modules that clamp inputs.

---

## Finding 6: No `__all__` exports in package `__init__.py`

**Issue:** Package modules don't define `__all__`, making it unclear what the
public API surface is.

**Correction:** Add `__all__` to key modules:

```python
# photonstrust/__init__.py
__all__ = ["compute_sweep", "compute_point", "load_config", "build_scenarios"]

# photonstrust/qkd.py
__all__ = ["QKDResult", "compute_sweep", "compute_point"]
```

---

## Summary

| Finding | Severity | Fix effort |
|---------|----------|------------|
| Duplicated validation helpers | Medium | Low (consolidate) |
| Broad exception catching in API | Medium | Low (custom exceptions) |
| Missing type hints on public API | Low | Low (add annotations) |
| Float drift in distance expansion | Low | Low (use round()) |
| Inconsistent warnings | Low | Low (add to clamp sites) |
| No `__all__` exports | Low | Low (add to modules) |
