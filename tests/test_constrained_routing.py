"""Tests for photonstrust.network.constrained_routing."""

from __future__ import annotations

import math

import pytest

from photonstrust.network.constrained_routing import (
    fidelity_constrained_path,
    k_disjoint_paths,
    rate_constrained_path,
)


# ---------------------------------------------------------------------------
# rate_constrained_path
# ---------------------------------------------------------------------------


def test_rate_constrained_finds_widest_path():
    """Prefer path with higher bottleneck rate (widest path)."""
    nodes = ["A", "B", "C"]
    edges = [
        {"from": "A", "to": "B", "rate_bps": 100.0},   # direct but narrow
        {"from": "A", "to": "C", "rate_bps": 500.0},
        {"from": "C", "to": "B", "rate_bps": 500.0},
    ]
    result = rate_constrained_path(nodes, edges, "A", "B")
    assert result is not None
    # Widest path is A->C->B (bottleneck 500) vs A->B (100)
    assert result.bottleneck_rate_bps == pytest.approx(500.0)
    assert result.nodes == ["A", "C", "B"]


def test_rate_filter_excludes_low_links():
    """With min_rate_bps > some edge rate, that path is excluded."""
    nodes = ["A", "B", "C"]
    edges = [
        {"from": "A", "to": "B", "rate_bps": 50.0},
        {"from": "A", "to": "C", "rate_bps": 200.0},
        {"from": "C", "to": "B", "rate_bps": 200.0},
    ]
    result = rate_constrained_path(nodes, edges, "A", "B", min_rate_bps=100.0)
    assert result is not None
    # Direct A->B (50) is filtered out; must route via C
    assert result.nodes == ["A", "C", "B"]
    assert result.bottleneck_rate_bps == pytest.approx(200.0)


# ---------------------------------------------------------------------------
# fidelity_constrained_path
# ---------------------------------------------------------------------------


def test_fidelity_constraint_rejects_low_fidelity():
    """Path with product fidelity < min_fidelity returns None."""
    nodes = ["A", "B", "C"]
    edges = [
        {"from": "A", "to": "C", "fidelity": 0.7, "rate_bps": 100.0},
        {"from": "C", "to": "B", "fidelity": 0.7, "rate_bps": 100.0},
    ]
    # Product fidelity = 0.7 * 0.7 = 0.49 < 0.5
    result = fidelity_constrained_path(
        nodes, edges, "A", "B", min_fidelity=0.5,
    )
    assert result is None


def test_fidelity_path_prefers_high_fidelity():
    """Shorter log-cost path (higher product fidelity) is chosen."""
    nodes = ["A", "B", "C", "D"]
    edges = [
        {"from": "A", "to": "B", "fidelity": 0.99, "rate_bps": 100.0},
        {"from": "A", "to": "C", "fidelity": 0.99, "rate_bps": 100.0},
        {"from": "C", "to": "D", "fidelity": 0.99, "rate_bps": 100.0},
        {"from": "D", "to": "B", "fidelity": 0.99, "rate_bps": 100.0},
    ]
    result = fidelity_constrained_path(
        nodes, edges, "A", "B", min_fidelity=0.5,
    )
    assert result is not None
    # Direct A->B (1 hop, fidelity 0.99) beats A->C->D->B (3 hops)
    assert result.nodes == ["A", "B"]
    product_fidelity = math.exp(-result.total_metric)
    assert product_fidelity >= 0.5 - 1e-9


# ---------------------------------------------------------------------------
# k_disjoint_paths
# ---------------------------------------------------------------------------


def test_k_disjoint_paths_edge_disjoint():
    """Two paths in a diamond graph share no edges."""
    nodes = ["A", "C", "D", "B"]
    edges = [
        {"from": "A", "to": "C", "rate_bps": 100.0},
        {"from": "C", "to": "B", "rate_bps": 100.0},
        {"from": "A", "to": "D", "rate_bps": 200.0},
        {"from": "D", "to": "B", "rate_bps": 200.0},
    ]
    paths = k_disjoint_paths(nodes, edges, "A", "B", k=2)
    assert len(paths) == 2
    # Collect edges from both paths (both directions) and verify disjoint
    edges_0 = set(paths[0].edges) | {(b, a) for a, b in paths[0].edges}
    edges_1 = set(paths[1].edges) | {(b, a) for a, b in paths[1].edges}
    assert edges_0.isdisjoint(edges_1)


def test_k_disjoint_returns_fewer_if_not_available():
    """k=3 but only 2 disjoint paths exist; returns fewer."""
    nodes = ["A", "B", "C", "D"]
    edges = [
        {"from": "A", "to": "C", "rate_bps": 100.0},
        {"from": "C", "to": "D", "rate_bps": 100.0},
        {"from": "A", "to": "B", "rate_bps": 100.0},
        {"from": "B", "to": "D", "rate_bps": 100.0},
    ]
    paths = k_disjoint_paths(nodes, edges, "A", "D", k=3)
    assert len(paths) == 2  # only 2 disjoint paths in this graph


def test_no_path_returns_none():
    """Disconnected source and sink returns None."""
    nodes = ["A", "B", "C"]
    edges = [{"from": "A", "to": "B", "rate_bps": 100.0}]
    result = rate_constrained_path(nodes, edges, "A", "C")
    assert result is None
