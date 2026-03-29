"""High-level deployment plan builder."""

from __future__ import annotations

import math
import uuid

from photonstrust.planner.capacity import forecast_capacity
from photonstrust.planner.node_placement import _haversine_km, optimize_node_placement
from photonstrust.planner.redundancy import analyze_redundancy
from photonstrust.planner.types import DeploymentPlan, PlannerConstraints


def build_deployment_plan(
    demand_endpoints: list[dict],
    *,
    constraints: dict | None = None,
    scenario_defaults: dict | None = None,
) -> DeploymentPlan:
    """Build a complete QKD network deployment plan.

    Parameters
    ----------
    demand_endpoints:
        Each entry must contain ``"node_id"`` and ``"location"`` (``[lat, lon]``).
        An optional ``"demand_bps"`` field is accepted but not required.
    constraints:
        Optional dict of constraint overrides fed to :class:`PlannerConstraints`.
    scenario_defaults:
        Reserved for future scenario presets (currently unused).

    Returns
    -------
    DeploymentPlan
    """
    constraints = constraints or {}
    pc = PlannerConstraints(**{
        k: v
        for k, v in constraints.items()
        if k in PlannerConstraints.__dataclass_fields__
    })

    # ---- 1. Parse endpoints ----
    endpoints: list[tuple[str, tuple[float, float]]] = [
        (ep["node_id"], tuple(ep["location"]))
        for ep in demand_endpoints
    ]

    # ---- 2. Node placement ----
    placements = optimize_node_placement(
        endpoints,
        max_link_distance_km=pc.max_link_distance_km,
    )

    # ---- 3. Build topology (connect consecutive nodes along pairs) ----
    nodes_list: list[dict] = [
        {"node_id": p.node_id, "node_type": p.node_type}
        for p in placements
    ]
    placement_map = {p.node_id: p for p in placements}
    links_list: list[dict] = []
    seen_links: set[tuple[str, str]] = set()

    for i in range(len(endpoints)):
        for j in range(i + 1, len(endpoints)):
            nid_a = endpoints[i][0]
            nid_b = endpoints[j][0]

            # Collect nodes on the path between these two endpoints
            path_nodes = [nid_a]
            # Find trusted nodes that lie between these endpoints
            trusted_on_path = [
                p
                for p in placements
                if p.node_type == "trusted"
            ]
            # Sort trusted nodes by distance from endpoint A
            loc_a = placement_map[nid_a].location
            trusted_on_path.sort(
                key=lambda p: _haversine_km(
                    loc_a[0], loc_a[1], p.location[0], p.location[1],
                ),
            )
            for tn in trusted_on_path:
                d_a = _haversine_km(
                    loc_a[0], loc_a[1], tn.location[0], tn.location[1],
                )
                loc_b = placement_map[nid_b].location
                d_b = _haversine_km(
                    loc_b[0], loc_b[1], tn.location[0], tn.location[1],
                )
                d_ab = _haversine_km(
                    loc_a[0], loc_a[1], loc_b[0], loc_b[1],
                )
                # Node is roughly on the path if d_a + d_b ≈ d_ab
                if d_a + d_b < d_ab * 1.1:
                    path_nodes.append(tn.node_id)
            path_nodes.append(nid_b)

            # Sort by distance from A
            path_nodes_sorted = sorted(
                path_nodes,
                key=lambda nid: _haversine_km(
                    loc_a[0],
                    loc_a[1],
                    placement_map[nid].location[0],
                    placement_map[nid].location[1],
                ),
            )

            for k in range(len(path_nodes_sorted) - 1):
                src = path_nodes_sorted[k]
                tgt = path_nodes_sorted[k + 1]
                link_key = (min(src, tgt), max(src, tgt))
                if link_key not in seen_links:
                    seen_links.add(link_key)
                    links_list.append({"source": src, "target": tgt})

    topology_dict: dict = {
        "topology_id": f"topo_{uuid.uuid4().hex[:8]}",
        "nodes": nodes_list,
        "links": links_list,
    }

    # ---- 4. Estimate key rates and forecast capacity ----
    link_results: dict[str, dict] = {}
    capacity_forecasts = []
    for link in links_list:
        src, tgt = link["source"], link["target"]
        loc_s = placement_map[src].location
        loc_t = placement_map[tgt].location
        dist = _haversine_km(loc_s[0], loc_s[1], loc_t[0], loc_t[1])
        # Simple exponential decay: 0.046 ≈ 0.2 dB/km * ln(10)/10
        key_rate = 10000.0 * math.exp(-dist * 0.046)
        link_id = f"{src}--{tgt}"
        link_results[link_id] = {
            "key_rate_bps": key_rate,
            "distance_km": dist,
        }
        fc = forecast_capacity(
            link_id=link_id,
            current_key_rate_bps=key_rate,
            distance_km=dist,
            detector_class=pc.detector_class,
        )
        capacity_forecasts.append(fc)

    # ---- 5. Redundancy analysis ----
    redundancy = analyze_redundancy(topology_dict, link_results=link_results)

    # ---- 6. Cost estimate ----
    total_link_cost = 0.0
    for link_id, lr in link_results.items():
        total_link_cost += lr["distance_km"] * 5000.0 + 150000.0
    total_node_cost = len(placements) * 50000.0
    total_capex = total_link_cost + total_node_cost
    cost_estimate = {
        "total_capex_usd": round(total_capex, 2),
        "link_cost_usd": round(total_link_cost, 2),
        "node_cost_usd": round(total_node_cost, 2),
    }

    # ---- 7. Plan score ----
    budget_ratio = 1.0 - min(1.0, total_capex / pc.max_budget_usd) if pc.max_budget_usd > 0 else 0.0
    min_rate = min(
        (lr["key_rate_bps"] for lr in link_results.values()),
        default=0.0,
    )
    rate_ratio = min(1.0, min_rate / pc.min_key_rate_bps) if pc.min_key_rate_bps > 0 else 1.0
    resilience = redundancy.resilience_score
    score = round(0.4 * budget_ratio + 0.3 * rate_ratio + 0.3 * resilience, 4)

    # ---- 8. Warnings ----
    warnings: list[str] = []
    if total_capex > pc.max_budget_usd:
        warnings.append(
            f"Budget exceeded: estimated ${total_capex:,.0f} > ${pc.max_budget_usd:,.0f}",
        )
    if min_rate < pc.min_key_rate_bps:
        warnings.append(
            f"Minimum key rate {min_rate:.1f} bps below required {pc.min_key_rate_bps} bps",
        )
    if redundancy.single_points_of_failure:
        warnings.append(
            f"Topology has {len(redundancy.single_points_of_failure)} single point(s) of failure",
        )

    return DeploymentPlan(
        plan_id=f"plan_{uuid.uuid4().hex[:8]}",
        node_placements=placements,
        topology=topology_dict,
        cost_estimate=cost_estimate,
        capacity_forecasts=capacity_forecasts,
        redundancy=redundancy,
        constraints=pc.as_dict(),
        warnings=warnings,
        score=score,
    )
