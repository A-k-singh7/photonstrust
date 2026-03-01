from __future__ import annotations

from pathlib import Path

from photonstrust.pic.tapeout_gate import run_pic_tapeout_gate


def _create_synthetic_run_dir(root: Path) -> Path:
    run_dir = root / "run_pkg"
    inputs = run_dir / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    (inputs / "graph.json").write_text("{}", encoding="utf-8")
    (inputs / "ports.json").write_text("[]", encoding="utf-8")
    (inputs / "routes.json").write_text("[]", encoding="utf-8")
    (inputs / "layout.gds").write_bytes(b"GDSII")
    return run_dir


def test_run_pic_tapeout_gate_dry_run_returns_ok_and_command(tmp_path: Path) -> None:
    report_path = tmp_path / "dry_run_report.json"

    result = run_pic_tapeout_gate(
        {
            "run_dir": "results/does_not_matter",
            "dry_run": True,
            "report_path": str(report_path),
        }
    )

    assert result["ok"] is True
    assert result["returncode"] == 0
    assert isinstance(result["command"], list)
    assert "--dry-run" in result["command"]
    assert result["report"] is None
    assert result["report_path"] == str(report_path.resolve())


def test_run_pic_tapeout_gate_minimal_fixture_passes(tmp_path: Path) -> None:
    run_dir = _create_synthetic_run_dir(tmp_path)
    report_path = tmp_path / "report.json"

    result = run_pic_tapeout_gate(
        {
            "run_dir": str(run_dir),
            "report_path": str(report_path),
        }
    )

    assert result["ok"] is True, str(result["stdout"]) + str(result["stderr"])
    assert result["returncode"] == 0
    assert result["report_path"] == str(report_path.resolve())
    assert isinstance(result["report"], dict)
    assert result["report"]["all_passed"] is True
