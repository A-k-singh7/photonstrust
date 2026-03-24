"""CAPEX/OPEX cost model implementations."""

from __future__ import annotations

import json
from pathlib import Path

from photonstrust.cost.types import (
    EquipmentCost,
    InfrastructureCost,
    LinkCostResult,
    NetworkCostResult,
    OperationalCost,
)

DEFAULT_EQUIPMENT_COSTS: dict[str, dict] = {
    "snspd_system": {"unit_cost_usd": 150_000, "category": "detector"},
    "ingaas_apd_system": {"unit_cost_usd": 20_000, "category": "detector"},
    "si_apd_system": {"unit_cost_usd": 5_000, "category": "detector"},
    "qkd_tx_bb84": {"unit_cost_usd": 80_000, "category": "source"},
    "qkd_tx_entangled": {"unit_cost_usd": 200_000, "category": "source"},
    "timing_electronics": {"unit_cost_usd": 15_000, "category": "electronics"},
    "classical_channel": {"unit_cost_usd": 5_000, "category": "electronics"},
    "trusted_node_enclosure": {"unit_cost_usd": 25_000, "category": "electronics"},
}

DEFAULT_INFRASTRUCTURE_COSTS: dict[str, dict] = {
    "dark_fiber_per_km": {"cost_per_km_usd": 5_000, "category": "fiber"},
    "leased_fiber_annual_per_km": {"cost_per_km_usd": 2_000, "category": "fiber"},
    "node_site_prep": {"fixed_cost_usd": 50_000, "category": "housing"},
}

DEFAULT_OPEX_COSTS: dict[str, dict] = {
    "maintenance_per_link_annual": {"annual_cost_usd": 10_000, "category": "maintenance"},
    "power_per_kw_annual": {"annual_cost_per_kw_usd": 1_000, "category": "power"},
    "cooling_per_snspd_annual": {"annual_cost_usd": 8_000, "category": "cooling"},
}

_DETECTOR_EQUIPMENT_MAP = {
    "snspd": "snspd_system",
    "ingaas": "ingaas_apd_system",
    "si_apd": "si_apd_system",
}

_SOURCE_EQUIPMENT_MAP = {
    "emitter_cavity": "qkd_tx_entangled",
    "spdc": "qkd_tx_entangled",
    "bb84_decoy": "qkd_tx_bb84",
    "bb84": "qkd_tx_bb84",
}


def cost_per_key_bit(
    total_cost_usd: float,
    key_rate_bps: float,
    operational_hours_per_year: float = 8760.0,
    years: int = 10,
) -> float:
    """Compute cost per secret key bit delivered."""
    total_bits = key_rate_bps * operational_hours_per_year * 3600.0 * years
    if total_bits <= 0:
        return float("inf")
    return total_cost_usd / total_bits


