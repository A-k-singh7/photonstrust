"""Acceleration helpers for satellite-chain pass accumulation."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np


def jax_available() -> bool:
    """Return True when JAX runtime is importable."""

    try:
        import jax.numpy  # noqa: F401
    except Exception:
        return False
    return True


def accumulate_key_bits(
    key_rates_bps: Sequence[float],
    dt_s: float,
    *,
    backend: str = "numpy",
) -> float:
    """Accumulate key bits with optional JAX backend.

    Backends:
    - ``numpy``: deterministic CPU path.
    - ``jax``: JAX array path; falls back to NumPy if unavailable.
    - ``auto``: prefers JAX when available.
    """

    selected = str(backend or "numpy").strip().lower()
    if selected == "auto":
        selected = "jax" if jax_available() else "numpy"

    if selected == "jax":
        value = _accumulate_key_bits_jax(key_rates_bps, dt_s)
        if value is not None:
            return float(value)
        return float(_accumulate_key_bits_numpy(key_rates_bps, dt_s))

    return float(_accumulate_key_bits_numpy(key_rates_bps, dt_s))


def _accumulate_key_bits_numpy(key_rates_bps: Sequence[float], dt_s: float) -> float:
    dt = max(0.0, float(dt_s))
    if dt <= 0.0:
        return 0.0

    arr = np.asarray(list(key_rates_bps), dtype=float)
    if arr.size == 0:
        return 0.0
    arr = np.clip(arr, a_min=0.0, a_max=None)
    return float(arr.sum() * dt)


def _accumulate_key_bits_jax(key_rates_bps: Sequence[float], dt_s: float) -> float | None:
    try:
        import jax.numpy as jnp
    except Exception:
        return None

    dt = max(0.0, float(dt_s))
    if dt <= 0.0:
        return 0.0

    arr = jnp.asarray(list(key_rates_bps), dtype=float)
    if int(arr.size) == 0:
        return 0.0
    arr = jnp.clip(arr, a_min=0.0)
    return float(jnp.sum(arr) * dt)

