from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import pytest

import photonstrust.cli as cli_mod
import photonstrust.pipeline.m3_checkpoint as m3_checkpoint_mod
from photonstrust.benchmarks.schema import validate_instance
from photonstrust.pipeline.m3_checkpoint import run_m3_checkpoint
from photonstrust.workflow.schema import m3_checkpoint_report_schema_path


REPO_ROOT = Path(__file__).resolve().parents[1]
QKD_CONFIG = REPO_ROOT / "configs" / "quickstart" / "qkd_default.yml"
REPEATER_CONFIG = REPO_ROOT / "configs" / "demo2_repeater_spacing.yml"
REFERENCE_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "m3_checkpoint_reference.json"


def _path_to_repo_rel_or_placeholder(raw: object, *, repo_root: Path) -> str:
    if not isinstance(raw, str) or not raw.strip():
        return "<MISSING_PATH>"
    try:
        rel = Path(raw).resolve().relative_to(repo_root.resolve())
        return rel.as_posix()
    except Exception:
        return "<ABS_PATH>"


def _round_floats(obj: object) -> object:
    if isinstance(obj, float):
        return round(float(obj), 15)
    if isinstance(obj, list):
        return [_round_floats(item) for item in obj]
    if isinstance(obj, dict):
        return {str(key): _round_floats(value) for key, value in obj.items()}
    return obj


def _canonicalize_report(report: dict[str, object], *, repo_root: Path) -> dict[str, object]:
    payload = copy.deepcopy(report)
    payload["generated_at"] = "<GENERATED_AT>"

    inputs = payload.get("inputs")
    if isinstance(inputs, dict):
        inputs["qkd_config_path"] = _path_to_repo_rel_or_placeholder(inputs.get("qkd_config_path"), repo_root=repo_root)
        inputs["repeater_config_path"] = _path_to_repo_rel_or_placeholder(
            inputs.get("repeater_config_path"),
            repo_root=repo_root,
        )
        inputs["output_dir"] = "<OUTPUT_DIR>"

    qkd = payload.get("qkd")
    if isinstance(qkd, dict) and isinstance(qkd.get("bands"), list):
        qkd["bands"] = sorted(
            list(qkd["bands"]),
            key=lambda row: (
                str(row.get("scenario_id", "")) if isinstance(row, dict) else "",
                str(row.get("band", "")) if isinstance(row, dict) else "",
            ),
        )

    repeater = payload.get("repeater")
    if isinstance(repeater, dict) and isinstance(repeater.get("distances"), list):
        repeater["distances"] = sorted(
            list(repeater["distances"]),
            key=lambda row: float(row.get("total_distance_km", 0.0)) if isinstance(row, dict) else 0.0,
        )

    rounded = _round_floats(payload)
    assert isinstance(rounded, dict)
    return rounded


@pytest.fixture(scope="module")
def default_lane_report(tmp_path_factory: pytest.TempPathFactory) -> tuple[dict[str, object], Path]:
    output_dir = tmp_path_factory.mktemp("m3_checkpoint_default_lane")
    report = run_m3_checkpoint(
        qkd_config_path=QKD_CONFIG,
        repeater_config_path=REPEATER_CONFIG,
        output_dir=output_dir,
        force_analytic_backend=True,
        perturbation_fraction=0.05,
    )
    report_path = output_dir / "m3_checkpoint_report.json"
    assert report_path.exists()
    return report, report_path


def test_run_m3_checkpoint_returns_expected_report_shape(default_lane_report: tuple[dict[str, object], Path]) -> None:
    report, report_path = default_lane_report
    assert report.get("kind") == "photonstrust.m3_checkpoint_report"
    assert report.get("schema_version") == "0.1"
    assert isinstance(report.get("inputs"), dict)
    assert isinstance(report.get("qkd"), dict)
    assert isinstance(report.get("repeater"), dict)
    assert isinstance(report.get("summary"), dict)
    assert str(report.get("overall_status")) in {"PASS", "HOLD"}

    written = json.loads(report_path.read_text(encoding="utf-8"))
    assert written == report


def test_m3_report_validates_against_schema_helper_when_available(
    default_lane_report: tuple[dict[str, object], Path],
) -> None:
    report, _ = default_lane_report
    schema_path = m3_checkpoint_report_schema_path()
    if not schema_path.exists():
        pytest.skip("m3 checkpoint schema helper path exists but schema file is unavailable in this checkout")
    validate_instance(report, schema_path)


def test_m3_cli_strict_mode_exits_non_zero_on_hold(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def _fake_run_m3_checkpoint(**kwargs: object) -> dict[str, object]:
        _ = kwargs
        return {
            "schema_version": "0.1",
            "kind": "photonstrust.m3_checkpoint_report",
            "generated_at": "2026-03-02T00:00:00+00:00",
            "inputs": {
                "qkd_config_path": str(QKD_CONFIG),
                "repeater_config_path": str(REPEATER_CONFIG),
                "output_dir": None,
                "force_analytic_backend": True,
                "perturbation_fraction": 0.05,
            },
            "qkd": {"scenario_count": 0, "bands": [], "status": "HOLD"},
            "repeater": {"checks": {}, "distances": [], "status": "HOLD"},
            "summary": {
                "qkd_pass_bands": 0,
                "qkd_total_bands": 0,
                "repeater_stable_distances": 0,
                "repeater_total_distances": 0,
                "all_qkd_checks_pass": False,
                "repeater_stability_pass": False,
            },
            "overall_status": "HOLD",
        }

    monkeypatch.setattr(m3_checkpoint_mod, "run_m3_checkpoint", _fake_run_m3_checkpoint)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "photonstrust",
            "m3",
            "checkpoint",
            "--strict",
            "--output-dir",
            "results/test_m3_cli_strict_hold",
        ],
    )

    with pytest.raises(SystemExit) as excinfo:
        cli_mod.main()
    assert int(excinfo.value.code) == 1

    output = capsys.readouterr().out.strip()
    assert output
    summary = json.loads(output.splitlines()[-1])
    assert summary["overall_status"] == "HOLD"


def test_m3_default_lane_passes_and_writes_report_json(default_lane_report: tuple[dict[str, object], Path]) -> None:
    report, report_path = default_lane_report
    assert report_path.exists()
    assert report_path.name == "m3_checkpoint_report.json"
    assert report.get("overall_status") == "PASS"


def test_m3_reference_fixture_locked(default_lane_report: tuple[dict[str, object], Path]) -> None:
    if not REFERENCE_FIXTURE.exists():
        pytest.skip("M3 reference fixture missing. Run scripts/generate_m3_checkpoint_reference.py")

    report, _ = default_lane_report
    actual = _canonicalize_report(report, repo_root=REPO_ROOT)
    expected = json.loads(REFERENCE_FIXTURE.read_text(encoding="utf-8"))
    assert actual == expected
