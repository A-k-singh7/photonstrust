from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_materialize(args: list[str]) -> subprocess.CompletedProcess[str]:
    script = REPO_ROOT / "scripts" / "materialize_local_tapeout_run.py"
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=str(REPO_ROOT),
        check=False,
        capture_output=True,
        text=True,
    )


def _run_smoke(args: list[str]) -> subprocess.CompletedProcess[str]:
    script = REPO_ROOT / "scripts" / "run_foundry_smoke.py"
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=str(REPO_ROOT),
        check=False,
        capture_output=True,
        text=True,
    )


def _parse_stdout_json(completed: subprocess.CompletedProcess[str]) -> dict:
    return json.loads(completed.stdout)


def test_materialize_local_tapeout_run_success_and_smoke_compatible(tmp_path: Path) -> None:
    run_dir = tmp_path / "run_pkg"
    report_path = tmp_path / "materialize_report.json"

    completed = _run_materialize(["--run-dir", str(run_dir), "--report-path", str(report_path), "--allow-ci"])
    assert completed.returncode == 0, completed.stdout + completed.stderr
    report = _parse_stdout_json(completed)
    assert report["ok"] is True
    assert report["error"] is None
    assert report["run_dir"] == str(run_dir.resolve())
    assert report["report_path"] == str(report_path.resolve())
    assert report_path.exists()
    assert json.loads(report_path.read_text(encoding="utf-8")) == report

    graph_path = run_dir / "inputs" / "graph.json"
    ports_path = run_dir / "inputs" / "ports.json"
    routes_path = run_dir / "inputs" / "routes.json"
    layout_path = run_dir / "inputs" / "layout.gds"
    pdk_path = run_dir / "pdk_manifest.json"
    for path in (graph_path, ports_path, routes_path, layout_path, pdk_path):
        assert path.exists()

    routes_payload = json.loads(routes_path.read_text(encoding="utf-8"))
    route_rows = routes_payload.get("routes")
    assert isinstance(route_rows, list)
    assert len(route_rows) == 2
    assert all(float(row.get("width_um", 0.0)) > 0.0 for row in route_rows)
    assert all(float(row.get("enclosure_um", 0.0)) >= 1.0 for row in route_rows)
    assert all(isinstance(row.get("source"), dict) and isinstance((row.get("source") or {}).get("edge"), dict) for row in route_rows)
    assert all(isinstance(row.get("bends"), list) and len(row.get("bends") or []) >= 1 for row in route_rows)
    assert all(float((row.get("bends") or [{}])[0].get("radius_um", 0.0)) >= 5.0 for row in route_rows)
    assert all(0.0 < float(row.get("coupling_coeff", 0.0)) < 0.1 for row in route_rows)

    pdk_payload = json.loads(pdk_path.read_text(encoding="utf-8"))
    assert pdk_payload["name"] == "generic_silicon_photonics"
    assert pdk_payload["design_rules"]["min_waveguide_width_um"] == 0.45
    assert pdk_payload["pex_rules"]["max_coupling_coeff"] == 0.1

    smoke_output_json = tmp_path / "foundry_smoke_report.json"
    smoke = _run_smoke(
        [
            "--use-local-backend",
            "--run-dir",
            str(run_dir),
            "--output-json",
            str(smoke_output_json),
        ]
    )
    assert smoke.returncode == 0, smoke.stdout + smoke.stderr
    smoke_report = json.loads(smoke_output_json.read_text(encoding="utf-8"))
    assert smoke_report["mode"] == "local"
    assert smoke_report["overall_status"] == "pass"
    assert smoke_report["stages"]["drc"]["execution_backend"] == "local_rules"
    assert smoke_report["stages"]["lvs"]["execution_backend"] == "local_lvs"
    assert smoke_report["stages"]["pex"]["execution_backend"] == "local_pex"


