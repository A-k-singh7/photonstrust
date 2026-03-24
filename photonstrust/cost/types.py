"""Cost model data types."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EquipmentCost:
    """Single equipment line item."""

    item_id: str
    category: str
    unit_cost_usd: float
    quantity: int
    total_cost_usd: float
    vendor: str | None = None
    notes: str = ""

    def as_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "category": self.category,
            "unit_cost_usd": self.unit_cost_usd,
            "quantity": self.quantity,
            "total_cost_usd": self.total_cost_usd,
            "vendor": self.vendor,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class InfrastructureCost:
    """Infrastructure line item (e.g. fiber)."""

    item_id: str
    category: str
    cost_per_km_usd: float
    distance_km: float
    total_cost_usd: float
    notes: str = ""

    def as_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "category": self.category,
            "cost_per_km_usd": self.cost_per_km_usd,
            "distance_km": self.distance_km,
            "total_cost_usd": self.total_cost_usd,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class OperationalCost:
    """Annual operational cost line item."""

    item_id: str
    category: str
    annual_cost_usd: float
    notes: str = ""

    def as_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "category": self.category,
            "annual_cost_usd": self.annual_cost_usd,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class LinkCostResult:
    """Cost model result for a single QKD link."""

    link_id: str
    capex_equipment: list[EquipmentCost]
    capex_infrastructure: list[InfrastructureCost]
    opex_annual: list[OperationalCost]
    total_capex_usd: float
    total_annual_opex_usd: float
    key_rate_bps: float
    cost_per_key_bit_usd: float
    tco_usd: float
    tco_horizon_years: int

    def as_dict(self) -> dict:
        return {
            "link_id": self.link_id,
            "capex_equipment": [e.as_dict() for e in self.capex_equipment],
            "capex_infrastructure": [i.as_dict() for i in self.capex_infrastructure],
            "opex_annual": [o.as_dict() for o in self.opex_annual],
            "total_capex_usd": self.total_capex_usd,
            "total_annual_opex_usd": self.total_annual_opex_usd,
            "key_rate_bps": self.key_rate_bps,
            "cost_per_key_bit_usd": self.cost_per_key_bit_usd,
            "tco_usd": self.tco_usd,
            "tco_horizon_years": self.tco_horizon_years,
        }


@dataclass(frozen=True)
class NetworkCostResult:
    """Aggregated cost model for a QKD network."""

    links: list[LinkCostResult]
    total_capex_usd: float
    total_annual_opex_usd: float
    total_tco_usd: float
    tco_horizon_years: int
    cost_per_key_bit_network_avg_usd: float
    summary: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "links": [l.as_dict() for l in self.links],
            "total_capex_usd": self.total_capex_usd,
            "total_annual_opex_usd": self.total_annual_opex_usd,
            "total_tco_usd": self.total_tco_usd,
            "tco_horizon_years": self.tco_horizon_years,
            "cost_per_key_bit_network_avg_usd": self.cost_per_key_bit_network_avg_usd,
            "summary": self.summary,
        }
