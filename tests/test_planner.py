"""Tests for the deployment planner and capacity optimizer module."""

from __future__ import annotations

import json

from photonstrust.planner.capacity import forecast_capacity
from photonstrust.planner.node_placement import _haversine_km, optimize_node_placement
from photonstrust.planner.planner import build_deployment_plan
from photonstrust.planner.redundancy import analyze_redundancy


# ---- 1. node placement inserts trusted nodes for long links ----

def test_node_placement_inserts_trusted_nodes():
    """Two endpoints 400 km apart with max_link_distance=200 must get at least 1 trusted node."""
    # ~400 km apart (roughly London to Paris-ish latitudes spread)
    endpoints = [
        ("A", (51.5, -0.1)),
        ("B", (48.0, 5.0)),
    ]
    placements = optimize_node_placement(endpoints, max_link_distance_km=200.0)
    trusted = [p for p in placements if p.node_type == "trusted"]
    assert len(trusted) >= 1, f"Expected at least 1 trusted node, got {len(trusted)}"


# ---- 2. short distance -> no trusted nodes ----

def test_node_placement_short_distance_no_insert():
    """Two endpoints only 50 km apart should need no trusted relay nodes."""
    endpoints = [
        ("A", (51.5, -0.1)),
        ("B", (51.5, 0.6)),
    ]
    placements = optimize_node_placement(endpoints, max_link_distance_km=200.0)
    trusted = [p for p in placements if p.node_type == "trusted"]
    assert len(trusted) == 0, f"Expected 0 trusted nodes, got {len(trusted)}"


# ---- 3. haversine known distance ----

def test_haversine_known_distance():
    """London to Paris is approximately 340-345 km."""
    dist = _haversine_km(51.5074, -0.1278, 48.8566, 2.3522)
    assert 340 <= dist <= 345, f"Expected 340-345 km, got {dist:.1f}"


# ---- 4. capacity forecast positive trend ----

def test_capacity_forecast_positive_trend():
    """With 5% tech improvement the year-5 rate should exceed the current rate."""
    fc = forecast_capacity(
        link_id="link_test",
        current_key_rate_bps=1000.0,
        distance_km=50.0,
        detector_class="snspd",
        forecast_years=10,
        technology_improvement_rate=0.05,
    )
    assert len(fc.forecast_years) == 10
    assert len(fc.forecast_key_rate_bps) == 10
    # Year 5 rate (index 4) should be higher than current
    assert fc.forecast_key_rate_bps[4] > fc.current_key_rate_bps


# ---- 5. chain topology has SPOF ----

def test_redundancy_chain_has_spof():
    """A linear chain A-B-C should have B as a single point of failure."""
    topo = {
        "topology_id": "chain",
        "nodes": [
            {"node_id": "A", "node_type": "endpoint"},
            {"node_id": "B", "node_type": "trusted"},
            {"node_id": "C", "node_type": "endpoint"},
        ],
        "links": [
            {"source": "A", "target": "B"},
            {"source": "B", "target": "C"},
        ],
    }
    result = analyze_redundancy(topo)
    assert "B" in result.single_points_of_failure
    assert result.resilience_score < 1.0


# ---- 6. ring topology has no node SPOF ----

def test_redundancy_ring_no_spof():
    """A ring A-B-C-A should have no node single points of failure."""
    topo = {
        "topology_id": "ring",
        "nodes": [
            {"node_id": "A", "node_type": "endpoint"},
            {"node_id": "B", "node_type": "endpoint"},
            {"node_id": "C", "node_type": "endpoint"},
        ],
        "links": [
            {"source": "A", "target": "B"},
            {"source": "B", "target": "C"},
            {"source": "C", "target": "A"},
        ],
    }
    result = analyze_redundancy(topo)
    node_spofs = [s for s in result.single_points_of_failure if not s.startswith("link:")]
    assert len(node_spofs) == 0, f"Expected no node SPOFs, got {node_spofs}"


# ---- 7. end-to-end deployment plan ----

def test_deployment_plan_end_to_end():
    """Three endpoints should produce a valid plan."""
    demand = [
        {"node_id": "HQ", "location": [40.7128, -74.0060]},
        {"node_id": "DC1", "location": [40.7580, -73.9855]},
        {"node_id": "DC2", "location": [40.6892, -74.0445]},
    ]
    plan = build_deployment_plan(demand)
    assert plan.plan_id.startswith("plan_")
    assert len(plan.node_placements) >= 3
    assert plan.topology.get("links")
    assert plan.cost_estimate.get("total_capex_usd", 0) > 0
    assert 0.0 <= plan.score <= 1.0


# ---- 8. serialization round-trip ----

def test_deployment_plan_serialization():
    """plan.as_dict() must produce a JSON-serialisable dict."""
    demand = [
        {"node_id": "N1", "location": [52.52, 13.405]},
        {"node_id": "N2", "location": [48.1351, 11.582]},
    ]
    plan = build_deployment_plan(demand)
    d = plan.as_dict()
    # Must not raise
    serialized = json.dumps(d)
    assert isinstance(serialized, str)
    assert "plan_id" in d
    assert "node_placements" in d


# ---- 9. budget constraint triggers warning ----

def test_plan_respects_budget_constraint():
    """A tiny budget should produce a warning about budget being exceeded."""
    demand = [
        {"node_id": "X", "location": [35.6762, 139.6503]},
        {"node_id": "Y", "location": [34.6937, 135.5023]},
    ]
    plan = build_deployment_plan(demand, constraints={"max_budget_usd": 100})
    budget_warnings = [w for w in plan.warnings if "Budget exceeded" in w]
    assert len(budget_warnings) >= 1, f"Expected budget warning, got {plan.warnings}"
