"""High-level API -- simulate QKD links, compare protocols, design PICs, and more in 3-5 lines.

Example
-------
    from photonstrust.easy import simulate_qkd_link, compare_protocols

    result = simulate_qkd_link(protocol="bb84", distance_km=50)
    print(result.summary())

    comp = compare_protocols(protocols=["bb84", "tf_qkd"], distances={"start": 0, "stop": 100, "step": 10})
    print(comp.winner_at(50))
"""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Result wrapper classes
# ---------------------------------------------------------------------------


@dataclass
class QKDLinkResult:
    """Wraps a list of :class:`QKDResult` from a single-protocol sweep."""

    results: list[Any]
    config: dict

    # -- convenience accessors ------------------------------------------------

    def summary(self) -> str:
        """Return a human-readable summary string."""
        if not self.results:
            return "No results."
        protocol = self.results[0].protocol_name or self.config.get("protocol", {}).get("name", "unknown")
        peak_rate = max(r.key_rate_bps for r in self.results)
        max_dist = self.max_distance_km()
        return (
            f"Protocol: {protocol}\n"
            f"Peak key rate: {_format_key_rate(peak_rate)}\n"
            f"Max distance (key rate > 0): {max_dist:.1f} km\n"
            f"Points evaluated: {len(self.results)}"
        )

    def as_dict(self) -> dict:
        """Serialisable dictionary representation."""
        rows = []
        for r in self.results:
            rows.append({
                "distance_km": r.distance_km,
                "key_rate_bps": r.key_rate_bps,
                "qber_total": r.qber_total,
                "fidelity": r.fidelity,
                "loss_db": r.loss_db,
                "protocol_name": r.protocol_name,
            })
        return {"results": rows, "config": self.config}

    def max_distance_km(self) -> float:
        """Maximum distance where key_rate_bps > 0."""
        positive = [r.distance_km for r in self.results if r.key_rate_bps > 0]
        return max(positive) if positive else 0.0

    def key_rate_at(self, distance_km: float) -> float:
        """Return the key rate at *distance_km* (nearest-neighbour lookup)."""
        if not self.results:
            return 0.0
        best = min(self.results, key=lambda r: abs(r.distance_km - distance_km))
        return best.key_rate_bps

    def plot(self, save_path: str | None = None) -> Any:
        """Plot rate-vs-distance (requires matplotlib)."""
        try:
            import matplotlib.pyplot as plt
        except ImportError:  # pragma: no cover
            warnings.warn("matplotlib not installed -- plot() is a no-op")
            return None
        distances = [r.distance_km for r in self.results]
        rates = [r.key_rate_bps for r in self.results]
        fig, ax = plt.subplots()
        ax.semilogy(distances, [max(r, 1e-30) for r in rates], marker="o", linewidth=1.5)
        ax.set_xlabel("Distance (km)")
        ax.set_ylabel("Secure key rate (bps)")
        protocol = self.results[0].protocol_name if self.results else ""
        ax.set_title(f"QKD link: {protocol}")
        ax.grid(True, which="both", ls="--", alpha=0.5)
        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches="tight")
        return fig


@dataclass
class ProtocolComparison:
    """Wraps per-protocol :class:`QKDLinkResult` dicts."""

    protocols: dict[str, QKDLinkResult]

    def summary(self) -> str:
        """Return a table comparing protocols."""
        header = f"{'Protocol':<20} {'Peak rate':>15} {'Max dist (km)':>15}"
        lines = [header, "-" * len(header)]
        for name, lr in sorted(self.protocols.items()):
            peak = max((r.key_rate_bps for r in lr.results), default=0.0)
            md = lr.max_distance_km()
            lines.append(f"{name:<20} {_format_key_rate(peak):>15} {md:>15.1f}")
        return "\n".join(lines)

    def winner_at(self, distance_km: float) -> str:
        """Return the protocol name with the highest key rate at *distance_km*."""
        best_name = ""
        best_rate = -1.0
        for name, lr in self.protocols.items():
            rate = lr.key_rate_at(distance_km)
            if rate > best_rate:
                best_rate = rate
                best_name = name
        return best_name

    def as_dict(self) -> dict:
        return {name: lr.as_dict() for name, lr in self.protocols.items()}

    def plot(self, save_path: str | None = None) -> Any:
        """Overlay all protocols on one rate-vs-distance chart."""
        try:
            import matplotlib.pyplot as plt
        except ImportError:  # pragma: no cover
            warnings.warn("matplotlib not installed -- plot() is a no-op")
            return None
        fig, ax = plt.subplots()
        for name, lr in sorted(self.protocols.items()):
            distances = [r.distance_km for r in lr.results]
            rates = [max(r.key_rate_bps, 1e-30) for r in lr.results]
            ax.semilogy(distances, rates, marker="o", linewidth=1.5, label=name)
        ax.set_xlabel("Distance (km)")
        ax.set_ylabel("Secure key rate (bps)")
        ax.set_title("Protocol comparison")
        ax.legend()
        ax.grid(True, which="both", ls="--", alpha=0.5)
        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches="tight")
        return fig


