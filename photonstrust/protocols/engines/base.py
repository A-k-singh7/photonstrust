"""Base contracts for protocol engines."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Mapping


class ProtocolEngineError(RuntimeError):
    """Base error for protocol engine failures."""


class ProtocolEngineUnavailableError(ProtocolEngineError):
    """Raised when an optional engine dependency is unavailable."""


@dataclass(frozen=True)
class ProtocolPrimitiveResult:
    """Normalized primitive metric payload returned by protocol engines."""

    engine_id: str
    primitive: str
    metrics: Mapping[str, float]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "engine_id": str(self.engine_id),
            "primitive": str(self.primitive),
            "metrics": {str(k): float(v) for k, v in dict(self.metrics).items()},
            "metadata": dict(self.metadata),
        }


class ProtocolEngine(ABC):
    """Abstract protocol engine contract."""

    engine_id = "engine"
    engine_version = "0.1"

    @abstractmethod
    def run_primitive(self, primitive: str, *, seed: int | None = None) -> ProtocolPrimitiveResult:
        """Execute a canonical primitive and return normalized metric values."""
        raise NotImplementedError

    @abstractmethod
    def supported_primitives(self) -> tuple[str, ...]:
        """Return primitives implemented by this engine."""
        raise NotImplementedError

    def availability(self) -> tuple[bool, str | None]:
        """Return whether the engine can execute in this environment."""
        return True, None

    def require_available(self) -> None:
        available, reason = self.availability()
        if not available:
            detail = reason or "dependency unavailable"
            raise ProtocolEngineUnavailableError(f"protocol engine {self.engine_id!r} unavailable: {detail}")

    def provenance(self) -> dict[str, Any]:
        return {
            "engine_id": str(self.engine_id),
            "engine_version": str(self.engine_version),
        }
