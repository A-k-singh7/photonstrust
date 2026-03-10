"""Protocol engine abstraction layer and parity harness."""

from photonstrust.protocols.engines.analytic_engine import AnalyticProtocolEngine
from photonstrust.protocols.engines.base import (
    ProtocolEngine,
    ProtocolEngineError,
    ProtocolEngineUnavailableError,
    ProtocolPrimitiveResult,
)
from photonstrust.protocols.engines.cirq_engine import CirqProtocolEngine
from photonstrust.protocols.engines.parity import DEFAULT_THRESHOLD_POLICY, run_protocol_engine_parity
from photonstrust.protocols.engines.pennylane_engine import PennyLaneProtocolEngine
from photonstrust.protocols.engines.qiskit_engine import QiskitProtocolEngine
from photonstrust.protocols.engines.registry import (
    available_protocol_engines,
    get_protocol_engine,
    protocol_engine_status,
    register_protocol_engine,
)

__all__ = [
    "AnalyticProtocolEngine",
    "CirqProtocolEngine",
    "DEFAULT_THRESHOLD_POLICY",
    "PennyLaneProtocolEngine",
    "ProtocolEngine",
    "ProtocolEngineError",
    "ProtocolEngineUnavailableError",
    "ProtocolPrimitiveResult",
    "QiskitProtocolEngine",
    "available_protocol_engines",
    "get_protocol_engine",
    "protocol_engine_status",
    "register_protocol_engine",
    "run_protocol_engine_parity",
]
