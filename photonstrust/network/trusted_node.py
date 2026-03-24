"""Trusted node key relay protocol simulation."""

from __future__ import annotations


def trusted_node_key_rate(
    path_link_results: list[dict],
    path_nodes: list[str] | None = None,
    node_types: dict[str, str] | None = None,
) -> float:
    """Compute end-to-end key rate through trusted nodes.

    For a chain of trusted nodes, the end-to-end key rate is limited by the
    minimum link key rate (bottleneck model).  All intermediate nodes must be
    trusted for this model to apply.

    Parameters
    ----------
    path_link_results : list[dict]
        Ordered list of per-link QKDResult-like dicts along the path.
    path_nodes : list[str] | None
        Node IDs along the path (optional, for validation).
    node_types : dict[str, str] | None
        Mapping node_id -> node_type (optional, for validation).

    Returns
    -------
    float
        End-to-end key rate in bits/s.
    """
    if not path_link_results:
        return 0.0

    rates = [float(lr.get("key_rate_bps", 0.0)) for lr in path_link_results]
    return min(rates) if rates else 0.0


def trusted_node_latency_s(
    path_link_results: list[dict],
    processing_time_per_node_s: float = 0.001,
) -> float:
    """Estimate key relay latency through trusted node chain.

    Includes fiber propagation delay (5 us/km) plus per-node processing time.

    Parameters
    ----------
    path_link_results : list[dict]
        Ordered list of per-link result dicts (must contain ``distance_km``).
    processing_time_per_node_s : float
        Processing time at each intermediate node.

    Returns
    -------
    float
        Total estimated latency in seconds.
    """
    fiber_delay_s_per_km = 5e-6
    total_latency = 0.0
    for lr in path_link_results:
        total_latency += float(lr.get("distance_km", 0.0)) * fiber_delay_s_per_km
    n_intermediate = max(0, len(path_link_results) - 1)
    total_latency += n_intermediate * processing_time_per_node_s
    return total_latency
