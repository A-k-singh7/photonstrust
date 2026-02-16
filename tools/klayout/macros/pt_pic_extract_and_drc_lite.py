"""PhotonTrust KLayout macro template: PIC extraction + DRC-lite (v0.1).

This script is intended to be run in KLayout batch mode:

  klayout -b -r pt_pic_extract_and_drc_lite.py ^
    -rd input_gds=path/to/layout.gds ^
    -rd output_dir=path/to/out ^
    -rd wg_layer=1 -rd wg_datatype=0 ^
    -rd label_layer=10 -rd label_datatype=0 ^
    -rd label_prefix=PTPORT ^
    -rd min_waveguide_width_um=0.5 ^
    -rd endpoint_snap_tol_um=2.0

Required variables (via -rd):
  - input_gds: path to input GDS
  - output_dir: directory to write outputs into

Optional variables:
  - top_cell: top cell name (default: first top cell)
  - wg_layer, wg_datatype: waveguide path layer spec (default: 1/0)
  - label_layer, label_datatype: port label layer spec (default: 10/0)
  - label_prefix: port label prefix (default: "PTPORT")
  - min_waveguide_width_um: DRC-lite min PATH width (default: 0.5)
  - endpoint_snap_tol_um: DRC-lite route endpoint-to-port snap tolerance (default: 2.0)
  - ports_json, routes_json, drc_json, provenance_json: explicit output paths

Outputs (default filenames under output_dir):
  - ports_extracted.json
  - routes_extracted.json
  - drc_lite.json
  - macro_provenance.json

Notes:
  - DRC-lite failures are reported in drc_lite.json. The macro will still exit 0
    if it successfully produced the outputs, even when DRC-lite status is "fail".
  - Fatal errors (e.g., cannot read GDS) will attempt to write drc_lite.json
    with status "error" and exit non-zero.
"""

from __future__ import annotations

import json
import math
import os
import sys
import traceback
from typing import Any

import pya

SCHEMA_VERSION = "0.1"


def _var(name: str, default: Any = None) -> Any:
    # KLayout `-rd` variables are injected into script globals.
    return globals().get(name, default)


def _as_str(v: Any, default: str = "") -> str:
    try:
        s = str(v)
    except Exception:
        return default
    return s


def _as_int(v: Any, default: int) -> int:
    try:
        return int(str(v).strip())
    except Exception:
        return int(default)


def _as_float(v: Any, default: float) -> float:
    try:
        return float(str(v).strip())
    except Exception:
        return float(default)


def _mkdirs(p: str) -> None:
    if not p:
        return
    os.makedirs(p, exist_ok=True)


def _write_json(path: str, obj: Any) -> None:
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(obj, indent=2))
    os.replace(tmp, path)


def _distance_um(a: tuple[float, float], b: tuple[float, float]) -> float:
    dx = float(a[0]) - float(b[0])
    dy = float(a[1]) - float(b[1])
    return float(math.sqrt(dx * dx + dy * dy))


