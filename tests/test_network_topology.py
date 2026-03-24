"""Tests for network topology, routing, and simulation."""

from __future__ import annotations

import pytest

from photonstrust.network.routing import (
    all_paths,
    compute_routing_table,
    max_key_rate_path,
    shortest_path,
)
from photonstrust.network.trusted_node import trusted_node_key_rate, trusted_node_latency_s
from photonstrust.network.types import NetworkLink, NetworkNode, NetworkTopology


def _chain_topology() -> NetworkTopology:
    """A -> T1 -> B, distances 80 and 120 km."""
    topo = NetworkTopology()
    topo.add_node(NetworkNode("alice", "endpoint"))
    topo.add_node(NetworkNode("trusted_1", "trusted_node"))
    topo.add_node(NetworkNode("bob", "endpoint"))
    topo.add_link(NetworkLink("l1", "alice", "trusted_1", 80.0))
    topo.add_link(NetworkLink("l2", "trusted_1", "bob", 120.0))
    return topo


def _star_topology() -> NetworkTopology:
    """Hub with 3 spokes."""
    topo = NetworkTopology()
    topo.add_node(NetworkNode("hub", "trusted_node"))
    for name in ("a", "b", "c"):
        topo.add_node(NetworkNode(name, "endpoint"))
        topo.add_link(NetworkLink(f"l_{name}", "hub", name, 50.0))
    return topo


def _diamond_topology() -> NetworkTopology:
    """A -> M1, A -> M2, M1 -> B, M2 -> B with different distances."""
    topo = NetworkTopology()
    topo.add_node(NetworkNode("a", "endpoint"))
    topo.add_node(NetworkNode("m1", "trusted_node"))
    topo.add_node(NetworkNode("m2", "trusted_node"))
    topo.add_node(NetworkNode("b", "endpoint"))
    topo.add_link(NetworkLink("l1", "a", "m1", 50.0))
    topo.add_link(NetworkLink("l2", "a", "m2", 80.0))
    topo.add_link(NetworkLink("l3", "m1", "b", 60.0))
    topo.add_link(NetworkLink("l4", "m2", "b", 30.0))
    return topo


# --- Topology tests ---

def test_build_chain_topology():
    topo = _chain_topology()
    assert len(topo.nodes) == 3
    assert len(topo.links) == 2


def test_neighbors():
    topo = _chain_topology()
    assert "trusted_1" in topo.neighbors("alice")
    assert "alice" in topo.neighbors("trusted_1")
    assert "bob" in topo.neighbors("trusted_1")


def test_get_link_between():
    topo = _chain_topology()
    link = topo.get_link_between("alice", "trusted_1")
    assert link is not None
    assert link.distance_km == 80.0
    assert topo.get_link_between("alice", "bob") is None


def test_endpoint_ids():
    topo = _chain_topology()
    eps = topo.endpoint_ids()
    assert "alice" in eps
    assert "bob" in eps
    assert "trusted_1" not in eps


def test_from_config():
    cfg = {
        "nodes": [
            {"id": "a", "type": "endpoint"},
            {"id": "b", "type": "endpoint"},
        ],
        "links": [
            {"id": "l1", "node_a": "a", "node_b": "b", "distance_km": 100},
        ],
    }
    topo = NetworkTopology.from_config(cfg)
    assert len(topo.nodes) == 2
    assert len(topo.links) == 1


# --- Routing tests ---

def test_shortest_path_chain():
    topo = _chain_topology()
    path = shortest_path(topo, "alice", "bob")
    assert path == ["alice", "trusted_1", "bob"]


def test_shortest_path_same_node():
    topo = _chain_topology()
    assert shortest_path(topo, "alice", "alice") == ["alice"]


def test_shortest_path_diamond_picks_shorter():
    topo = _diamond_topology()
    path = shortest_path(topo, "a", "b")
    total = sum(
        topo.get_link_between(path[i], path[i + 1]).distance_km
        for i in range(len(path) - 1)
    )
    assert total <= 110.0 + 1e-9


def test_max_key_rate_path():
    topo = _diamond_topology()
    link_results = {
        "l1": {"key_rate_bps": 5000},
        "l2": {"key_rate_bps": 8000},
        "l3": {"key_rate_bps": 3000},
        "l4": {"key_rate_bps": 9000},
    }
    path = max_key_rate_path(topo, link_results, "a", "b")
    # Path via m2 has bottleneck min(8000, 9000) = 8000
    # Path via m1 has bottleneck min(5000, 3000) = 3000
    assert "m2" in path


def test_all_paths_bounded():
    topo = _diamond_topology()
    paths = all_paths(topo, "a", "b", max_hops=10)
    assert len(paths) == 2
    paths_short = all_paths(topo, "a", "b", max_hops=1)
    assert len(paths_short) == 0


def test_routing_table_complete():
    topo = _star_topology()
    link_results = {f"l_{n}": {"key_rate_bps": 1000} for n in ("a", "b", "c")}
    table = compute_routing_table(topo, link_results)
    assert "a->b" in table
    assert "b->c" in table
    assert "a->c" in table


# --- Trusted node tests ---

def test_trusted_node_key_rate_bottleneck():
    results = [
        {"key_rate_bps": 5000},
        {"key_rate_bps": 3000},
        {"key_rate_bps": 8000},
    ]
    rate = trusted_node_key_rate(results)
    assert rate == 3000


def test_trusted_node_latency():
    results = [
        {"distance_km": 80},
        {"distance_km": 120},
    ]
    latency = trusted_node_latency_s(results)
    assert latency > 0
    assert latency == pytest.approx((80 + 120) * 5e-6 + 0.001)


# --- Legacy bridge test ---

def test_topology_dict_bridge():
    from photonstrust.events.topology import build_chain, topology_dict_to_network

    legacy = build_chain(["a", "b", "c"], {"model": "fiber"})
    nt = topology_dict_to_network(legacy)
    assert len(nt.nodes) == 3
    assert len(nt.links) == 2
    assert "b" in nt.neighbors("a")


# --- Network simulation test (lightweight, no real physics) ---

def test_network_sim_result_serialization():
    from photonstrust.network.types import NetworkSimResult

    result = NetworkSimResult(
        topology={"nodes": [], "links": []},
        paths=[],
        link_results={},
        routing_table={},
        aggregate_metrics={"total_links": 0},
    )
    d = result.as_dict()
    assert "topology" in d
    assert "aggregate_metrics" in d
