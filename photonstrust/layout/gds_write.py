"""Dedicated GDS writer for PIC layout artifacts."""

from __future__ import annotations

import math
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


class OptionalDependencyError(RuntimeError):
    pass


def write_gds(
    netlist: dict[str, Any],
    pdk: Any,
    output_path: str | Path,
    routes: dict[str, Any] | list[dict[str, Any]] | None = None,
    ports: dict[str, Any] | list[dict[str, Any]] | None = None,
    settings: dict[str, Any] | None = None,
    timestamp: Any = None,
) -> Path:
    """Write a compact PIC layout GDS from placement/route sidecars."""

    if not isinstance(netlist, dict):
        raise TypeError("netlist must be an object")

    gdstk = _import_gdstk()
    s = dict(settings or {})

    wg_layer = _resolve_waveguide_layer(pdk, s.get("waveguide_layer"))
    comp_layer = _normalize_layer_spec(s.get("component_layer"), default_layer=2, default_datatype=0)
    label_layer = _normalize_layer_spec(s.get("label_layer"), default_layer=10, default_datatype=0)

    label_prefix = str(s.get("label_prefix", "PTPORT") or "PTPORT").strip() or "PTPORT"
    cell_name = _resolve_top_cell_name(s)
    unit = _as_positive_float(s.get("gds_unit"), 1e-6)
    precision = _as_positive_float(s.get("gds_precision"), 1e-9)

    lib = gdstk.Library(unit=unit, precision=precision)
    top = gdstk.Cell(cell_name)
    lib.add(top)

    ports_list = _coerce_ports(ports)
    node_positions_um = _resolve_node_positions_um(netlist, ports_list, s)
    _add_component_geometry(
        gdstk=gdstk,
        lib=lib,
        top=top,
        netlist=netlist,
        node_positions_um=node_positions_um,
        layer=comp_layer,
        box_w_um=_as_positive_float(s.get("component_box_w_um"), 20.0),
        box_h_um=_as_positive_float(s.get("component_box_h_um"), 10.0),
    )
    _add_route_geometry(
        gdstk=gdstk,
        top=top,
        routes=_coerce_routes(routes),
        layer=wg_layer,
        default_width_um=_default_waveguide_width_um(pdk, s),
    )
    _add_port_annotations(
        gdstk=gdstk,
        top=top,
        ports=ports_list,
        layer=label_layer,
        label_prefix=label_prefix,
        marker_size_um=_as_positive_float(s.get("port_marker_size_um"), 1.0),
    )

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    ts = _resolve_timestamp(timestamp=timestamp, settings=s)
    if ts is None:
        lib.write_gds(out_path)
    else:
        lib.write_gds(out_path, timestamp=ts)
    return out_path


def _import_gdstk():
    try:
        import gdstk  # type: ignore
    except Exception as exc:
        raise OptionalDependencyError(
            "GDS emission requires optional dependency 'gdstk'. "
            "Install with: pip install 'photonstrust[layout]'"
        ) from exc
    return gdstk


def _resolve_waveguide_layer(pdk: Any, fallback: Any) -> dict[str, int]:
    pdk_layer = _extract_waveguide_layer_from_pdk(pdk)
    if pdk_layer is not None:
        return pdk_layer
    return _normalize_layer_spec(fallback, default_layer=1, default_datatype=0)


def _extract_waveguide_layer_from_pdk(pdk: Any) -> dict[str, int] | None:
    if not isinstance(pdk, Mapping):
        return None
    layer_stack = pdk.get("layer_stack")
    entries = _iter_layer_stack_entries(layer_stack)
    if not entries:
        return None

    preferred_keys = {"waveguide", "wg", "core", "strip", "si", "si_core", "silicon_core"}
    for names, value in entries:
        if any(name in preferred_keys for name in names):
            layer = _layer_spec_from_any(value)
            if layer is not None:
                return layer

    for names, value in entries:
        if any(("waveguide" in name) or name == "wg" or ("core" in name) or ("strip" in name) for name in names):
            layer = _layer_spec_from_any(value)
            if layer is not None:
                return layer

    for _names, value in entries:
        layer = _layer_spec_from_any(value)
        if layer is not None:
            return layer
    return None


def _iter_layer_stack_entries(layer_stack: Any) -> list[tuple[set[str], Any]]:
    entries: list[tuple[set[str], Any]] = []
    if isinstance(layer_stack, Mapping):
        for key, value in layer_stack.items():
            names = {str(key).strip().lower()}
            names.update(_layer_entry_names(value))
            entries.append((names, value))
        return entries
    if isinstance(layer_stack, list):
        for value in layer_stack:
            entries.append((_layer_entry_names(value), value))
        return entries
    return entries