@dataclass
class PICDesignResult:
    """Wraps PIC netlist creation, optional simulation & DRC."""

    netlist: dict
    sim_result: dict | None = None
    drc_result: dict | None = None

    def summary(self) -> str:
        n_nodes = len(self.netlist.get("nodes", []))
        n_edges = len(self.netlist.get("edges", []))
        parts = [f"PIC netlist: {n_nodes} components, {n_edges} connections"]
        if self.drc_result is not None:
            violations = self.drc_result.get("violations", [])
            status = self.drc_result.get("status", "unknown")
            parts.append(f"DRC status: {status} ({len(violations)} violations)")
        if self.sim_result is not None:
            parts.append("Simulation: completed")
        return "\n".join(parts)

    def as_dict(self) -> dict:
        return {
            "netlist": self.netlist,
            "sim_result": self.sim_result,
            "drc_result": self.drc_result,
        }


@dataclass
class NetworkPlan:
    """Wraps network topology analysis results."""

    topology: dict
    paths: list[dict]
    aggregate: dict

    def summary(self) -> str:
        n_nodes = len(self.topology.get("nodes", []))
        n_links = len(self.topology.get("links", []))
        n_paths = len(self.paths)
        parts = [
            f"Network: {n_nodes} nodes, {n_links} links",
            f"Paths computed: {n_paths}",
        ]
        agg_rate = self.aggregate.get("total_key_rate_bps")
        if agg_rate is not None:
            parts.append(f"Aggregate key rate: {_format_key_rate(agg_rate)}")
        bottleneck = self.aggregate.get("bottleneck_link_id")
        if bottleneck:
            parts.append(f"Bottleneck link: {bottleneck}")
        return "\n".join(parts)

    def as_dict(self) -> dict:
        return {
            "topology": self.topology,
            "paths": self.paths,
            "aggregate": self.aggregate,
        }


@dataclass
class SatellitePlan:
    """Wraps satellite pass scheduling results."""

    constellation: dict | None
    schedule: dict

    def summary(self) -> str:
        parts = []
        if self.constellation:
            parts.append(
                f"Constellation: {self.constellation.get('total_sats', '?')} satellites, "
                f"{self.constellation.get('n_planes', '?')} planes, "
                f"altitude {self.constellation.get('altitude_km', '?')} km"
            )
        total_key = self.schedule.get("total_expected_key_bits", 0.0)
        n_passes = self.schedule.get("n_passes", 0)
        parts.append(f"Scheduled passes: {n_passes}")
        parts.append(f"Total expected key: {_format_bits(total_key)}")
        utilization = self.schedule.get("utilization", 0.0)
        parts.append(f"Contact utilization: {utilization:.0%}")
        return "\n".join(parts)

    def as_dict(self) -> dict:
        return {
            "constellation": self.constellation,
            "schedule": self.schedule,
        }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _format_key_rate(bps: float) -> str:
    """Pretty-print a key rate value."""
    if not math.isfinite(bps) or bps <= 0:
        return "0 bps"
    if bps >= 1e9:
        return f"{bps / 1e9:.2f} Gbps"
    if bps >= 1e6:
        return f"{bps / 1e6:.2f} Mbps"
    if bps >= 1e3:
        return f"{bps / 1e3:.2f} kbps"
    return f"{bps:.1f} bps"


