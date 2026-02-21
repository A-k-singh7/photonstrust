"""KLayout GDS cell generation API for PhotonTrust PIC components.

This module enables creating GDS layout cells for every photonic component
in the library, *without* requiring KLayout to be installed. It outputs
GDS-II compatible geometry as a pure-Python data structure that can be:

1. Written to a plain-text GDS-ASCII (human-readable) for review
2. Passed to ``klayout.db`` (if available) for full GDS-II binary output
3. Passed to ``gdstk`` (if available) for GDS-II output

The geometry here is **schematic-level** – real foundry tapeout would replace
these placeholder shapes with PDK-specific pcells.

Usage
-----
    from photonstrust.layout.pic.klayout_cell import (
        component_gdl_cell,
        netlist_to_gdl,
        write_gdl,
        write_gds_via_klayout,
    )

    # Generate a single waveguide cell
    cell = component_gdl_cell("pic.waveguide", {"length_um": 100.0})
    print(cell)  # GDL-ASCII dict representation

    # Convert a whole netlist to GDS
    write_gdl("my_chip.gdl.json", netlist)
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

# Layer definitions (schematic-level, override for real PDK)
LAYER_WG      = (1, 0)    # Waveguide core
LAYER_SLAB    = (2, 0)    # Slab (rib waveguide)
LAYER_METAL   = (11, 0)   # Metal heater for phase shifter
LAYER_PORT    = (10, 0)   # Port markers / labels
LAYER_BOUNDARY = (99, 0)  # Cell boundary box


def _rect(x0: float, y0: float, x1: float, y1: float, layer: tuple[int, int]) -> dict:
    """Return a GDL rectangle shape dict (in µm)."""
    return {
        "type": "rect",
        "layer": layer[0],
        "datatype": layer[1],
        "bbox": [round(x0, 6), round(y0, 6), round(x1, 6), round(y1, 6)],
    }


def _port(x: float, y: float, angle_deg: float, name: str) -> dict:
    return {
        "type": "port",
        "layer": LAYER_PORT[0],
        "datatype": LAYER_PORT[1],
        "x": round(x, 6),
        "y": round(y, 6),
        "angle_deg": round(angle_deg, 2),
        "name": name,
    }


def _cell(name: str, shapes: list[dict], ports: list[dict]) -> dict:
    return {"cell_name": name, "shapes": shapes, "ports": ports}


# ---------------------------------------------------------------------------
# Per-component cell factories
# ---------------------------------------------------------------------------

def _cell_waveguide(params: dict[str, Any], name: str) -> dict:
    length_um = float(params.get("length_um", 100.0) or 100.0)
    width_um  = float(params.get("width_um", 0.45) or 0.45)
    shapes = [
        _rect(0, -width_um / 2, length_um, width_um / 2, LAYER_WG),
        _rect(0, -width_um / 2, length_um, width_um / 2, LAYER_BOUNDARY),
    ]
    ports = [
        _port(0, 0, 180, "in"),
        _port(length_um, 0, 0, "out"),
    ]
    return _cell(name, shapes, ports)


def _cell_phase_shifter(params: dict[str, Any], name: str) -> dict:
    length_um = float(params.get("length_um", 50.0) or 50.0)
    width_um  = float(params.get("width_um", 0.45) or 0.45)
    heater_w  = float(params.get("heater_width_um", 2.0) or 2.0)
    shapes = [
        _rect(0, -width_um / 2, length_um, width_um / 2, LAYER_WG),
        _rect(0, -heater_w / 2, length_um, heater_w / 2, LAYER_METAL),
        _rect(-1, -heater_w / 2 - 1, length_um + 1, heater_w / 2 + 1, LAYER_BOUNDARY),
    ]
    ports = [
        _port(0, 0, 180, "in"),
        _port(length_um, 0, 0, "out"),
    ]
    return _cell(name, shapes, ports)


def _cell_coupler(params: dict[str, Any], name: str) -> dict:
    """Symmetric directional coupler stub."""
    gap_um      = float(params.get("gap_um", 0.2) or 0.2)
    length_um   = float(params.get("coupler_length_um", 10.0) or 10.0)
    s_bend_um   = float(params.get("s_bend_length_um", 20.0) or 20.0)
    wg_width_um = float(params.get("width_um", 0.45) or 0.45)
    pitch_um    = gap_um + wg_width_um
    total_len   = s_bend_um * 2 + length_um
    shapes = [
        # Top waveguide
        _rect(0, pitch_um / 2 - wg_width_um / 2, total_len, pitch_um / 2 + wg_width_um / 2, LAYER_WG),
        # Bottom waveguide
        _rect(0, -pitch_um / 2 - wg_width_um / 2, total_len, -pitch_um / 2 + wg_width_um / 2, LAYER_WG),
        _rect(-1, -pitch_um, total_len + 1, pitch_um, LAYER_BOUNDARY),
    ]
    ports = [
        _port(0, pitch_um / 2, 180, "in1"),
        _port(0, -pitch_um / 2, 180, "in2"),
        _port(total_len, pitch_um / 2, 0, "out1"),
        _port(total_len, -pitch_um / 2, 0, "out2"),
    ]
    return _cell(name, shapes, ports)


def _cell_ring(params: dict[str, Any], name: str) -> dict:
    radius_um = float(params.get("radius_um", 10.0) or 10.0)
    wg_w      = float(params.get("width_um", 0.45) or 0.45)
    gap_um    = float(params.get("gap_um", 0.15) or 0.15)
    bus_len   = radius_um * 3

    shapes = [
        # Bus waveguide
        _rect(0, -(wg_w / 2), bus_len, (wg_w / 2), LAYER_WG),
        # Ring boundary (approximated as outer-inner annulus bbox)
        _rect(
            bus_len / 2 - radius_um - wg_w,
            gap_um + wg_w,
            bus_len / 2 + radius_um + wg_w,
            gap_um + wg_w + 2 * radius_um + 2 * wg_w,
            LAYER_WG,
        ),
        _rect(-1, -radius_um - wg_w - 1, bus_len + 1, 2 * radius_um + gap_um + 2 * wg_w + 1, LAYER_BOUNDARY),
    ]
    ports = [
        _port(0, 0, 180, "in"),
        _port(bus_len, 0, 0, "out"),
    ]
    return _cell(name, shapes, ports)


def _cell_grating_coupler(params: dict[str, Any], name: str) -> dict:
    width_um  = float(params.get("width_um", 12.0) or 12.0)
    length_um = float(params.get("length_um", 20.0) or 20.0)
    wg_w      = float(params.get("wg_width_um", 0.45) or 0.45)
    n_teeth   = int(params.get("n_teeth", 20) or 20)
    pitch_um  = length_um / max(1, n_teeth)

    shapes = [_rect(-width_um / 2, 0, width_um / 2, -length_um, LAYER_WG)]
    for i in range(n_teeth):
        y = -i * pitch_um - pitch_um / 4
        shapes.append(_rect(-width_um / 2, y, width_um / 2, y - pitch_um / 2, LAYER_SLAB))
    shapes.append(_rect(-wg_w / 2, 0, wg_w / 2, 5, LAYER_WG))
    shapes.append(_rect(-width_um / 2 - 1, -length_um - 1, width_um / 2 + 1, 6, LAYER_BOUNDARY))

    ports = [
        _port(0, 5, 90, "in"),
        _port(0, -length_um, 270, "out"),
    ]
    return _cell(name, shapes, ports)


def _cell_edge_coupler(params: dict[str, Any], name: str) -> dict:
    length_um = float(params.get("length_um", 30.0) or 30.0)
    tip_um    = float(params.get("tip_width_um", 0.1) or 0.1)
    wg_w      = float(params.get("wg_width_um", 0.45) or 0.45)

    # Taper from tip_um to wg_w
    shapes = [
        _rect(0, -tip_um / 2, length_um, tip_um / 2, LAYER_WG),   # placeholder linear taper
        _rect(0, -wg_w / 2, length_um, wg_w / 2, LAYER_SLAB),
        _rect(-1, -wg_w - 1, length_um + 1, wg_w + 1, LAYER_BOUNDARY),
    ]
    ports = [
        _port(0, 0, 180, "in"),
        _port(length_um, 0, 0, "out"),
    ]
    return _cell(name, shapes, ports)


def _cell_isolator(params: dict[str, Any], name: str) -> dict:
    length_um = float(params.get("length_um", 40.0) or 40.0)
    width_um  = float(params.get("width_um", 4.0) or 4.0)
    wg_w      = 0.45
    shapes = [
        _rect(0, -wg_w / 2, length_um, wg_w / 2, LAYER_WG),
        # Magnetic cladding region
        _rect(5, -width_um / 2, length_um - 5, width_um / 2, LAYER_METAL),
        _rect(-1, -width_um / 2 - 1, length_um + 1, width_um / 2 + 1, LAYER_BOUNDARY),
    ]
    ports = [
        _port(0, 0, 180, "in"),
        _port(length_um, 0, 0, "out"),
    ]
    return _cell(name, shapes, ports)


def _cell_touchstone_stub(params: dict[str, Any], name: str) -> dict:
    """Generic placeholder for Touchstone-defined components."""
    size_um = 20.0
    shapes = [_rect(0, 0, size_um, size_um, LAYER_WG),
              _rect(0, 0, size_um, size_um, LAYER_BOUNDARY)]
    ports = [
        _port(0, size_um / 2, 180, "in"),
        _port(size_um, size_um / 2, 0, "out"),
    ]
    return _cell(name, shapes, ports)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_CELL_REGISTRY: dict[str, Any] = {
    "pic.waveguide":         _cell_waveguide,
    "pic.phase_shifter":     _cell_phase_shifter,
    "pic.coupler":           _cell_coupler,
    "pic.ring":              _cell_ring,
    "pic.grating_coupler":   _cell_grating_coupler,
    "pic.edge_coupler":      _cell_edge_coupler,
    "pic.isolator_2port":    _cell_isolator,
    "pic.touchstone_2port":  _cell_touchstone_stub,
    "pic.touchstone_nport":  _cell_touchstone_stub,
}


def supported_kinds() -> list[str]:
    """Return all component kinds with GDS cell factories."""
    return sorted(_CELL_REGISTRY.keys())


def component_gdl_cell(
    kind: str,
    params: dict[str, Any] | None = None,
    *,
    cell_name: str | None = None,
) -> dict[str, Any]:
    """Generate a GDS Layout dict (GDL) for a single PIC component.

    Parameters
    ----------
    kind:
        PhotonTrust component kind string, e.g. ``"pic.waveguide"``.
    params:
        Component parameter overrides.
    cell_name:
        Override cell name (default: derived from kind).

    Returns
    -------
    dict
        GDL cell dict with keys ``cell_name``, ``shapes``, ``ports``.
    """
    k = str(kind).strip().lower()
    if k not in _CELL_REGISTRY:
        raise KeyError(
            f"No GDS cell for kind={kind!r}. Supported: {supported_kinds()}"
        )
    name = cell_name or ("PT_" + k.replace(".", "_"))
    return _CELL_REGISTRY[k](params or {}, name)


def netlist_to_gdl(netlist: dict[str, Any]) -> dict[str, Any]:
    """Convert a compiled PIC netlist into a GDL layout dict.

    Each node becomes a GDS cell instance. Edges are represented as simple
    straight-line connection annotations (not routed paths, which require a
    full router).

    Parameters
    ----------
    netlist:
        Dict matching the compiled netlist schema.

    Returns
    -------
    dict
        ``{"cells": [cell_def, ...], "instances": [inst, ...], "wires": [wire, ...]}``
    """
    circuit = netlist.get("circuit", {}) or {}
    nodes = circuit.get("nodes") or netlist.get("nodes") or []
    edges = circuit.get("edges") or netlist.get("edges") or []

    cells_seen: dict[str, dict] = {}
    instances: list[dict] = []

    # Lay out nodes in a simple left-to-right auto-placement grid
    x_cursor = 0.0
    node_ports: dict[str, dict[str, tuple[float, float]]] = {}

    for node in nodes:
        nid   = str(node.get("id", ""))
        kind  = str(node.get("kind", "")).strip().lower()
        params = node.get("params") or {}

        if kind not in _CELL_REGISTRY:
            kind_fallback = "pic.waveguide"
        else:
            kind_fallback = kind

        cell = component_gdl_cell(kind_fallback, params)
        cell_name = cell["cell_name"]
        if cell_name not in cells_seen:
            cells_seen[cell_name] = cell

        # Simple auto-placement: stack horizontally
        # Determine cell width from boundary bbox
        boundary_shapes = [s for s in cell["shapes"] if s.get("layer") == LAYER_BOUNDARY[0]]
        if boundary_shapes:
            bbox = boundary_shapes[-1]["bbox"]
            cell_w = abs(bbox[2] - bbox[0])
        else:
            cell_w = 20.0

        inst = {
            "cell_name": cell_name,
            "node_id": nid,
            "x": round(x_cursor, 4),
            "y": 0.0,
        }
        instances.append(inst)

        # Track absolute port positions for wire routing
        for p in cell["ports"]:
            node_ports.setdefault(nid, {})[p["name"]] = (
                round(x_cursor + p["x"], 4),
                round(p["y"], 4),
            )
        x_cursor += cell_w + 5.0

    # Build wire annotations (straight lines between connected ports)
    wires: list[dict] = []
    for edge in edges:
        from_node = str(edge.get("from", ""))
        from_port = str(edge.get("from_port", "out"))
        to_node   = str(edge.get("to", ""))
        to_port   = str(edge.get("to_port", "in"))
        p0 = node_ports.get(from_node, {}).get(from_port)
        p1 = node_ports.get(to_node, {}).get(to_port)
        if p0 and p1:
            wires.append({"from": list(p0), "to": list(p1), "layer": LAYER_WG[0]})

    return {
        "cells": list(cells_seen.values()),
        "instances": instances,
        "wires": wires,
    }


def write_gdl(
    output_path: str | Path,
    netlist: dict[str, Any],
) -> Path:
    """Write a GDL layout JSON to disk.

    Parameters
    ----------
    output_path:
        Destination ``.gdl.json`` file.
    netlist:
        Compiled netlist dict to convert.

    Returns
    -------
    Path
        Resolved output path.
    """
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    gdl = netlist_to_gdl(netlist)
    p.write_text(json.dumps(gdl, indent=2), encoding="utf-8")
    return p.resolve()


def write_gds_via_klayout(
    output_gds: str | Path,
    netlist: dict[str, Any],
    *,
    top_cell_name: str = "PT_TOP",
    dbu_um: float = 0.001,
) -> Path:
    """Convert a netlist to a GDS-II binary file using KLayout Python API.

    Requires ``klayout`` Python package: ``pip install klayout``.

    Parameters
    ----------
    output_gds:
        Destination ``.gds`` path.
    netlist:
        Compiled netlist dict.
    top_cell_name:
        Name of the top-level GDS cell.
    dbu_um:
        Database unit in µm (default 1 nm = 0.001 µm).

    Returns
    -------
    Path
        Resolved output ``.gds`` path.
    """
    try:
        import klayout.db as db  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ImportError(
            "The `klayout` Python package is required for GDS output. "
            "Install with: pip install klayout"
        ) from exc

    layout = db.Layout()
    layout.dbu = dbu_um
    top = layout.create_cell(top_cell_name)

    gdl = netlist_to_gdl(netlist)

    # Create a cell for each component type
    cell_map: dict[str, Any] = {}
    for cell_def in gdl["cells"]:
        cell = layout.create_cell(cell_def["cell_name"])
        cell_map[cell_def["cell_name"]] = cell
        for shape in cell_def["shapes"]:
            if shape["type"] == "rect":
                layer_idx = layout.layer(shape["layer"], shape.get("datatype", 0))
                b = shape["bbox"]
                box = db.DBox(b[0], b[1], b[2], b[3])
                cell.shapes(layer_idx).insert(box)

    # Place instances
    for inst in gdl["instances"]:
        cell_name = inst["cell_name"]
        if cell_name in cell_map:
            t = db.DCellInstArray(
                cell_map[cell_name].cell_index(),
                db.DTrans(db.DVector(inst["x"], inst["y"]))
            )
            top.insert(t)

    # Draw wires
    wg_layer = layout.layer(LAYER_WG[0], LAYER_WG[1])
    for wire in gdl["wires"]:
        p0 = db.DPoint(wire["from"][0], wire["from"][1])
        p1 = db.DPoint(wire["to"][0], wire["to"][1])
        top.shapes(wg_layer).insert(db.DPath([p0, p1], width=0.45))

    out = Path(output_gds)
    out.parent.mkdir(parents=True, exist_ok=True)
    layout.write(str(out))
    return out.resolve()
