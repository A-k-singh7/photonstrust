"""Network-scale QKD simulation engine."""

from __future__ import annotations

from dataclasses import asdict

from photonstrust.network.routing import compute_routing_table
from photonstrust.network.types import NetworkSimResult, NetworkTopology


def simulate_network(
    topology_cfg: dict,
    scenario_defaults: dict,
    *,
    routing_strategy: str = "max_key_rate",
    include_routing_table: bool = True,
) -> NetworkSimResult:
    """Run QKD simulation on every link in the topology, then route.

    1. Parse topology into NetworkTopology.
    2. For each link, run ``compute_point()`` with link-specific config merged
       with *scenario_defaults*.
    3. Compute routing table.
    4. Compute end-to-end key rates for all endpoint pairs.
    5. Return aggregate metrics.
    """
    from photonstrust.qkd import compute_point

    topo = NetworkTopology.from_config(topology_cfg)
    warnings: list[str] = []

    link_results: dict[str, dict] = {}
    for link_id, link in topo.links.items():
        scenario = _build_link_scenario(link, scenario_defaults)
        try:
            result = compute_point(scenario, link.distance_km)
            link_results[link_id] = asdict(result)
        except Exception as exc:
            warnings.append(f"Link '{link_id}' simulation failed: {exc}")
            link_results[link_id] = {
                "distance_km": link.distance_km,
                "key_rate_bps": 0.0,
                "error": str(exc),
            }

    routing_table_raw: dict[str, dict] = {}
    paths: list[dict] = []
    if include_routing_table:
        rt = compute_routing_table(topo, link_results, strategy=routing_strategy)
        for key, np in rt.items():
            routing_table_raw[key] = np.as_dict()
            if key not in [p.get("path_id", "") for p in paths]:
                paths.append(np.as_dict())

    all_rates = [
        float(lr.get("key_rate_bps", 0.0))
        for lr in link_results.values()
        if "error" not in lr
    ]
    aggregate = {
        "total_links": len(topo.links),
        "total_nodes": len(topo.nodes),
        "total_endpoints": len(topo.endpoint_ids()),
        "mean_link_key_rate_bps": sum(all_rates) / len(all_rates) if all_rates else 0.0,
        "min_link_key_rate_bps": min(all_rates) if all_rates else 0.0,
        "max_link_key_rate_bps": max(all_rates) if all_rates else 0.0,
        "total_fiber_km": sum(l.distance_km for l in topo.links.values()),
        "routing_strategy": routing_strategy,
    }

    return NetworkSimResult(
        topology=topo.as_dict(),
        paths=paths,
        link_results=link_results,
        routing_table=routing_table_raw,
        aggregate_metrics=aggregate,
        warnings=warnings,
    )


def simulate_network_from_config(config: dict) -> NetworkSimResult:
    """Load network config dict and run simulation."""
    network_cfg = config.get("network", config)
    topology_cfg = network_cfg.get("topology", {})
    scenario_defaults = network_cfg.get("scenario_defaults", {})
    routing_cfg = network_cfg.get("routing", {})
    strategy = str(routing_cfg.get("strategy", "max_key_rate"))

    return simulate_network(
        topology_cfg=topology_cfg,
        scenario_defaults=scenario_defaults,
        routing_strategy=strategy,
    )


def _build_link_scenario(link, defaults: dict) -> dict:
    """Merge link-specific channel config with scenario defaults."""
    scenario = {
        "scenario": {
            "id": f"network_link_{link.link_id}",
            "distance_km": link.distance_km,
            "band": defaults.get("band", "c_1550"),
        },
        "source": dict(defaults.get("source", {"type": "emitter_cavity", "rep_rate_mhz": 100})),
        "channel": {
            "model": link.channel_cfg.get("model", link.link_type),
            **{k: v for k, v in link.channel_cfg.items() if k != "model"},
        },
        "detector": dict(defaults.get("detector", {"class": "snspd"})),
        "timing": dict(defaults.get("timing", {})),
        "protocol": dict(defaults.get("protocol", {"name": "BB84_DECOY"})),
    }
    if "finite_key" in defaults:
        scenario["finite_key"] = dict(defaults["finite_key"])
    return scenario
