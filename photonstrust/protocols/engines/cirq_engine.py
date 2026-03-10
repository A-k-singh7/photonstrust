"""Optional Cirq protocol engine adapter."""

from __future__ import annotations

import importlib
import importlib.util

from photonstrust.protocols.engines.base import ProtocolEngine, ProtocolPrimitiveResult


class CirqProtocolEngine(ProtocolEngine):
    engine_id = "cirq"
    engine_version = "0.1"

    def supported_primitives(self) -> tuple[str, ...]:
        return ("swap_bsm_equal_bits",)

    def availability(self) -> tuple[bool, str | None]:
        if _module_available("cirq"):
            return True, None
        return False, "cirq dependency not installed; install with pip install cirq"

    def run_primitive(self, primitive: str, *, seed: int | None = None) -> ProtocolPrimitiveResult:
        self.require_available()
        _ = seed
        normalized = str(primitive or "").strip().lower()
        if normalized != "swap_bsm_equal_bits":
            raise ValueError(f"unsupported primitive {primitive!r} for cirq protocol engine")
        return ProtocolPrimitiveResult(
            engine_id=self.engine_id,
            primitive=normalized,
            metrics={"success_probability": 0.5},
            metadata={"adapter_mode": "analytic_reference"},
        )

    def provenance(self) -> dict[str, object]:
        payload = super().provenance()
        payload["cirq_version"] = _module_version("cirq")
        return payload


def _module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _module_version(module_name: str) -> str | None:
    if not _module_available(module_name):
        return None
    module = importlib.import_module(module_name)
    return str(getattr(module, "__version__", "unknown"))
