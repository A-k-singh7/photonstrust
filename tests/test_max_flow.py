"""Tests for photonstrust.network.max_flow -- max-flow and multi-commodity flow."""

from __future__ import annotations

import pytest

from photonstrust.network.max_flow import max_flow_key_rate, multi_commodity_flow


# ---------------------------------------------------------------------------
# max_flow_key_rate
# ---------------------------------------------------------------------------


def test_simple_two_path_network():
    """Diamond graph A->B, A->C, B->D, C->D; max flow = sum of parallel paths."""
    nodes = ["A", "B", "C", "D"]
    edges = [
        {"from": "A", "to": "B", "rate_bps": 300.0},
        {"from": "A", "to": "C", "rate_bps": 200.0},
        {"from": "B", "to": "D", "rate_bps": 300.0},
        {"from": "C", "to": "D", "rate_bps": 200.0},
    ]
    result = max_flow_key_rate(nodes, edges, "A", "D")
    # Two disjoint paths: A->B->D (300) and A->C->D (200) => total 500
    assert result.max_rate_bps == pytest.approx(500.0)
    assert len(result.flow_paths) >= 2


def test_single_path_bottleneck():
    """Linear A->B->C: flow = min(cap_AB, cap_BC)."""
    nodes = ["A", "B", "C"]
    edges = [
        {"from": "A", "to": "B", "rate_bps": 1000.0},
        {"from": "B", "to": "C", "rate_bps": 400.0},
    ]
    result = max_flow_key_rate(nodes, edges, "A", "C")
    assert result.max_rate_bps == pytest.approx(400.0)


def test_max_flow_equals_min_cut():
    """Verify max_flow equals the sum of min_cut edge capacities."""
    nodes = ["S", "A", "B", "T"]
    edges = [
        {"from": "S", "to": "A", "rate_bps": 100.0},
        {"from": "S", "to": "B", "rate_bps": 200.0},
        {"from": "A", "to": "T", "rate_bps": 150.0},
        {"from": "B", "to": "T", "rate_bps": 100.0},
    ]
    result = max_flow_key_rate(nodes, edges, "S", "T")
    # Compute sum of capacities of min-cut edges
    edge_cap = {(e["from"], e["to"]): e["rate_bps"] for e in edges}
    min_cut_cap = sum(
        edge_cap.get(pair, edge_cap.get((pair[1], pair[0]), 0.0))
        for pair in result.min_cut_edges
    )
    assert result.max_rate_bps == pytest.approx(min_cut_cap)
    assert len(result.min_cut_edges) >= 1


def test_mcf_single_demand_matches_max_flow():
    """Single MCF demand should match plain max_flow result."""
    nodes = ["A", "B"]
    edges = [{"from": "A", "to": "B", "rate_bps": 1000.0}]

    mf = max_flow_key_rate(nodes, edges, "A", "B")

    demands = [{"id": "d1", "source": "A", "sink": "B", "demand_bps": 1000.0}]
    mcf = multi_commodity_flow(nodes, edges, demands)

    assert mcf.demand_satisfaction["d1"] == pytest.approx(1.0)
    assert mcf.total_throughput_bps == pytest.approx(mf.max_rate_bps)


def test_mcf_capacity_sharing():
    """Two demands share edges; total throughput does not exceed capacity."""
    nodes = ["A", "B"]
    edges = [{"from": "A", "to": "B", "rate_bps": 100.0}]
    demands = [
        {"id": "d1", "source": "A", "sink": "B", "demand_bps": 80.0},
        {"id": "d2", "source": "A", "sink": "B", "demand_bps": 80.0},
    ]
    result = multi_commodity_flow(nodes, edges, demands)
    satisfied_1 = result.demand_satisfaction["d1"] * 80.0
    satisfied_2 = result.demand_satisfaction["d2"] * 80.0
    # Total throughput cannot exceed bidirectional capacity
    assert result.total_throughput_bps <= 200.0 + 1e-9
    assert satisfied_1 + satisfied_2 == pytest.approx(result.total_throughput_bps)


def test_empty_network():
    """No edges yields zero flow."""
    nodes = ["A", "B"]
    edges: list[dict] = []
    result = max_flow_key_rate(nodes, edges, "A", "B")
    assert result.max_rate_bps == pytest.approx(0.0)
    assert result.flow_paths == []


def test_no_path():
    """Disconnected source and sink yields zero flow."""
    nodes = ["A", "B", "C"]
    edges = [{"from": "A", "to": "B", "rate_bps": 500.0}]
    result = max_flow_key_rate(nodes, edges, "A", "C")
    assert result.max_rate_bps == pytest.approx(0.0)
    assert result.flow_paths == []
