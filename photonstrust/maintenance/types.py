"""Data types for predictive maintenance engine."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DegradationModel:
    """Describes how a component type degrades over time."""

    component_type: str
    degradation_type: str  # "exponential" or "linear"
    rate_parameter: float
    unit: str  # "per_hour"

    def as_dict(self) -> dict:
        return {
            "component_type": self.component_type,
            "degradation_type": self.degradation_type,
            "rate_parameter": self.rate_parameter,
            "unit": self.unit,
        }


@dataclass(frozen=True)
class ComponentHealth:
    """Current health assessment for a single component."""

    component_id: str
    component_type: str
    current_performance: float  # 0.0-1.0
    age_hours: float
    predicted_eol_hours: float
    degradation_model: str

    def as_dict(self) -> dict:
        return {
            "component_id": self.component_id,
            "component_type": self.component_type,
            "current_performance": self.current_performance,
            "age_hours": self.age_hours,
            "predicted_eol_hours": self.predicted_eol_hours,
            "degradation_model": self.degradation_model,
        }


@dataclass(frozen=True)
class FailurePrediction:
    """Predicted failure event for a component on a link."""

    component_id: str
    link_id: str
    predicted_failure_date_iso: str
    confidence: float
    failure_mode: str
    impact_description: str
    urgency: str  # "immediate" / "soon" / "planned" / "none"

    def as_dict(self) -> dict:
        return {
            "component_id": self.component_id,
            "link_id": self.link_id,
            "predicted_failure_date_iso": self.predicted_failure_date_iso,
            "confidence": self.confidence,
            "failure_mode": self.failure_mode,
            "impact_description": self.impact_description,
            "urgency": self.urgency,
        }


@dataclass(frozen=True)
class MaintenanceAction:
    """A single maintenance action to perform."""

    action_id: str
    component_id: str
    link_id: str
    action_type: str  # "replace" / "recalibrate" / "inspect"
    scheduled_date_iso: str
    estimated_cost_usd: float
    estimated_downtime_hours: float
    priority: int

    def as_dict(self) -> dict:
        return {
            "action_id": self.action_id,
            "component_id": self.component_id,
            "link_id": self.link_id,
            "action_type": self.action_type,
            "scheduled_date_iso": self.scheduled_date_iso,
            "estimated_cost_usd": self.estimated_cost_usd,
            "estimated_downtime_hours": self.estimated_downtime_hours,
            "priority": self.priority,
        }


@dataclass(frozen=True)
class MaintenanceSchedule:
    """Optimised schedule of maintenance actions."""

    schedule_id: str
    actions: list[MaintenanceAction] = field(default_factory=list)
    total_estimated_cost_usd: float = 0.0
    total_downtime_hours: float = 0.0
    optimization_strategy: str = "priority_based"

    def as_dict(self) -> dict:
        return {
            "schedule_id": self.schedule_id,
            "actions": [a.as_dict() for a in self.actions],
            "total_estimated_cost_usd": self.total_estimated_cost_usd,
            "total_downtime_hours": self.total_downtime_hours,
            "optimization_strategy": self.optimization_strategy,
        }
