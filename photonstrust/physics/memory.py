"""QuTiP-based memory model with T1/T2 decay."""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass
from typing import Any, Dict

import numpy as np


@dataclass
class MemoryStats:
    p_store: float
    p_retrieve: float
    fidelity: float
    variance_fidelity: float
    backend: str
    diagnostics: Dict[str, Any]


def simulate_memory(memory_cfg: dict, wait_time_ns: float) -> MemoryStats:
    backend = memory_cfg.get("physics_backend", "analytic")
    if backend != "qutip":
        return _analytic_memory(memory_cfg, wait_time_ns)

    try:
        return _qutip_memory(memory_cfg, wait_time_ns)
    except Exception as exc:
        warnings.warn(f"QuTiP backend unavailable, using analytic model: {exc}")
        return _analytic_memory(memory_cfg, wait_time_ns)


def _analytic_memory(memory_cfg: dict, wait_time_ns: float) -> MemoryStats:
    t1_ms = _positive(memory_cfg.get("t1_ms", 50.0), default=50.0, field_name="t1_ms")
    t2_ms = _positive(memory_cfg.get("t2_ms", 10.0), default=10.0, field_name="t2_ms")
    retrieval = _clamp_prob(memory_cfg.get("retrieval_efficiency", 0.8), "retrieval_efficiency")
    p_store = _clamp_prob(memory_cfg.get("store_efficiency", 1.0), "store_efficiency")

    wait_s = max(0.0, float(wait_time_ns)) * 1e-9
    t1_s = t1_ms / 1000.0
    t2_s = t2_ms / 1000.0

    decay = math.exp(-wait_s / t2_s)
    t1_decay = math.exp(-wait_s / t1_s)
    fidelity = 0.5 + 0.5 * decay * t1_decay
    p_retrieve = _clamp_prob(p_store * retrieval * t1_decay, "p_retrieve")

    return MemoryStats(
        p_store=p_store,
        p_retrieve=p_retrieve,
        fidelity=fidelity,
        variance_fidelity=0.0,
        backend="analytic",
        diagnostics={
            "wait_time_ns": max(0.0, float(wait_time_ns)),
            "t1_ms": t1_ms,
            "t2_ms": t2_ms,
            "t1_decay": t1_decay,
            "coherence_decay": decay,
        },
    )


def _qutip_memory(memory_cfg: dict, wait_time_ns: float) -> MemoryStats:
    from qutip import basis, destroy, expect, qeye, mesolve

    t1_ms = _positive(memory_cfg.get("t1_ms", 50.0), default=50.0, field_name="t1_ms")
    t2_ms = _positive(memory_cfg.get("t2_ms", 10.0), default=10.0, field_name="t2_ms")
    retrieval = _clamp_prob(memory_cfg.get("retrieval_efficiency", 0.8), "retrieval_efficiency")
    p_store = _clamp_prob(memory_cfg.get("store_efficiency", 1.0), "store_efficiency")
    n_trajectories = int(memory_cfg.get("n_trajectories", 200))
    seed = int(memory_cfg.get("seed", 7))

    t1_s = t1_ms / 1000.0
    t2_s = t2_ms / 1000.0
    wait_s = max(0.0, float(wait_time_ns)) * 1e-9

    sm = destroy(2)
    sz = qeye(2) - 2 * sm.dag() * sm
    gamma1 = 1.0 / t1_s
    gamma2 = max(0.0, (1.0 / t2_s) - 0.5 * gamma1)

    collapse_ops = [math.sqrt(gamma1) * sm]
    if gamma2 > 0:
        collapse_ops.append(math.sqrt(gamma2) * sz)

    rho0 = basis(2, 1) * basis(2, 1).dag()
    times = np.linspace(0, wait_s, 32)
    result = mesolve(0 * sm, rho0, times, collapse_ops, [])
    fidelity = float(expect(rho0, result.states[-1]))

    rng = np.random.default_rng(seed)
    fidelity_samples = np.clip(rng.normal(fidelity, 0.02, n_trajectories), 0.0, 1.0)
    variance = float(np.var(fidelity_samples))
    t1_decay = math.exp(-wait_s / t1_s)
    p_retrieve = _clamp_prob(p_store * retrieval * t1_decay, "p_retrieve")

    return MemoryStats(
        p_store=p_store,
        p_retrieve=p_retrieve,
        fidelity=fidelity,
        variance_fidelity=variance,
        backend="qutip",
        diagnostics={
            "wait_time_ns": max(0.0, float(wait_time_ns)),
            "t1_ms": t1_ms,
            "t2_ms": t2_ms,
            "t1_decay": t1_decay,
            "gamma1_per_s": gamma1,
            "gamma2_per_s": gamma2,
            "seed": seed,
            "n_trajectories": n_trajectories,
        },
    )


def _positive(value: float, default: float, field_name: str) -> float:
    out = float(value)
    if out <= 0.0 or not math.isfinite(out):
        warnings.warn(f"{field_name}={value} invalid; using {default}", stacklevel=3)
        return float(default)
    return out


def _clamp_prob(value: float, field_name: str) -> float:
    out = float(value)
    if not math.isfinite(out):
        warnings.warn(f"{field_name} non-finite; using 0.0", stacklevel=3)
        return 0.0
    if out < 0.0:
        warnings.warn(f"{field_name}={out} below 0.0; clamped", stacklevel=3)
        return 0.0
    if out > 1.0:
        warnings.warn(f"{field_name}={out} above 1.0; clamped", stacklevel=3)
        return 1.0
    return out