def test_materialize_local_tapeout_run_accepts_custom_graph_template_path(tmp_path: Path) -> None:
    template_path = tmp_path / "custom_graph_template.json"
    custom_graph = {
        "schema_version": "0.1",
        "graph_id": "custom_template_graph",
        "profile": "pic_circuit",
        "circuit": {"id": "custom_template_graph", "wavelength_nm": 1550},
        "nodes": [
            {"id": "gc_in", "kind": "pic.grating_coupler", "params": {}},
            {"id": "wg_1", "kind": "pic.waveguide", "params": {"length_um": 250.0}},
            {"id": "ec_out", "kind": "pic.edge_coupler", "params": {}},
        ],
        "edges": [
            {"from": "gc_in", "to": "wg_1", "kind": "optical"},
            {"from": "wg_1", "to": "ec_out", "kind": "optical"},
        ],
    }
    template_path.write_text(json.dumps(custom_graph, indent=2), encoding="utf-8")

    run_dir = tmp_path / "run_pkg_custom"
    completed = _run_materialize(
        [
            "--run-dir",
            str(run_dir),
            "--graph-template",
            str(template_path),
        ]
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    report = _parse_stdout_json(completed)
    assert report["ok"] is True
    assert report["graph_template"] == str(template_path)

    persisted_graph = json.loads((run_dir / "inputs" / "graph.json").read_text(encoding="utf-8"))
    assert persisted_graph["graph_id"] == "custom_template_graph"
    assert len(persisted_graph["edges"]) == 2

    smoke_output_json = tmp_path / "foundry_smoke_custom_report.json"
    smoke = _run_smoke(
        [
            "--use-local-backend",
            "--run-dir",
            str(run_dir),
            "--output-json",
            str(smoke_output_json),
        ]
    )
    assert smoke.returncode == 0, smoke.stdout + smoke.stderr
    smoke_report = json.loads(smoke_output_json.read_text(encoding="utf-8"))
    assert smoke_report["overall_status"] == "pass"


def test_materialize_local_tapeout_run_is_idempotent_without_force(tmp_path: Path) -> None:
    run_dir = tmp_path / "run_pkg"
    first = _run_materialize(["--run-dir", str(run_dir)])
    assert first.returncode == 0, first.stdout + first.stderr

    second = _run_materialize(["--run-dir", str(run_dir)])
    assert second.returncode == 0, second.stdout + second.stderr
    report = _parse_stdout_json(second)
    assert report["ok"] is True
    assert report["conflicted_files"] == []
    assert report["written_files"] == []
    assert sorted(report["unchanged_files"]) == sorted(
        [
            "inputs/graph.json",
            "inputs/layout.gds",
            "inputs/ports.json",
            "inputs/routes.json",
            "pdk_manifest.json",
        ]
    )


def test_materialize_local_tapeout_run_requires_force_for_conflicting_files(tmp_path: Path) -> None:
    run_dir = tmp_path / "run_pkg"
    initial = _run_materialize(["--run-dir", str(run_dir)])
    assert initial.returncode == 0, initial.stdout + initial.stderr

    routes_path = run_dir / "inputs" / "routes.json"
    routes_path.write_text('{"schema_version":"0.1","kind":"pic.routes","routes":[]}\n', encoding="utf-8")

    no_force = _run_materialize(["--run-dir", str(run_dir)])
    assert no_force.returncode == 1, no_force.stdout + no_force.stderr
    no_force_report = _parse_stdout_json(no_force)
    assert no_force_report["ok"] is False
    assert no_force_report["error"] == "existing_conflicts_require_force"
    assert "inputs/routes.json" in no_force_report["conflicted_files"]

    with_force = _run_materialize(["--run-dir", str(run_dir), "--force"])
    assert with_force.returncode == 0, with_force.stdout + with_force.stderr
    force_report = _parse_stdout_json(with_force)
    assert force_report["ok"] is True
    assert "inputs/routes.json" in force_report["written_files"]

    repaired_routes = json.loads(routes_path.read_text(encoding="utf-8"))
    repaired_rows = repaired_routes.get("routes")
    assert isinstance(repaired_rows, list)
    assert len(repaired_rows) == 2
    assert all(0.0 < float(row.get("coupling_coeff", 0.0)) < 0.1 for row in repaired_rows)
