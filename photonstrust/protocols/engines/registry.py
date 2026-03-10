"""Protocol engine registry and resolver."""

from __future__ import annotations

from typing import Callable

from photonstrust.protocols.engines.analytic_engine import AnalyticProtocolEngine
from photonstrust.protocols.engines.base import ProtocolEngine
from photonstrust.protocols.engines.cirq_engine import CirqProtocolEngine
from photonstrust.protocols.engines.pennylane_engine import PennyLaneProtocolEngine
from photonstrust.protocols.engines.qiskit_engine import QiskitProtocolEngine


EngineFactory = Callable[[], ProtocolEngine]


_ENGINE_FACTORIES: dict[str, EngineFactory] = {
    "analytic": AnalyticProtocolEngine,
    "qiskit": QiskitProtocolEngine,
    "cirq": CirqProtocolEngine,
    "pennylane": PennyLaneProtocolEngine,
}


def register_protocol_engine(engine_id: str, factory: EngineFactory) -> None:
    key = str(engine_id or "").strip().lower()
    if not key:
        raise ValueError("engine_id must be non-empty")
    _ENGINE_FACTORIES[key] = factory


def available_protocol_engines() -> tuple[str, ...]:
    return tuple(sorted(_ENGINE_FACTORIES.keys()))


def get_protocol_engine(engine_id: str) -> ProtocolEngine:
    key = str(engine_id or "").strip().lower()
    factory = _ENGINE_FACTORIES.get(key)
    if factory is None:
        known = ", ".join(available_protocol_engines())
        raise ValueError(f"unknown protocol engine {key!r}; known engines: {known}")
    return factory()


def protocol_engine_status(engine_id: str) -> dict[str, object]:
    engine = get_protocol_engine(engine_id)
    available, reason = engine.availability()
    return {
        "engine_id": engine.engine_id,
        "available": bool(available),
        "reason": reason,
        "provenance": engine.provenance(),
    }