def _main() -> int:
    input_gds = _as_str(_var("input_gds") or _var("gds") or _var("gds_path") or "").strip()
    output_dir = _as_str(_var("output_dir") or _var("out") or "").strip()
    if not input_gds:
        raise RuntimeError("Missing required -rd variable: input_gds")
    if not output_dir:
        raise RuntimeError("Missing required -rd variable: output_dir")

    _mkdirs(output_dir)

    ports_json = _as_str(_var("ports_json") or os.path.join(output_dir, "ports_extracted.json"))
    routes_json = _as_str(_var("routes_json") or os.path.join(output_dir, "routes_extracted.json"))
    drc_json = _as_str(_var("drc_json") or os.path.join(output_dir, "drc_lite.json"))
    provenance_json = _as_str(_var("provenance_json") or os.path.join(output_dir, "macro_provenance.json"))

    top_cell_name = _as_str(_var("top_cell") or _var("cell_name") or "").strip()

    wg_layer = _as_int(_var("wg_layer"), 1)
    wg_datatype = _as_int(_var("wg_datatype"), 0)
    label_layer = _as_int(_var("label_layer"), 10)
    label_datatype = _as_int(_var("label_datatype"), 0)
    label_prefix = _as_str(_var("label_prefix") or "PTPORT").strip() or "PTPORT"

    min_waveguide_width_um = _as_float(_var("min_waveguide_width_um"), 0.5)
    endpoint_snap_tol_um = _as_float(_var("endpoint_snap_tol_um"), 2.0)

    # Load layout.
    layout = pya.Layout()
    layout.read(input_gds)
    dbu_um = float(layout.dbu)  # um per DBU

    # Select top cell.
    top = None
    if top_cell_name:
        try:
            top = layout.cell(top_cell_name)
        except Exception:
            top = None
    if top is None:
        tops = list(layout.top_cells())
        if tops:
            top = tops[0]
            top_cell_name = str(top.name)
    if top is None:
        raise RuntimeError("No top cell found in GDS")

    # Layer indices.
    li_wg = layout.layer(int(wg_layer), int(wg_datatype))
    li_label = layout.layer(int(label_layer), int(label_datatype))

    # Extract ports from TEXT labels.
    ports_out: list[dict[str, Any]] = []
    label_parse_errors = 0
    for shape in top.shapes(li_label).each():
        if not shape.is_text():
            continue
        t = shape.text
        s = _as_str(t.string).strip()
        if not s.startswith(label_prefix + ":"):
            continue
        parts = s.split(":")
        if len(parts) < 3:
            label_parse_errors += 1
            continue
        node = _as_str(parts[1]).strip()
        port = _as_str(parts[2]).strip()
        if not node or not port:
            label_parse_errors += 1
            continue

        x_um = float(t.trans.disp.x) * dbu_um
        y_um = float(t.trans.disp.y) * dbu_um
        ports_out.append(
            {
                "node": node,
                "port": port,
                "x_um": float(x_um),
                "y_um": float(y_um),
                "source": {
                    "layer": {"layer": int(label_layer), "datatype": int(label_datatype)},
                    "text": s,
                },
            }
        )
    ports_out.sort(
        key=lambda p: (
            str(p.get("node", "")).lower(),
            str(p.get("port", "")).lower(),
            float(p.get("x_um", 0.0)),
            float(p.get("y_um", 0.0)),
        )
    )
    ports_doc = {"schema_version": SCHEMA_VERSION, "kind": "pic.ports", "ports": ports_out}
    _write_json(ports_json, ports_doc)

    # Extract waveguide routes from PATH shapes.
    raw_routes: list[dict[str, Any]] = []
    skipped_polygons = 0
    skipped_other = 0
    for shape in top.shapes(li_wg).each():
        if shape.is_path():
            p = shape.path
            pts = [(int(pt.x), int(pt.y)) for pt in p.each_point()]
            width_dbu = int(p.width)
            raw_routes.append(
                {
                    "_sort": (width_dbu, tuple(pts)),
                    "width_um": float(width_dbu) * dbu_um,
                    "points_um": [[float(x) * dbu_um, float(y) * dbu_um] for (x, y) in pts],
                    "source": {"layer": {"layer": int(wg_layer), "datatype": int(wg_datatype)}, "shape_type": "path"},
                }
            )
        elif shape.is_polygon():
            skipped_polygons += 1
            continue
        else:
            skipped_other += 1
            continue

    raw_routes.sort(key=lambda r: r.get("_sort"))
    routes_out = []
    for idx, r in enumerate(raw_routes):
        r = dict(r)
        r.pop("_sort", None)
        r["route_id"] = f"r{idx + 1}"
        routes_out.append(r)

    routes_doc = {"schema_version": SCHEMA_VERSION, "kind": "pic.routes", "routes": routes_out}
    _write_json(routes_json, routes_doc)

    # DRC-lite
    issues: list[dict[str, Any]] = []

    if label_parse_errors:
        issues.append(
            {
                "rule": "port_label_parse",
                "severity": "warning",
                "message": f"{label_parse_errors} port labels could not be parsed on label layer",
            }
        )

    if not ports_out:
        issues.append(
            {
                "rule": "ports_present",
                "severity": "error",
                "message": "No port labels were extracted (check label layer/prefix).",
            }
        )

    # Duplicate port keys.
    seen = set()
    for p in ports_out:
        k = (str(p.get("node", "")).strip().lower(), str(p.get("port", "")).strip().lower())
        if k in seen:
            issues.append(
                {
                    "rule": "port_unique",
                    "severity": "error",
                    "message": f"Duplicate port label detected: {p.get('node')}.{p.get('port')}",
                    "port": {"node": p.get("node"), "port": p.get("port")},
                }
            )
        seen.add(k)

    if not routes_out:
        issues.append(
            {
                "rule": "routes_present",
                "severity": "error",
                "message": "No PATH routes were extracted on waveguide layer (polygons are currently ignored).",
            }
        )

    # Route checks.
    port_pts = [(float(p["x_um"]), float(p["y_um"])) for p in ports_out if "x_um" in p and "y_um" in p]
    for r in routes_out:
        rid = str(r.get("route_id", "")).strip() or "route"
        width_um = float(r.get("width_um", 0.0) or 0.0)
        pts = r.get("points_um") or []
        if width_um and width_um < float(min_waveguide_width_um):
            issues.append(
                {
                    "rule": "min_waveguide_width_um",
                    "severity": "error",
                    "message": f"{rid}: PATH width {width_um:.6g} um < min {float(min_waveguide_width_um):.6g} um",
                    "route_id": rid,
                    "measured_width_um": float(width_um),
                    "min_width_um": float(min_waveguide_width_um),
                }
            )

        # Manhattan spine check.
        if isinstance(pts, list) and len(pts) >= 2:
            for i in range(len(pts) - 1):
                try:
                    x0, y0 = float(pts[i][0]), float(pts[i][1])
                    x1, y1 = float(pts[i + 1][0]), float(pts[i + 1][1])
                except Exception:
                    continue
                dx = x1 - x0
                dy = y1 - y0
                if dx == 0.0 and dy == 0.0:
                    issues.append(
                        {
                            "rule": "route_degenerate_segment",
                            "severity": "warning",
                            "message": f"{rid}: degenerate segment at index {i}",
                            "route_id": rid,
                            "segment_index": int(i),
                        }
                    )
                elif dx != 0.0 and dy != 0.0:
                    issues.append(
                        {
                            "rule": "route_manhattan",
                            "severity": "error",
                            "message": f"{rid}: non-Manhattan segment at index {i}",
                            "route_id": rid,
                            "segment_index": int(i),
                            "p0_um": [float(x0), float(y0)],
                            "p1_um": [float(x1), float(y1)],
                        }
                    )

        # Endpoint snap check (only if we have any ports).
        if port_pts and isinstance(pts, list) and len(pts) >= 2:
            ends = []
            try:
                ends = [(float(pts[0][0]), float(pts[0][1])), (float(pts[-1][0]), float(pts[-1][1]))]
            except Exception:
                ends = []
            for end_idx, end_pt in enumerate(ends):
                d = min((_distance_um(end_pt, p) for p in port_pts), default=None)
                if d is None:
                    continue
                if float(d) > float(endpoint_snap_tol_um):
                    issues.append(
                        {
                            "rule": "endpoint_snap_tol_um",
                            "severity": "error",
                            "message": f"{rid}: endpoint {end_idx} is {float(d):.6g} um from nearest port > tol {float(endpoint_snap_tol_um):.6g} um",
                            "route_id": rid,
                            "endpoint_index": int(end_idx),
                            "endpoint_um": [float(end_pt[0]), float(end_pt[1])],
                            "distance_um": float(d),
                            "tol_um": float(endpoint_snap_tol_um),
                        }
                    )

    status = "pass" if len([i for i in issues if str(i.get("severity")) == "error"]) == 0 else "fail"

    metrics = {
        "ports_extracted": int(len(ports_out)),
        "routes_extracted": int(len(routes_out)),
        "routes_skipped_polygons": int(skipped_polygons),
        "routes_skipped_other": int(skipped_other),
        "label_parse_errors": int(label_parse_errors),
    }

    drc_doc = {
        "schema_version": SCHEMA_VERSION,
        "kind": "pic.klayout.drc_lite",
        "summary": {
            "status": status,
            "issue_count": int(len(issues)),
            "error_count": int(len([i for i in issues if str(i.get("severity")) == "error"])),
        },
        "issues": issues,
        "metrics": metrics,
        "layers": {
            "waveguide": {"layer": int(wg_layer), "datatype": int(wg_datatype)},
            "label": {"layer": int(label_layer), "datatype": int(label_datatype)},
        },
        "provenance": {
            "input_gds": input_gds,
            "top_cell": top_cell_name,
            "dbu_um": float(dbu_um),
        },
    }
    _write_json(drc_json, drc_doc)

    prov_doc = {
        "schema_version": SCHEMA_VERSION,
        "generated_by": "pt_pic_extract_and_drc_lite",
        "inputs": {
            "input_gds": input_gds,
            "top_cell": top_cell_name,
            "dbu_um": float(dbu_um),
        },
        "settings": {
            "label_prefix": label_prefix,
            "min_waveguide_width_um": float(min_waveguide_width_um),
            "endpoint_snap_tol_um": float(endpoint_snap_tol_um),
        },
        "layers": drc_doc["layers"],
        "outputs": {
            "ports_json": ports_json,
            "routes_json": routes_json,
            "drc_json": drc_json,
        },
        "metrics": metrics,
    }
    _write_json(provenance_json, prov_doc)

    return 0


if __name__ == "__main__":
    try:
        rc = _main()
    except Exception as exc:
        # Attempt to emit a minimal DRC-lite error record if we can infer output_dir.
        out = _as_str(_var("output_dir") or _var("out") or "").strip()
        drc_path = _as_str(_var("drc_json") or (os.path.join(out, "drc_lite.json") if out else ""))
        if out:
            try:
                _mkdirs(out)
                _write_json(
                    drc_path,
                    {
                        "schema_version": SCHEMA_VERSION,
                        "kind": "pic.klayout.drc_lite",
                        "summary": {"status": "error", "issue_count": 1, "error_count": 1},
                        "issues": [
                            {
                                "rule": "exception",
                                "severity": "error",
                                "message": _as_str(exc),
                                "traceback": traceback.format_exc(),
                            }
                        ],
                        "metrics": {},
                        "layers": {},
                        "provenance": {"input_gds": _as_str(_var("input_gds") or ""), "top_cell": _as_str(_var("top_cell") or "")},
                    },
                )
            except Exception:
                pass
        print(traceback.format_exc(), file=sys.stderr)
        rc = 2
    raise SystemExit(rc)
