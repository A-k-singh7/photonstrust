"""Executive analytics report generation."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from photonstrust.analytics.benchmark import benchmark_vendors
from photonstrust.analytics.kpis import compute_link_kpis, compute_network_kpis
from photonstrust.analytics.roi import compute_roi
from photonstrust.analytics.types import AnalyticsReport, KPISnapshot


def generate_analytics_report(
    *,
    entity_type: str = "network",
    entity_id: str = "default",
    sim_result: dict | None = None,
    cost_result: dict | None = None,
    components: list[dict] | None = None,
    roi_params: dict | None = None,
) -> AnalyticsReport:
    """Generate a comprehensive analytics report.

    Parameters
    ----------
    entity_type:
        ``"link"`` or ``"network"``.
    entity_id:
        Identifier of the entity being analysed.
    sim_result:
        Simulation output dict.
    cost_result:
        Cost-model output dict.
    components:
        List of component dicts for vendor benchmarking.
    roi_params:
        Dict with ROI computation parameters (``deployment_id``,
        ``total_investment_usd``, ``annual_key_rate_bps``, and optional
        overrides).
    """
    now = datetime.now(timezone.utc).isoformat()

    # ---- KPIs ----
    kpis = []
    if sim_result is not None and cost_result is not None:
        if entity_type == "link":
            kpis = compute_link_kpis(entity_id, sim_result, cost_result)
        else:
            kpis = compute_network_kpis(sim_result, cost_result)

    snapshot = KPISnapshot(
        timestamp_iso=now,
        entity_type=entity_type,
        entity_id=entity_id,
        kpis=kpis,
    )

    # ---- Vendor benchmarks ----
    benchmarks_dicts: list[dict] = []
    if components:
        benchmarks = benchmark_vendors(components)
        benchmarks_dicts = [b.as_dict() for b in benchmarks]

    # ---- ROI ----
    roi_dict: dict | None = None
    if roi_params is not None:
        roi = compute_roi(
            deployment_id=roi_params.get("deployment_id", entity_id),
            total_investment_usd=float(roi_params.get("total_investment_usd", 0)),
            annual_key_rate_bps=float(roi_params.get("annual_key_rate_bps", 0)),
            key_value_per_bit_usd=float(roi_params.get("key_value_per_bit_usd", 1e-6)),
            annual_opex_usd=float(roi_params.get("annual_opex_usd", 0)),
            discount_rate=float(roi_params.get("discount_rate", 0.08)),
            projection_years=int(roi_params.get("projection_years", 10)),
        )
        roi_dict = roi.as_dict()

    # ---- Recommendations ----
    recommendations: list[str] = []
    for kpi in kpis:
        if kpi.status == "below_target":
            recommendations.append(
                f"KPI '{kpi.name}' is below target ({kpi.value} vs {kpi.target}). "
                f"Consider optimising this metric."
            )
        elif kpi.status == "above_target":
            recommendations.append(
                f"KPI '{kpi.name}' exceeds acceptable threshold "
                f"({kpi.value} vs {kpi.target}). Investigate mitigation options."
            )

    return AnalyticsReport(
        report_id=str(uuid.uuid4()),
        generated_at_iso=now,
        kpi_snapshot=snapshot.as_dict(),
        vendor_benchmarks=benchmarks_dicts,
        roi_analysis=roi_dict,
        recommendations=recommendations,
    )
