from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_SMOKE_GENERATED_AT = "2026-03-01T00:00:00+00:00"
_MANDATORY_DRC_RULE_IDS = (
    "DRC.WG.MIN_WIDTH",
    "DRC.WG.MIN_SPACING",
    "DRC.WG.MIN_BEND_RADIUS",
    "DRC.WG.MIN_ENCLOSURE",
)
_SIGNOFF_STAGE_ORDER = (
    "chip_assembly",
    "drc",
    "lvs",
    "pex",
    "foundry_approval",
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _make_local_layout_run_dir(root: Path) -> Path:
    run_dir = root / "real_run_pkg"
    inputs = run_dir / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)

    _write_json(
        inputs / "graph.json",
        {
            "schema_version": "0.1",
            "graph_id": "day10_local_graph",
            "profile": "pic_circuit",
            "circuit": {"id": "day10_local_graph", "wavelength_nm": 1550},
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
            "name": "day10_local_pdk",
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


def _run_day10(args: list[str]) -> subprocess.CompletedProcess[str]:
    script = REPO_ROOT / "scripts" / "run_day10_tapeout_rehearsal.py"
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


def _load_day10_module():
    script_path = REPO_ROOT / "scripts" / "run_day10_tapeout_rehearsal.py"
    spec = importlib.util.spec_from_file_location("day10_tapeout_rehearsal_under_test", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_day10_rehearsal_dry_run_prints_plan(tmp_path: Path) -> None:
    packet_path = tmp_path / "dry_run_packet.json"
    completed = _run_day10(["--dry-run", "--output-json", str(packet_path)])

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "[dry-run] Day 10 tapeout rehearsal plan" in completed.stdout
    assert packet_path.exists() is False


def test_day10_rehearsal_synthetic_pass_emits_go_packet(tmp_path: Path) -> None:
    packet_path = tmp_path / "day10_packet_pass.json"
    run_dir = tmp_path / "run_pkg_pass"
    completed = _run_day10(
        [
            "--mode",
            "synthetic",
            "--output-json",
            str(packet_path),
            "--run-dir",
            str(run_dir),
        ]
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert packet_path.exists()

    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    assert packet["kind"] == "photonstrust.day10_tapeout_rehearsal_packet"
    assert packet["decision"] == "GO"
    assert packet["smoke_overall_status"] == "pass"
    assert packet["tapeout_all_passed"] is True
    smoke_step = next(step for step in packet.get("steps", []) if step.get("name") == "foundry_smoke")
    assert smoke_step["execution"] == "in_process_synthetic"
    assert "command" not in smoke_step

    artifacts = packet.get("artifacts", {})
    assert Path(artifacts["foundry_smoke_report_json"]).exists()
    assert Path(artifacts["tapeout_gate_report_json"]).exists()
    smoke_report = json.loads(Path(artifacts["foundry_smoke_report_json"]).read_text(encoding="utf-8"))
    assert smoke_report["generated_at"] == SYNTHETIC_SMOKE_GENERATED_AT
    assert smoke_report["overall_status"] == "pass"
    assert smoke_report["stages"]["drc"]["status"] == "pass"
    assert smoke_report["stages"]["lvs"]["status"] == "pass"
    assert smoke_report["stages"]["pex"]["status"] == "pass"
    foundry_paths = artifacts.get("foundry_summary_paths", {})
    assert Path(foundry_paths["drc"]).exists()
    assert Path(foundry_paths["lvs"]).exists()
    assert Path(foundry_paths["pex"]).exists()
    assert Path(foundry_paths["foundry_approval"]).exists()
    drc_summary = json.loads(Path(foundry_paths["drc"]).read_text(encoding="utf-8"))
    rule_results = drc_summary.get("rule_results")
    assert isinstance(rule_results, dict)
    assert sorted(rule_results.keys()) == sorted(_MANDATORY_DRC_RULE_IDS)
    foundry_approval_summary = json.loads(Path(foundry_paths["foundry_approval"]).read_text(encoding="utf-8"))
    assert foundry_approval_summary["kind"] == "pic.foundry_approval_sealed_summary"
    assert foundry_approval_summary["decision"] == "GO"
    assert foundry_approval_summary["status"] == "pass"
    assert foundry_approval_summary["failed_check_ids"] == []
    tapeout_package = artifacts.get("tapeout_package", {})
    assert isinstance(tapeout_package, dict)
    assert Path(tapeout_package["package_dir"]).exists()
    assert Path(tapeout_package["manifest_path"]).exists()
    assert Path(tapeout_package["package_manifest_path"]).exists()
    assert Path(tapeout_package["report_json"]).exists()


def test_day10_rehearsal_synthetic_fail_returns_hold_in_strict_mode(tmp_path: Path) -> None:
    packet_path = tmp_path / "day10_packet_hold.json"
    run_dir = tmp_path / "run_pkg_hold"
    completed = _run_day10(
        [
            "--mode",
            "synthetic",
            "--fail-stage",
            "drc",
            "--output-json",
            str(packet_path),
            "--run-dir",
            str(run_dir),
        ]
    )

    assert completed.returncode == 1
    assert packet_path.exists()

    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    assert packet["decision"] == "HOLD"
    assert packet["smoke_overall_status"] == "fail"
    assert isinstance(packet.get("reasons"), list)
    assert "foundry_smoke_status=fail" in packet.get("reasons", [])
    smoke_report_path = Path(packet["artifacts"]["foundry_smoke_report_json"])
    smoke_report = json.loads(smoke_report_path.read_text(encoding="utf-8"))
    assert smoke_report["generated_at"] == SYNTHETIC_SMOKE_GENERATED_AT
    assert smoke_report["stages"]["drc"]["status"] == "fail"
    assert smoke_report["stages"]["lvs"]["status"] == "pass"
    assert smoke_report["stages"]["pex"]["status"] == "pass"
    assert smoke_report["stages"]["drc"]["failed_check_ids"] == ["DRC.SYNTH.FAIL"]
    foundry_paths = packet["artifacts"]["foundry_summary_paths"]
    foundry_approval_summary = _load_json(Path(foundry_paths["foundry_approval"]))
    assert foundry_approval_summary["decision"] == "HOLD"
    assert foundry_approval_summary["status"] == "fail"
    assert "DRC.SYNTH.FAIL" in foundry_approval_summary["failed_check_ids"]
    assert "foundry_approval.hold" not in foundry_approval_summary["failed_check_ids"]


def test_day10_rehearsal_synthetic_fail_can_exit_zero_in_non_strict_mode(tmp_path: Path) -> None:
    packet_path = tmp_path / "day10_packet_hold_nonstrict.json"
    run_dir = tmp_path / "run_pkg_hold_nonstrict"
    completed = _run_day10(
        [
            "--mode",
            "synthetic",
            "--fail-stage",
            "pex",
            "--no-strict",
            "--output-json",
            str(packet_path),
            "--run-dir",
            str(run_dir),
        ]
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert packet_path.exists()
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    assert packet["decision"] == "HOLD"


def test_day10_rehearsal_real_mode_missing_external_scripts_fails_fast(tmp_path: Path) -> None:
    packet_path = tmp_path / "day10_packet_real.json"
    run_dir = tmp_path / "run_pkg_real"
    run_dir.mkdir(parents=True, exist_ok=True)
    runner_config = tmp_path / "runner_config.json"
    runner_config.write_text("{}", encoding="utf-8")

    completed = _run_day10(
        [
            "--mode",
            "real",
            "--output-json",
            str(packet_path),
            "--run-dir",
            str(run_dir),
            "--runner-config",
            str(runner_config),
        ]
    )

    smoke_script = REPO_ROOT / "scripts" / "run_foundry_smoke.py"
    gate_script = REPO_ROOT / "scripts" / "check_pic_tapeout_gate.py"
    combined_output = completed.stdout + completed.stderr

    if not smoke_script.exists() or not gate_script.exists():
        assert completed.returncode == 2, combined_output
        assert "day10 error: missing required external scripts for real mode:" in combined_output
        assert "run_foundry_smoke.py" in combined_output
        assert "check_pic_tapeout_gate.py" in combined_output
        assert packet_path.exists() is False
        return

    assert completed.returncode == 1, combined_output
    assert packet_path.exists()
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    assert packet["decision"] == "HOLD"
    assert packet["smoke_overall_status"] == "error"


def test_day10_rehearsal_real_mode_can_use_local_smoke_backend_without_runner_config(tmp_path: Path) -> None:
    packet_path = tmp_path / "day10_packet_real_local_go.json"
    run_dir = _make_local_layout_run_dir(tmp_path)

    completed = _run_day10(
        [
            "--mode",
            "real",
            "--output-json",
            str(packet_path),
            "--run-dir",
            str(run_dir),
            "--smoke-local-backend",
        ]
    )

    combined_output = completed.stdout + completed.stderr
    assert completed.returncode == 0, combined_output
    assert packet_path.exists()

    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    assert packet["decision"] == "GO"
    assert packet["smoke_overall_status"] == "pass"
    assert packet["tapeout_all_passed"] is True
    assert packet["inputs"]["runner_config"] is None
    assert packet["inputs"]["smoke_local_backend"] is True

    smoke_step = next(step for step in packet.get("steps", []) if step.get("name") == "foundry_smoke")
    assert smoke_step["passed"] is True
    assert "--use-local-backend" in smoke_step.get("command", [])

    artifacts = packet.get("artifacts", {})
    smoke_report = json.loads(Path(artifacts["foundry_smoke_report_json"]).read_text(encoding="utf-8"))
    assert smoke_report["mode"] == "local"
    assert smoke_report["overall_status"] == "pass"
    assert smoke_report["stages"]["drc"]["execution_backend"] == "local_rules"
    assert smoke_report["stages"]["lvs"]["execution_backend"] == "local_lvs"
    assert smoke_report["stages"]["pex"]["execution_backend"] == "local_pex"

    signoff_path = run_dir / "signoff_ladder.json"
    assert signoff_path.exists()
    signoff = _load_json(signoff_path)
    assert signoff["kind"] == "pic.signoff_ladder"
    ladder = signoff.get("ladder", [])
    assert isinstance(ladder, list)
    assert len(ladder) == len(_SIGNOFF_STAGE_ORDER)
    assert [str(stage.get("stage")) for stage in ladder] == list(_SIGNOFF_STAGE_ORDER)

    foundry_paths = artifacts.get("foundry_summary_paths", {})
    summary_run_ids = {
        kind: str(_load_json(Path(foundry_paths[kind])).get("run_id") or "")
        for kind in ("drc", "lvs", "pex", "foundry_approval")
    }
    signoff_run_ids = {
        str(stage.get("stage")): str(stage.get("run_id") or "")
        for stage in ladder
        if str(stage.get("stage")) in {"drc", "lvs", "pex", "foundry_approval"}
    }
    for kind in ("drc", "lvs", "pex", "foundry_approval"):
        assert summary_run_ids[kind]
        assert signoff_run_ids[kind] == summary_run_ids[kind]


def test_day10_rehearsal_real_mode_local_backend_hold_signoff_foundry_approval_uses_foundry_failure_ids(
    tmp_path: Path,
) -> None:
    packet_path = tmp_path / "day10_packet_real_local_hold.json"
    run_dir = _make_local_layout_run_dir(tmp_path)

    pdk_manifest_path = run_dir / "pdk_manifest.json"
    pdk_manifest = _load_json(pdk_manifest_path)
    design_rules = pdk_manifest.get("design_rules")
    assert isinstance(design_rules, dict)
    design_rules["min_waveguide_width_um"] = 0.60
    _write_json(pdk_manifest_path, pdk_manifest)

    completed = _run_day10(
        [
            "--mode",
            "real",
            "--output-json",
            str(packet_path),
            "--run-dir",
            str(run_dir),
            "--smoke-local-backend",
        ]
    )

    combined_output = completed.stdout + completed.stderr
    assert completed.returncode == 1, combined_output
    assert packet_path.exists()

    packet = _load_json(packet_path)
    assert packet["decision"] == "HOLD"
    assert packet["smoke_overall_status"] == "fail"

    artifacts = packet.get("artifacts", {})
    smoke_report = _load_json(Path(artifacts["foundry_smoke_report_json"]))
    foundry_paths = artifacts.get("foundry_summary_paths", {})
    foundry_approval_summary = _load_json(Path(foundry_paths["foundry_approval"]))
    assert foundry_approval_summary["decision"] == "HOLD"
    assert foundry_approval_summary["status"] == "fail"
    assert "foundry_approval.hold" not in foundry_approval_summary["failed_check_ids"]
    smoke_failed_ids = sorted(
        {
            str(check_id)
            for stage in (smoke_report.get("stages") or {}).values()
            if isinstance(stage, dict)
            for check_id in (stage.get("failed_check_ids") or [])
            if str(check_id).strip()
        }
    )
    assert smoke_failed_ids

    signoff_path = run_dir / "signoff_ladder.json"
    assert signoff_path.exists()
    signoff = _load_json(signoff_path)
    assert signoff["kind"] == "pic.signoff_ladder"

    ladder = signoff.get("ladder", [])
    drc_stage = next(row for row in ladder if row.get("stage") == "drc")
    assert str(drc_stage.get("status")) == "fail"
    drc_failure_ids = [str(v) for v in (drc_stage.get("failure_rule_ids") or []) if str(v).strip()]
    assert drc_failure_ids
    assert set(smoke_failed_ids).issubset(set(drc_failure_ids))

    foundry_approval_stage = next(row for row in ladder if row.get("stage") == "foundry_approval")
    assert str(foundry_approval_stage.get("status")) == "skipped"
    assert list(foundry_approval_stage.get("failure_rule_ids") or []) == []
    all_failure_ids = [str(v) for row in ladder if isinstance(row, dict) for v in (row.get("failure_rule_ids") or [])]
    assert "foundry_approval.synthetic_hold" not in all_failure_ids
    assert "foundry_approval.hold" not in all_failure_ids


def test_day10_rehearsal_real_mode_bootstrap_local_backend_end_to_end(tmp_path: Path) -> None:
    packet_path = tmp_path / "day10_packet_real_bootstrap_go.json"
    run_dir = tmp_path / "real_bootstrap_run_pkg"

    completed = _run_day10(
        [
            "--mode",
            "real",
            "--output-json",
            str(packet_path),
            "--run-dir",
            str(run_dir),
            "--smoke-local-backend",
            "--bootstrap-local-run-dir",
            "--allow-ci",
        ]
    )

    combined_output = completed.stdout + completed.stderr
    assert completed.returncode == 0, combined_output
    assert packet_path.exists()

    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    assert packet["decision"] == "GO"
    assert packet["smoke_overall_status"] == "pass"
    assert packet["tapeout_all_passed"] is True
    assert packet["inputs"]["smoke_local_backend"] is True
    assert packet["inputs"]["bootstrap_local_run_dir"] is True
    assert packet["inputs"]["bootstrap_local_run_dir_used"] is True

    steps = packet.get("steps", [])
    bootstrap_step = next(step for step in steps if step.get("name") == "bootstrap_local_run_dir")
    smoke_step = next(step for step in steps if step.get("name") == "foundry_smoke")
    assert bootstrap_step["passed"] is True
    assert smoke_step["passed"] is True
    assert "--use-local-backend" in smoke_step.get("command", [])
    assert "--allow-ci" in smoke_step.get("command", [])

    step_names = [str(step.get("name")) for step in steps]
    assert step_names.index("bootstrap_local_run_dir") < step_names.index("foundry_smoke")

    artifacts = packet.get("artifacts", {})
    smoke_report = json.loads(Path(artifacts["foundry_smoke_report_json"]).read_text(encoding="utf-8"))
    assert smoke_report["mode"] == "local"
    assert smoke_report["overall_status"] == "pass"
    assert smoke_report["stages"]["drc"]["execution_backend"] == "local_rules"
    assert smoke_report["stages"]["lvs"]["execution_backend"] == "local_lvs"
    assert smoke_report["stages"]["pex"]["execution_backend"] == "local_pex"

    foundry_paths = artifacts.get("foundry_summary_paths", {})
    assert Path(foundry_paths["drc"]).exists()
    assert Path(foundry_paths["lvs"]).exists()
    assert Path(foundry_paths["pex"]).exists()
    assert Path(foundry_paths["foundry_approval"]).exists()
    foundry_approval_summary = _load_json(Path(foundry_paths["foundry_approval"]))
    assert foundry_approval_summary["decision"] == "GO"
    assert foundry_approval_summary["status"] == "pass"

    tapeout_package = artifacts.get("tapeout_package", {})
    assert isinstance(tapeout_package, dict)
    assert Path(tapeout_package["package_dir"]).exists()
    assert Path(tapeout_package["manifest_path"]).exists()
    assert Path(tapeout_package["package_manifest_path"]).exists()
    assert Path(tapeout_package["report_json"]).exists()


def test_day10_rehearsal_real_mode_bootstrap_local_run_dir_records_step_and_inputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _load_day10_module()
    packet_path = tmp_path / "day10_packet_real_local_bootstrap.json"
    run_dir = tmp_path / "bootstrap_run_pkg"

    args = argparse.Namespace(
        mode="real",
        output_json=packet_path,
        run_dir=run_dir,
        runner_config=None,
        smoke_local_backend=True,
        bootstrap_local_run_dir=True,
        waiver_file=None,
        allow_waived_failures=False,
        require_non_mock_backend=True,
        run_pic_gate=False,
        pic_gate_args="--dry-run",
        deck_fingerprint="sha256:day10-bootstrap",
        timeout_sec=60.0,
        fail_stage="none",
        strict=True,
        dry_run=False,
        allow_ci=True,
    )
    monkeypatch.setattr(module, "parse_args", lambda: args)
    monkeypatch.setattr(module, "_missing_real_mode_scripts", lambda repo_root, include_bootstrap: [])

    command_log: list[list[str]] = []

    def _arg_value(cmd: list[str], flag: str) -> str:
        idx = cmd.index(flag)
        return str(cmd[idx + 1])

    def _fake_run_command(cmd: list[str], *, cwd: Path) -> dict:
        command_log.append(list(cmd))
        cmd_text = " ".join(cmd)
        if "materialize_local_tapeout_run.py" in cmd_text:
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "inputs").mkdir(parents=True, exist_ok=True)
        elif "run_foundry_smoke.py" in cmd_text:
            out_path = Path(_arg_value(cmd, "--output-json"))
            _write_json(
                out_path,
                {
                    "schema_version": "0.1",
                    "kind": "photonstrust.foundry_smoke_report",
                    "generated_at": "2026-03-01T00:00:00+00:00",
                    "deck_fingerprint": "sha256:day10-bootstrap",
                    "overall_status": "pass",
                    "stages": {
                        "drc": {
                            "run_id": "drc_bootstrap",
                            "status": "pass",
                            "execution_backend": "local_rules",
                            "check_counts": {"total": 1, "passed": 1, "failed": 0, "errored": 0},
                            "failed_check_ids": [],
                            "failed_check_names": [],
                            "error_code": None,
                        },
                        "lvs": {
                            "run_id": "lvs_bootstrap",
                            "status": "pass",
                            "execution_backend": "local_lvs",
                            "check_counts": {"total": 1, "passed": 1, "failed": 0, "errored": 0},
                            "failed_check_ids": [],
                            "failed_check_names": [],
                            "error_code": None,
                        },
                        "pex": {
                            "run_id": "pex_bootstrap",
                            "status": "pass",
                            "execution_backend": "local_pex",
                            "check_counts": {"total": 1, "passed": 1, "failed": 0, "errored": 0},
                            "failed_check_ids": [],
                            "failed_check_names": [],
                            "error_code": None,
                        },
                    },
                },
            )
        elif "check_pic_tapeout_gate.py" in cmd_text:
            report_path = Path(_arg_value(cmd, "--report-path"))
            _write_json(report_path, {"all_passed": True, "checks": []})
        return {
            "command": list(cmd),
            "returncode": 0,
            "duration_s": 0.001,
            "stdout_tail": "",
            "stderr_tail": "",
        }

    def _fake_build_tapeout_package(payload: dict, *, repo_root: Path) -> dict:
        package_dir = Path(payload["output_root"]) / "pkg"
        package_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = package_dir / "manifest.json"
        package_manifest_path = package_dir / "package_manifest.json"
        manifest_path.write_text("{}", encoding="utf-8")
        package_manifest_path.write_text("{}", encoding="utf-8")
        return {
            "package_dir": str(package_dir),
            "manifest_path": str(manifest_path),
            "package_manifest_path": str(package_manifest_path),
        }

    monkeypatch.setattr(module, "_run_command", _fake_run_command)
    monkeypatch.setattr(module, "build_tapeout_package", _fake_build_tapeout_package)

    returncode = module.main()
    assert returncode == 0
    assert packet_path.exists()

    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    assert packet["decision"] == "GO"
    assert packet["inputs"]["smoke_local_backend"] is True
    assert packet["inputs"]["bootstrap_local_run_dir"] is True
    assert packet["inputs"]["bootstrap_local_run_dir_used"] is True
    assert packet["inputs"]["allow_ci"] is True

    steps = packet.get("steps", [])
    bootstrap_step = next(step for step in steps if step.get("name") == "bootstrap_local_run_dir")
    assert bootstrap_step["passed"] is True
    assert "--allow-ci" in bootstrap_step.get("command", [])

    smoke_step = next(step for step in steps if step.get("name") == "foundry_smoke")
    assert smoke_step["passed"] is True
    assert "--allow-ci" in smoke_step.get("command", [])
    assert "--use-local-backend" in smoke_step.get("command", [])

    ordered_step_names = [str(step.get("name")) for step in steps]
    assert ordered_step_names.index("bootstrap_local_run_dir") < ordered_step_names.index("foundry_smoke")
    assert run_dir.exists()
    foundry_paths = packet["artifacts"]["foundry_summary_paths"]
    foundry_approval_summary = _load_json(Path(foundry_paths["foundry_approval"]))
    assert foundry_approval_summary["decision"] == "GO"
    assert foundry_approval_summary["status"] == "pass"


def test_day10_rehearsal_synthetic_gate_failure_signoff_uses_materialized_foundry_approval_summary(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _load_day10_module()
    packet_path = tmp_path / "day10_packet_synthetic_gate_hold.json"
    run_dir = tmp_path / "run_pkg_synthetic_gate_hold"

    args = argparse.Namespace(
        mode="synthetic",
        output_json=packet_path,
        run_dir=run_dir,
        runner_config=None,
        smoke_local_backend=False,
        bootstrap_local_run_dir=False,
        waiver_file=None,
        allow_waived_failures=False,
        require_non_mock_backend=True,
        run_pic_gate=False,
        pic_gate_args="--dry-run",
        deck_fingerprint="sha256:day10-synthetic-gate-hold",
        timeout_sec=60.0,
        fail_stage="none",
        strict=True,
        dry_run=False,
        allow_ci=False,
    )
    monkeypatch.setattr(module, "parse_args", lambda: args)

    def _fake_build_synthetic_tapeout_gate_report(**kwargs) -> dict:
        return {
            "schema_version": "0.1",
            "kind": "photonstrust.pic_tapeout_gate_report",
            "generated_at": SYNTHETIC_SMOKE_GENERATED_AT,
            "run_dir": str(kwargs["run_dir"]),
            "all_passed": False,
            "checks": [
                {
                    "name": "require_non_mock_backend",
                    "passed": False,
                }
            ],
            "policy": {
                "require_non_mock_backend": True,
                "allow_waived_failures": False,
                "run_pic_gate": False,
            },
        }

    def _fake_assembly_report(*, run_dir: Path) -> dict:
        return {
            "schema_version": "0.1",
            "kind": "pic.chip_assembly",
            "assembly_run_id": "abc12345",
            "outputs": {
                "summary": {
                    "status": "pass",
                    "output_hash": "a" * 64,
                }
            },
            "stitch": {
                "summary": {
                    "status": "pass",
                    "failed_links": 0,
                    "stitched_links": 1,
                    "warnings": [],
                }
            },
        }

    def _fake_build_tapeout_package(payload: dict, *, repo_root: Path) -> dict:
        package_dir = Path(payload["output_root"]) / "pkg"
        package_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = package_dir / "manifest.json"
        package_manifest_path = package_dir / "package_manifest.json"
        manifest_path.write_text("{}", encoding="utf-8")
        package_manifest_path.write_text("{}", encoding="utf-8")
        return {
            "package_dir": str(package_dir),
            "manifest_path": str(manifest_path),
            "package_manifest_path": str(package_manifest_path),
        }

    monkeypatch.setattr(module, "_build_synthetic_tapeout_gate_report", _fake_build_synthetic_tapeout_gate_report)
    monkeypatch.setattr(module, "_load_or_derive_assembly_report", _fake_assembly_report)
    monkeypatch.setattr(module, "build_tapeout_package", _fake_build_tapeout_package)

    returncode = module.main()
    assert returncode == 1
    assert packet_path.exists()

    packet = _load_json(packet_path)
    assert packet["decision"] == "HOLD"
    foundry_paths = packet["artifacts"]["foundry_summary_paths"]
    foundry_approval_summary = _load_json(Path(foundry_paths["foundry_approval"]))
    assert foundry_approval_summary["decision"] == "HOLD"
    assert foundry_approval_summary["status"] == "fail"
    assert foundry_approval_summary["failed_check_ids"] == ["tapeout_gate.require_non_mock_backend"]
    assert "foundry_approval.hold" not in foundry_approval_summary["failed_check_ids"]

    signoff = _load_json(run_dir / "signoff_ladder.json")
    ladder = signoff.get("ladder", [])
    foundry_approval_stage = next(row for row in ladder if row.get("stage") == "foundry_approval")
    assert str(foundry_approval_stage.get("status")) == "fail"
    assert sorted(list(foundry_approval_stage.get("failure_rule_ids") or [])) == sorted(
        foundry_approval_summary["failed_check_ids"]
    )
    assert "foundry_approval.hold" not in list(foundry_approval_stage.get("failure_rule_ids") or [])


def test_day10_rehearsal_bootstrap_flag_requires_real_mode(tmp_path: Path) -> None:
    packet_path = tmp_path / "day10_packet_bootstrap_argparse.json"
    completed = _run_day10(
        [
            "--mode",
            "synthetic",
            "--bootstrap-local-run-dir",
            "--output-json",
            str(packet_path),
        ]
    )

    assert completed.returncode == 2
    assert "--bootstrap-local-run-dir requires --mode real" in (completed.stdout + completed.stderr)


def test_day10_rehearsal_bootstrap_flag_requires_local_smoke_backend(tmp_path: Path) -> None:
    packet_path = tmp_path / "day10_packet_bootstrap_local_argparse.json"
    runner_config = tmp_path / "runner_config.json"
    runner_config.write_text("{}", encoding="utf-8")
    completed = _run_day10(
        [
            "--mode",
            "real",
            "--bootstrap-local-run-dir",
            "--runner-config",
            str(runner_config),
            "--output-json",
            str(packet_path),
        ]
    )

    assert completed.returncode == 2
    assert "--bootstrap-local-run-dir requires --smoke-local-backend" in (completed.stdout + completed.stderr)
