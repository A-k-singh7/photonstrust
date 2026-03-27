"""Maintenance schedule optimisation for QKD networks."""

from __future__ import annotations

import uuid

from photonstrust.maintenance.types import (
    FailurePrediction,
    MaintenanceAction,
    MaintenanceSchedule,
)

_URGENCY_PRIORITY = {"immediate": 0, "soon": 1, "planned": 2, "none": 3}

_COST_USD: dict[str, float] = {
    "detector": 50_000.0,
    "fiber": 10_000.0,
    "source": 80_000.0,
}
_DEFAULT_COST_USD = 20_000.0

_DOWNTIME_HOURS: dict[str, float] = {
    "detector": 8.0,
    "fiber": 24.0,
    "source": 12.0,
}
_DEFAULT_DOWNTIME_HOURS = 4.0


def optimize_maintenance_schedule(
    predictions: list[FailurePrediction],
    *,
    budget_usd: float = float("inf"),
    max_simultaneous_downtime: int = 1,
) -> MaintenanceSchedule:
    """Build a priority-based maintenance schedule from failure predictions."""
    # Sort by urgency priority (immediate first)
    sorted_preds = sorted(
        predictions,
        key=lambda p: _URGENCY_PRIORITY.get(p.urgency, 3),
    )

    actions: list[MaintenanceAction] = []
    cumulative_cost = 0.0
    total_downtime = 0.0

    for pred in sorted_preds:
        urgency_idx = _URGENCY_PRIORITY.get(pred.urgency, 3)
        # Infer component_type from failure_mode ("<type>_degradation")
        component_type = pred.failure_mode.replace("_degradation", "")

        cost = _COST_USD.get(component_type, _DEFAULT_COST_USD)
        downtime = _DOWNTIME_HOURS.get(component_type, _DEFAULT_DOWNTIME_HOURS)

        if cumulative_cost + cost > budget_usd:
            action_type = "deferred"
        elif pred.urgency in ("immediate", "soon"):
            action_type = "replace"
        else:
            action_type = "inspect"

        action = MaintenanceAction(
            action_id=str(uuid.uuid4()),
            component_id=pred.component_id,
            link_id=pred.link_id,
            action_type=action_type,
            scheduled_date_iso=pred.predicted_failure_date_iso,
            estimated_cost_usd=cost,
            estimated_downtime_hours=downtime,
            priority=urgency_idx + 1,
        )
        actions.append(action)

        if action_type != "deferred":
            cumulative_cost += cost
            total_downtime += downtime

    return MaintenanceSchedule(
        schedule_id=str(uuid.uuid4()),
        actions=actions,
        total_estimated_cost_usd=cumulative_cost,
        total_downtime_hours=total_downtime,
        optimization_strategy="priority_based",
    )
