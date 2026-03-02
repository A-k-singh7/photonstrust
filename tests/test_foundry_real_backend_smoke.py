from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _make_local_layout_run_dir(root: Path) -> Path:
    run_dir = root / "layout_run"
    inputs = run_dir / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)

    _write_json(
        inputs / "graph.json",
        {
            "schema_version": "0.1",
            "graph_id": "smoke_local_graph",
            "profile": "pic_circuit",
            "circuit": {"id": "smoke_local_graph", "wavelength_nm": 1550},
            "nodes": [
                {"id": "gc_in", "kind": "pic.grating_coupler", "params": {}},
                {"id": "wg_1", "kind": "pic.waveguide", "params": {"length_um": 200.0}},
                {"id": "ec_out", "kind": "pic.edge_coupler", "params": {}},
            ],
            "edges": [
                {"from": "gc_in", "to": "wg_1", "kind": "optical"},
                {"from": "wg_1", "to": "ec_out", "kind": "optical"},
            ],
        },
    )
    _write_json(
        inputs / "ports.json",
        {
            "schema_version": "0.1",
            "kind": "pic.ports",
            "ports": [
                {"node": "gc_in", "port": "out", "role": "out", "x_um": -20.0, "y_um": 0.0},
                {"node": "wg_1", "port": "in", "role": "in", "x_um": 80.0, "y_um": 0.0},
                {"node": "wg_1", "port": "out", "role": "out", "x_um": 120.0, "y_um": 0.0},
                {"node": "ec_out", "port": "in", "role": "in", "x_um": 220.0, "y_um": 0.0},
            ],
        },
    )
    _write_json(
        inputs / "routes.json",
        {
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
                    "source": {"edge": {"from": "gc_in", "from_port": "out", "to": "wg_1", "to_port": "in", "kind": "optical"}},
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
        },
    )
    _write_json(
        run_dir / "pdk_manifest.json",
        {
            "name": "local_smoke_pdk",
            "version": "1",
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
        },
    )
    (inputs / "layout.gds").write_bytes(b"GDSII")
    return run_dir


def _run_smoke(
    args: list[str],
    *,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    script = REPO_ROOT / "scripts" / "run_foundry_smoke.py"
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=str(cwd or REPO_ROOT),
        check=False,
        capture_output=True,
        text=True,
        env=run_env,
    )


def test_foundry_smoke_dry_run_prints_plan(tmp_path: Path) -> None:
    output_json = tmp_path / "dry_run_report.json"
    completed = _run_smoke(["--dry-run", "--output-json", str(output_json)])
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "[dry-run] foundry smoke plan" in completed.stdout
    assert "stages: drc, lvs, pex" in completed.stdout
    assert output_json.exists() is False


def test_foundry_smoke_stub_pass_writes_report_and_returns_zero(tmp_path: Path) -> None:
    output_json = tmp_path / "smoke_pass_report.json"
    completed = _run_smoke(["--output-json", str(output_json)])
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert output_json.exists()

    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["kind"] == "photonstrust.foundry_real_backend_smoke"
    assert report["mode"] == "stub"
    assert report["overall_status"] == "pass"
    for stage in ("drc", "lvs", "pex"):
        summary = report["stages"][stage]
        assert summary["status"] == "pass"
        assert summary["execution_backend"] == "generic_cli"
        assert summary["error_code"] is None


def test_foundry_smoke_stub_fail_stage_returns_one_in_strict_mode(tmp_path: Path) -> None:
    output_json = tmp_path / "smoke_fail_report.json"
    completed = _run_smoke(["--fail-stage", "lvs", "--output-json", str(output_json)])
    assert completed.returncode == 1
    assert output_json.exists()

    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["overall_status"] == "fail"
    assert report["stages"]["lvs"]["status"] == "fail"


def test_foundry_smoke_stub_fail_stage_returns_zero_in_non_strict_mode(tmp_path: Path) -> None:
    output_json = tmp_path / "smoke_fail_nonstrict_report.json"
    completed = _run_smoke(["--fail-stage", "drc", "--no-strict", "--output-json", str(output_json)])
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert output_json.exists()

    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["strict"] is False
    assert report["overall_status"] == "fail"
    assert report["stages"]["drc"]["status"] == "fail"


def test_foundry_smoke_local_only_guard_blocks_ci_without_allow_ci(tmp_path: Path) -> None:
    output_json = tmp_path / "ci_blocked_report.json"
    completed = _run_smoke(["--output-json", str(output_json)], env={"CI": "1"})
    assert completed.returncode == 2
    assert "local-only script refused in CI" in (completed.stdout + completed.stderr)
    assert output_json.exists() is False


def test_foundry_smoke_runner_config_missing_file_fails_cleanly(tmp_path: Path) -> None:
    output_json = tmp_path / "missing_config_report.json"
    missing_config = tmp_path / "missing_runner_config.json"
    completed = _run_smoke(["--runner-config", str(missing_config), "--output-json", str(output_json)])
    assert completed.returncode == 1
    assert "runner-config file not found" in (completed.stdout + completed.stderr).lower()
    assert output_json.exists() is False


def test_foundry_smoke_local_backend_from_run_dir_context_without_runner_config(tmp_path: Path) -> None:
    run_dir = _make_local_layout_run_dir(tmp_path)
    output_json = tmp_path / "local_backend_report.json"
    completed = _run_smoke(
        [
            "--use-local-backend",
            "--output-json",
            str(output_json),
        ],
        cwd=run_dir,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert output_json.exists()

    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["mode"] == "local"
    assert report["overall_status"] == "pass"
    assert report["stages"]["drc"]["execution_backend"] == "local_rules"
    assert report["stages"]["lvs"]["execution_backend"] == "local_lvs"
    assert report["stages"]["pex"]["execution_backend"] == "local_pex"
    for stage in ("drc", "lvs", "pex"):
        assert report["stages"][stage]["status"] == "pass"


def test_foundry_smoke_report_does_not_include_command_or_env_leakage(tmp_path: Path) -> None:
    output_json = tmp_path / "leakage_check_report.json"
    completed = _run_smoke(["--output-json", str(output_json)])
    assert completed.returncode == 0, completed.stdout + completed.stderr
    payload_text = output_json.read_text(encoding="utf-8")

    forbidden_tokens = [
        '"command"',
        '"env"',
        '"env_allowlist"',
        "deck_path",
        "rule_text",
        "summary_json_path",
        str(tmp_path),
    ]
    for token in forbidden_tokens:
        assert token not in payload_text