def _layer_entry_names(value: Any) -> set[str]:
    out: set[str] = set()
    if not isinstance(value, Mapping):
        return out
    for key in ("name", "kind", "type", "role", "id", "layer_name"):
        raw = value.get(key)
        if raw is None:
            continue
        text = str(raw).strip().lower()
        if text:
            out.add(text)
    return out


def _normalize_layer_spec(raw: Any, *, default_layer: int, default_datatype: int) -> dict[str, int]:
    layer = _layer_spec_from_any(raw)
    if layer is not None:
        return layer
    return {"layer": int(default_layer), "datatype": int(default_datatype)}


def _layer_spec_from_any(raw: Any) -> dict[str, int] | None:
    if raw is None:
        return None

    if isinstance(raw, Mapping):
        if "layer" in raw:
            layer_field = raw.get("layer")
            nested = _layer_spec_from_any(layer_field) if isinstance(layer_field, Mapping) else None
            if nested is not None:
                datatype = raw.get("datatype")
                if datatype is not None:
                    nested["datatype"] = int(datatype)
                return nested
            try:
                layer = int(layer_field)
            except Exception:
                layer = None
            if layer is not None:
                datatype = int(raw.get("datatype", raw.get("gds_datatype", 0)) or 0)
                return {"layer": layer, "datatype": datatype}

        if "gds_layer" in raw:
            try:
                layer = int(raw.get("gds_layer"))
            except Exception:
                layer = None
            if layer is not None:
                datatype = int(raw.get("gds_datatype", raw.get("datatype", 0)) or 0)
                return {"layer": layer, "datatype": datatype}

        for nested_key in ("gds", "spec", "drawing", "default"):
            if nested_key in raw:
                nested = _layer_spec_from_any(raw.get(nested_key))
                if nested is not None:
                    return nested
        return None

    if isinstance(raw, (list, tuple)) and len(raw) >= 1:
        try:
            layer = int(raw[0])
            datatype = int(raw[1]) if len(raw) > 1 else 0
        except Exception:
            return None
        return {"layer": layer, "datatype": datatype}

    if isinstance(raw, (int, float)):
        return {"layer": int(raw), "datatype": 0}
    return None


