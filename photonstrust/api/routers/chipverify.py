from __future__ import annotations

from fastapi import APIRouter, HTTPException

from photonstrust.chipverify.orchestrator import run_chipverify

router = APIRouter(prefix="/v1/chipverify", tags=["chipverify"])


@router.post("/run")
def chipverify_run_endpoint(payload: dict) -> dict:
    try:
        result = run_chipverify(
            graph=payload.get("graph", payload),
            gates=payload.get("gates"),
            wavelength_nm=payload.get("wavelength_nm"),
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return result.as_dict()
