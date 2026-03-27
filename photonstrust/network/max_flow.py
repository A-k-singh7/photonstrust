"""Max-flow and multi-commodity flow algorithms for QKD network optimisation.

Provides Edmonds-Karp max-flow to compute the maximum aggregate key rate
between two nodes using parallel paths, and a sequential multi-commodity
flow solver for networks with multiple concurrent key-distribution demands.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field


@dataclass(frozen=True)
class MaxFlowResult:
    """Result of a single-commodity max-flow computation."""

    max_rate_bps: float
    flow_paths: list[dict]  # [{"path": [...], "flow": float}, ...]
    min_cut_edges: list[tuple[str, str]]


def _bfs_augmenting_path(
    adj: dict[str, dict[str, float]],
    source: str,
    sink: str,
    parent: dict[str, str],
) -> bool:
    """BFS to find an augmenting path in the residual graph."""
    visited = {source}
    queue: deque[str] = deque([source])
    while queue:
        u = queue.popleft()
        for v in adj[u]:
            if v not in visited and adj[u][v] > 1e-15:
                visited.add(v)
                parent[v] = u
                if v == sink:
                    return True
                queue.append(v)
    return False


def max_flow_key_rate(
    nodes: list[str],
    edges: list[dict],  # [{"from", "to", "rate_bps"}, ...]
    source: str,
    sink: str,
) -> MaxFlowResult:
    """Edmonds-Karp max-flow algorithm for QKD network key distribution.

    Edges are bidirectional with capacity equal to the link key rate (bps).
    Returns the maximum aggregate key rate achievable using parallel paths.
    """
    # Build adjacency (residual graph)
    adj: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for e in edges:
        u, v, cap = e["from"], e["to"], float(e["rate_bps"])
        adj[u][v] += cap
        adj[v][u] += cap  # bidirectional

    total_flow = 0.0
    flow_paths: list[dict] = []

    while True:
        parent: dict[str, str] = {}
        if not _bfs_augmenting_path(adj, source, sink, parent):
            break
        # Find bottleneck
        path_flow = float("inf")
        v = sink
        path_nodes = [sink]
        while v != source:
            u = parent[v]
            path_flow = min(path_flow, adj[u][v])
            path_nodes.append(u)
            v = u
        path_nodes.reverse()

        # Update residual capacities
        v = sink
        while v != source:
            u = parent[v]
            adj[u][v] -= path_flow
            adj[v][u] += path_flow
            v = u

        total_flow += path_flow
        flow_paths.append({"path": path_nodes, "flow": path_flow})

    # Find min-cut: nodes reachable from source in the residual graph
    visited: set[str] = set()
    queue: deque[str] = deque([source])
    visited.add(source)
    while queue:
        u = queue.popleft()
        for v in adj[u]:
            if v not in visited and adj[u][v] > 1e-15:
                visited.add(v)
                queue.append(v)

    min_cut: list[tuple[str, str]] = []
    for e in edges:
        u, v = e["from"], e["to"]
        if (u in visited and v not in visited) or (
            v in visited and u not in visited
        ):
            min_cut.append((u, v))

    return MaxFlowResult(
        max_rate_bps=total_flow,
        flow_paths=flow_paths,
        min_cut_edges=min_cut,
    )


# ---------------------------------------------------------------------------
# Multi-commodity flow
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MCFResult:
    """Result of a multi-commodity flow computation."""

    total_throughput_bps: float
    demand_satisfaction: dict[str, float]  # demand_id -> fraction satisfied
    edge_utilization: dict[str, float]  # "u->v" -> utilisation fraction


def multi_commodity_flow(
    nodes: list[str],
    edges: list[dict],  # [{"from", "to", "rate_bps"}, ...]
    demands: list[dict],  # [{"id", "source", "sink", "demand_bps"}, ...]
) -> MCFResult:
    """Multi-commodity flow via sequential max-flow decomposition.

    Processes demands in order, allocating residual capacity with
    Edmonds-Karp for each demand.  Maximises total satisfied demand
    subject to edge capacity constraints.
    """
    n_demands = len(demands)
    n_edges = len(edges)

    if n_demands == 0 or n_edges == 0:
        return MCFResult(
            total_throughput_bps=0.0,
            demand_satisfaction={d["id"]: 0.0 for d in demands},
            edge_utilization={f'{e["from"]}->{e["to"]}': 0.0 for e in edges},
        )

    # Build shared residual capacity
    residual: dict[tuple[str, str], float] = {}
    for e in edges:
        key_fwd = (e["from"], e["to"])
        key_rev = (e["to"], e["from"])
        cap = float(e["rate_bps"])
        residual[key_fwd] = residual.get(key_fwd, 0.0) + cap
        residual[key_rev] = residual.get(key_rev, 0.0) + cap

    demand_satisfaction: dict[str, float] = {}
    total_throughput = 0.0

    for d in demands:
        # Build residual adjacency for this round
        adj_res: dict[str, dict[str, float]] = defaultdict(
            lambda: defaultdict(float)
        )
        for (u, v), cap in residual.items():
            if cap > 1e-15:
                adj_res[u][v] = cap

        flow = 0.0
        while True:
            parent: dict[str, str] = {}
            if not _bfs_augmenting_path(adj_res, d["source"], d["sink"], parent):
                break
            pf = float("inf")
            v = d["sink"]
            while v != d["source"]:
                u = parent[v]
                pf = min(pf, adj_res[u][v])
                v = u

            remaining = float(d["demand_bps"]) - flow
            pf = min(pf, remaining)
            if pf <= 1e-15:
                break

            v = d["sink"]
            while v != d["source"]:
                u = parent[v]
                adj_res[u][v] -= pf
                adj_res[v][u] += pf
                residual[(u, v)] = adj_res[u][v]
                residual[(v, u)] = adj_res[v][u]
                v = u

            flow += pf
            if flow >= float(d["demand_bps"]) - 1e-15:
                break

        demand_bps = float(d["demand_bps"])
        frac = flow / demand_bps if demand_bps > 0 else 0.0
        demand_satisfaction[d["id"]] = min(frac, 1.0)
        total_throughput += flow

    # Compute edge utilisation
    edge_utilization: dict[str, float] = {}
    for e in edges:
        cap = float(e["rate_bps"])
        key_fwd = (e["from"], e["to"])
        key_rev = (e["to"], e["from"])
        original_cap = cap * 2  # bidirectional
        remaining = residual.get(key_fwd, 0.0) + residual.get(key_rev, 0.0)
        used = max(0.0, original_cap - remaining)
        utilization = used / original_cap if original_cap > 0 else 0.0
        edge_utilization[f'{e["from"]}->{e["to"]}'] = min(utilization, 1.0)

    return MCFResult(
        total_throughput_bps=total_throughput,
        demand_satisfaction=demand_satisfaction,
        edge_utilization=edge_utilization,
    )