def compute_link_cost(
    *,
    distance_km: float,
    detector_class: str = "snspd",
    source_type: str = "emitter_cavity",
    protocol_name: str = "BBM92",
    key_rate_bps: float = 0.0,
    tco_horizon_years: int = 10,
    equipment_costs: dict | None = None,
    infrastructure_costs: dict | None = None,
    opex_costs: dict | None = None,
    fiber_ownership: str = "dark",
    link_id: str = "default_link",
) -> LinkCostResult:
    """Compute cost model for a single QKD link."""
    eq_costs = {**DEFAULT_EQUIPMENT_COSTS, **(equipment_costs or {})}
    infra_costs = {**DEFAULT_INFRASTRUCTURE_COSTS, **(infrastructure_costs or {})}
    op_costs = {**DEFAULT_OPEX_COSTS, **(opex_costs or {})}

    capex_equipment: list[EquipmentCost] = []
    capex_infra: list[InfrastructureCost] = []
    opex_annual: list[OperationalCost] = []

    det_key = _DETECTOR_EQUIPMENT_MAP.get(detector_class, "snspd_system")
    det_info = eq_costs.get(det_key, eq_costs["snspd_system"])
    det_unit = float(det_info.get("unit_cost_usd", det_info.get("cost_per_km_usd", 0)))
    capex_equipment.append(EquipmentCost(
        item_id=det_key, category="detector",
        unit_cost_usd=det_unit, quantity=2,
        total_cost_usd=det_unit * 2,
        notes="One detector per endpoint",
    ))

    src_key = _SOURCE_EQUIPMENT_MAP.get(source_type, "qkd_tx_entangled")
    proto_upper = protocol_name.upper().replace("-", "_")
    if "BB84" in proto_upper:
        src_key = "qkd_tx_bb84"
    src_info = eq_costs.get(src_key, eq_costs.get("qkd_tx_entangled", {}))
    src_unit = float(src_info.get("unit_cost_usd", 80_000))
    capex_equipment.append(EquipmentCost(
        item_id=src_key, category="source",
        unit_cost_usd=src_unit, quantity=1,
        total_cost_usd=src_unit,
    ))

    timing_info = eq_costs.get("timing_electronics", {})
    timing_unit = float(timing_info.get("unit_cost_usd", 15_000))
    capex_equipment.append(EquipmentCost(
        item_id="timing_electronics", category="electronics",
        unit_cost_usd=timing_unit, quantity=2,
        total_cost_usd=timing_unit * 2,
    ))

    classical_info = eq_costs.get("classical_channel", {})
    classical_unit = float(classical_info.get("unit_cost_usd", 5_000))
    capex_equipment.append(EquipmentCost(
        item_id="classical_channel", category="electronics",
        unit_cost_usd=classical_unit, quantity=1,
        total_cost_usd=classical_unit,
    ))

    if fiber_ownership == "dark":
        fiber_info = infra_costs.get("dark_fiber_per_km", {})
        fiber_per_km = float(fiber_info.get("cost_per_km_usd", 5_000))
        capex_infra.append(InfrastructureCost(
            item_id="dark_fiber", category="fiber",
            cost_per_km_usd=fiber_per_km, distance_km=distance_km,
            total_cost_usd=fiber_per_km * distance_km,
        ))
    else:
        lease_info = infra_costs.get("leased_fiber_annual_per_km", {})
        lease_per_km = float(lease_info.get("cost_per_km_usd", 2_000))
        opex_annual.append(OperationalCost(
            item_id="fiber_lease", category="fiber",
            annual_cost_usd=lease_per_km * distance_km,
            notes=f"Leased fiber at ${lease_per_km}/km/year",
        ))

    site_info = infra_costs.get("node_site_prep", {})
    site_cost = float(site_info.get("fixed_cost_usd", 50_000))
    capex_infra.append(InfrastructureCost(
        item_id="site_prep", category="housing",
        cost_per_km_usd=0, distance_km=0,
        total_cost_usd=site_cost * 2,
        notes="Site preparation at both endpoints",
    ))

    maint_info = op_costs.get("maintenance_per_link_annual", {})
    opex_annual.append(OperationalCost(
        item_id="maintenance", category="maintenance",
        annual_cost_usd=float(maint_info.get("annual_cost_usd", 10_000)),
    ))

    if detector_class == "snspd":
        cool_info = op_costs.get("cooling_per_snspd_annual", {})
        opex_annual.append(OperationalCost(
            item_id="snspd_cooling", category="cooling",
            annual_cost_usd=float(cool_info.get("annual_cost_usd", 8_000)) * 2,
            notes="Cooling for 2 SNSPD systems",
        ))

    total_capex = (
        sum(e.total_cost_usd for e in capex_equipment)
        + sum(i.total_cost_usd for i in capex_infra)
    )
    total_opex = sum(o.annual_cost_usd for o in opex_annual)
    tco = total_capex + total_opex * tco_horizon_years
    cpkb = cost_per_key_bit(tco, key_rate_bps, years=tco_horizon_years)

    return LinkCostResult(
        link_id=link_id,
        capex_equipment=capex_equipment,
        capex_infrastructure=capex_infra,
        opex_annual=opex_annual,
        total_capex_usd=total_capex,
        total_annual_opex_usd=total_opex,
        key_rate_bps=key_rate_bps,
        cost_per_key_bit_usd=cpkb,
        tco_usd=tco,
        tco_horizon_years=tco_horizon_years,
    )


def compute_network_cost(
    *,
    network_sim_result: dict,
    tco_horizon_years: int = 10,
    cost_overrides: dict | None = None,
) -> NetworkCostResult:
    """Aggregate cost model across a network topology."""
    overrides = cost_overrides or {}
    link_results = network_sim_result.get("link_results", {})
    topology = network_sim_result.get("topology", {})

    link_costs: list[LinkCostResult] = []
    for link_data in topology.get("links", []):
        lid = link_data.get("link_id", link_data.get("id", "unknown"))
        dist = float(link_data.get("distance_km", 0))
        lr = link_results.get(lid, {})
        kr = float(lr.get("key_rate_bps", 0))

        lc = compute_link_cost(
            distance_km=dist,
            key_rate_bps=kr,
            tco_horizon_years=tco_horizon_years,
            equipment_costs=overrides.get("equipment_overrides"),
            infrastructure_costs=overrides.get("infrastructure_overrides"),
            opex_costs=overrides.get("opex_overrides"),
            fiber_ownership=overrides.get("fiber_ownership", "dark"),
            link_id=lid,
        )
        link_costs.append(lc)

    total_capex = sum(l.total_capex_usd for l in link_costs)
    total_opex = sum(l.total_annual_opex_usd for l in link_costs)
    total_tco = total_capex + total_opex * tco_horizon_years

    all_rates = [l.key_rate_bps for l in link_costs if l.key_rate_bps > 0]
    avg_rate = sum(all_rates) / len(all_rates) if all_rates else 0.0
    avg_cpkb = cost_per_key_bit(total_tco, avg_rate, years=tco_horizon_years) if avg_rate > 0 else float("inf")

    return NetworkCostResult(
        links=link_costs,
        total_capex_usd=total_capex,
        total_annual_opex_usd=total_opex,
        total_tco_usd=total_tco,
        tco_horizon_years=tco_horizon_years,
        cost_per_key_bit_network_avg_usd=avg_cpkb,
        summary={
            "total_links": len(link_costs),
            "total_fiber_km": sum(
                sum(i.distance_km for i in l.capex_infrastructure) for l in link_costs
            ),
        },
    )
