from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_script_module():
    script_path = REPO_ROOT / "scripts" / "check_maintainability_budgets.py"
    spec = importlib.util.spec_from_file_location("check_maintainability_budgets_under_test", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_file(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_policy(path: Path, *, budgets: list[dict], commands: list[str] | None = None) -> None:
    payload = {
        "schema_version": "0.1",
        "kind": "photonstrust.maintainability_budget_policy",
        "phase": "phase0",
        "budgets": budgets,
        "characterization_commands": commands or [],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_budget_script_writes_pass_report(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _load_script_module()
    repo_root = tmp_path / "repo"
    policy_path = tmp_path / "policy.json"
    output_json = tmp_path / "report.json"

    _write_file(repo_root / "pkg" / "small.py", "a\n" * 4)
    _write_file(repo_root / "web" / "src" / "state" / "tiny.js", "x\n" * 3)
    _write_policy(
        policy_path,
        budgets=[
            {
                "label": "pkg-modules",
                "include_glob": "pkg/*.py",
                "max_lines": 5,
            },
            {
                "label": "future-hooks",
                "include_glob": "web/src/hooks/**/*.js",
                "max_lines": 10,
                "allow_zero_matches": True,
            },
        ],
        commands=["python -m pytest -q tests/test_example.py"],
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "check_maintainability_budgets.py",
            "--config",
            str(policy_path),
            "--repo-root",
            str(repo_root),
            "--output-json",
            str(output_json),
        ],
    )

    assert module.main() == 0

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["kind"] == "photonstrust.maintainability_budget_report"
    assert payload["status"]["overall"] == "pass"
    assert payload["status"]["failed_budget_count"] == 0
    assert payload["characterization_commands"] == ["python -m pytest -q tests/test_example.py"]


def test_budget_script_reports_breaches_and_missing_required_matches(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _load_script_module()
    repo_root = tmp_path / "repo"
    policy_path = tmp_path / "policy.json"
    output_json = tmp_path / "report.json"

    _write_file(repo_root / "pkg" / "too_big.py", "a\n" * 6)
    _write_policy(
        policy_path,
        budgets=[
            {
                "label": "pkg-modules",
                "include_glob": "pkg/*.py",
                "max_lines": 5,
            },
            {
                "label": "required-hooks",
                "include_glob": "web/src/hooks/**/*.js",
                "max_lines": 10,
            },
        ],
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "check_maintainability_budgets.py",
            "--config",
            str(policy_path),
            "--repo-root",
            str(repo_root),
            "--output-json",
            str(output_json),
        ],
    )

    assert module.main() == 1

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["status"]["overall"] == "fail"
    assert payload["status"]["failed_budget_count"] == 2
    pkg_budget = next(item for item in payload["budgets"] if item["label"] == "pkg-modules")
    hooks_budget = next(item for item in payload["budgets"] if item["label"] == "required-hooks")
    assert pkg_budget["offending_files"][0]["path"] == "pkg/too_big.py"
    assert hooks_budget["missing_match"] is True


def test_repo_phase0_policy_matches_current_baseline(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _load_script_module()
    output_json = tmp_path / "baseline_report.json"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "check_maintainability_budgets.py",
            "--config",
            str(REPO_ROOT / "configs" / "maintainability" / "phase0_refactor_budgets.json"),
            "--repo-root",
            str(REPO_ROOT),
            "--output-json",
            str(output_json),
        ],
    )

    assert module.main() == 0

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["status"]["overall"] == "pass"
    assert payload["status"]["failed_budget_count"] == 0
