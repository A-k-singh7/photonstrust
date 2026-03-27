"""API routes for predictive maintenance engine."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/v1/maintenance", tags=["maintenance"])


@router.post("/predict")
def predict_failures_endpoint(payload: dict) -> dict:
    """Predict component failures for a QKD link."""
    from photonstrust.maintenance.predictor import predict_failures

    try:
        predictions = predict_failures(
            link_id=payload["link_id"],
            components=payload["components"],
            prediction_horizon_days=int(
                payload.get("prediction_horizon_days", 365)
            ),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return {
        "status": "ok",
        "predictions": [p.as_dict() for p in predictions],
    }


@router.post("/schedule")
def optimize_schedule(payload: dict) -> dict:
    """Build an optimised maintenance schedule from failure predictions."""
    from photonstrust.maintenance.predictor import predict_failures
    from photonstrust.maintenance.scheduler import optimize_maintenance_schedule
    from photonstrust.maintenance.types import FailurePrediction

    try:
        # Accept either raw predictions or components to predict first
        if "predictions" in payload:
            preds = [
                FailurePrediction(**p) for p in payload["predictions"]
            ]
        else:
            preds = predict_failures(
                link_id=payload["link_id"],
                components=payload["components"],
                prediction_horizon_days=int(
                    payload.get("prediction_horizon_days", 365)
                ),
            )

        schedule = optimize_maintenance_schedule(
            preds,
            budget_usd=float(payload.get("budget_usd", float("inf"))),
            max_simultaneous_downtime=int(
                payload.get("max_simultaneous_downtime", 1)
            ),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return {"status": "ok", "schedule": schedule.as_dict()}


@router.post("/degradation")
def compute_degradation(payload: dict) -> dict:
    """Compute current degradation state for a component."""
    from photonstrust.maintenance.degradation import estimate_component_health

    try:
        health = estimate_component_health(
            component_type=payload["component_type"],
            initial_value=float(payload["initial_value"]),
            age_hours=float(payload["age_hours"]),
            threshold=float(payload["threshold"]),
            detector_class=payload.get("detector_class", "snspd"),
            source_type=payload.get("source_type", "emitter_cavity"),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return {"status": "ok", "health": health.as_dict()}