def _format_bits(bits: float) -> str:
    """Pretty-print a bit count."""
    if not math.isfinite(bits) or bits <= 0:
        return "0 bits"
    if bits >= 1e9:
        return f"{bits / 1e9:.2f} Gbit"
    if bits >= 1e6:
        return f"{bits / 1e6:.2f} Mbit"
    if bits >= 1e3:
        return f"{bits / 1e3:.2f} kbit"
    return f"{bits:.0f} bits"


def _expand_distances(distance_km: float | list | dict) -> list[float]:
    """Normalise *distance_km* to a list of floats.

    Accepts:
    - ``float`` / ``int`` -> sweep from 0 to that value
    - ``list``            -> used as-is
    - ``dict``            -> ``{"start", "stop", "step"}`` expanded via config helper
    """
    if isinstance(distance_km, (int, float)):
        stop = float(distance_km)
        step = max(1.0, stop / 20.0)
        # Use config._expand_distance for consistency
        from photonstrust.config import _expand_distance
        return _expand_distance({"start": 0, "stop": stop, "step": step})
    if isinstance(distance_km, list):
        return [float(d) for d in distance_km]
    if isinstance(distance_km, dict):
        from photonstrust.config import _expand_distance
        return _expand_distance(distance_km)
    raise TypeError(f"distance_km must be float, list, or dict, got {type(distance_km).__name__}")


def _deep_update(base: dict, overrides: dict) -> dict:
    """Recursively merge *overrides* into *base* (mutates *base*)."""
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_update(base[key], value)
        else:
            base[key] = value
    return base


def _build_scenario(
    protocol: str,
    band: str,
    detector: str,
    source_type: str,
    channel_model: str,
    distances_km: list[float],
    include_uncertainty: bool,
    overrides: dict,
) -> dict:
    """Assemble a full scenario dict ready for :func:`qkd.compute_sweep`."""
    from photonstrust.config import (
        apply_source_defaults,
        apply_channel_defaults,
        apply_detector_defaults,
        apply_timing_defaults,
        resolve_band_wavelength,
    )
    from photonstrust.qkd_protocols.common import normalize_protocol_name

    protocol_name = normalize_protocol_name(protocol)

    source = apply_source_defaults({"type": source_type})
    channel = apply_channel_defaults({"model": channel_model}, band)
    det = apply_detector_defaults({"class": detector}, band)
    timing = apply_timing_defaults({})
    wavelength_nm = resolve_band_wavelength(band, None)

    # Protocol-specific defaults
    protocol_defaults: dict[str, Any] = {"name": protocol_name}
    if protocol_name in ("pm_qkd", "tf_qkd"):
        protocol_defaults.setdefault("mu", 0.1)
        protocol_defaults.setdefault("phase_slices", 16)
    elif protocol_name in ("mdi_qkd", "amdi_qkd"):
        protocol_defaults.setdefault("mu", 0.3)
        protocol_defaults.setdefault("nu", 0.05)
    elif protocol_name == "sns_tf_qkd":
        protocol_defaults.setdefault("mu_z", 0.3)
        protocol_defaults.setdefault("mu_1", 0.1)
        protocol_defaults.setdefault("mu_2", 0.02)

    scenario: dict[str, Any] = {
        "schema_version": "0.1",
        "band": band,
        "wavelength_nm": wavelength_nm,
        "distances_km": distances_km,
        "source": source,
        "channel": channel,
        "detector": det,
        "timing": timing,
        "protocol": protocol_defaults,
        "finite_key": {},
    }

    if include_uncertainty:
        scenario["uncertainty"] = {"seed": 42}
    else:
        scenario["uncertainty"] = {}

    # Apply caller overrides (nested)
    if overrides:
        _deep_update(scenario, overrides)

    return scenario


# ---------------------------------------------------------------------------
# Power function 1: simulate_qkd_link
# ---------------------------------------------------------------------------