def _coerce_routes(routes: dict[str, Any] | list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if isinstance(routes, dict):
        raw = routes.get("routes")
        return list(raw) if isinstance(raw, list) else []
    if isinstance(routes, list):
        return list(routes)
    return []


def _coerce_ports(ports: dict[str, Any] | list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if isinstance(ports, dict):
        raw = ports.get("ports")
        return list(raw) if isinstance(raw, list) else []
    if isinstance(ports, list):
        return list(ports)
    return []


def _resolve_node_positions_um(
    netlist: dict[str, Any],
    ports: list[dict[str, Any]],
    settings: dict[str, Any],
) -> dict[str, tuple[float, float]]:
    explicit = settings.get("_node_positions_um")
    pos = _coerce_node_positions_um(explicit)
    if pos:
        return pos

    if ports:
        inferred = _infer_node_positions_from_ports(ports)
        if inferred:
            return inferred

    out: dict[str, tuple[float, float]] = {}
    grid_um = _as_positive_float(settings.get("grid_um"), 50.0)
    idx = 0
    nodes = netlist.get("nodes")
    if not isinstance(nodes, list):
        return out
    for node in sorted((n for n in nodes if isinstance(n, dict)), key=lambda n: str(n.get("id", "")).lower()):
        node_id = str(node.get("id", "")).strip()
        if not node_id:
            continue
        out[node_id] = (float(idx) * grid_um, 0.0)
        idx += 1
    return out


def _coerce_node_positions_um(raw: Any) -> dict[str, tuple[float, float]]:
    if not isinstance(raw, Mapping):
        return {}
    out: dict[str, tuple[float, float]] = {}
    for node_id_raw, value in raw.items():
        node_id = str(node_id_raw).strip()
        if not node_id:
            continue
        coords = _coerce_xy(value)
        if coords is None:
            continue
        out[node_id] = coords
    return out


def _infer_node_positions_from_ports(ports: list[dict[str, Any]]) -> dict[str, tuple[float, float]]:
    accum: dict[str, list[float]] = {}
    for port in ports:
        if not isinstance(port, dict):
            continue
        node = str(port.get("node", "")).strip()
        if not node:
            continue
        coords = _coerce_xy(port)
        if coords is None:
            continue
        rec = accum.setdefault(node, [0.0, 0.0, 0.0])
        rec[0] += coords[0]
        rec[1] += coords[1]
        rec[2] += 1.0

    out: dict[str, tuple[float, float]] = {}
    for node in sorted(accum.keys(), key=lambda s: s.lower()):
        sx, sy, c = accum[node]
        if c <= 0:
            continue
        out[node] = (float(sx / c), float(sy / c))
    return out


def _coerce_xy(value: Any) -> tuple[float, float] | None:
    if isinstance(value, Mapping):
        x_raw = value.get("x_um", value.get("x"))
        y_raw = value.get("y_um", value.get("y"))
        try:
            return (float(x_raw), float(y_raw))
        except Exception:
            return None
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        try:
            return (float(value[0]), float(value[1]))
        except Exception:
            return None
    return None


def _add_component_geometry(
    *,
    gdstk: Any,
    lib: Any,
    top: Any,
    netlist: dict[str, Any],
    node_positions_um: dict[str, tuple[float, float]],
    layer: dict[str, int],
    box_w_um: float,
    box_h_um: float,
) -> None:
    nodes = netlist.get("nodes")
    if not isinstance(nodes, list):
        return

    comp_cells: dict[str, Any] = {}
    used_names = {str(getattr(c, "name", "") or "") for c in getattr(lib, "cells", [])}

    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("id", "")).strip()
        if not node_id:
            continue
        kind = str(node.get("kind", "component") or "component").strip().lower()
        x0, y0 = node_positions_um.get(node_id, (0.0, 0.0))

        if kind not in comp_cells:
            comp_name = _unique_cell_name(f"PT_COMP_{_sanitize_cell_token(kind)}", used_names)
            comp_cell = gdstk.Cell(comp_name)
            comp_cell.add(
                gdstk.rectangle(
                    (-box_w_um / 2.0, -box_h_um / 2.0),
                    (box_w_um / 2.0, box_h_um / 2.0),
                    layer=int(layer["layer"]),
                    datatype=int(layer["datatype"]),
                )
            )
            lib.add(comp_cell)
            comp_cells[kind] = comp_cell
            used_names.add(comp_name)

        comp_cell = comp_cells[kind]
        try:
            ref_kwargs = _resolve_reference_transform(node)
            top.add(gdstk.Reference(comp_cell, (x0, y0), **ref_kwargs))
        except Exception:
            top.add(
                gdstk.rectangle(
                    (x0 - box_w_um / 2.0, y0 - box_h_um / 2.0),
                    (x0 + box_w_um / 2.0, y0 + box_h_um / 2.0),
                    layer=int(layer["layer"]),
                    datatype=int(layer["datatype"]),
                )
            )


def _add_route_geometry(
    *,
    gdstk: Any,
    top: Any,
    routes: list[dict[str, Any]],
    layer: dict[str, int],
    default_width_um: float,
) -> None:
    for route in routes:
        if not isinstance(route, dict):
            continue
        pts_raw = route.get("points_um")
        if not isinstance(pts_raw, list) or len(pts_raw) < 2:
            continue
        points: list[tuple[float, float]] = []
        for p in pts_raw:
            coords = _coerce_xy(p)
            if coords is None:
                points = []
                break
            points.append(coords)
        if len(points) < 2:
            continue
        width_um = _as_positive_float(route.get("width_um"), default_width_um)
        if width_um <= 0.0:
            continue
        top.add(
            gdstk.FlexPath(
                points,
                width_um,
                simple_path=True,
                layer=int(layer["layer"]),
                datatype=int(layer["datatype"]),
            )
        )


def _add_port_annotations(
    *,
    gdstk: Any,
    top: Any,
    ports: list[dict[str, Any]],
    layer: dict[str, int],
    label_prefix: str,
    marker_size_um: float,
) -> None:
    half = max(marker_size_um, 0.0) / 2.0
    for port in ports:
        if not isinstance(port, dict):
            continue
        node = str(port.get("node", "")).strip()
        name = str(port.get("port", "")).strip()
        coords = _coerce_xy(port)
        if not node or not name or coords is None:
            continue
        x, y = coords
        top.add(
            gdstk.rectangle(
                (x - half, y - half),
                (x + half, y + half),
                layer=int(layer["layer"]),
                datatype=int(layer["datatype"]),
            )
        )
        text = f"{label_prefix}:{node}:{name}"
        top.add(
            gdstk.Label(
                text,
                (x, y),
                layer=int(layer["layer"]),
                texttype=int(layer["datatype"]),
            )
        )


def _default_waveguide_width_um(pdk: Any, settings: dict[str, Any]) -> float:
    width = settings.get("waveguide_width_um")
    if width is not None:
        return _as_positive_float(width, 0.5)

    if isinstance(pdk, Mapping):
        rules = pdk.get("design_rules")
        if isinstance(rules, Mapping):
            return _as_positive_float(rules.get("min_waveguide_width_um"), 0.5)
    return 0.5


def _resolve_top_cell_name(settings: Mapping[str, Any]) -> str:
    for key in ("cell_name", "top_cell_name", "top_cell"):
        raw = settings.get(key)
        if raw is None:
            continue
        name = str(raw).strip()
        if name:
            return name
    return "TOP"


def _resolve_reference_transform(node: Mapping[str, Any]) -> dict[str, Any]:
    rotation_rad: float | None = None
    rotation_deg: float | None = None
    x_reflection: bool | None = None

    params = node.get("params")
    node_orientation = node.get("orientation")
    node_placement = node.get("placement")
    params_orientation = params.get("orientation") if isinstance(params, Mapping) else None
    params_placement = params.get("placement") if isinstance(params, Mapping) else None

    for source in (params, params_orientation, params_placement, node, node_orientation, node_placement):
        r_rad, r_deg, x_ref = _extract_transform_fields(source)
        if r_rad is not None:
            rotation_rad = r_rad
        if r_deg is not None:
            rotation_deg = r_deg
        if x_ref is not None:
            x_reflection = x_ref

    transform: dict[str, Any] = {}
    if rotation_deg is not None:
        transform["rotation"] = math.radians(rotation_deg)
    elif rotation_rad is not None:
        if abs(rotation_rad) > 2.0 * math.pi + 1e-6:
            transform["rotation"] = math.radians(rotation_rad)
        else:
            transform["rotation"] = rotation_rad
    if x_reflection is not None:
        transform["x_reflection"] = bool(x_reflection)
    return transform


def _extract_transform_fields(raw: Any) -> tuple[float | None, float | None, bool | None]:
    rotation_rad: float | None = None
    rotation_deg: float | None = None
    x_reflection: bool | None = None

    if isinstance(raw, Mapping):
        if "rotation" in raw:
            rotation_rad = _as_optional_float(raw.get("rotation"))
        if "rotation_deg" in raw:
            rotation_deg = _as_optional_float(raw.get("rotation_deg"))
        if "x_reflection" in raw:
            x_reflection = _as_optional_bool(raw.get("x_reflection"))
        if "mirror" in raw:
            x_reflection = _as_optional_bool(raw.get("mirror"))
        if "mirrored" in raw:
            x_reflection = _as_optional_bool(raw.get("mirrored"))
        if "orientation" in raw:
            o_rad, o_deg, o_reflect = _extract_transform_fields(raw.get("orientation"))
            if o_rad is not None:
                rotation_rad = o_rad
            if o_deg is not None:
                rotation_deg = o_deg
            if o_reflect is not None:
                x_reflection = o_reflect
        return rotation_rad, rotation_deg, x_reflection

    if isinstance(raw, str):
        token = raw.strip().upper()
        if not token:
            return None, None, None
        match = re.match(r"^R\s*([+-]?\d+(?:\.\d+)?)$", token)
        if match:
            return None, float(match.group(1)), None
        if token in {"MX", "MIRROR", "MIRROR_X", "X_REFLECTION", "XREFLECTION", "FLIPX", "X_FLIP"}:
            return None, None, True
        if token in {"NO_MIRROR", "NO_MIRROR_X", "NO_X_REFLECTION"}:
            return None, None, False
        return None, None, None

    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        return None, float(raw), None
    return None, None, None


def _as_optional_float(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def _as_optional_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return bool(value)
    if isinstance(value, str):
        key = value.strip().lower()
        if key in {"1", "true", "t", "yes", "y", "on"}:
            return True
        if key in {"0", "false", "f", "no", "n", "off"}:
            return False
    return None


def _resolve_timestamp(*, timestamp: Any, settings: dict[str, Any]) -> datetime | None:
    if timestamp is not None:
        return _coerce_timestamp(timestamp)

    settings_ts = settings.get("gds_timestamp", settings.get("timestamp"))
    if settings_ts is not None and str(settings_ts).strip():
        return _coerce_timestamp(settings_ts)

    env_ts = os.environ.get("PT_GDS_TIMESTAMP")
    if env_ts is not None and str(env_ts).strip():
        return _coerce_timestamp(env_ts)
    return None


def _coerce_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value))

    raw = str(value).strip()
    if not raw:
        raise ValueError("GDS timestamp must be non-empty when provided.")
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(raw)
    except Exception as exc:
        raise ValueError(
            "Invalid GDS timestamp; expected ISO-8601 string, datetime object, or epoch seconds."
        ) from exc


def _as_positive_float(value: Any, default: float) -> float:
    try:
        out = float(value)
    except Exception:
        out = float(default)
    if out <= 0.0:
        return float(default)
    return out


def _sanitize_cell_token(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_")
    return token or "COMP"


def _unique_cell_name(base: str, used_names: set[str]) -> str:
    if base not in used_names:
        return base
    idx = 1
    while True:
        cand = f"{base}_{idx}"
        if cand not in used_names:
            return cand
        idx += 1
