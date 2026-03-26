"""Constrained routing algorithms for QKD networks.

Provides rate-constrained widest-path routing, fidelity-constrained
shortest-path routing (via log-transform of link fidelities), and
edge-disjoint multi-path computation for resilient key distribution.
"""

from __future__ import annotations

import heapq
import math
from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass(frozen=True)
class ConstrainedPath:
    """A path satisfying one or more QoS constraints."""

    nodes: list[str]
    edges: list[tuple[str, str]]
    total_metric: float  # e.g. total -log(fidelity) or hop count
    bottleneck_rate_bps: float


def rate_constrained_path(
    nodes: list[str],
    edges: list[dict],  # [{"from", "to", "rate_bps", ...}]
    source: str,
    sink: str,
    min_rate_bps: float = 0.0,
) -> ConstrainedPath | None:
    """Modified Dijkstra: skip links with rate < *min_rate_bps*.

    Optimises for the maximum bottleneck rate (widest path).
    """
    # Build adjacency, filtering edges below the rate threshold
    adj: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for e in edges:
        rate = float(e["rate_bps"])
        if rate >= min_rate_bps:
            adj[e["from"]].append((e["to"], rate))
            adj[e["to"]].append((e["from"], rate))

    # Widest path via modified Dijkstra (max-heap using negation)
    best: dict[str, float] = {source: float("inf")}
    parent: dict[str, str] = {}
    heap: list[tuple[float, str]] = [(-float("inf"), source)]

    while heap:
        neg_bw, u = heapq.heappop(heap)
        bw = -neg_bw
        if bw < best.get(u, 0.0):
            continue
        if u == sink:
            break
        for v, rate in adj[u]:
            new_bw = min(bw, rate)
            if new_bw > best.get(v, 0.0):
                best[v] = new_bw
                parent[v] = u
                heapq.heappush(heap, (-new_bw, v))

    if sink not in parent and source != sink:
        return None

    path_nodes: list[str] = []
    v = sink
    while v != source:
        path_nodes.append(v)
        v = parent[v]
    path_nodes.append(source)
    path_nodes.reverse()

    path_edges = [
        (path_nodes[i], path_nodes[i + 1]) for i in range(len(path_nodes) - 1)
    ]

    return ConstrainedPath(
        nodes=path_nodes,
        edges=path_edges,
        total_metric=float(len(path_edges)),
        bottleneck_rate_bps=best.get(sink, 0.0),
    )


def fidelity_constrained_path(
    nodes: list[str],
    edges: list[dict],  # [{"from", "to", "fidelity", ...}]
    source: str,
    sink: str,
    min_fidelity: float = 0.5,
) -> ConstrainedPath | None:
    """Shortest path with a product-fidelity constraint (log-transform).

    The product fidelity along a path equals ``prod(F_ij)`` and must satisfy
    ``prod(F_ij) >= min_fidelity``.  By taking ``-log(F_ij)`` as edge
    weights the problem reduces to a shortest-path problem with an upper
    bound on total cost.
    """
    max_cost = -math.log(max(min_fidelity, 1e-15))

    adj: dict[str, list[tuple[str, float, float]]] = defaultdict(list)
    for e in edges:
        f = float(e["fidelity"])
        if f > 0:
            cost = -math.log(f)
            adj[e["from"]].append((e["to"], cost, f))
            adj[e["to"]].append((e["from"], cost, f))

    dist: dict[str, float] = {source: 0.0}
    parent: dict[str, str] = {}
    heap: list[tuple[float, str]] = [(0.0, source)]

    while heap:
        d, u = heapq.heappop(heap)
        if d > dist.get(u, float("inf")):
            continue
        if u == sink:
            break
        for v, cost, _ in adj[u]:
            nd = d + cost
            if nd <= max_cost and nd < dist.get(v, float("inf")):
                dist[v] = nd
                parent[v] = u
                heapq.heappush(heap, (nd, v))

    if sink not in parent and source != sink:
        return None

    path_nodes: list[str] = []
    v = sink
    while v != source:
        path_nodes.append(v)
        v = parent[v]
    path_nodes.append(source)
    path_nodes.reverse()

    path_edges = [
        (path_nodes[i], path_nodes[i + 1]) for i in range(len(path_nodes) - 1)
    ]
    total_log_fidelity = dist.get(sink, 0.0)

    # Compute bottleneck rate from edges along the path
    edge_set = set(path_edges)
    rates: list[float] = []
    for e in edges:
        if (e["from"], e["to"]) in edge_set or (e["to"], e["from"]) in edge_set:
            rates.append(float(e.get("rate_bps", 0.0)))

    return ConstrainedPath(
        nodes=path_nodes,
        edges=path_edges,
        total_metric=total_log_fidelity,
        bottleneck_rate_bps=min(rates) if rates else 0.0,
    )


def k_disjoint_paths(
    nodes: list[str],
    edges: list[dict],
    source: str,
    sink: str,
    k: int = 2,
) -> list[ConstrainedPath]:
    """Find up to *k* edge-disjoint paths via iterative BFS + edge removal."""
    results: list[ConstrainedPath] = []
    used_edges: set[tuple[str, str]] = set()

    for _ in range(k):
        adj: dict[str, list[tuple[str, float]]] = defaultdict(list)
        for e in edges:
            key = (e["from"], e["to"])
            rev_key = (e["to"], e["from"])
            if key not in used_edges and rev_key not in used_edges:
                rate = float(e.get("rate_bps", 0.0))
                adj[e["from"]].append((e["to"], rate))
                adj[e["to"]].append((e["from"], rate))

        # BFS shortest path
        visited = {source}
        parent: dict[str, str] = {}
        queue: deque[str] = deque([source])
        found = False
        while queue:
            u = queue.popleft()
            if u == sink:
                found = True
                break
            for v, _ in adj[u]:
                if v not in visited:
                    visited.add(v)
                    parent[v] = u
                    queue.append(v)

        if not found:
            break

        path_nodes: list[str] = []
        v = sink
        while v != source:
            path_nodes.append(v)
            v = parent[v]
        path_nodes.append(source)
        path_nodes.reverse()

        path_edges = [
            (path_nodes[i], path_nodes[i + 1])
            for i in range(len(path_nodes) - 1)
        ]

        # Mark edges as used (both directions)
        for pe in path_edges:
            used_edges.add(pe)
            used_edges.add((pe[1], pe[0]))

        # Find bottleneck rate
        path_edge_set = set(path_edges)
        min_rate = float("inf")
        for e in edges:
            if (e["from"], e["to"]) in path_edge_set or (
                e["to"], e["from"]
            ) in path_edge_set:
                min_rate = min(min_rate, float(e.get("rate_bps", 0.0)))
        if min_rate == float("inf"):
            min_rate = 0.0

        results.append(
            ConstrainedPath(
                nodes=path_nodes,
                edges=path_edges,
                total_metric=float(len(path_edges)),
                bottleneck_rate_bps=min_rate,
            )
        )

    return results
