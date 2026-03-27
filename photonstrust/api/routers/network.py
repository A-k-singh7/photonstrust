"""Network topology simulation API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/v1/network", tags=["network"])


@router.post("/simulate")
def simulate_network_endpoint(payload: dict) -> dict:
    """Run network-scale QKD simulation."""
    from photonstrust.network.simulator import simulate_network_from_config

    try:
        result = simulate_network_from_config(payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return result.as_dict()


@router.post("/route")
def compute_route(payload: dict) -> dict:
    """Compute optimal route between two endpoints."""
    from photonstrust.network.routing import max_key_rate_path, shortest_path
    from photonstrust.network.types import NetworkTopology

    topology_cfg = payload.get("topology", {})
    src = str(payload.get("src", ""))
    dst = str(payload.get("dst", ""))
    strategy = str(payload.get("strategy", "shortest"))

    if not src or not dst:
        raise HTTPException(status_code=422, detail="src and dst are required")

    topo = NetworkTopology.from_config(topology_cfg)

    if strategy == "max_key_rate":
        link_results = payload.get("link_results", {})
        path = max_key_rate_path(topo, link_results, src, dst)
    else:
        path = shortest_path(topo, src, dst)

    if not path:
        raise HTTPException(status_code=404, detail=f"No path from '{src}' to '{dst}'")

    return {"path": path, "strategy": strategy, "hop_count": len(path) - 1}


@router.get("/topologies")
def list_builtin_topologies() -> dict:
    """List available built-in topology templates."""
    return {
        "topologies": [
            {"id": "chain_3", "description": "3-node linear chain with trusted node"},
            {"id": "star_4", "description": "4-spoke star topology with central hub"},
            {"id": "ring_4", "description": "4-node ring topology"},
        ]
    }
