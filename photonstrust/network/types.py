"""Network simulation data types."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class NetworkNode:
    """A node in the QKD network."""

    node_id: str
    node_type: str = "endpoint"
    location: tuple[float, float] | None = None
    capacity_links: int = 4
    properties: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "location": list(self.location) if self.location else None,
            "capacity_links": self.capacity_links,
            "properties": dict(self.properties),
        }


@dataclass(frozen=True)
class NetworkLink:
    """A QKD link between two nodes."""

    link_id: str
    node_a: str
    node_b: str
    distance_km: float
    channel_cfg: dict = field(default_factory=dict)
    link_type: str = "fiber"

    def as_dict(self) -> dict:
        return {
            "link_id": self.link_id,
            "node_a": self.node_a,
            "node_b": self.node_b,
            "distance_km": self.distance_km,
            "channel_cfg": dict(self.channel_cfg),
            "link_type": self.link_type,
        }


@dataclass(frozen=True)
class NetworkPath:
    """A route through the network between two endpoints."""

    path_id: str
    nodes: tuple[str, ...]
    links: tuple[str, ...]
    total_distance_km: float
    trusted_node_count: int
    end_to_end_key_rate_bps: float
    bottleneck_link_key_rate_bps: float
    bottleneck_link_id: str

    def as_dict(self) -> dict:
        return {
            "path_id": self.path_id,
            "nodes": list(self.nodes),
            "links": list(self.links),
            "total_distance_km": self.total_distance_km,
            "trusted_node_count": self.trusted_node_count,
            "end_to_end_key_rate_bps": self.end_to_end_key_rate_bps,
            "bottleneck_link_key_rate_bps": self.bottleneck_link_key_rate_bps,
            "bottleneck_link_id": self.bottleneck_link_id,
        }


class NetworkTopology:
    """Mutable graph structure for a QKD network."""

    def __init__(self) -> None:
        self.nodes: dict[str, NetworkNode] = {}
        self.links: dict[str, NetworkLink] = {}
        self._adjacency: dict[str, list[str]] = {}

    def add_node(self, node: NetworkNode) -> None:
        self.nodes[node.node_id] = node
        if node.node_id not in self._adjacency:
            self._adjacency[node.node_id] = []

    def add_link(self, link: NetworkLink) -> None:
        self.links[link.link_id] = link
        if link.node_a not in self._adjacency:
            self._adjacency[link.node_a] = []
        if link.node_b not in self._adjacency:
            self._adjacency[link.node_b] = []
        if link.node_b not in self._adjacency[link.node_a]:
            self._adjacency[link.node_a].append(link.node_b)
        if link.node_a not in self._adjacency[link.node_b]:
            self._adjacency[link.node_b].append(link.node_a)

    def neighbors(self, node_id: str) -> list[str]:
        return list(self._adjacency.get(node_id, []))

    def get_link_between(self, a: str, b: str) -> NetworkLink | None:
        for link in self.links.values():
            if (link.node_a == a and link.node_b == b) or (
                link.node_a == b and link.node_b == a
            ):
                return link
        return None

    def endpoint_ids(self) -> list[str]:
        return sorted(
            nid for nid, node in self.nodes.items() if node.node_type == "endpoint"
        )

    def as_dict(self) -> dict:
        return {
            "nodes": [n.as_dict() for n in self.nodes.values()],
            "links": [l.as_dict() for l in self.links.values()],
        }

    @classmethod
    def from_config(cls, cfg: dict) -> NetworkTopology:
        topo = cls()
        for n in cfg.get("nodes", []):
            loc = n.get("location")
            topo.add_node(NetworkNode(
                node_id=str(n["id"]),
                node_type=str(n.get("type", "endpoint")),
                location=tuple(loc) if loc else None,
                properties=n.get("properties", {}),
            ))
        for l in cfg.get("links", []):
            topo.add_link(NetworkLink(
                link_id=str(l["id"]),
                node_a=str(l["node_a"]),
                node_b=str(l["node_b"]),
                distance_km=float(l["distance_km"]),
                channel_cfg=l.get("channel", {}),
                link_type=str(l.get("link_type", "fiber")),
            ))
        return topo


@dataclass
class NetworkSimResult:
    """Result of a network-scale QKD simulation."""

    topology: dict
    paths: list[dict]
    link_results: dict[str, dict]
    routing_table: dict[str, dict]
    aggregate_metrics: dict
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "topology": self.topology,
            "paths": self.paths,
            "link_results": self.link_results,
            "routing_table": self.routing_table,
            "aggregate_metrics": self.aggregate_metrics,
            "warnings": self.warnings,
        }
