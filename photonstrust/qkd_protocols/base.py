"""Protocol module contract for QKD dispatch."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional

from photonstrust.qkd_types import QKDResult


_APPLICABILITY_STATUSES = {"pass", "warn", "fail"}


@dataclass(frozen=True)
class ProtocolApplicability:
    status: str
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        status = str(self.status).strip().lower()
        if status not in _APPLICABILITY_STATUSES:
            raise ValueError(f"Unsupported applicability status: {self.status!r}")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "reasons", tuple(str(v) for v in self.reasons))

    def as_dict(self) -> dict[str, Any]:
        return {"status": self.status, "reasons": list(self.reasons)}


ProtocolEvaluator = Callable[[dict, float, Optional[dict]], QKDResult]
ProtocolApplicabilityFn = Callable[[dict], ProtocolApplicability]


@dataclass(frozen=True)
class QKDProtocolModule:
    protocol_id: str
    evaluator: ProtocolEvaluator
    applicability_fn: ProtocolApplicabilityFn
    aliases: tuple[str, ...] = ()
    gate_policy: Mapping[str, Any] | None = None

    def evaluate_point(
        self,
        scenario: dict,
        distance_km: float,
        runtime_overrides: dict | None = None,
    ) -> QKDResult:
        return self.evaluator(scenario, float(distance_km), runtime_overrides)

    def applicability(self, scenario: dict) -> ProtocolApplicability:
        return self.applicability_fn(scenario)
