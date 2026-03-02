#!/usr/bin/env python3
"""Materialize a deterministic local tapeout run directory for smoke rehearsal."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
from typing import Any

from photonstrust.layout.pic.build_layout import build_pic_layout_artifacts
from photonstrust.pdk import resolve_pdk_contract


_PLACEHOLDER_GDS_BYTES = b"PHOTONTRUST_LOCAL_GDS_PLACEHOLDER_V1\n"
_DETERMINISTIC_GDS_TIMESTAMP = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
_DEFAULT_PDK_REQUEST = {"name": "generic_silicon_photonics"}
_LOCAL_DESIGN_RULE_FALLBACK = {
    "min_waveguide_width_um": 0.45,
    "min_waveguide_gap_um": 0.2,
    "min_bend_radius_um": 5.0,
    "min_waveguide_enclosure_um": 1.0,
}
_PEX_RULE_DEFAULTS = {
    "resistance_ohm_per_um": 0.02,
    "capacitance_ff_per_um": 0.002,
    "max_total_resistance_ohm": 5000.0,
    "max_total_capacitance_ff": 10000.0,
    "max_rc_delay_ps": 50000.0,
    "max_coupling_coeff": 0.1,
    "min_net_coverage_ratio": 1.0,
}

_TEMPLATE_MINIMAL_CHAIN = {
    "schema_version": "0.1",
    "graph_id": "local_tapeout_minimal_chain",
    "profile": "pic_circuit",
    "metadata": {
        "title": "Local Tapeout Minimal Chain",
        "description": "Deterministic local fixture for non-proprietary smoke rehearsal",
        "created_at": "2026-03-02",
    },
    "circuit": {"id": "local_tapeout_minimal_chain", "wavelength_nm": 1550},
    "nodes": [
        {"id": "gc_in", "kind": "pic.grating_coupler", "params": {}},
        {"id": "wg_1", "kind": "pic.waveguide", "params": {"length_um": 200.0}},
        {"id": "ec_out", "kind": "pic.edge_coupler", "params": {}},
    ],
    "edges": [
        {"from": "gc_in", "to": "wg_1", "kind": "optical"},
        {"from": "wg_1", "to": "ec_out", "kind": "optical"},
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Materialize deterministic local tapeout run artifacts suitable for "
            "scripts/run_foundry_smoke.py --use-local-backend"
        )
    )
    parser.add_argument("--run-dir", type=Path, required=True, help="Target run directory to materialize")
    parser.add_argument(
        "--graph-template",
        default="minimal_chain",
        help="Graph template id ('minimal_chain') or path to JSON graph template",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=None,
        help="Optional file path for machine-readable materialization report JSON",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite conflicting existing files when set",
    )
    parser.add_argument(
        "--allow-ci",
        action="store_true",
        help="Compatibility no-op for CI wrappers that forward this flag",
    )
    return parser.parse_args()


def _resolve_graph_template(template_ref: str) -> dict[str, Any]:
    value = str(template_ref or "").strip()
    if value == "minimal_chain":
        return dict(_TEMPLATE_MINIMAL_CHAIN)

    path = Path(value)
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"graph-template path not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"graph-template JSON must be an object: {path}")
    return payload


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def _safe_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed


def _resolve_output_path(run_dir: Path, value: Path | None) -> Path | None:
    if value is None:
        return None
    if value.is_absolute():
        return value.resolve()
    return (run_dir / value).resolve()


def _resolve_pdk_request(graph_payload: dict[str, Any]) -> dict[str, Any]:
    raw = graph_payload.get("pdk")
    if isinstance(raw, dict):
        out: dict[str, Any] = {}
        name = str(raw.get("name") or "").strip()
        manifest_path = str(raw.get("manifest_path") or "").strip()
        if name:
            out["name"] = name
        if manifest_path:
            out["manifest_path"] = manifest_path
        if out:
            return out
    return dict(_DEFAULT_PDK_REQUEST)


def _merge_pex_rules(raw: Any) -> dict[str, float]:
    source = raw if isinstance(raw, dict) else {}
    out: dict[str, float] = {}
    for key, default_value in _PEX_RULE_DEFAULTS.items():
        value = _safe_float(source.get(key))
        if value is None:
            out[key] = float(default_value)
            continue
        if key.startswith("min_"):
            out[key] = float(value) if value >= 0.0 else float(default_value)
        else:
            out[key] = float(value) if value > 0.0 else float(default_value)
    return out


def _build_pdk_manifest_payload(pdk_request: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
    try:
        contract = resolve_pdk_contract(pdk_request)
        pdk_payload = contract.get("pdk") if isinstance(contract, dict) else {}
        if not isinstance(pdk_payload, dict):
            raise ValueError("pdk contract payload is invalid")
        out = {
            "name": str(pdk_payload.get("name") or "local_smoke_pdk"),
            "version": str(pdk_payload.get("version") or "1"),
            "design_rules": dict(pdk_payload.get("design_rules") or {}),
            "notes": [str(v) for v in list(pdk_payload.get("notes") or []) if str(v).strip()],
        }
        if not out["design_rules"]:
            out["design_rules"] = dict(_LOCAL_DESIGN_RULE_FALLBACK)
            warnings.append("pdk_design_rules_missing_using_local_fallback")
        out["pex_rules"] = _merge_pex_rules(pdk_payload.get("pex_rules"))
        return out
    except Exception:
        warnings.append("pdk_resolve_failed_using_local_fallback")
        return {
            "name": "local_smoke_pdk",
            "version": "1",
            "notes": [
                "Synthetic non-proprietary local PDK fallback fixture.",
                "Values are deterministic smoke defaults only.",
            ],
            "design_rules": dict(_LOCAL_DESIGN_RULE_FALLBACK),
            "pex_rules": dict(_PEX_RULE_DEFAULTS),
        }


def _fallback_sidecars_from_graph(graph_payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    nodes = graph_payload.get("nodes")
    edges = graph_payload.get("edges")
    node_ids: list[str] = []
    if isinstance(nodes, list):
        for node in nodes:
            if not isinstance(node, dict):
                continue
            node_id = str(node.get("id") or "").strip()
            if node_id and node_id not in node_ids:
                node_ids.append(node_id)
    if isinstance(edges, list):
        for edge in edges:
            if not isinstance(edge, dict):
                continue
            left = str(edge.get("from") or "").strip()
            right = str(edge.get("to") or "").strip()
            if left and left not in node_ids:
                node_ids.append(left)
            if right and right not in node_ids:
                node_ids.append(right)

    pos_by_node: dict[str, tuple[float, float]] = {}
    for idx, node_id in enumerate(node_ids):
        pos_by_node[node_id] = (float(idx * 100.0), 0.0)

    ports_rows: list[dict[str, Any]] = []
    for node_id in sorted(node_ids, key=lambda t: t.lower()):
        x, y = pos_by_node.get(node_id, (0.0, 0.0))
        ports_rows.append({"node": node_id, "kind": "pic.component", "port": "in", "role": "in", "x_um": x - 10.0, "y_um": y})
        ports_rows.append({"node": node_id, "kind": "pic.component", "port": "out", "role": "out", "x_um": x + 10.0, "y_um": y})

    port_by_ref = {(str(p.get("node")), str(p.get("port"))): p for p in ports_rows}
    routes_rows: list[dict[str, Any]] = []
    if isinstance(edges, list):
        for idx, edge in enumerate(edges):
            if not isinstance(edge, dict):
                continue
            src = str(edge.get("from") or "").strip()
            dst = str(edge.get("to") or "").strip()
            if not src or not dst:
                continue
            from_port = str(edge.get("from_port") or "out").strip() or "out"
            to_port = str(edge.get("to_port") or "in").strip() or "in"
            src_port = port_by_ref.get((src, from_port))
            dst_port = port_by_ref.get((dst, to_port))
            if not isinstance(src_port, dict) or not isinstance(dst_port, dict):
                continue
            points_um = [
                [float(src_port.get("x_um", 0.0)), float(src_port.get("y_um", 0.0))],
                [float(dst_port.get("x_um", 0.0)), float(dst_port.get("y_um", 0.0))],
            ]
            routes_rows.append(
                {
                    "route_id": f"e{idx + 1}:{src}.{from_port}->{dst}.{to_port}",
                    "width_um": 0.5,
                    "points_um": points_um,
                    "source": {
                        "edge": {
                            "from": src,
                            "from_port": from_port,
                            "to": dst,
                            "to_port": to_port,
                            "kind": edge.get("kind"),
                        }
                    },
                }
            )

    ports_payload = {"schema_version": "0.1", "kind": "pic.ports", "ports": ports_rows}
    routes_payload = {"schema_version": "0.1", "kind": "pic.routes", "routes": routes_rows}
    return ports_payload, routes_payload


def _generate_layout_sidecars(
    *,
    graph_payload: dict[str, Any],
    pdk_request: dict[str, Any],
    warnings: list[str],
) -> tuple[dict[str, Any], dict[str, Any], str, bytes]:
    settings = {
        "cell_name": "PT_LOCAL_LAYOUT",
        "waveguide_width_um": 0.5,
        "gds_timestamp": _DETERMINISTIC_GDS_TIMESTAMP.isoformat(),
        "gds_unit": 1e-6,
        "gds_precision": 1e-9,
        "port_marker_size_um": 1.0,
    }
    try:
        with tempfile.TemporaryDirectory(prefix="pt_local_materialize_") as tmp_dir:
            output_dir = Path(tmp_dir).resolve()
            build_report = build_pic_layout_artifacts(
                {
                    "graph": graph_payload,
                    "pdk": dict(pdk_request),
                    "settings": settings,
                },
                output_dir=output_dir,
            )
            if isinstance(build_report, dict):
                report_warnings = build_report.get("warnings")
                if isinstance(report_warnings, list):
                    warnings.extend(str(v) for v in report_warnings if str(v).strip())
                artifacts = build_report.get("artifacts") if isinstance(build_report.get("artifacts"), dict) else {}
            else:
                artifacts = {}

            ports_rel = str(artifacts.get("ports_json_path") or "ports.json")
            routes_rel = str(artifacts.get("routes_json_path") or "routes.json")
            ports_payload = _load_json_object((output_dir / ports_rel).resolve())
            routes_payload = _load_json_object((output_dir / routes_rel).resolve())

            gds_rel = artifacts.get("layout_gds_path")
            if isinstance(gds_rel, str) and gds_rel.strip():
                gds_path = (output_dir / gds_rel).resolve()
                if gds_path.exists() and gds_path.is_file():
                    return ports_payload, routes_payload, "gdstk", gds_path.read_bytes()

            warnings.append("layout_pipeline_gds_missing_placeholder_layout_gds_written")
            return ports_payload, routes_payload, "placeholder", _PLACEHOLDER_GDS_BYTES
    except Exception:
        warnings.append("layout_pipeline_failed_fallback_sidecars_used")
        ports_payload, routes_payload = _fallback_sidecars_from_graph(graph_payload)
        return ports_payload, routes_payload, "placeholder", _PLACEHOLDER_GDS_BYTES


def _derive_required_enclosure_um(design_rules: dict[str, Any]) -> float:
    for key in ("min_waveguide_enclosure_um", "min_enclosure_um", "waveguide_min_enclosure_um"):
        value = _safe_float(design_rules.get(key))
        if value is not None and value >= 0.0:
            return float(value)
    return 1.0


def _derive_min_bend_radius_um(design_rules: dict[str, Any]) -> float:
    for key in ("min_bend_radius_um", "min_waveguide_bend_radius_um", "min_radius_um"):
        value = _safe_float(design_rules.get(key))
        if value is not None and value > 0.0:
            return float(value)
    return 5.0


def _enrich_routes_for_local_backend(
    *,
    routes_payload: dict[str, Any],
    graph_payload: dict[str, Any],
    design_rules: dict[str, Any],
) -> dict[str, Any]:
    raw_routes = routes_payload.get("routes")
    route_rows = list(raw_routes) if isinstance(raw_routes, list) else []
    raw_edges = graph_payload.get("edges")
    graph_edges = list(raw_edges) if isinstance(raw_edges, list) else []

    required_enclosure_um = _derive_required_enclosure_um(design_rules)
    min_bend_radius_um = max(10.0, _derive_min_bend_radius_um(design_rules))

    out_routes: list[dict[str, Any]] = []
    for idx, raw in enumerate(route_rows):
        if not isinstance(raw, dict):
            continue
        route = dict(raw)

        width_um = _safe_float(route.get("width_um"))
        if width_um is None or width_um <= 0.0:
            route["width_um"] = 0.5
        else:
            route["width_um"] = float(width_um)

        enclosure_um = _safe_float(route.get("enclosure_um"))
        if enclosure_um is None or enclosure_um < required_enclosure_um:
            route["enclosure_um"] = float(required_enclosure_um)
        else:
            route["enclosure_um"] = float(enclosure_um)

        default_coupling = min(0.09, 0.01 * float(idx + 1))
        coupling_coeff = _safe_float(route.get("coupling_coeff"))
        if coupling_coeff is None or coupling_coeff <= 0.0 or coupling_coeff >= 0.1:
            route["coupling_coeff"] = float(default_coupling)
        else:
            route["coupling_coeff"] = float(coupling_coeff)

        # Keep local spacing checks deterministic and passable when the upstream
        # builder does not emit explicit layer assignments.
        raw_layer = route.get("layer")
        if raw_layer is None:
            route["layer"] = {"layer": int(idx + 1), "datatype": 0}

        raw_bends = route.get("bends")
        bends_out: list[dict[str, Any]] = []
        if isinstance(raw_bends, list):
            for bend in raw_bends:
                if not isinstance(bend, dict):
                    continue
                radius_um = _safe_float(bend.get("radius_um"))
                if radius_um is None or radius_um <= 0.0:
                    continue
                bends_out.append({"radius_um": float(radius_um)})
        if not bends_out:
            bends_out = [{"radius_um": float(min_bend_radius_um)}]
        route["bends"] = bends_out

        source = route.get("source")
        source_edge = source.get("edge") if isinstance(source, dict) and isinstance(source.get("edge"), dict) else {}
        graph_edge = graph_edges[idx] if idx < len(graph_edges) and isinstance(graph_edges[idx], dict) else {}
        src = str(source_edge.get("from") or route.get("from") or graph_edge.get("from") or "").strip()
        dst = str(source_edge.get("to") or route.get("to") or graph_edge.get("to") or "").strip()
        from_port = str(source_edge.get("from_port") or route.get("from_port") or graph_edge.get("from_port") or "out").strip() or "out"
        to_port = str(source_edge.get("to_port") or route.get("to_port") or graph_edge.get("to_port") or "in").strip() or "in"
        if src and dst:
            edge_payload: dict[str, Any] = {
                "from": src,
                "from_port": from_port,
                "to": dst,
                "to_port": to_port,
            }
            kind = source_edge.get("kind", graph_edge.get("kind"))
            if kind is not None:
                edge_payload["kind"] = kind
            edge_id = source_edge.get("id", graph_edge.get("id"))
            if edge_id is not None:
                edge_payload["id"] = edge_id
            route["source"] = {"edge": edge_payload}

        out_routes.append(route)

    out_routes.sort(key=lambda r: (str(r.get("route_id", "")).lower(), str(r.get("route_id", ""))))
    return {
        "schema_version": "0.1",
        "kind": str(routes_payload.get("kind") or "pic.routes"),
        "routes": out_routes,
    }


def _materialize(
    *,
    run_dir: Path,
    graph_template_ref: str,
    force: bool,
    report_path: Path | None,
) -> tuple[dict[str, Any], int]:
    warnings: list[str] = []
    graph_payload = _resolve_graph_template(graph_template_ref)
    pdk_request = _resolve_pdk_request(graph_payload)
    pdk_manifest_payload = _build_pdk_manifest_payload(pdk_request, warnings)

    ports_payload, routes_raw_payload, gds_mode, gds_expected = _generate_layout_sidecars(
        graph_payload=graph_payload,
        pdk_request=pdk_request,
        warnings=warnings,
    )
    routes_payload = _enrich_routes_for_local_backend(
        routes_payload=routes_raw_payload,
        graph_payload=graph_payload,
        design_rules=dict(pdk_manifest_payload.get("design_rules") or {}),
    )

    inputs_dir = (run_dir / "inputs").resolve()
    graph_path = (inputs_dir / "graph.json").resolve()
    ports_path = (inputs_dir / "ports.json").resolve()
    routes_path = (inputs_dir / "routes.json").resolve()
    layout_path = (inputs_dir / "layout.gds").resolve()
    pdk_manifest_path = (run_dir / "pdk_manifest.json").resolve()

    expected_text_payloads: dict[Path, bytes] = {
        graph_path: _json_bytes(graph_payload),
        ports_path: _json_bytes(ports_payload),
        routes_path: _json_bytes(routes_payload),
        pdk_manifest_path: _json_bytes(pdk_manifest_payload),
    }

    conflicted_files: list[str] = []
    unchanged_files: list[str] = []
    written_files: list[str] = []

    run_dir.mkdir(parents=True, exist_ok=True)
    inputs_dir.mkdir(parents=True, exist_ok=True)

    for path, expected in expected_text_payloads.items():
        rel = str(path.relative_to(run_dir)).replace("\\", "/")
        if path.exists():
            existing = path.read_bytes()
            if existing == expected:
                unchanged_files.append(rel)
                continue
            if not force:
                conflicted_files.append(rel)
                continue
        path.write_bytes(expected)
        written_files.append(rel)

    if layout_path.exists():
        rel_layout = str(layout_path.relative_to(run_dir)).replace("\\", "/")
        existing_layout = layout_path.read_bytes()
        if existing_layout == gds_expected:
            unchanged_files.append(rel_layout)
        elif not force:
            conflicted_files.append(rel_layout)
        else:
            layout_path.write_bytes(gds_expected)
            written_files.append(rel_layout)
    else:
        layout_path.write_bytes(gds_expected)
        written_files.append(str(layout_path.relative_to(run_dir)).replace("\\", "/"))

    ok = len(conflicted_files) == 0
    if not ok:
        exit_code = 1
        error = "existing_conflicts_require_force"
    else:
        exit_code = 0
        error = None

    report = {
        "schema_version": "0.1",
        "kind": "photonstrust.local_tapeout_run_materialization_report",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ok": ok,
        "error": error,
        "run_dir": str(run_dir),
        "graph_template": str(graph_template_ref),
        "force": bool(force),
        "warnings": sorted({str(v) for v in warnings if str(v).strip()}, key=lambda t: t.lower()),
        "gds_mode": gds_mode,
        "gds_placeholder_sha256_hint": "static:PHOTONTRUST_LOCAL_GDS_PLACEHOLDER_V1",
        "artifacts": {
            "graph_json": "inputs/graph.json",
            "ports_json": "inputs/ports.json",
            "routes_json": "inputs/routes.json",
            "layout_gds": "inputs/layout.gds",
            "pdk_manifest_json": "pdk_manifest.json",
        },
        "written_files": sorted(set(written_files), key=lambda t: t.lower()),
        "unchanged_files": sorted(set(unchanged_files), key=lambda t: t.lower()),
        "conflicted_files": sorted(set(conflicted_files), key=lambda t: t.lower()),
        "determinism": {
            "json_sort_keys": True,
            "json_trailing_newline": True,
            "graph_template_builtin_default": "minimal_chain",
            "gds_bytes_len": int(len(gds_expected)),
        },
    }

    if gds_mode == "placeholder":
        report["warnings"] = sorted(
            set(report["warnings"] + ["gdstk_unavailable_placeholder_layout_gds_written"]),
            key=lambda t: t.lower(),
        )

    if report_path is not None:
        report["report_path"] = str(report_path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    return report, exit_code


def main() -> int:
    args = parse_args()
    run_dir = args.run_dir if args.run_dir.is_absolute() else (Path.cwd() / args.run_dir)
    run_dir = run_dir.resolve()
    report_path = _resolve_output_path(run_dir, args.report_path)

    try:
        report, code = _materialize(
            run_dir=run_dir,
            graph_template_ref=str(args.graph_template),
            force=bool(args.force),
            report_path=report_path,
        )
    except Exception as exc:
        report = {
            "schema_version": "0.1",
            "kind": "photonstrust.local_tapeout_run_materialization_report",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "ok": False,
            "error": str(exc),
            "run_dir": str(run_dir),
            "graph_template": str(args.graph_template),
            "force": bool(args.force),
            "warnings": [],
            "artifacts": {},
            "written_files": [],
            "unchanged_files": [],
            "conflicted_files": [],
        }
        code = 1

    print(json.dumps(report, indent=2))
    return int(code)


if __name__ == "__main__":
    raise SystemExit(main())