def simulate_qkd_link(
    *,
    protocol: str = "bb84",
    distance_km: float | list | dict = 50.0,
    band: str = "c_1550",
    detector: str = "snspd",
    source_type: str = "emitter_cavity",
    channel_model: str = "fiber",
    include_uncertainty: bool = True,
    **overrides: Any,
) -> QKDLinkResult:
    """Simulate a QKD link in one call.

    Parameters
    ----------
    protocol
        Protocol shorthand, e.g. ``"bb84"``, ``"tf_qkd"``, ``"cv_qkd"``.
    distance_km
        Single float (auto-sweep 0..distance), list of distances, or
        ``{"start": 0, "stop": 100, "step": 10}`` dict.
    band
        Wavelength band preset name.
    detector
        Detector class preset name.
    source_type
        Photon source type (``"emitter_cavity"`` or ``"spdc"``).
    channel_model
        Channel model (``"fiber"``, ``"free_space"``, ``"satellite"``).
    include_uncertainty
        Whether to run Monte-Carlo uncertainty analysis.
    **overrides
        Arbitrary nested overrides merged into the scenario dict.

    Returns
    -------
    QKDLinkResult
    """
    from photonstrust.qkd import compute_sweep

    distances = _expand_distances(distance_km)
    scenario = _build_scenario(
        protocol=protocol,
        band=band,
        detector=detector,
        source_type=source_type,
        channel_model=channel_model,
        distances_km=distances,
        include_uncertainty=include_uncertainty,
        overrides=overrides,
    )
    sweep = compute_sweep(scenario, include_uncertainty=include_uncertainty)
    return QKDLinkResult(results=sweep["results"], config=scenario)


# ---------------------------------------------------------------------------
# Power function 2: compare_protocols
# ---------------------------------------------------------------------------


def compare_protocols(
    *,
    protocols: list[str] | None = None,
    distances: float | list | dict | None = None,
    band: str = "c_1550",
    detector: str = "snspd",
    **overrides: Any,
) -> ProtocolComparison:
    """Compare multiple QKD protocols over the same distance sweep.

    Parameters
    ----------
    protocols
        List of protocol names.  If ``None``, all registered protocols are used.
    distances
        Distance specification (see :func:`simulate_qkd_link`).
        Defaults to ``{"start": 0, "stop": 100, "step": 5}``.
    band
        Wavelength band preset.
    detector
        Detector class preset.
    **overrides
        Extra overrides forwarded to each :func:`simulate_qkd_link` call.

    Returns
    -------
    ProtocolComparison
    """
    from photonstrust.qkd_protocols.registry import available_protocols

    if protocols is None:
        protocols = list(available_protocols())
    if distances is None:
        distances = {"start": 0, "stop": 100, "step": 5}

    results: dict[str, QKDLinkResult] = {}
    for proto in protocols:
        try:
            lr = simulate_qkd_link(
                protocol=proto,
                distance_km=distances,
                band=band,
                detector=detector,
                include_uncertainty=False,
                **overrides,
            )
            results[proto] = lr
        except Exception as exc:  # noqa: BLE001
            warnings.warn(f"Protocol {proto!r} skipped: {exc}")
    return ProtocolComparison(protocols=results)


# ---------------------------------------------------------------------------
# Power function 3: design_pic
# ---------------------------------------------------------------------------


