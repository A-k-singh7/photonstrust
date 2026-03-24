"""Node placement optimization for QKD network deployment."""

from __future__ import annotations

import math

from photonstrust.planner.types import NodePlacement


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine great-circle distance in km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def optimize_node_placement(
    endpoints: list[tuple[str, tuple[float, float]]],
    *,
    max_link_distance_km: float = 200.0,
    max_trusted_nodes: int = 20,
) -> list[NodePlacement]:
    """Compute optimal node placements including trusted relay nodes.

    Parameters
    ----------
    endpoints:
        List of ``(node_id, (lat, lon))`` tuples for demand endpoints.
    max_link_distance_km:
        Maximum allowed distance between adjacent nodes.
    max_trusted_nodes:
        Hard cap on the number of trusted relay nodes to insert.

    Returns
    -------
    list[NodePlacement]
        Ordered list of endpoint and trusted-relay placements.
    """
    # Step 1 -- endpoint placements
    placements: list[NodePlacement] = [
        NodePlacement(
            node_id=nid,
            location=loc,
            node_type="endpoint",
            score=1.0,
        )
        for nid, loc in endpoints
    ]

    # Step 2 & 3 -- insert intermediates where needed
    trusted_nodes: list[NodePlacement] = []
    trusted_counter = 0

    for i in range(len(endpoints)):
        for j in range(i + 1, len(endpoints)):
            nid_a, loc_a = endpoints[i]
            nid_b, loc_b = endpoints[j]
            dist = _haversine_km(loc_a[0], loc_a[1], loc_b[0], loc_b[1])

            if dist > max_link_distance_km:
                n_segments = math.ceil(dist / max_link_distance_km)
                n_intermediates = n_segments - 1

                for k in range(1, n_intermediates + 1):
                    frac = k / n_segments
                    lat = loc_a[0] + frac * (loc_b[0] - loc_a[0])
                    lon = loc_a[1] + frac * (loc_b[1] - loc_a[1])
                    trusted_counter += 1
                    trusted_nodes.append(
                        NodePlacement(
                            node_id=f"trusted_{trusted_counter}",
                            location=(lat, lon),
                            node_type="trusted",
                            score=0.0,  # placeholder, scored later
                        )
                    )

    # Step 4 -- greedy merge: if two trusted nodes < 5km apart, merge
    merged = True
    while merged:
        merged = False
        new_trusted: list[NodePlacement] = []
        skip: set[int] = set()
        for i in range(len(trusted_nodes)):
            if i in skip:
                continue
            best_merge = -1
            for j in range(i + 1, len(trusted_nodes)):
                if j in skip:
                    continue
                d = _haversine_km(
                    trusted_nodes[i].location[0],
                    trusted_nodes[i].location[1],
                    trusted_nodes[j].location[0],
                    trusted_nodes[j].location[1],
                )
                if d < 5.0:
                    best_merge = j
                    break
            if best_merge >= 0:
                merged = True
                skip.add(best_merge)
                mid_lat = (
                    trusted_nodes[i].location[0]
                    + trusted_nodes[best_merge].location[0]
                ) / 2
                mid_lon = (
                    trusted_nodes[i].location[1]
                    + trusted_nodes[best_merge].location[1]
                ) / 2
                new_trusted.append(
                    NodePlacement(
                        node_id=trusted_nodes[i].node_id,
                        location=(mid_lat, mid_lon),
                        node_type="trusted",
                        score=0.0,
                    )
                )
            else:
                new_trusted.append(trusted_nodes[i])
        trusted_nodes = new_trusted

    # Step 6 -- limit to max_trusted_nodes
    trusted_nodes = trusted_nodes[:max_trusted_nodes]

    # Step 5 -- score each trusted node
    all_nodes = placements + trusted_nodes
    scored_trusted: list[NodePlacement] = []
    for tn in trusted_nodes:
        max_adj = 0.0
        for other in all_nodes:
            if other.node_id == tn.node_id:
                continue
            d = _haversine_km(
                tn.location[0],
                tn.location[1],
                other.location[0],
                other.location[1],
            )
            if d > max_adj:
                max_adj = d
        score = 1.0 / (1.0 + max_adj / max_link_distance_km)
        scored_trusted.append(
            NodePlacement(
                node_id=tn.node_id,
                location=tn.location,
                node_type=tn.node_type,
                score=round(score, 4),
            )
        )

    return placements + scored_trusted
