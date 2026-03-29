"""Satellite channel realism routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException

from photonstrust.satellite.extinction import get_atmosphere_profiles
from photonstrust.satellite.pass_budget import compute_pass_key_budget

router = APIRouter(prefix="/v1/satellite", tags=["satellite"])


@router.post("/simulate-pass")
def simulate_pass_endpoint(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """Compute cumulative key budget for a satellite pass."""
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Expected JSON object")

    time_steps = payload.get("time_steps")
    key_rates = payload.get("key_rates")
    dt_s = payload.get("dt_s")

    if not isinstance(time_steps, list) or not isinstance(key_rates, list):
        raise HTTPException(
            status_code=400,
            detail="time_steps and key_rates must be lists",
        )
    if not isinstance(dt_s, (int, float)):
        raise HTTPException(status_code=400, detail="dt_s must be a number")

    result = compute_pass_key_budget(
        time_steps_s=[float(t) for t in time_steps],
        key_rates_bps=[float(r) for r in key_rates],
        dt_s=float(dt_s),
    )
    return result.as_dict()


@router.get("/atmosphere-profiles")
def get_atmosphere_profiles_endpoint() -> dict[str, Any]:
    """Return all standard atmosphere extinction profiles."""
    return {"profiles": get_atmosphere_profiles()}
