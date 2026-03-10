"""Qiskit-backed protocol engine."""

from __future__ import annotations

import importlib
import importlib.util

from photonstrust.protocols.circuits import repeater_bsm_success_probability
from photonstrust.protocols.engines.base import ProtocolEngine, ProtocolPrimitiveResult


class QiskitProtocolEngine(ProtocolEngine):
    engine_id = "qiskit"
    engine_version = "0.1"

    def supported_primitives(self) -> tuple[str, ...]:
        return ("swap_bsm_equal_bits",)

    def availability(self) -> tuple[bool, str | None]:
        if _module_available("qiskit"):
            return True, None
        return False, "qiskit dependency not installed; install with pip install -e .[qiskit]"

    def run_primitive(self, primitive: str, *, seed: int | None = None) -> ProtocolPrimitiveResult:
        self.require_available()
        normalized = str(primitive or "").strip().lower()
        if normalized != "swap_bsm_equal_bits":
            raise ValueError(f"unsupported primitive {primitive!r} for qiskit protocol engine")
        comparison = repeater_bsm_success_probability(seed=seed)
        return ProtocolPrimitiveResult(
            engine_id=self.engine_id,
            primitive=normalized,
            metrics={"success_probability": float(comparison["circuit_probability"])},
            metadata={"formula_probability": float(comparison["formula_probability"])},
        )

    def provenance(self) -> dict[str, object]:
        payload = super().provenance()
        payload["qiskit_version"] = _module_version("qiskit")
        return payload


def _module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _module_version(module_name: str) -> str | None:
    if not _module_available(module_name):
        return None
    module = importlib.import_module(module_name)
    return str(getattr(module, "__version__", "unknown"))
