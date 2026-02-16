"""Shared interfaces for physics backend implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Mapping


_APPLICABILITY_STATUSES = {"pass", "warn", "fail"}


@dataclass(frozen=True)
class ApplicabilityReport:
    status: str
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        status = str(self.status).strip().lower()
        if status not in _APPLICABILITY_STATUSES:
            raise ValueError(f"Unsupported applicability status: {self.status!r}")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "reasons", tuple(str(v) for v in self.reasons))

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class BackendProvenance:
    backend_name: str
    backend_version: str
    seed: int | None = None
    details: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "backend_name": str(self.backend_name),
            "backend_version": str(self.backend_version),
            "seed": int(self.seed) if self.seed is not None else None,
        }
        payload.update(dict(self.details))
        return payload


class PhysicsBackend(ABC):
    backend_name = "backend"
    backend_version = "0.1"

    @abstractmethod
    def simulate(
        self,
        component: str,
        inputs: Mapping[str, Any],
        *,
        seed: int | None = None,
        mode: str | None = None,
    ) -> Any:
        raise NotImplementedError

    @abstractmethod
    def applicability(self, component: str, inputs: Mapping[str, Any]) -> ApplicabilityReport:
        raise NotImplementedError

    def provenance(self, *, seed: int | None = None, details: Mapping[str, Any] | None = None) -> BackendProvenance:
        return BackendProvenance(
            backend_name=self.backend_name,
            backend_version=self.backend_version,
            seed=int(seed) if seed is not None else None,
            details=dict(details or {}),
        )


def normalize_component_name(component: str) -> str:
    return str(component or "").strip().lower()
