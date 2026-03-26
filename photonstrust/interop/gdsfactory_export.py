"""Export PhotonsTrust graph to gdsfactory format."""
from __future__ import annotations
from dataclasses import dataclass

# Internal kind -> gdsfactory function name mapping
_KIND_TO_GDS = {
    "pic.mmi": "mmi1x2",
    "pic.y_branch": "y_branch",
    "pic.mzm": "mzi",
    "pic.crossing": "crossing",
    "pic.grating_coupler": "grating_coupler_elliptical",
    "pic.ring_filter": "ring_single",
    "pic.waveguide": "straight",
    "pic.heater": "straight_heater_metal",
    "pic.photodetector": "ge_detector",
    "pic.ssc": "taper",
}

# Reverse port mapping
_INTERNAL_TO_GDS_PORT = {
    "in": "o1",
    "out": "o2",
    "out_2": "o3",
    "out_3": "o4",
}


@dataclass(frozen=True)
class ExportedNetlist:
    """A netlist exported for gdsfactory."""
    name: str
    instances: dict[str, dict]  # inst_id -> {"component": cell_name, "settings": {...}}
    connections: dict[str, str]  # "inst1,port" -> "inst2,port"
    ports: dict[str, str]       # exposed ports


def _map_port_to_gds(internal_port: str) -> str:
    """Map internal port name to gdsfactory convention."""
    return _INTERNAL_TO_GDS_PORT.get(internal_port, internal_port)


def _kind_to_gds_cell(kind: str) -> str:
    """Map internal component kind to gdsfactory cell name."""
    return _KIND_TO_GDS.get(kind, kind.replace("pic.", ""))


def export_to_netlist(
    graph: dict,
    pdk_name: str | None = None,
) -> ExportedNetlist:
    """Export PhotonsTrust graph dict to gdsfactory-compatible netlist.

    Parameters
    ----------
    graph : dict
        PhotonsTrust graph with 'nodes' and 'edges' keys.
    pdk_name : str or None
        PDK name for cell name resolution.
    """
    nodes = graph.get("nodes", [])
    edges_list = graph.get("edges", [])
    circuit_id = graph.get("id", "exported_circuit")

    instances = {}
    for node in nodes:
        node_id = node["id"]
        kind = node.get("kind", "pic.waveguide")
        cell_name = _kind_to_gds_cell(kind)

        settings = {}
        params = node.get("params", {})
        for k, v in params.items():
            if isinstance(v, (int, float, str, bool)):
                settings[k] = v

        instances[node_id] = {
            "component": cell_name,
            "settings": settings,
        }

    connections = {}
    for edge in edges_list:
        src = edge["from"]
        dst = edge["to"]
        src_port = _map_port_to_gds(edge.get("from_port", "out"))
        dst_port = _map_port_to_gds(edge.get("to_port", "in"))

        connections[f"{src},{src_port}"] = f"{dst},{dst_port}"

    # Find exposed ports (nodes with unconnected ports)
    connected_ports: set[str] = set()
    for edge in edges_list:
        connected_ports.add(f'{edge["from"]}:{edge.get("from_port", "out")}')
        connected_ports.add(f'{edge["to"]}:{edge.get("to_port", "in")}')

    ports = {}
    for node in nodes:
        node_id = node["id"]
        kind = node.get("kind", "")
        # Check typical input/output ports
        for port in ["in", "out", "out_2"]:
            key = f"{node_id}:{port}"
            if key not in connected_ports:
                gds_port = _map_port_to_gds(port)
                ports[f"{node_id}_{port}"] = f"{node_id},{gds_port}"

    return ExportedNetlist(
        name=circuit_id,
        instances=instances,
        connections=connections,
        ports=ports,
    )


def export_to_netlist_yaml(graph: dict, pdk_name: str | None = None) -> str:
    """Export to YAML string format compatible with gdsfactory."""
    netlist = export_to_netlist(graph, pdk_name)

    lines = [f"name: {netlist.name}", "", "instances:"]
    for inst_id, info in netlist.instances.items():
        lines.append(f"  {inst_id}:")
        lines.append(f"    component: {info['component']}")
        if info.get("settings"):
            lines.append("    settings:")
            for k, v in info["settings"].items():
                lines.append(f"      {k}: {v}")

    lines.extend(["", "connections:"])
    for src, dst in netlist.connections.items():
        lines.append(f"  {src}: {dst}")

    if netlist.ports:
        lines.extend(["", "ports:"])
        for name, ref in netlist.ports.items():
            lines.append(f"  {name}: {ref}")

    return "\n".join(lines) + "\n"
