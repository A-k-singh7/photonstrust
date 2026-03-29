"""Failure prediction for QKD link components."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from photonstrust.maintenance.degradation import estimate_component_health
from photonstrust.maintenance.types import FailurePrediction


def predict_failures(
    link_id: str,
    components: list[dict],
    *,
    prediction_horizon_days: int = 365,
) -> list[FailurePrediction]:
    """Predict upcoming failures for a set of components on a link.

    Each component dict must contain:
      - component_id, component_type, initial_value, age_hours, threshold
    Optional keys: detector_class, source_type.
    """
    predictions: list[FailurePrediction] = []
    now = datetime.now(timezone.utc)

    for comp in components:
        component_id = comp["component_id"]
        component_type = comp["component_type"]
        initial_value = float(comp["initial_value"])
        age_hours = float(comp["age_hours"])
        threshold = float(comp["threshold"])
        detector_class = comp.get("detector_class", "snspd")
        source_type = comp.get("source_type", "emitter_cavity")

        health = estimate_component_health(
            component_type,
            initial_value,
            age_hours,
            threshold=threshold,
            detector_class=detector_class,
            source_type=source_type,
        )

        remaining_hours = health.predicted_eol_hours - age_hours
        remaining_days = remaining_hours / 24.0

        if remaining_days <= 0:
            urgency = "immediate"
            predicted_date = now
        elif remaining_days <= 30:
            urgency = "immediate"
            predicted_date = now + timedelta(days=remaining_days)
        elif remaining_days <= 90:
            urgency = "soon"
            predicted_date = now + timedelta(days=remaining_days)
        elif remaining_days <= prediction_horizon_days:
            urgency = "planned"
            predicted_date = now + timedelta(days=remaining_days)
        else:
            # Component is healthy enough -- no prediction needed
            continue

        failure_mode = f"{component_type}_degradation"
        impact_description = f"{component_type} performance below threshold"
        confidence = 0.9 if remaining_days < 90 else 0.7

        predictions.append(
            FailurePrediction(
                component_id=component_id,
                link_id=link_id,
                predicted_failure_date_iso=predicted_date.isoformat(),
                confidence=confidence,
                failure_mode=failure_mode,
                impact_description=impact_description,
                urgency=urgency,
            )
        )

    return predictions
