"""Physics backend interface and resolver layer."""

from __future__ import annotations

import warnings

from photonstrust.physics.backends.analytic import AnalyticBackend
from photonstrust.physics.backends.base import ApplicabilityReport, BackendProvenance, PhysicsBackend
from photonstrust.physics.backends.qiskit_backend import QiskitBackend
from photonstrust.physics.backends.qutip_backend import QutipBackend
from photonstrust.physics.backends.stochastic import StochasticBackend


_BACKEND_FACTORIES: dict[str, type[PhysicsBackend]] = {
    "analytic": AnalyticBackend,
    "qiskit": QiskitBackend,
    "qutip": QutipBackend,
    "stochastic": StochasticBackend,
}


def resolve_backend(name: str | None, *, default: str = "analytic") -> PhysicsBackend:
    requested = str(name or "").strip().lower()
    if requested in _BACKEND_FACTORIES:
        return _BACKEND_FACTORIES[requested]()

    fallback = str(default or "analytic").strip().lower()
    if fallback not in _BACKEND_FACTORIES:
        fallback = "analytic"

    if requested:
        warnings.warn(
            f"Unsupported physics backend {requested!r}; using {fallback!r}",
            stacklevel=2,
        )
    return _BACKEND_FACTORIES[fallback]()


def available_backends() -> tuple[str, ...]:
    return tuple(sorted(_BACKEND_FACTORIES.keys()))


__all__ = [
    "AnalyticBackend",
    "ApplicabilityReport",
    "BackendProvenance",
    "PhysicsBackend",
    "QiskitBackend",
    "QutipBackend",
    "StochasticBackend",
    "available_backends",
    "resolve_backend",
]
