"""Qiskit backend wrapper for repeater primitive cross-checks."""

from __future__ import annotations

import importlib
import importlib.util
from typing import Any, Mapping

from photonstrust.physics.backends.base import ApplicabilityReport, BackendProvenance, PhysicsBackend, normalize_component_name
from photonstrust.protocols.circuits import repeater_bsm_success_probability


class QiskitBackend(PhysicsBackend):
    backend_name = "qiskit"
    backend_version = "0.1"

    def simulate(
        self,
        component: str,
        inputs: Mapping[str, Any],
        *,
        seed: int | None = None,
        mode: str | None = None,
    ) -> Any:
        del mode
        normalized = normalize_component_name(component)
        if normalized not in {"repeater", "repeater_primitive", "protocol"}:
            raise ValueError(f"Qiskit backend does not support component: {component!r}")

        tolerance = float(inputs.get("tolerance", 1.0e-9) or 1.0e-9)
        comparison = repeater_bsm_success_probability(seed=seed)
        delta = abs(float(comparison["formula_probability"]) - float(comparison["circuit_probability"]))
        status = "pass" if delta <= tolerance else "warn"

        return {
            "status": status,
            "summary": comparison,
            "tolerances": {"abs_delta": tolerance},
        }

    def applicability(self, component: str, inputs: Mapping[str, Any]) -> ApplicabilityReport:
        del inputs
        normalized = normalize_component_name(component)
        if normalized not in {"repeater", "repeater_primitive", "protocol"}:
            return ApplicabilityReport(
                status="fail",
                reasons=(f"component '{normalized}' is not implemented by qiskit backend",),
            )
        if not _qiskit_is_available():
            return ApplicabilityReport(
                status="fail",
                reasons=("qiskit dependency not installed; install with pip install -e .[qiskit]",),
            )
        return ApplicabilityReport(status="pass", reasons=())

    def provenance(self, *, seed: int | None = None, details: Mapping[str, Any] | None = None) -> BackendProvenance:
        merged = dict(details or {})
        merged.setdefault("qiskit_available", _qiskit_is_available())
        merged.setdefault("qiskit_version", _qiskit_version())
        return super().provenance(seed=seed, details=merged)


def _qiskit_is_available() -> bool:
    return importlib.util.find_spec("qiskit") is not None


def _qiskit_version() -> str | None:
    if not _qiskit_is_available():
        return None
    qiskit_mod = importlib.import_module("qiskit")
    return str(getattr(qiskit_mod, "__version__", "unknown"))
