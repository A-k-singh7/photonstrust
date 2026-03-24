"""Tests for QKD deployment cost modeling."""

from __future__ import annotations

import math

import pytest

from photonstrust.cost.models import (
    compute_link_cost,
    compute_network_cost,
    cost_per_key_bit,
)


def test_cost_per_key_bit_positive():
    cpkb = cost_per_key_bit(total_cost_usd=1_000_000, key_rate_bps=10_000)
    assert cpkb > 0
    assert math.isfinite(cpkb)


def test_cost_per_key_bit_zero_rate():
    cpkb = cost_per_key_bit(total_cost_usd=1_000_000, key_rate_bps=0)
    assert cpkb == float("inf")


def test_link_cost_basic():
    result = compute_link_cost(
        distance_km=50,
        detector_class="snspd",
        key_rate_bps=10_000,
        tco_horizon_years=10,
    )
    assert result.total_capex_usd > 0
    assert result.total_annual_opex_usd > 0
    assert result.tco_usd > result.total_capex_usd
    assert result.tco_horizon_years == 10


def test_tco_increases_with_horizon():
    r5 = compute_link_cost(distance_km=50, key_rate_bps=10_000, tco_horizon_years=5)
    r10 = compute_link_cost(distance_km=50, key_rate_bps=10_000, tco_horizon_years=10)
    r20 = compute_link_cost(distance_km=50, key_rate_bps=10_000, tco_horizon_years=20)
    assert r5.tco_usd < r10.tco_usd < r20.tco_usd


def test_snspd_more_expensive_than_ingaas():
    snspd = compute_link_cost(distance_km=50, detector_class="snspd", key_rate_bps=1000)
    ingaas = compute_link_cost(distance_km=50, detector_class="ingaas", key_rate_bps=1000)
    assert snspd.total_capex_usd > ingaas.total_capex_usd


def test_leased_vs_dark_fiber():
    dark = compute_link_cost(distance_km=100, fiber_ownership="dark", key_rate_bps=1000)
    leased = compute_link_cost(distance_km=100, fiber_ownership="leased", key_rate_bps=1000)
    assert dark.total_capex_usd > leased.total_capex_usd
    assert leased.total_annual_opex_usd > dark.total_annual_opex_usd


def test_cost_overrides_applied():
    custom = {"snspd_system": {"unit_cost_usd": 50_000, "category": "detector"}}
    default_result = compute_link_cost(distance_km=50, detector_class="snspd", key_rate_bps=1000)
    custom_result = compute_link_cost(
        distance_km=50, detector_class="snspd", key_rate_bps=1000,
        equipment_costs=custom,
    )
    assert custom_result.total_capex_usd < default_result.total_capex_usd


def test_network_cost_aggregation():
    sim_result = {
        "topology": {
            "nodes": [
                {"node_id": "a"}, {"node_id": "t"}, {"node_id": "b"},
            ],
            "links": [
                {"link_id": "l1", "distance_km": 50},
                {"link_id": "l2", "distance_km": 80},
            ],
        },
        "link_results": {
            "l1": {"key_rate_bps": 5000},
            "l2": {"key_rate_bps": 3000},
        },
    }
    result = compute_network_cost(network_sim_result=sim_result, tco_horizon_years=10)
    assert len(result.links) == 2
    assert result.total_capex_usd == pytest.approx(
        sum(l.total_capex_usd for l in result.links)
    )
    assert result.total_tco_usd > result.total_capex_usd


def test_cost_result_serialization():
    result = compute_link_cost(distance_km=50, key_rate_bps=1000)
    d = result.as_dict()
    assert "link_id" in d
    assert "capex_equipment" in d
    assert "tco_usd" in d
    assert isinstance(d["capex_equipment"], list)


def test_network_cost_serialization():
    sim_result = {
        "topology": {
            "nodes": [],
            "links": [{"link_id": "l1", "distance_km": 50}],
        },
        "link_results": {"l1": {"key_rate_bps": 1000}},
    }
    result = compute_network_cost(network_sim_result=sim_result)
    d = result.as_dict()
    assert "total_tco_usd" in d
    assert "links" in d


def test_bb84_uses_cheaper_source():
    entangled = compute_link_cost(
        distance_km=50, protocol_name="BBM92", key_rate_bps=1000,
    )
    bb84 = compute_link_cost(
        distance_km=50, protocol_name="BB84_DECOY", key_rate_bps=1000,
    )
    assert bb84.total_capex_usd < entangled.total_capex_usd