def design_pic(
    *,
    components: list[str | dict],
    connections: list[dict] | None = None,
    pdk: str = "generic_silicon_photonics",
    wavelength_nm: float = 1550.0,
    run_drc: bool = True,
    run_yield: bool = False,
    **overrides: Any,
) -> PICDesignResult:
    """Build a PIC netlist from a component list, optionally run DRC and simulation.

    Parameters
    ----------
    components
        List of component kinds (strings) or dicts with ``{"kind": ..., "params": ...}``.
    connections
        List of connection dicts: ``{"from": (idx, port), "to": (idx, port)}``.
    pdk
        PDK identifier for DRC rule lookup.
    wavelength_nm
        Simulation wavelength.
    run_drc
        Whether to run graph-level DRC checks.
    run_yield
        Whether to run Monte-Carlo yield estimation (slow).
    **overrides
        Extra fields merged into the netlist dict.

    Returns
    -------
    PICDesignResult
    """
    # Build nodes
    nodes: list[dict] = []
    for idx, comp in enumerate(components):
        if isinstance(comp, str):
            node = {"id": f"comp_{idx}", "kind": comp, "params": {}}
        elif isinstance(comp, dict):
            node = {
                "id": comp.get("id", f"comp_{idx}"),
                "kind": comp.get("kind", comp.get("type", "unknown")),
                "params": comp.get("params", {}),
            }
        else:
            raise TypeError(f"Component must be str or dict, got {type(comp).__name__}")
        nodes.append(node)

    # Build edges
    edges: list[dict] = []
    for idx, conn in enumerate(connections or []):
        src = conn.get("from", conn.get("src"))
        dst = conn.get("to", conn.get("dst"))
        edge: dict[str, Any] = {"id": f"edge_{idx}"}
        if isinstance(src, (list, tuple)) and len(src) == 2:
            edge["src_node"] = f"comp_{src[0]}" if isinstance(src[0], int) else str(src[0])
            edge["src_port"] = str(src[1])
        else:
            edge["src_node"] = str(src)
            edge["src_port"] = "out0"
        if isinstance(dst, (list, tuple)) and len(dst) == 2:
            edge["dst_node"] = f"comp_{dst[0]}" if isinstance(dst[0], int) else str(dst[0])
            edge["dst_port"] = str(dst[1])
        else:
            edge["dst_node"] = str(dst)
            edge["dst_port"] = "in0"
        edges.append(edge)

    netlist: dict[str, Any] = {
        "schema_version": "0.1",
        "pdk": pdk,
        "wavelength_nm": wavelength_nm,
        "nodes": nodes,
        "edges": edges,
    }
    if overrides:
        _deep_update(netlist, overrides)

    # Optional DRC
    drc_result: dict | None = None
    if run_drc:
        try:
            from photonstrust.pic.drc import run_graph_drc
            drc_result = run_graph_drc(netlist, pdk=pdk)
        except Exception as exc:  # noqa: BLE001
            drc_result = {"status": "error", "violations": [], "error": str(exc)}

    # Optional simulation
    sim_result: dict | None = None
    try:
        from photonstrust.sdk import simulate_netlist
        sim_result = simulate_netlist(netlist, wavelength_nm=wavelength_nm)
    except Exception:  # noqa: BLE001
        pass  # Simulation may not be available for all netlists

    return PICDesignResult(netlist=netlist, sim_result=sim_result, drc_result=drc_result)


# ---------------------------------------------------------------------------
# Power function 4: plan_network
# ---------------------------------------------------------------------------


