"""Topology builders for network layouts."""

from __future__ import annotations


def build_link(node_a: str, node_b: str, channel_cfg: dict) -> dict:
    return {
        "nodes": [node_a, node_b],
        "links": [{"a": node_a, "b": node_b, "channel": channel_cfg}],
    }


def build_chain(nodes: list[str], channel_cfg: dict) -> dict:
    links = []
    for idx in range(len(nodes) - 1):
        links.append({"a": nodes[idx], "b": nodes[idx + 1], "channel": channel_cfg})
    return {"nodes": nodes, "links": links}


def build_star(center: str, nodes: list[str], channel_cfg: dict) -> dict:
    links = []
    for node in nodes:
        links.append({"a": center, "b": node, "channel": channel_cfg})
    return {"nodes": [center] + nodes, "links": links}


def topology_dict_to_network(topo_dict: dict) -> "NetworkTopology":
    """Convert legacy ``{nodes, links}`` dict to :class:`NetworkTopology`."""
    from photonstrust.network.types import NetworkLink, NetworkNode, NetworkTopology

    nt = NetworkTopology()
    for idx, nid in enumerate(topo_dict.get("nodes", [])):
        nt.add_node(NetworkNode(node_id=str(nid)))
    for idx, link in enumerate(topo_dict.get("links", [])):
        nt.add_link(NetworkLink(
            link_id=f"link_{idx}",
            node_a=str(link["a"]),
            node_b=str(link["b"]),
            channel_cfg=link.get("channel", {}),
            distance_km=float(link.get("distance_km", 0)),
        ))
    return nt
