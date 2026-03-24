"""Analytics data types."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class KPI:
    """Single key performance indicator."""

    kpi_id: str
    name: str
    value: float
    unit: str
    target: float | None
    status: str  # "on_target" / "below_target" / "above_target"

    def as_dict(self) -> dict:
        return {
            "kpi_id": self.kpi_id,
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "target": self.target,
            "status": self.status,
        }


@dataclass(frozen=True)
class KPISnapshot:
    """Point-in-time snapshot of KPIs for an entity."""

    timestamp_iso: str
    entity_type: str
    entity_id: str
    kpis: list[KPI] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "timestamp_iso": self.timestamp_iso,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "kpis": [k.as_dict() for k in self.kpis],
        }


@dataclass(frozen=True)
class VendorBenchmark:
    """Benchmark comparison across vendors for a component category."""

    vendor: str
    component_category: str
    average_key_rate_bps: float
    average_cost_per_bit_usd: float
    reliability_score: float
    sample_size: int
    components_tested: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "vendor": self.vendor,
            "component_category": self.component_category,
            "average_key_rate_bps": self.average_key_rate_bps,
            "average_cost_per_bit_usd": self.average_cost_per_bit_usd,
            "reliability_score": self.reliability_score,
            "sample_size": self.sample_size,
            "components_tested": list(self.components_tested),
        }


@dataclass(frozen=True)
class ROIAnalysis:
    """Return-on-investment analysis for a QKD deployment."""

    deployment_id: str
    total_investment_usd: float
    annual_key_value_usd: float
    payback_period_years: float
    net_present_value_usd: float
    internal_rate_of_return: float
    assumptions: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "deployment_id": self.deployment_id,
            "total_investment_usd": self.total_investment_usd,
            "annual_key_value_usd": self.annual_key_value_usd,
            "payback_period_years": self.payback_period_years,
            "net_present_value_usd": self.net_present_value_usd,
            "internal_rate_of_return": self.internal_rate_of_return,
            "assumptions": dict(self.assumptions),
        }


@dataclass(frozen=True)
class AnalyticsReport:
    """Executive analytics report."""

    report_id: str
    generated_at_iso: str
    kpi_snapshot: dict = field(default_factory=dict)
    vendor_benchmarks: list[dict] = field(default_factory=list)
    roi_analysis: dict | None = None
    recommendations: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "report_id": self.report_id,
            "generated_at_iso": self.generated_at_iso,
            "kpi_snapshot": dict(self.kpi_snapshot),
            "vendor_benchmarks": list(self.vendor_benchmarks),
            "roi_analysis": self.roi_analysis,
            "recommendations": list(self.recommendations),
        }
