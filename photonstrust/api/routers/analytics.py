"""Analytics & executive reporting API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from photonstrust.analytics.benchmark import benchmark_vendors
from photonstrust.analytics.kpis import compute_link_kpis, compute_network_kpis
from photonstrust.analytics.report import generate_analytics_report
from photonstrust.analytics.roi import compute_roi

router = APIRouter(prefix="/v1/analytics", tags=["analytics"])


@router.post("/kpis")
def compute_kpis_endpoint(payload: dict) -> dict:
    """Compute KPIs for a link or network."""
    try:
        entity_type = payload.get("entity_type", "link")
        if entity_type == "link":
            kpis = compute_link_kpis(
                link_id=payload.get("link_id", "default"),
                sim_result=payload.get("sim_result", {}),
                cost_result=payload.get("cost_result", {}),
                targets=payload.get("targets"),
            )
        else:
            kpis = compute_network_kpis(
                network_sim_result=payload.get("sim_result", {}),
                network_cost_result=payload.get("cost_result", {}),
            )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"kpis": [k.as_dict() for k in kpis]}


@router.post("/benchmark")
def benchmark_endpoint(payload: dict) -> dict:
    """Benchmark vendors for a component category."""
    try:
        benchmarks = benchmark_vendors(
            components=payload.get("components", []),
            category=payload.get("category", "detector"),
            scenario_defaults=payload.get("scenario_defaults"),
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"benchmarks": [b.as_dict() for b in benchmarks]}


@router.post("/roi")
def roi_endpoint(payload: dict) -> dict:
    """Compute ROI analysis."""
    try:
        result = compute_roi(
            deployment_id=payload.get("deployment_id", "default"),
            total_investment_usd=float(payload.get("total_investment_usd", 0)),
            annual_key_rate_bps=float(payload.get("annual_key_rate_bps", 0)),
            key_value_per_bit_usd=float(payload.get("key_value_per_bit_usd", 1e-6)),
            annual_opex_usd=float(payload.get("annual_opex_usd", 0)),
            discount_rate=float(payload.get("discount_rate", 0.08)),
            projection_years=int(payload.get("projection_years", 10)),
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return result.as_dict()


@router.post("/report")
def generate_report(payload: dict) -> dict:
    """Generate a full analytics report."""
    try:
        report = generate_analytics_report(
            entity_type=payload.get("entity_type", "network"),
            entity_id=payload.get("entity_id", "default"),
            sim_result=payload.get("sim_result"),
            cost_result=payload.get("cost_result"),
            components=payload.get("components"),
            roi_params=payload.get("roi_params"),
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return report.as_dict()
