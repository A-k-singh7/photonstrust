"""PIC layout spec normalization (v0.1).

We intentionally keep the v0.1 contract simple and dict-based so it can be
carried through APIs and artifacts without custom serialization code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LayerSpec:
    layer: int
    datatype: int


def _as_layer_spec(v: Any, *, default: LayerSpec) -> LayerSpec:
    if v is None:
        return default
    if isinstance(v, LayerSpec):
        return v
    if isinstance(v, (list, tuple)) and len(v) == 2:
        return LayerSpec(layer=int(v[0]), datatype=int(v[1]))
    if isinstance(v, dict):
        if "layer" in v and "datatype" in v:
            return LayerSpec(layer=int(v["layer"]), datatype=int(v["datatype"]))
    raise ValueError(f"Invalid layer spec: {v!r}. Expected [layer, datatype] or {{layer, datatype}}.")


def normalize_layout_settings(settings: dict[str, Any] | None) -> dict[str, Any]:
    s = dict(settings or {})

    grid_um = float(s.get("grid_um", 50.0) or 50.0)
    if grid_um <= 0.0:
        raise ValueError("settings.grid_um must be > 0")

    # UI node positions are typically in "canvas units" (pixels). v0.1 uses a
    # scalar to convert UI units to microns.
    ui_scale_um_per_unit = float(s.get("ui_scale_um_per_unit", 1.0) or 1.0)
    if ui_scale_um_per_unit <= 0.0:
        raise ValueError("settings.ui_scale_um_per_unit must be > 0")

    waveguide_width_um = s.get("waveguide_width_um")
    waveguide_width_um = float(waveguide_width_um) if waveguide_width_um is not None else None
    if waveguide_width_um is not None and waveguide_width_um <= 0.0:
        raise ValueError("settings.waveguide_width_um must be > 0 when provided")

    port_offset_um = float(s.get("port_offset_um", 10.0) or 10.0)
    if port_offset_um <= 0.0:
        raise ValueError("settings.port_offset_um must be > 0")

    port_pitch_um = float(s.get("port_pitch_um", 10.0) or 10.0)
    if port_pitch_um <= 0.0:
        raise ValueError("settings.port_pitch_um must be > 0")

    component_box_w_um = float(s.get("component_box_w_um", 20.0) or 20.0)
    component_box_h_um = float(s.get("component_box_h_um", 10.0) or 10.0)
    if component_box_w_um <= 0.0 or component_box_h_um <= 0.0:
        raise ValueError("settings.component_box_w_um and component_box_h_um must be > 0")

    coord_tol_um = float(s.get("coord_tol_um", 1e-6) or 1e-6)
    if coord_tol_um <= 0.0:
        raise ValueError("settings.coord_tol_um must be > 0")

    waveguide_layer = _as_layer_spec(s.get("waveguide_layer"), default=LayerSpec(layer=1, datatype=0))
    component_layer = _as_layer_spec(s.get("component_layer"), default=LayerSpec(layer=2, datatype=0))
    label_layer = _as_layer_spec(s.get("label_layer"), default=LayerSpec(layer=10, datatype=0))

    label_prefix = str(s.get("label_prefix", "PTPORT") or "PTPORT").strip()
    if not label_prefix:
        raise ValueError("settings.label_prefix must be non-empty")

    cell_name = str(s.get("cell_name", "TOP") or "TOP").strip() or "TOP"

    return {
        "grid_um": grid_um,
        "ui_scale_um_per_unit": ui_scale_um_per_unit,
        "waveguide_width_um": waveguide_width_um,
        "port_offset_um": port_offset_um,
        "port_pitch_um": port_pitch_um,
        "component_box_w_um": component_box_w_um,
        "component_box_h_um": component_box_h_um,
        "coord_tol_um": coord_tol_um,
        "waveguide_layer": {"layer": waveguide_layer.layer, "datatype": waveguide_layer.datatype},
        "component_layer": {"layer": component_layer.layer, "datatype": component_layer.datatype},
        "label_layer": {"layer": label_layer.layer, "datatype": label_layer.datatype},
        "label_prefix": label_prefix,
        "cell_name": cell_name,
    }


def node_ui_position_um(node: dict[str, Any], *, ui_scale_um_per_unit: float) -> tuple[float, float] | None:
    ui = node.get("ui")
    if not isinstance(ui, dict):
        return None
    pos = ui.get("position")
    if isinstance(pos, dict) and "x" in pos and "y" in pos:
        try:
            x = float(pos.get("x"))
            y = float(pos.get("y"))
            return (x * ui_scale_um_per_unit, y * ui_scale_um_per_unit)
        except Exception:
            return None
    # Back-compat: allow ui to directly contain x/y.
    if "x" in ui and "y" in ui:
        try:
            x = float(ui.get("x"))
            y = float(ui.get("y"))
            return (x * ui_scale_um_per_unit, y * ui_scale_um_per_unit)
        except Exception:
            return None
    return None
