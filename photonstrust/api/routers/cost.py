"""Cost modeling API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from photonstrust.cost.models import compute_link_cost, compute_network_cost

router = APIRouter(prefix="/v1/cost", tags=["cost"])


@router.post("/link")
def cost_link_endpoint(payload: dict) -> dict:
    """Compute cost model for a single QKD link."""
    try:
        result = compute_link_cost(
            distance_km=float(payload.get("distance_km", 50)),
            detector_class=str(payload.get("detector_class", "snspd")),
            source_type=str(payload.get("source_type", "emitter_cavity")),
            protocol_name=str(payload.get("protocol_name", "BBM92")),
            key_rate_bps=float(payload.get("key_rate_bps", 0)),
            tco_horizon_years=int(payload.get("tco_horizon_years", 10)),
            fiber_ownership=str(payload.get("fiber_ownership", "dark")),
            link_id=str(payload.get("link_id", "default_link")),
            equipment_costs=payload.get("equipment_overrides"),
            infrastructure_costs=payload.get("infrastructure_overrides"),
            opex_costs=payload.get("opex_overrides"),
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return result.as_dict()


@router.post("/network")
def cost_network_endpoint(payload: dict) -> dict:
    """Compute cost model for a QKD network."""
    try:
        result = compute_network_cost(
            network_sim_result=payload.get("network_sim_result", payload),
            tco_horizon_years=int(payload.get("tco_horizon_years", 10)),
            cost_overrides=payload.get("cost_overrides"),
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return result.as_dict()


@router.get("/catalog")
def get_cost_catalog() -> dict:
    """Return the default cost catalog."""
    import json
    from pathlib import Path

    data_path = Path(__file__).parent.parent.parent / "cost" / "data" / "default_costs.json"
    if data_path.exists():
        return json.loads(data_path.read_text(encoding="utf-8"))
    from photonstrust.cost.models import (
        DEFAULT_EQUIPMENT_COSTS,
        DEFAULT_INFRASTRUCTURE_COSTS,
        DEFAULT_OPEX_COSTS,
    )
    return {
        "equipment": DEFAULT_EQUIPMENT_COSTS,
        "infrastructure": DEFAULT_INFRASTRUCTURE_COSTS,
        "opex": DEFAULT_OPEX_COSTS,
    }
