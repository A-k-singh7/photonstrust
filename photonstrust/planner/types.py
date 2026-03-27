"""Data types for the deployment planner and capacity optimizer."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PlannerConstraints:
    """Constraints governing a deployment plan."""

    max_link_distance_km: float = 200.0
    min_key_rate_bps: float = 100.0
    max_budget_usd: float = float("inf")
    required_redundancy: int = 1
    fiber_ownership: str = "dark"
    detector_class: str = "snspd"
    protocol_name: str = "BB84_DECOY"
    tco_horizon_years: int = 10

    def as_dict(self) -> dict:
        return {
            "max_link_distance_km": self.max_link_distance_km,
            "min_key_rate_bps": self.min_key_rate_bps,
            "max_budget_usd": self.max_budget_usd,
            "required_redundancy": self.required_redundancy,
            "fiber_ownership": self.fiber_ownership,
            "detector_class": self.detector_class,
            "protocol_name": self.protocol_name,
            "tco_horizon_years": self.tco_horizon_years,
        }


@dataclass(frozen=True)
class NodePlacement:
    """A single node placement recommendation."""

    node_id: str
    location: tuple[float, float]
    node_type: str
    score: float

    def as_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "location": list(self.location),
            "node_type": self.node_type,
            "score": self.score,
        }


@dataclass(frozen=True)
class CapacityForecast:
    """Capacity forecast for a single link over multiple years."""

    link_id: str
    current_key_rate_bps: float
    forecast_key_rate_bps: list[float] = field(default_factory=list)
    forecast_years: list[int] = field(default_factory=list)
    bottleneck_component: str = ""
    upgrade_recommendation: str = ""

    def as_dict(self) -> dict:
        return {
            "link_id": self.link_id,
            "current_key_rate_bps": self.current_key_rate_bps,
            "forecast_key_rate_bps": list(self.forecast_key_rate_bps),
            "forecast_years": list(self.forecast_years),
            "bottleneck_component": self.bottleneck_component,
            "upgrade_recommendation": self.upgrade_recommendation,
        }


@dataclass(frozen=True)
class RedundancyAnalysis:
    """Redundancy and resilience analysis for a network topology."""

    topology_id: str
    single_points_of_failure: list[str] = field(default_factory=list)
    resilience_score: float = 0.0
    disjoint_path_pairs: int = 0
    min_vertex_connectivity: int = 0
    recommendations: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "topology_id": self.topology_id,
            "single_points_of_failure": list(self.single_points_of_failure),
            "resilience_score": self.resilience_score,
            "disjoint_path_pairs": self.disjoint_path_pairs,
            "min_vertex_connectivity": self.min_vertex_connectivity,
            "recommendations": list(self.recommendations),
        }


@dataclass(frozen=True)
class DeploymentPlan:
    """Complete deployment plan output."""

    plan_id: str
    node_placements: list[NodePlacement] = field(default_factory=list)
    topology: dict = field(default_factory=dict)
    cost_estimate: dict = field(default_factory=dict)
    capacity_forecasts: list[CapacityForecast] = field(default_factory=list)
    redundancy: RedundancyAnalysis = field(
        default_factory=lambda: RedundancyAnalysis(topology_id="unknown"),
    )
    constraints: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    score: float = 0.0

    def as_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "node_placements": [n.as_dict() for n in self.node_placements],
            "topology": dict(self.topology),
            "cost_estimate": dict(self.cost_estimate),
            "capacity_forecasts": [c.as_dict() for c in self.capacity_forecasts],
            "redundancy": self.redundancy.as_dict(),
            "constraints": dict(self.constraints),
            "warnings": list(self.warnings),
            "score": self.score,
        }
