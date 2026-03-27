"""Backend type definitions and data containers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@runtime_checkable
class PhysicsBackend(Protocol):
    """Protocol every physics backend must satisfy."""

    @property
    def name(self) -> str: ...

    @property
    def tier(self) -> int: ...  # 0=analytic, 1=stochastic, 2=high-fidelity

    def simulate(
        self,
        component: str,
        inputs: dict,
        *,
        seed: int | None = None,
        mode: str = "preview",
    ) -> dict: ...

    def applicability(self, inputs: dict) -> dict: ...

    def provenance(self) -> dict: ...


@dataclass(frozen=True)
class BackendProvenance:
    """Immutable provenance record for a single backend run."""

    backend_name: str
    tier: int
    version: str
    seed: int | None
    config_hash: str
    timestamp: str

    def as_dict(self) -> dict:
        return {
            "backend_name": self.backend_name,
            "tier": self.tier,
            "version": self.version,
            "seed": self.seed,
            "config_hash": self.config_hash,
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True)
class ComparisonResult:
    """Immutable result of a cross-fidelity comparison run."""

    scenario_id: str
    backends_compared: list[str]
    results: dict  # backend_name -> output dict
    deltas: dict  # pairwise deltas
    consistency_verdict: str  # "consistent" | "divergent" | "inconclusive"
    max_relative_delta: float
    provenance: list[dict]

    def as_dict(self) -> dict:
        return {
            "scenario_id": self.scenario_id,
            "backends_compared": list(self.backends_compared),
            "results": dict(self.results),
            "deltas": dict(self.deltas),
            "consistency_verdict": self.consistency_verdict,
            "max_relative_delta": self.max_relative_delta,
            "provenance": list(self.provenance),
        }


@dataclass(frozen=True)
class MultifidelityEvidence:
    """Immutable multi-fidelity evidence artifact."""

    comparison: ComparisonResult
    tier_coverage: dict  # tier_num -> backend_name
    recommendation: str

    def as_dict(self) -> dict:
        return {
            "comparison": self.comparison.as_dict(),
            "tier_coverage": dict(self.tier_coverage),
            "recommendation": self.recommendation,
        }
