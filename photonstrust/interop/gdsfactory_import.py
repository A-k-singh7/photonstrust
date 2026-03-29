"""Import gdsfactory components/netlists into PhotonsTrust graph format."""
from __future__ import annotations
from dataclasses import dataclass

# Default port name mapping: gdsfactory convention -> internal
_PORT_MAP = {
    "o1": "in",
    "o2": "out",
    "o3": "out_2",
    "o4": "out_3",
    "in": "in",
    "out": "out",
}

@dataclass(frozen=True)
class ImportedComponent:
    """A component imported from gdsfactory."""
    name: str
    kind: str  # internal kind (e.g., "pic.mmi")
    ports: dict[str, str]  # port_name -> direction
    params: dict  # component parameters

@dataclass(frozen=True)
class ImportedCircuit:
    """A full circuit imported from gdsfactory."""
    circuit_id: str
    nodes: list[dict]
    edges: list[dict]
    n_ports: int


def _map_port_name(gds_port_name: str, custom_map: dict | None = None) -> str:
    """Map a gdsfactory port name to internal convention."""
    m = {**_PORT_MAP, **(custom_map or {})}
    return m.get(gds_port_name, gds_port_name)


def _infer_kind_from_cell_name(cell_name: str, pdk_cells: dict | None = None) -> str:
    """Infer internal component kind from gdsfactory cell name.

    First checks PDK cell mapping, then falls back to heuristics.
    """
    if pdk_cells:
        for cell_id, info in pdk_cells.items():
            if cell_id == cell_name or cell_name.startswith(cell_id):
                return info.get("maps_to_internal_kind", f"pic.{cell_name}")

    # Heuristic mapping
    name_lower = cell_name.lower()
    if "mmi" in name_lower:
        return "pic.mmi"
    if "y_branch" in name_lower or "ybranch" in name_lower:
        return "pic.y_branch"
    if "mzm" in name_lower or "mzi" in name_lower:
        return "pic.mzm"
    if "crossing" in name_lower:
        return "pic.crossing"
    if "grating" in name_lower or "gc" in name_lower:
        return "pic.grating_coupler"
    if "ring" in name_lower:
        return "pic.ring_filter"
    if "waveguide" in name_lower or "straight" in name_lower:
        return "pic.waveguide"
    if "heater" in name_lower:
        return "pic.heater"
    if "photodetect" in name_lower or "pd" == name_lower:
        return "pic.photodetector"

    return f"pic.{cell_name}"


def import_gdsfactory_component(
    component,
    pdk_cells: dict | None = None,
    port_map: dict | None = None,
) -> ImportedComponent:
    """Import a single gdsfactory Component into PhotonsTrust format.

    Parameters
    ----------
    component : gf.Component (or duck-typed object with .name and .ports)
        The gdsfactory component.
    pdk_cells : dict or None
        PDK cell mapping for kind inference.
    port_map : dict or None
        Custom port name mapping.
    """
    name = getattr(component, "name", str(component))
    cell_name = getattr(component, "function_name", name) if hasattr(component, "function_name") else name

    kind = _infer_kind_from_cell_name(cell_name, pdk_cells)

    ports = {}
    comp_ports = getattr(component, "ports", {})
    if isinstance(comp_ports, dict):
        port_iter = comp_ports.items()
    elif hasattr(comp_ports, '__iter__'):
        port_iter = [(getattr(p, 'name', str(p)), p) for p in comp_ports]
    else:
        port_iter = []

    for port_name, port_obj in port_iter:
        internal_name = _map_port_name(str(port_name), port_map)
        orientation = getattr(port_obj, 'orientation', 0)
        if orientation is not None and (orientation % 360) in (0, 180):
            direction = "horizontal"
        else:
            direction = "vertical"
        ports[internal_name] = direction

    # Extract settings/params if available
    settings = {}
    if hasattr(component, 'settings'):
        s = component.settings
        if isinstance(s, dict):
            settings = dict(s)
        elif hasattr(s, 'model_dump'):
            settings = s.model_dump()

    return ImportedComponent(name=name, kind=kind, ports=ports, params=settings)


def import_gdsfactory_netlist(
    netlist: dict,
    pdk_cells: dict | None = None,
    port_map: dict | None = None,
) -> ImportedCircuit:
    """Import a gdsfactory YAML netlist dict into PhotonsTrust graph.

    Expected netlist format:
    {"instances": {"inst_name": {"component": "cell_name", "settings": {...}}, ...},
     "connections": {"inst1,port1": "inst2,port2", ...},
     "ports": {"port_name": "inst,port", ...}}
    """
    instances = netlist.get("instances", {})
    connections = netlist.get("connections", {})
    top_ports = netlist.get("ports", {})

    # Build nodes
    nodes = []
    for inst_name, inst_info in instances.items():
        if isinstance(inst_info, dict):
            cell_name = inst_info.get("component", inst_name)
            settings = inst_info.get("settings", {})
        else:
            cell_name = str(inst_info)
            settings = {}

        kind = _infer_kind_from_cell_name(cell_name, pdk_cells)
        nodes.append({
            "id": inst_name,
            "kind": kind,
            "params": settings,
        })

    # Build edges from connections
    edges = []
    for src, dst in connections.items():
        src_parts = src.split(",")
        dst_parts = dst.split(",")

        src_inst = src_parts[0].strip()
        src_port = _map_port_name(src_parts[1].strip() if len(src_parts) > 1 else "o1", port_map)
        dst_inst = dst_parts[0].strip()
        dst_port = _map_port_name(dst_parts[1].strip() if len(dst_parts) > 1 else "o1", port_map)

        edges.append({
            "from": src_inst,
            "to": dst_inst,
            "from_port": src_port,
            "to_port": dst_port,
        })

    n_ports = len(top_ports)
    circuit_id = netlist.get("name", "imported_circuit")

    return ImportedCircuit(
        circuit_id=circuit_id,
        nodes=nodes,
        edges=edges,
        n_ports=n_ports,
    )
