"""QuTiP backend wrapper for emitter-domain high-fidelity checks."""

from __future__ import annotations

import copy
import importlib
import importlib.util
from typing import Any, Mapping

from photonstrust.physics.backends.base import ApplicabilityReport, BackendProvenance, PhysicsBackend, normalize_component_name
from photonstrust.physics.emitter import get_emitter_stats


class QutipBackend(PhysicsBackend):
    backend_name = "qutip"
    backend_version = "0.1"

    def simulate(
        self,
        component: str,
        inputs: Mapping[str, Any],
        *,
        seed: int | None = None,
        mode: str | None = None,
    ) -> Any:
        normalized = normalize_component_name(component)
        if normalized != "emitter":
            raise ValueError(f"QuTiP backend does not support component: {component!r}")

        payload = copy.deepcopy(dict(inputs))
        payload["physics_backend"] = "qutip"
        if seed is not None:
            payload["seed"] = int(seed)
        if mode is not None:
            payload["emission_mode"] = str(mode)
        return get_emitter_stats(payload)

    def applicability(self, component: str, inputs: Mapping[str, Any]) -> ApplicabilityReport:
        del inputs
        normalized = normalize_component_name(component)
        if normalized != "emitter":
            return ApplicabilityReport(
                status="fail",
                reasons=(f"component '{normalized}' is not implemented by qutip backend",),
            )

        if not _qutip_is_available():
            return ApplicabilityReport(
                status="fail",
                reasons=("qutip dependency not installed; install with pip install -e .[qutip]",),
            )

        return ApplicabilityReport(status="pass", reasons=())

    def provenance(self, *, seed: int | None = None, details: Mapping[str, Any] | None = None) -> BackendProvenance:
        merged = dict(details or {})
        merged.setdefault("qutip_available", _qutip_is_available())
        merged.setdefault("qutip_version", _qutip_version())
        return super().provenance(seed=seed, details=merged)


def _qutip_is_available() -> bool:
    return importlib.util.find_spec("qutip") is not None


def _qutip_version() -> str | None:
    if not _qutip_is_available():
        return None
    qutip_mod = importlib.import_module("qutip")
    return str(getattr(qutip_mod, "__version__", "unknown"))