def plan_network(
    *,
    nodes: list[str | dict],
    links: list[dict],
    protocol: str = "bb84",
    band: str = "c_1550",
    detector: str = "snspd",
    routing_strategy: str = "max_key_rate",
) -> NetworkPlan:
    """Plan a multi-node QKD network.

    Parameters
    ----------
    nodes
        List of node IDs (strings) or dicts ``{"id": ..., "type": ..., "location": ...}``.
    links
        List of link dicts ``{"a": node_id, "b": node_id, "distance_km": float}``.
    protocol
        Default QKD protocol for each link.
    band
        Wavelength band preset.
    detector
        Detector class preset.
    routing_strategy
        ``"max_key_rate"`` or ``"shortest_path"``.

    Returns
    -------
    NetworkPlan
    """
    from photonstrust.network.types import NetworkNode, NetworkLink, NetworkTopology
    from photonstrust.qkd import compute_point
    from photonstrust.qkd_protocols.common import normalize_protocol_name

    topo = NetworkTopology()

    # Add nodes
    for n in nodes:
        if isinstance(n, str):
            topo.add_node(NetworkNode(node_id=n))
        elif isinstance(n, dict):
            topo.add_node(NetworkNode(
                node_id=str(n.get("id", n.get("node_id", ""))),
                node_type=str(n.get("type", n.get("node_type", "endpoint"))),
                location=tuple(n["location"]) if n.get("location") else None,
            ))
        else:
            raise TypeError(f"Node must be str or dict, got {type(n).__name__}")

    # Add links and compute per-link key rates
    link_rates: dict[str, dict] = {}
    protocol_name = normalize_protocol_name(protocol)

    for idx, lk in enumerate(links):
        link_id = str(lk.get("id", lk.get("link_id", f"link_{idx}")))
        node_a = str(lk.get("a", lk.get("node_a", "")))
        node_b = str(lk.get("b", lk.get("node_b", "")))
        dist = float(lk.get("distance_km", 0.0))
        topo.add_link(NetworkLink(link_id=link_id, node_a=node_a, node_b=node_b, distance_km=dist))

        # Single-point QKD estimate for this link
        scenario = _build_scenario(
            protocol=protocol,
            band=band,
            detector=detector,
            source_type="emitter_cavity",
            channel_model="fiber",
            distances_km=[dist],
            include_uncertainty=False,
            overrides={},
        )
        try:
            result = compute_point(scenario, dist)
            link_rates[link_id] = {
                "key_rate_bps": result.key_rate_bps,
                "qber": result.qber_total,
                "loss_db": result.loss_db,
            }
        except Exception:  # noqa: BLE001
            link_rates[link_id] = {"key_rate_bps": 0.0, "qber": 0.5, "loss_db": float("inf")}

    # Compute paths between all endpoint pairs
    endpoint_ids = topo.endpoint_ids()
    paths: list[dict] = []

    if routing_strategy == "max_key_rate":
        from photonstrust.network.routing import max_key_rate_path
        for i, src in enumerate(endpoint_ids):
            for dst in endpoint_ids[i + 1:]:
                path_nodes = max_key_rate_path(topo, link_rates, src, dst)
                if path_nodes:
                    path_links = []
                    total_dist = 0.0
                    bottleneck_rate = float("inf")
                    bottleneck_id = ""
                    for a, b in zip(path_nodes[:-1], path_nodes[1:]):
                        link = topo.get_link_between(a, b)
                        if link:
                            path_links.append(link.link_id)
                            total_dist += link.distance_km
                            lr = link_rates.get(link.link_id, {})
                            rate = lr.get("key_rate_bps", 0.0)
                            if rate < bottleneck_rate:
                                bottleneck_rate = rate
                                bottleneck_id = link.link_id
                    paths.append({
                        "src": src,
                        "dst": dst,
                        "nodes": path_nodes,
                        "links": path_links,
                        "total_distance_km": total_dist,
                        "bottleneck_rate_bps": bottleneck_rate if math.isfinite(bottleneck_rate) else 0.0,
                        "bottleneck_link_id": bottleneck_id,
                    })
    else:
        from photonstrust.network.routing import shortest_path
        for i, src in enumerate(endpoint_ids):
            for dst in endpoint_ids[i + 1:]:
                path_nodes = shortest_path(topo, src, dst)
                if path_nodes:
                    path_links = []
                    total_dist = 0.0
                    bottleneck_rate = float("inf")
                    bottleneck_id = ""
                    for a, b in zip(path_nodes[:-1], path_nodes[1:]):
                        link = topo.get_link_between(a, b)
                        if link:
                            path_links.append(link.link_id)
                            total_dist += link.distance_km
                            lr = link_rates.get(link.link_id, {})
                            rate = lr.get("key_rate_bps", 0.0)
                            if rate < bottleneck_rate:
                                bottleneck_rate = rate
                                bottleneck_id = link.link_id
                    paths.append({
                        "src": src,
                        "dst": dst,
                        "nodes": path_nodes,
                        "links": path_links,
                        "total_distance_km": total_dist,
                        "bottleneck_rate_bps": bottleneck_rate if math.isfinite(bottleneck_rate) else 0.0,
                        "bottleneck_link_id": bottleneck_id,
                    })

    # Aggregate metrics
    all_rates = [lr.get("key_rate_bps", 0.0) for lr in link_rates.values()]
    total_rate = sum(all_rates)
    bottleneck_link = min(link_rates.items(), key=lambda x: x[1].get("key_rate_bps", 0.0))[0] if link_rates else ""
    aggregate: dict[str, Any] = {
        "total_key_rate_bps": total_rate,
        "mean_link_rate_bps": total_rate / max(1, len(all_rates)),
        "bottleneck_link_id": bottleneck_link,
        "bottleneck_rate_bps": min(all_rates) if all_rates else 0.0,
        "n_paths": len(paths),
    }

    return NetworkPlan(
        topology=topo.as_dict(),
        paths=paths,
        aggregate=aggregate,
    )


