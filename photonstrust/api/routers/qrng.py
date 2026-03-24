"""API routes for QRNG simulation."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/v1/qrng", tags=["qrng"])


@router.post("/simulate")
def simulate_qrng_endpoint(payload: dict) -> dict:
    """Run a QRNG simulation."""
    from photonstrust.qrng.simulator import simulate_qrng

    try:
        result = simulate_qrng(
            source_type=payload.get("source_type", "vacuum_fluctuation"),
            source_params=payload.get("source_params"),
            conditioning_method=payload.get("conditioning_method", "toeplitz"),
            n_samples=int(payload.get("n_samples", 10000)),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return {"status": "ok", "result": result.as_dict()}


@router.post("/entropy")
def estimate_entropy_endpoint(payload: dict) -> dict:
    """Estimate entropy of provided samples."""
    import numpy as np

    from photonstrust.qrng.entropy import estimate_min_entropy

    try:
        samples = np.array(payload["samples"], dtype=int)
        entropy = estimate_min_entropy(samples)
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return {"status": "ok", "entropy": entropy.as_dict()}


@router.get("/sources")
def list_sources() -> dict:
    """List available QRNG source types."""
    return {"sources": ["vacuum_fluctuation", "photon_arrival", "beam_splitter"]}
