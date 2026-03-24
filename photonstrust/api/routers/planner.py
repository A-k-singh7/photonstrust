"""Deployment planner and capacity optimizer API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/v1/planner", tags=["planner"])


@router.post("/plan")
def create_deployment_plan(payload: dict) -> dict:
    """Build a full deployment plan from demand endpoints."""
    from photonstrust.planner.planner import build_deployment_plan

    try:
        plan = build_deployment_plan(
            demand_endpoints=payload["demand_endpoints"],
            constraints=payload.get("constraints"),
            scenario_defaults=payload.get("scenario_defaults"),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return {"status": "ok", "plan": plan.as_dict()}


@router.post("/placement")
def optimize_placement(payload: dict) -> dict:
    """Optimise node placements for a set of endpoints."""
    from photonstrust.planner.node_placement import optimize_node_placement

    try:
        endpoints = [
            (ep["node_id"], tuple(ep["location"]))
            for ep in payload["endpoints"]
        ]
        placements = optimize_node_placement(
            endpoints,
            max_link_distance_km=payload.get("max_link_distance_km", 200.0),
            max_trusted_nodes=payload.get("max_trusted_nodes", 20),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return {
        "status": "ok",
        "placements": [p.as_dict() for p in placements],
    }


@router.post("/capacity")
def forecast_capacity_endpoint(payload: dict) -> dict:
    """Forecast capacity for a single link."""
    from photonstrust.planner.capacity import forecast_capacity

    try:
        fc = forecast_capacity(
            link_id=payload["link_id"],
            current_key_rate_bps=float(payload["current_key_rate_bps"]),
            distance_km=float(payload["distance_km"]),
            detector_class=payload.get("detector_class", "snspd"),
            forecast_years=int(payload.get("forecast_years", 10)),
            technology_improvement_rate=float(
                payload.get("technology_improvement_rate", 0.05),
            ),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return {"status": "ok", "forecast": fc.as_dict()}


@router.post("/redundancy")
def analyze_redundancy_endpoint(payload: dict) -> dict:
    """Analyse redundancy for a given topology."""
    from photonstrust.planner.redundancy import analyze_redundancy

    try:
        result = analyze_redundancy(
            topology_dict=payload["topology"],
            link_results=payload.get("link_results"),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return {"status": "ok", "redundancy": result.as_dict()}