# ---------------------------------------------------------------------------
# Power function 5: plan_satellite
# ---------------------------------------------------------------------------


def plan_satellite(
    *,
    orbit_altitude_km: float = 500.0,
    ground_stations: list[str | dict] | None = None,
    pass_duration_s: float = 300.0,
    protocol: str = "bb84",
    n_sats: int = 6,
    n_planes: int = 2,
    **overrides: Any,
) -> SatellitePlan:
    """Plan a satellite QKD constellation schedule.

    Parameters
    ----------
    orbit_altitude_km
        Orbital altitude in km.
    ground_stations
        Ground station identifiers (strings) or dicts with ``{"id": ..., "lat": ..., "lon": ...}``.
        Defaults to 3 example stations.
    pass_duration_s
        Average pass duration in seconds.
    protocol
        QKD protocol for the satellite links.
    n_sats
        Total number of satellites (must be divisible by *n_planes*).
    n_planes
        Number of orbital planes.
    **overrides
        Extra overrides (currently unused, reserved for future).

    Returns
    -------
    SatellitePlan
    """
    from photonstrust.orbit.constellation import walker_constellation
    from photonstrust.orbit.scheduler import Contact, schedule_passes_greedy, key_volume_per_pass

    # Default ground stations
    if ground_stations is None:
        ground_stations = [
            {"id": "GS-London", "lat": 51.5, "lon": -0.1},
            {"id": "GS-Paris", "lat": 48.9, "lon": 2.3},
            {"id": "GS-Berlin", "lat": 52.5, "lon": 13.4},
        ]

    gs_ids: list[str] = []
    for gs in ground_stations:
        if isinstance(gs, str):
            gs_ids.append(gs)
        elif isinstance(gs, dict):
            gs_ids.append(str(gs.get("id", gs.get("name", f"GS-{len(gs_ids)}"))))
        else:
            gs_ids.append(str(gs))

    # Generate constellation
    constellation = walker_constellation(
        total_sats=n_sats,
        n_planes=n_planes,
        phase_factor=0,
        altitude_km=orbit_altitude_km,
    )

    # Generate synthetic contacts (one per satellite per ground station)
    contacts: list[Contact] = []
    time_offset = 0.0
    for sat in constellation.satellites:
        for gs_id in gs_ids:
            # Synthetic pass: staggered start times
            start = time_offset
            end = start + pass_duration_s
            # Vary elevation based on satellite position
            max_elev = 45.0 + 30.0 * math.sin(math.radians(sat.mean_anomaly_deg))
            max_elev = max(15.0, min(85.0, max_elev))
            mean_elev = max_elev * 0.7

            contacts.append(Contact(
                satellite_id=sat.sat_id,
                ground_station_id=gs_id,
                start_time_s=start,
                end_time_s=end,
                max_elevation_deg=max_elev,
                mean_elevation_deg=mean_elev,
            ))
            time_offset += pass_duration_s + 60.0  # 60s gap between passes

    # Schedule passes
    schedule = schedule_passes_greedy(contacts)

    # Build result dicts
    constellation_dict: dict[str, Any] = {
        "total_sats": constellation.total_sats,
        "n_planes": constellation.n_planes,
        "phase_factor": constellation.phase_factor,
        "altitude_km": constellation.altitude_km,
        "inclination_deg": constellation.inclination_deg,
    }

    schedule_dict: dict[str, Any] = {
        "n_passes": len(schedule.entries),
        "total_key_bits": schedule.total_key_bits,
        "total_expected_key_bits": schedule.total_expected_key_bits,
        "per_gs_key_bits": schedule.per_gs_key_bits,
        "utilization": schedule.utilization,
        "n_conflicts_resolved": schedule.n_conflicts_resolved,
    }

    return SatellitePlan(constellation=constellation_dict, schedule=schedule_dict)
