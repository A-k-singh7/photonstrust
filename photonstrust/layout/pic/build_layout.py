"""Deterministic PIC layout builder (v0.1).

This is a "layout hooks" seam, not a full physical design tool:
- It emits deterministic placement + routing sidecars (ports.json, routes.json).
- It can optionally emit a simple GDS (via optional `gdstk`) with:
  - waveguide paths on a waveguide layer
  - component bounding boxes on a component layer
  - port labels on a label layer

The output artifacts are intended to unlock:
- layout-aware Performance DRC (already built on route-level extraction),
- LVS-lite mismatch summaries (expected connectivity vs extracted connectivity),
- optional KLayout batch DRC macro runs (separate seam).
"""

from __future__ import annotations

import json
import platform
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from photonstrust.components.pic.library import component_ports
from photonstrust.graph.compiler import compile_graph
from photonstrust.graph.schema import validate_graph
from photonstrust.layout.gds_write import write_gds
from photonstrust.pdk import resolve_pdk_contract
from photonstrust.utils import hash_dict

from .spec import normalize_layout_settings, node_ui_position_um


class OptionalDependencyError(RuntimeError):
    pass


@dataclass(frozen=True)
class LayoutBuildArtifacts:
    output_dir: Path
    routes_json: Path
    ports_json: Path
    provenance_json: Path
    layout_gds: Path | None


