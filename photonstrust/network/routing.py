"""Network-level routing algorithms for QKD networks."""

from __future__ import annotations

import heapq
from collections import defaultdict

from photonstrust.network.types import NetworkPath, NetworkTopology


def shortest_path(topology: NetworkTopology, src: str, dst: str) -> list[str]:
    """Dijkstra shortest path by physical distance (km)."""
    if src == dst:
        return [src]

    dist: dict[str, float] = defaultdict(lambda: float("inf"))
    dist[src] = 0.0
    prev: dict[str, str | None] = {src: None}
    heap = [(0.0, src)]

    while heap:
        d, u = heapq.heappop(heap)
        if u == dst:
            break
        if d > dist[u]:
            continue
        for v in topology.neighbors(u):
            link = topology.get_link_between(u, v)
            if link is None:
                continue
            alt = d + link.distance_km
            if alt < dist[v]:
                dist[v] = alt
                prev[v] = u
                heapq.heappush(heap, (alt, v))

    if dst not in prev:
        return []

    path: list[str] = []
    node: str | None = dst
    while node is not None:
        path.append(node)
        node = prev.get(node)
    return list(reversed(path))


def max_key_rate_path(
    topology: NetworkTopology,
    link_results: dict[str, dict],
    src: str,
    dst: str,
) -> list[str]:
    """Path that maximizes the bottleneck (min-link) key rate.

    Uses a modified Dijkstra where the "distance" is the negative of the
    minimum key rate along the path so far, maximizing the worst link.
    """
    if src == dst:
        return [src]

    best_bottleneck: dict[str, float] = defaultdict(lambda: -1.0)
    best_bottleneck[src] = float("inf")
    prev: dict[str, str | None] = {src: None}
    heap = [(-float("inf"), src)]

    while heap:
        neg_bn, u = heapq.heappop(heap)
        bn = -neg_bn
        if u == dst:
            break
        if bn < best_bottleneck[u]:
            continue
        for v in topology.neighbors(u):
            link = topology.get_link_between(u, v)
            if link is None:
                continue
            lr = link_results.get(link.link_id, {})
            kr = float(lr.get("key_rate_bps", 0.0))
            new_bn = min(bn, kr)
            if new_bn > best_bottleneck[v]:
                best_bottleneck[v] = new_bn
                prev[v] = u
                heapq.heappush(heap, (-new_bn, v))

    if dst not in prev:
        return []

    path: list[str] = []
    node: str | None = dst
    while node is not None:
        path.append(node)
        node = prev.get(node)
    return list(reversed(path))


def all_paths(
    topology: NetworkTopology,
    src: str,
    dst: str,
    max_hops: int = 10,
) -> list[list[str]]:
    """Enumerate all simple paths up to *max_hops* length via DFS."""
    results: list[list[str]] = []

    def _dfs(current: str, target: str, visited: set[str], path: list[str]) -> None:
        if len(path) > max_hops + 1:
            return
        if current == target:
            results.append(list(path))
            return
        for neighbor in topology.neighbors(current):
            if neighbor not in visited:
                visited.add(neighbor)
                path.append(neighbor)
                _dfs(neighbor, target, visited, path)
                path.pop()
                visited.discard(neighbor)

    _dfs(src, dst, {src}, [src])
    return results


def _path_to_network_path(
    path_nodes: list[str],
    topology: NetworkTopology,
    link_results: dict[str, dict],
    path_id: str = "",
) -> NetworkPath:
    """Convert a node list into a NetworkPath with metrics."""
    links: list[str] = []
    total_dist = 0.0
    min_kr = float("inf")
    bottleneck_id = ""

    for i in range(len(path_nodes) - 1):
        link = topology.get_link_between(path_nodes[i], path_nodes[i + 1])
        if link is None:
            continue
        links.append(link.link_id)
        total_dist += link.distance_km
        lr = link_results.get(link.link_id, {})
        kr = float(lr.get("key_rate_bps", 0.0))
        if kr < min_kr:
            min_kr = kr
            bottleneck_id = link.link_id

    if min_kr == float("inf"):
        min_kr = 0.0

    trusted = sum(
        1
        for nid in path_nodes[1:-1]
        if topology.nodes.get(nid, None) is not None
        and topology.nodes[nid].node_type == "trusted_node"
    )

    return NetworkPath(
        path_id=path_id or f"{path_nodes[0]}_to_{path_nodes[-1]}",
        nodes=tuple(path_nodes),
        links=tuple(links),
        total_distance_km=total_dist,
        trusted_node_count=trusted,
        end_to_end_key_rate_bps=min_kr,
        bottleneck_link_key_rate_bps=min_kr,
        bottleneck_link_id=bottleneck_id,
    )


def compute_routing_table(
    topology: NetworkTopology,
    link_results: dict[str, dict],
    strategy: str = "max_key_rate",
) -> dict[str, NetworkPath]:
    """Compute best path for all endpoint pairs.

    Returns a dict keyed by ``"src->dst"`` with :class:`NetworkPath` values.
    """
    endpoints = topology.endpoint_ids()
    table: dict[str, NetworkPath] = {}

    for i, src in enumerate(endpoints):
        for dst in endpoints[i + 1:]:
            if strategy == "max_key_rate":
                path_nodes = max_key_rate_path(topology, link_results, src, dst)
            else:
                path_nodes = shortest_path(topology, src, dst)

            if not path_nodes:
                continue

            np = _path_to_network_path(path_nodes, topology, link_results)
            table[f"{src}->{dst}"] = np
            rev_nodes = list(reversed(path_nodes))
            table[f"{dst}->{src}"] = _path_to_network_path(
                rev_nodes, topology, link_results, path_id=f"{dst}_to_{src}"
            )

    return table
