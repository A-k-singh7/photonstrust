"""Redundancy and resilience analysis for QKD network topologies."""

from __future__ import annotations

from photonstrust.planner.types import RedundancyAnalysis


def _bfs_connected(adj: dict[str, list[str]], start: str, excluded: set[str]) -> set[str]:
    """Return all nodes reachable from *start* without traversing *excluded*."""
    visited = {start}
    queue = [start]
    while queue:
        node = queue.pop(0)
        for neighbor in adj.get(node, []):
            if neighbor not in visited and neighbor not in excluded:
                visited.add(neighbor)
                queue.append(neighbor)
    return visited


def _build_adjacency(links: list[dict]) -> dict[str, list[str]]:
    """Build an undirected adjacency list from a list of link dicts."""
    adj: dict[str, list[str]] = {}
    for link in links:
        a = link["source"]
        b = link["target"]
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
    return adj


def analyze_redundancy(
    topology_dict: dict,
    *,
    link_results: dict | None = None,
) -> RedundancyAnalysis:
    """Analyse a topology for single points of failure and resilience.

    Parameters
    ----------
    topology_dict:
        Must contain ``"nodes"`` (list of dicts with at least ``"node_id"``)
        and ``"links"`` (list of dicts with ``"source"`` / ``"target"``).
    link_results:
        Optional per-link metrics (unused in the simplified analysis).

    Returns
    -------
    RedundancyAnalysis
    """
    nodes_list: list[dict] = topology_dict.get("nodes", [])
    links_list: list[dict] = topology_dict.get("links", [])

    all_node_ids = [n["node_id"] for n in nodes_list]
    endpoint_ids = [
        n["node_id"]
        for n in nodes_list
        if n.get("node_type") == "endpoint"
    ] or list(all_node_ids)

    adj = _build_adjacency(links_list)

    # ---- single points of failure (nodes) ----
    spofs: list[str] = []

    for node_id in all_node_ids:
        remaining_endpoints = [e for e in endpoint_ids if e != node_id]
        if len(remaining_endpoints) < 2:
            continue
        reachable = _bfs_connected(adj, remaining_endpoints[0], {node_id})
        if not all(ep in reachable for ep in remaining_endpoints[1:]):
            spofs.append(node_id)

    # ---- single points of failure (links) ----
    for link in links_list:
        a, b = link["source"], link["target"]
        # Build adjacency without this link
        reduced: dict[str, list[str]] = {}
        for lk in links_list:
            if lk is link:
                continue
            sa, sb = lk["source"], lk["target"]
            reduced.setdefault(sa, []).append(sb)
            reduced.setdefault(sb, []).append(sa)
        if len(endpoint_ids) >= 2:
            reachable = _bfs_connected(reduced, endpoint_ids[0], set())
            if not all(ep in reachable for ep in endpoint_ids[1:]):
                link_label = f"link:{a}-{b}"
                spofs.append(link_label)

    # ---- disjoint path pairs (simplified) ----
    disjoint_pairs = 0
    for i in range(len(endpoint_ids)):
        for j in range(i + 1, len(endpoint_ids)):
            # Count as a disjoint pair if still connected after removing each link
            pair_ok = True
            for link in links_list:
                reduced_adj: dict[str, list[str]] = {}
                for lk in links_list:
                    if lk is link:
                        continue
                    sa, sb = lk["source"], lk["target"]
                    reduced_adj.setdefault(sa, []).append(sb)
                    reduced_adj.setdefault(sb, []).append(sa)
                reachable = _bfs_connected(reduced_adj, endpoint_ids[i], set())
                if endpoint_ids[j] not in reachable:
                    pair_ok = False
                    break
            if pair_ok and len(links_list) > 0:
                disjoint_pairs += 1

    # ---- vertex connectivity (simplified) ----
    node_spofs = [s for s in spofs if not s.startswith("link:")]
    min_vertex_connectivity = 2 if len(node_spofs) == 0 else 1

    # ---- resilience score ----
    total = max(1, len(all_node_ids) + len(links_list))
    resilience_score = round(1.0 - len(spofs) / total, 4)

    # ---- recommendations ----
    recommendations: list[str] = []
    for s in spofs:
        if s.startswith("link:"):
            recommendations.append(f"Add redundant path for {s}")
        else:
            recommendations.append(f"Add bypass for single-point-of-failure node {s}")

    topology_id = topology_dict.get("topology_id", "topo_0")

    return RedundancyAnalysis(
        topology_id=topology_id,
        single_points_of_failure=spofs,
        resilience_score=resilience_score,
        disjoint_path_pairs=disjoint_pairs,
        min_vertex_connectivity=min_vertex_connectivity,
        recommendations=recommendations,
    )
