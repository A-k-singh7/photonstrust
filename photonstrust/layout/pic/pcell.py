"""KLayout PCell (Parametric Cell) registration API for PhotonTrust PIC components.

PCells are KLayout's native mechanism for components that re-generate their
geometry whenever parameters change — equivalent to GDSFactory's pcells but
running directly inside KLayout.

Two modes
---------
1. **klayout mode** (requires ``pip install klayout``):
   - Subclasses ``klayout.db.PCellDeclarationHelper``
   - Registers via ``klayout.db.Library`` → accessible in KLayout GUI
   - Full polygon geometry with boolean operations

2. **Fallback / pure-Python mode** (always available):
   - Serialises PCell definitions as JSON
   - Can be imported into KLayout via the ``tools/klayout/macros/pt_pcell_load.py`` macro

Usage (in-process)
------------------
    from photonstrust.layout.pic.pcell import register_all_pcells, create_pcell_gds

    # Register with an existing klayout.db.Layout
    import klayout.db as db
    layout = db.Layout()
    register_all_pcells(layout)

    # Or: generate a GDS containing all PCell instances for inspection
    create_pcell_gds("photontrust_pcells.gds")

Usage (JSON export, no KLayout needed)
---------------------------------------
    from photonstrust.layout.pic.pcell import export_pcell_library_json
    export_pcell_library_json("pcell_library.json")
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from photonstrust.layout.pic.klayout_cell import (
    component_gdl_cell, supported_kinds,
    LAYER_WG, LAYER_METAL, LAYER_PORT, LAYER_BOUNDARY, LAYER_SLAB,
)


# ---------------------------------------------------------------------------
# PCell parameter schema (used by both KLayout and JSON modes)
# ---------------------------------------------------------------------------

_PCELL_PARAMS: dict[str, list[dict[str, Any]]] = {
    "pic.waveguide": [
        {"name": "length_um",       "type": "double", "default": 100.0, "description": "Waveguide length (µm)"},
        {"name": "width_um",        "type": "double", "default": 0.45,  "description": "Waveguide core width (µm)"},
        {"name": "loss_db_per_cm",  "type": "double", "default": 3.0,   "description": "Propagation loss (dB/cm)"},
        {"name": "n_g",             "type": "double", "default": 4.0,   "description": "Group index"},
    ],
    "pic.phase_shifter": [
        {"name": "phase_rad",        "type": "double", "default": 0.0,  "description": "Phase shift (rad)"},
        {"name": "length_um",        "type": "double", "default": 50.0, "description": "Heater length (µm)"},
        {"name": "width_um",         "type": "double", "default": 0.45, "description": "WG core width (µm)"},
        {"name": "heater_width_um",  "type": "double", "default": 2.0,  "description": "Metal heater width (µm)"},
        {"name": "insertion_loss_db","type": "double", "default": 0.5,  "description": "Insertion loss (dB)"},
    ],
    "pic.coupler": [
        {"name": "coupling_ratio",       "type": "double", "default": 0.5,  "description": "Power coupling ratio κ"},
        {"name": "gap_um",               "type": "double", "default": 0.2,  "description": "Coupling gap (µm)"},
        {"name": "coupler_length_um",    "type": "double", "default": 10.0, "description": "Coupling region length (µm)"},
        {"name": "s_bend_length_um",     "type": "double", "default": 20.0, "description": "S-bend length (µm)"},
        {"name": "insertion_loss_db",    "type": "double", "default": 0.0,  "description": "Insertion loss (dB)"},
    ],
    "pic.ring": [
        {"name": "radius_um",        "type": "double", "default": 10.0,  "description": "Ring radius (µm)"},
        {"name": "coupling_ratio",   "type": "double", "default": 0.002, "description": "Bus coupling ratio κ"},
        {"name": "n_eff",            "type": "double", "default": 2.4,   "description": "Effective index"},
        {"name": "gap_um",           "type": "double", "default": 0.15,  "description": "Ring-bus gap (µm)"},
        {"name": "loss_db_per_cm",   "type": "double", "default": 3.0,   "description": "Round-trip loss (dB/cm)"},
    ],
    "pic.grating_coupler": [
        {"name": "width_um",   "type": "double", "default": 12.0, "description": "Grating width (µm)"},
        {"name": "length_um",  "type": "double", "default": 20.0, "description": "Grating length (µm)"},
        {"name": "n_teeth",    "type": "int",    "default": 20,   "description": "Number of grating teeth"},
    ],
    "pic.edge_coupler": [
        {"name": "length_um",    "type": "double", "default": 30.0, "description": "Taper length (µm)"},
        {"name": "tip_width_um", "type": "double", "default": 0.1,  "description": "Tip width (µm)"},
    ],
    "pic.isolator_2port": [
        {"name": "length_um",      "type": "double", "default": 40.0, "description": "Component length (µm)"},
        {"name": "isolation_db",   "type": "double", "default": 30.0, "description": "Isolation (dB)"},
    ],
    "pic.touchstone_2port": [
        {"name": "touchstone_path", "type": "string", "default": "", "description": "Path to .s2p file"},
    ],
    "pic.touchstone_nport": [
        {"name": "touchstone_path", "type": "string", "default": "", "description": "Path to .sNp file"},
        {"name": "n_ports",         "type": "int",    "default": 4,   "description": "Number of ports"},
    ],
}


# ---------------------------------------------------------------------------
# JSON PCell library export (no KLayout needed)
# ---------------------------------------------------------------------------

def get_pcell_schema(kind: str) -> list[dict[str, Any]]:
    """Return the parameter schema list for a component kind."""
    k = str(kind).strip().lower()
    if k not in _PCELL_PARAMS:
        raise KeyError(f"No PCell schema for {kind!r}. Supported: {sorted(_PCELL_PARAMS.keys())}")
    return _PCELL_PARAMS[k]


def pcell_instance(
    kind: str,
    params: dict[str, Any] | None = None,
    *,
    x: float = 0.0,
    y: float = 0.0,
    rotation_deg: float = 0.0,
    instance_name: str | None = None,
) -> dict[str, Any]:
    """Return a PCell instance dict (JSON-serialisable).

    Parameters
    ----------
    kind:
        PhotonTrust component kind.
    params:
        Parameter overrides on top of schema defaults.
    x, y:
        Placement origin (µm).
    rotation_deg:
        Rotation in degrees.
    instance_name:
        Optional instance label.
    """
    schema = get_pcell_schema(kind)
    defaults = {p["name"]: p["default"] for p in schema}
    merged = {**defaults, **(params or {})}
    cell = component_gdl_cell(kind, merged)
    return {
        "kind": kind,
        "cell_name": cell["cell_name"],
        "params": merged,
        "placement": {"x": x, "y": y, "rotation_deg": rotation_deg},
        "instance_name": instance_name or cell["cell_name"],
        "geometry": cell,
    }


def export_pcell_library_json(
    output_path: str | Path,
    *,
    include_geometry: bool = True,
) -> Path:
    """Export the full PCell library as a JSON file.

    Each entry contains the parameter schema, defaults, and optionally the
    GDL geometry for preview rendering.

    Parameters
    ----------
    output_path:
        Destination JSON file path.
    include_geometry:
        If True, each entry includes GDL cell geometry.
    """
    lib: dict[str, Any] = {
        "schema_version": "0.1",
        "library_name": "PhotonTrust_PIC",
        "description": "Parametric PIC component library for KLayout",
        "components": {},
    }
    for kind in sorted(_PCELL_PARAMS.keys()):
        schema = _PCELL_PARAMS[kind]
        defaults = {p["name"]: p["default"] for p in schema}
        entry: dict[str, Any] = {
            "kind": kind,
            "parameters": schema,
        }
        if include_geometry:
            try:
                entry["geometry"] = component_gdl_cell(kind, defaults)
            except Exception as exc:
                entry["geometry_error"] = str(exc)
        lib["components"][kind] = entry

    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(lib, indent=2), encoding="utf-8")
    return p.resolve()


# ---------------------------------------------------------------------------
# KLayout PCellDeclarationHelper subclasses (requires klayout Python pkg)
# ---------------------------------------------------------------------------

def _register_pcells_klayout(layout: Any) -> None:
    """Register all PhotonTrust PCells in a ``klayout.db.Layout``.

    Called by ``register_all_pcells(layout)`` when the klayout package is
    available. Each PCell uses the GDL geometry engine as its produce method.
    """
    import klayout.db as db  # type: ignore[import-untyped]

    class _PTPCell(db.PCellDeclarationHelper):
        def __init__(self, kind: str, schema: list[dict]) -> None:
            super().__init__()
            self._kind = kind
            for p in schema:
                typ = p.get("type", "double")
                default = p.get("default", 0.0)
                desc = p.get("description", "")
                if typ == "double":
                    self.param(p["name"], self.TypeDouble, desc, default=float(default))
                elif typ == "int":
                    self.param(p["name"], self.TypeInt, desc, default=int(default))
                elif typ == "string":
                    self.param(p["name"], self.TypeString, desc, default=str(default))

        def display_text_impl(self) -> str:
            return f"PT_{self._kind}"

        def can_create_from_shape_impl(self) -> bool:
            return False

        def produce_impl(self) -> None:
            params: dict[str, Any] = {}
            schema = _PCELL_PARAMS.get(self._kind, [])
            for p in schema:
                try:
                    params[p["name"]] = getattr(self, p["name"])
                except AttributeError:
                    params[p["name"]] = p.get("default")

            cell_def = component_gdl_cell(self._kind, params)
            for shape in cell_def.get("shapes", []):
                if shape.get("type") != "rect":
                    continue
                layer_idx = self.layout.layer(
                    shape.get("layer", 1), shape.get("datatype", 0)
                )
                b = shape["bbox"]
                box = db.DBox(b[0], b[1], b[2], b[3])
                self.cell.shapes(layer_idx).insert(box)

    lib = db.Library()
    lib.description = "PhotonTrust PIC Component Library"
    for kind, schema in _PCELL_PARAMS.items():
        pcell = _PTPCell(kind, schema)
        lib.layout().register_pcell(f"PT_{kind.replace('.', '_')}", pcell)
    lib.register("PhotonTrust")


def register_all_pcells(layout: Any | None = None) -> bool:
    """Register all PhotonTrust PCells with KLayout.

    Parameters
    ----------
    layout:
        Optional ``klayout.db.Layout`` instance. If ``None``, registers
        globally via ``klayout.db.Library``.

    Returns
    -------
    bool
        ``True`` if KLayout is available and PCells were registered.
        ``False`` if klayout is not installed (safe fallback).
    """
    try:
        _register_pcells_klayout(layout)
        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# create_pcell_gds: instantiate all PCells and write a demonstration GDS
# ---------------------------------------------------------------------------

def create_pcell_gds(
    output_path: str | Path,
    *,
    top_cell_name: str = "PT_PCELL_DEMO",
    dbu_um: float = 0.001,
) -> Path:
    """Create a GDS-II file with one instance of every PCell kind.

    Useful for visual inspection in KLayout. Requires ``pip install klayout``.

    Parameters
    ----------
    output_path:
        Destination ``.gds`` file.
    top_cell_name:
        Name of the top-level demo cell.
    """
    try:
        import klayout.db as db  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ImportError(
            "klayout Python package required: pip install klayout"
        ) from exc

    layout = db.Layout()
    layout.dbu = dbu_um
    top = layout.create_cell(top_cell_name)
    register_all_pcells(layout)

    x_cursor = 0.0
    for kind in sorted(_PCELL_PARAMS.keys()):
        defaults = {p["name"]: p["default"] for p in _PCELL_PARAMS[kind]}
        cell_def = component_gdl_cell(kind, defaults)
        cell = layout.create_cell(cell_def["cell_name"])

        for shape in cell_def.get("shapes", []):
            if shape.get("type") != "rect":
                continue
            layer_idx = layout.layer(shape.get("layer", 1), shape.get("datatype", 0))
            b = shape["bbox"]
            cell.shapes(layer_idx).insert(db.DBox(b[0], b[1], b[2], b[3]))

        t = db.DCellInstArray(
            cell.cell_index(),
            db.DTrans(db.DVector(x_cursor, 0.0))
        )
        top.insert(t)

        # Estimate width
        bboxes = [s["bbox"] for s in cell_def["shapes"] if s.get("layer") == LAYER_BOUNDARY[0]]
        w = max((abs(b[2] - b[0]) for b in bboxes), default=20.0)
        x_cursor += w + 10.0

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    layout.write(str(out))
    return out.resolve()