def build_pic_layout_artifacts(
    request: dict[str, Any],
    output_dir: str | Path,
    *,
    require_schema: bool = False,
) -> dict[str, Any]:
    """Build deterministic layout artifacts from a PIC graph.

    Request (v0.1, minimal):
      - graph: PhotonTrust graph dict (profile=pic_circuit)
      - pdk: {name?: str, manifest_path?: str}
      - settings: dict

    Returns:
      A machine-readable report dict (schema_version=0.1).
    """

    if not isinstance(request, dict):
        raise TypeError("request must be an object")

    graph = request.get("graph")
    if not isinstance(graph, dict):
        raise TypeError("request.graph must be an object")

    validate_graph(graph, require_jsonschema=require_schema)
    if str(graph.get("profile", "")).strip().lower() != "pic_circuit":
        raise ValueError("build_pic_layout_artifacts requires graph.profile=pic_circuit")

    raw_settings = request.get("settings") if isinstance(request.get("settings"), dict) else None
    settings = normalize_layout_settings(raw_settings)
    if isinstance(raw_settings, dict):
        settings["cell_name"] = _resolve_top_cell_name_alias(raw_settings, default=str(settings.get("cell_name", "TOP")))
        # Forward deterministic/advanced writer knobs without changing v0.1 defaults.
        for key in ("gds_timestamp", "timestamp", "gds_unit", "gds_precision", "port_marker_size_um"):
            if key in raw_settings:
                settings[key] = raw_settings[key]

    # PDK: resolve through adapter contract for consistent portability.
    pdk_req = request.get("pdk") if isinstance(request.get("pdk"), dict) else {}
    pdk_contract = resolve_pdk_contract(pdk_req)
    pdk = pdk_contract["pdk"]
    pdk_for_gds = dict(pdk)
    if isinstance(pdk_req, dict) and "layer_stack" in pdk_req and "layer_stack" not in pdk_for_gds:
        pdk_for_gds["layer_stack"] = pdk_req["layer_stack"]

    # Compile to normalized netlist (but keep UI positions from the input graph).
    compiled = compile_graph(graph, require_schema=require_schema)
    netlist = compiled.compiled

    nodes_by_id = {str(n.get("id")): n for n in (graph.get("nodes") or []) if isinstance(n, dict)}
    ui_scale = float(settings["ui_scale_um_per_unit"])

    node_positions_um: dict[str, tuple[float, float]] = {}
    missing_ui = []
    for node_id in sorted(nodes_by_id.keys(), key=lambda s: s.lower()):
        pos = node_ui_position_um(nodes_by_id[node_id], ui_scale_um_per_unit=ui_scale)
        if pos is None:
            missing_ui.append(node_id)
            continue
        node_positions_um[node_id] = (float(pos[0]), float(pos[1]))

    # Deterministic fallback placement for nodes without UI positions.
    grid_um = float(settings["grid_um"])
    auto_idx = 0
    for node in (netlist.get("nodes") or []):
        node_id = str(node.get("id", "")).strip()
        if not node_id or node_id in node_positions_um:
            continue
        node_positions_um[node_id] = (float(auto_idx) * grid_um, 0.0)
        auto_idx += 1

    warnings: list[str] = []
    if missing_ui:
        warnings.append(f"{len(missing_ui)} nodes missing ui.position; auto-placed on grid: {sorted(missing_ui)}")
    warnings.extend(list(compiled.warnings or []))

    ports = _build_ports(netlist, node_positions_um, settings)
    routes = _build_routes(netlist, ports, settings, pdk)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    routes_path = output_dir / "routes.json"
    routes_path.write_text(json.dumps(routes, indent=2), encoding="utf-8")

    ports_path = output_dir / "ports.json"
    ports_path.write_text(json.dumps(ports, indent=2), encoding="utf-8")

    layout_gds_path = None
    try:
        layout_gds_path = _emit_gds(
            output_dir,
            netlist,
            pdk_for_gds,
            node_positions_um,
            ports,
            routes,
            settings,
        )
    except OptionalDependencyError as exc:
        warnings.append(str(exc))

    # Provenance (hash-stable inputs).
    graph_hash = hash_dict(graph)
    netlist_hash = hash_dict(netlist)
    settings_hash = hash_dict(settings)

    provenance = {
        "schema_version": "0.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "graph_id": graph.get("graph_id"),
        "graph_hash": graph_hash,
        "netlist_hash": netlist_hash,
        "settings_hash": settings_hash,
        "pdk": {
            "name": pdk["name"],
            "version": pdk["version"],
            "design_rules": dict(pdk.get("design_rules", {}) or {}),
            "notes": list(pdk.get("notes", []) or []),
        },
        "toolchain": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "gdstk": _gdstk_version_or_none(),
        },
        "artifacts": {
            "routes_json_path": str(routes_path.name),
            "ports_json_path": str(ports_path.name),
            "layout_gds_path": str(layout_gds_path.name) if layout_gds_path else None,
        },
        "warnings": warnings,
    }

    prov_path = output_dir / "layout_provenance.json"
    prov_path.write_text(json.dumps(provenance, indent=2), encoding="utf-8")

    report = {
        "schema_version": "0.1",
        "generated_at": provenance["generated_at"],
        "graph_id": provenance["graph_id"],
        "pdk": provenance["pdk"],
        "settings": settings,
        "summary": {
            "nodes": int(len(netlist.get("nodes") or [])),
            "edges": int(len(netlist.get("edges") or [])),
            "ports": int(len(ports.get("ports") or [])),
            "routes": int(len(routes.get("routes") or [])),
            "gds_emitted": bool(layout_gds_path),
        },
        "artifacts": {
            "routes_json_path": str(routes_path.name),
            "ports_json_path": str(ports_path.name),
            "layout_provenance_json_path": str(prov_path.name),
            "layout_gds_path": str(layout_gds_path.name) if layout_gds_path else None,
        },
        "warnings": warnings,
    }
    return report


def _build_ports(netlist: dict[str, Any], node_positions_um: dict[str, tuple[float, float]], settings: dict[str, Any]) -> dict[str, Any]:
    port_offset_um = float(settings["port_offset_um"])
    port_pitch_um = float(settings["port_pitch_um"])

    ports_out: list[dict[str, Any]] = []
    for node in (netlist.get("nodes") or []):
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("id", "")).strip()
        kind = str(node.get("kind", "")).strip().lower()
        if not node_id:
            continue
        x0, y0 = node_positions_um.get(node_id, (0.0, 0.0))

        params = node.get("params", {}) or {}
        p = component_ports(kind, params=params)
        in_ports = list(p.in_ports)
        out_ports = list(p.out_ports)

        for i, port in enumerate(in_ports):
            y_off = (float(i) - (len(in_ports) - 1) / 2.0) * port_pitch_um if in_ports else 0.0
            ports_out.append(
                {
                    "node": node_id,
                    "kind": kind,
                    "port": str(port),
                    "role": "in",
                    "x_um": float(x0 - port_offset_um),
                    "y_um": float(y0 + y_off),
                }
            )
        for i, port in enumerate(out_ports):
            y_off = (float(i) - (len(out_ports) - 1) / 2.0) * port_pitch_um if out_ports else 0.0
            ports_out.append(
                {
                    "node": node_id,
                    "kind": kind,
                    "port": str(port),
                    "role": "out",
                    "x_um": float(x0 + port_offset_um),
                    "y_um": float(y0 + y_off),
                }
            )

    ports_out.sort(key=lambda r: (str(r["node"]).lower(), str(r["port"]).lower()))
    return {"schema_version": "0.1", "kind": "pic.ports", "ports": ports_out}


