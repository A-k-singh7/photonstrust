#!/usr/bin/env python3
"""Materialize a deterministic local tapeout run directory for smoke rehearsal."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any


_PLACEHOLDER_GDS_BYTES = b"PHOTONTRUST_LOCAL_GDS_PLACEHOLDER_V1\n"
_DETERMINISTIC_GDS_TIMESTAMP = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

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

_PORTS_FIXTURE = {
    "schema_version": "0.1",
    "kind": "pic.ports",
    "ports": [
        {"node": "gc_in", "port": "out", "role": "out", "x_um": -20.0, "y_um": 0.0},
        {"node": "wg_1", "port": "in", "role": "in", "x_um": 80.0, "y_um": 0.0},
        {"node": "wg_1", "port": "out", "role": "out", "x_um": 120.0, "y_um": 0.0},
        {"node": "ec_out", "port": "in", "role": "in", "x_um": 220.0, "y_um": 0.0},
    ],
}

_ROUTES_FIXTURE = {
    "schema_version": "0.1",
    "kind": "pic.routes",
    "routes": [
        {
            "route_id": "e1:gc_in.out->wg_1.in",
            "width_um": 0.5,
            "enclosure_um": 1.5,
            "bends": [{"radius_um": 10.0}],
            "coupling_coeff": 0.01,
            "points_um": [[-20.0, 0.0], [80.0, 0.0]],
            "source": {
                "edge": {
                    "from": "gc_in",
                    "from_port": "out",
                    "to": "wg_1",
                    "to_port": "in",
                    "kind": "optical",
                }
            },
        },
        {
            "route_id": "e2:wg_1.out->ec_out.in",
            "width_um": 0.5,
            "enclosure_um": 1.5,
            "bends": [{"radius_um": 10.0}],
            "coupling_coeff": 0.02,
            "points_um": [[120.0, 0.0], [220.0, 0.0]],
            "source": {
                "edge": {
                    "from": "wg_1",
                    "from_port": "out",
                    "to": "ec_out",
                    "to_port": "in",
                    "kind": "optical",
                }
            },
        },
    ],
}

_PDK_MANIFEST_FIXTURE = {
    "name": "local_smoke_pdk",
    "version": "1",
    "notes": [
        "Synthetic non-proprietary local PDK fixture.",
        "Values are deterministic smoke defaults only.",
    ],
    "design_rules": {
        "min_waveguide_width_um": 0.45,
        "min_waveguide_gap_um": 0.2,
        "min_bend_radius_um": 5.0,
        "min_waveguide_enclosure_um": 1.0,
    },
    "pex_rules": {
        "resistance_ohm_per_um": 0.02,
        "capacitance_ff_per_um": 0.002,
        "max_total_resistance_ohm": 5000.0,
        "max_total_capacitance_ff": 10000.0,
        "max_rc_delay_ps": 50000.0,
        "max_coupling_coeff": 0.1,
        "min_net_coverage_ratio": 1.0,
    },
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


def _deterministic_layout_gds_bytes(warnings: list[str]) -> tuple[str, bytes]:
    try:
        import gdstk  # type: ignore
    except Exception:
        warnings.append("gdstk_unavailable_placeholder_layout_gds_written")
        return "placeholder", _PLACEHOLDER_GDS_BYTES

    try:
        lib = gdstk.Library(unit=1e-6, precision=1e-9)
        cell = lib.new_cell("PT_LOCAL_LAYOUT")
        cell.add(gdstk.rectangle((0.0, 0.0), (100.0, 10.0), layer=1, datatype=0))
        fd, tmp_name = tempfile.mkstemp(prefix="pt_local_layout_", suffix=".gds")
        os.close(fd)
        tmp_path = Path(tmp_name)
        try:
            lib.write_gds(str(tmp_path), timestamp=_DETERMINISTIC_GDS_TIMESTAMP)
        except TypeError:
            warnings.append("gdstk_no_timestamp_support_placeholder_layout_gds_written")
            return "placeholder", _PLACEHOLDER_GDS_BYTES
        payload = tmp_path.read_bytes()
        if not payload:
            warnings.append("gdstk_empty_output_placeholder_layout_gds_written")
            return "placeholder", _PLACEHOLDER_GDS_BYTES
        return "gdstk", payload
    except Exception:
        warnings.append("gdstk_write_failed_placeholder_layout_gds_written")
        return "placeholder", _PLACEHOLDER_GDS_BYTES
    finally:
        try:
            if "tmp_path" in locals() and isinstance(tmp_path, Path) and tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass


def _resolve_output_path(run_dir: Path, value: Path | None) -> Path | None:
    if value is None:
        return None
    if value.is_absolute():
        return value.resolve()
    return (run_dir / value).resolve()


def _materialize(
    *,
    run_dir: Path,
    graph_template_ref: str,
    force: bool,
    report_path: Path | None,
) -> tuple[dict[str, Any], int]:
    warnings: list[str] = []
    graph_payload = _resolve_graph_template(graph_template_ref)

    inputs_dir = (run_dir / "inputs").resolve()
    graph_path = (inputs_dir / "graph.json").resolve()
    ports_path = (inputs_dir / "ports.json").resolve()
    routes_path = (inputs_dir / "routes.json").resolve()
    layout_path = (inputs_dir / "layout.gds").resolve()
    pdk_manifest_path = (run_dir / "pdk_manifest.json").resolve()

    expected_text_payloads: dict[Path, bytes] = {
        graph_path: _json_bytes(graph_payload),
        ports_path: _json_bytes(_PORTS_FIXTURE),
        routes_path: _json_bytes(_ROUTES_FIXTURE),
        pdk_manifest_path: _json_bytes(_PDK_MANIFEST_FIXTURE),
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

    gds_mode, gds_expected = _deterministic_layout_gds_bytes(warnings)
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
        "warnings": sorted(set(warnings), key=lambda t: t.lower()),
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
            "gds_bytes_len": int(len(gds_expected)) if gds_mode == "placeholder" else int(layout_path.stat().st_size),
        },
    }

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
