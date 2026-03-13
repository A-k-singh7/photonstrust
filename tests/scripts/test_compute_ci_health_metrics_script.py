from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_script_module():
    script_path = REPO_ROOT / "scripts" / "compute_ci_health_metrics.py"
    spec = importlib.util.spec_from_file_location("compute_ci_health_metrics_under_test", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_runs(path: Path) -> None:
    payload = {
        "workflow_runs": [
            {
                "name": "ci-smoke",
                "conclusion": "failure",
                "run_attempt": 1,
                "created_at": "2026-03-01T00:00:00Z",
                "updated_at": "2026-03-01T00:10:00Z",
            },
            {
                "name": "ci-smoke",
                "conclusion": "success",
                "run_attempt": 1,
                "created_at": "2026-03-01T06:00:00Z",
                "updated_at": "2026-03-01T06:10:00Z",
            },
            {
                "name": "ci-smoke",
                "conclusion": "success",
                "run_attempt": 2,
                "created_at": "2026-03-02T00:00:00Z",
                "updated_at": "2026-03-02T00:10:00Z",
            },
            {
                "name": "ci-smoke",
                "conclusion": "failure",
                "run_attempt": 1,
                "created_at": "2026-03-03T00:00:00Z",
                "updated_at": "2026-03-03T00:10:00Z",
            },
            {
                "name": "security-baseline",
                "conclusion": "success",
                "run_attempt": 1,
                "created_at": "2026-03-01T01:00:00Z",
                "updated_at": "2026-03-01T01:05:00Z",
            },
        ]
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_compute_ci_health_metrics_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _load_script_module()
    runs_json = tmp_path / "runs.json"
    output_json = tmp_path / "ci_metrics.json"
    output_md = tmp_path / "ci_metrics.md"
    _write_runs(runs_json)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "compute_ci_health_metrics.py",
            "--runs-json",
            str(runs_json),
            "--workflow",
            "ci-smoke",
            "--window-days",
            "365",
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ],
    )

    assert module.main() == 0

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["kind"] == "photonstrust.ci_history_metrics"
    assert payload["metrics"]["run_count"] == 4
    assert payload["metrics"]["pass_rate_percent"] == 50.0
    assert payload["metrics"]["flaky_rate_percent"] == 25.0
    assert payload["metrics"]["mean_time_to_recovery_hours"] == 6.0
    assert payload["status"]["overall"] == "fail"

    markdown = output_md.read_text(encoding="utf-8")
    assert "CI Health Scoreboard" in markdown
    assert "Build pass rate" in markdown


def test_compute_ci_health_metrics_fails_on_threshold_breach(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _load_script_module()
    runs_json = tmp_path / "runs.json"
    output_json = tmp_path / "ci_metrics.json"
    output_md = tmp_path / "ci_metrics.md"
    _write_runs(runs_json)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "compute_ci_health_metrics.py",
            "--runs-json",
            str(runs_json),
            "--workflow",
            "ci-smoke",
            "--window-days",
            "365",
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
            "--min-pass-rate-percent",
            "90",
            "--fail-on-threshold-breach",
        ],
    )

    assert module.main() == 1