def _build_routes(
    netlist: dict[str, Any],
    ports: dict[str, Any],
    settings: dict[str, Any],
    pdk: Any,
) -> dict[str, Any]:
    width_um = settings.get("waveguide_width_um")
    if isinstance(pdk, dict):
        pdk_rules = pdk.get("design_rules", {}) or {}
    else:
        pdk_rules = getattr(pdk, "design_rules", {}) or {}
    if width_um is None:
        width_um = float(pdk_rules.get("min_waveguide_width_um", 0.5) or 0.5)
    width_um = float(width_um)

    # Port lookup.
    port_by_ref: dict[tuple[str, str], dict[str, Any]] = {}
    for p in (ports.get("ports") or []):
        if not isinstance(p, dict):
            continue
        port_by_ref[(str(p.get("node")), str(p.get("port")))] = p

    routes_out: list[dict[str, Any]] = []
    for idx, e in enumerate((netlist.get("edges") or [])):
        if not isinstance(e, dict):
            continue
        src = str(e.get("from", "")).strip()
        dst = str(e.get("to", "")).strip()
        from_port = str(e.get("from_port", "out"))
        to_port = str(e.get("to_port", "in"))
        if not src or not dst:
            continue

        p_src = port_by_ref.get((src, from_port))
        p_dst = port_by_ref.get((dst, to_port))
        if p_src is None or p_dst is None:
            continue

        a = (float(p_src["x_um"]), float(p_src["y_um"]))
        b = (float(p_dst["x_um"]), float(p_dst["y_um"]))

        pts = [a]
        if a[0] != b[0] and a[1] != b[1]:
            pts.append((b[0], a[1]))
        pts.append(b)

        points_um = [[float(x), float(y)] for (x, y) in pts]
        routes_out.append(
            {
                "route_id": f"e{idx + 1}:{src}.{from_port}->{dst}.{to_port}",
                "width_um": width_um,
                "points_um": points_um,
                "source": {
                    "edge": {
                        "id": e.get("id"),
                        "from": src,
                        "from_port": from_port,
                        "to": dst,
                        "to_port": to_port,
                        "kind": e.get("kind"),
                    }
                },
            }
        )

    return {"schema_version": "0.1", "kind": "pic.routes", "routes": routes_out}


def _import_gdstk():
    try:
        import gdstk  # type: ignore
    except Exception as exc:
        raise OptionalDependencyError(
            "GDS emission requires optional dependency 'gdstk'. "
            "Install with: pip install 'photonstrust[layout]'"
        ) from exc
    return gdstk


def _gdstk_version_or_none() -> str | None:
    try:
        import gdstk  # type: ignore

        return str(getattr(gdstk, "__version__", None) or "unknown")
    except Exception:
        return None


def _resolve_top_cell_name_alias(raw_settings: dict[str, Any], *, default: str) -> str:
    for key in ("cell_name", "top_cell_name", "top_cell"):
        if key not in raw_settings:
            continue
        value = str(raw_settings.get(key) or "").strip()
        if value:
            return value
    return str(default or "TOP").strip() or "TOP"


def _emit_gds(
    output_dir: Path,
    netlist: dict[str, Any],
    pdk: dict[str, Any],
    node_positions_um: dict[str, tuple[float, float]],
    ports: dict[str, Any],
    routes: dict[str, Any],
    settings: dict[str, Any],
) -> Path:
    _import_gdstk()
    writer_settings = dict(settings)
    writer_settings["_node_positions_um"] = {k: [float(v[0]), float(v[1])] for k, v in node_positions_um.items()}
    gds_path = output_dir / "layout.gds"
    return write_gds(
        netlist=netlist,
        pdk=pdk,
        output_path=gds_path,
        routes=routes,
        ports=ports,
        settings=writer_settings,
    )
