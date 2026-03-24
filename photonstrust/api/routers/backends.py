"""Backend listing and cross-fidelity comparison routes."""

from __future__ import annotations

from fastapi import APIRouter

from photonstrust.backends.comparison import run_cross_fidelity_comparison
from photonstrust.backends.registry import list_backends

router = APIRouter(prefix="/v1/backends", tags=["backends"])


@router.get("")
def list_backends_endpoint() -> dict:
    """Return all registered physics backends."""
    return {"backends": list_backends()}


@router.post("/compare")
def compare_backends_endpoint(payload: dict) -> dict:
    """Run a cross-fidelity comparison and return the result."""
    result = run_cross_fidelity_comparison(
        scenario=payload.get("scenario", {}),
        backends=payload.get("backends"),
        seed=payload.get("seed"),
        tolerance_rel=float(payload.get("tolerance_rel", 0.10)),
    )
    return result.as_dict()
