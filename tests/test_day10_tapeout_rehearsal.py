from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_day10(args: list[str]) -> subprocess.CompletedProcess[str]:
    script = REPO_ROOT / "scripts" / "run_day10_tapeout_rehearsal.py"
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


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

    artifacts = packet.get("artifacts", {})
    assert Path(artifacts["foundry_smoke_report_json"]).exists()
    assert Path(artifacts["tapeout_gate_report_json"]).exists()
    foundry_paths = artifacts.get("foundry_summary_paths", {})
    assert Path(foundry_paths["drc"]).exists()
    assert Path(foundry_paths["lvs"]).exists()
    assert Path(foundry_paths["pex"]).exists()
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
