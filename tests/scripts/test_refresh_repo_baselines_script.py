from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_script_module():
    script_path = REPO_ROOT / "scripts" / "refresh_repo_baselines.py"
    spec = importlib.util.spec_from_file_location("refresh_repo_baselines_under_test", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_refresh_measurement_bundle_manifest_updates_sha(tmp_path: Path) -> None:
    module = _load_script_module()
    fixture_dir = tmp_path / "tests" / "fixtures" / "bundle_a" / "data"
    fixture_dir.mkdir(parents=True)
    payload_path = fixture_dir.parent / "measurement_bundle.json"
    sample_path = fixture_dir / "sample.txt"
    sample_path.write_text("alpha\n", encoding="utf-8")
    payload_path.write_text(
        json.dumps(
            {
                "dataset_id": "demo",
                "files": [
                    {
                        "path": "data/sample.txt",
                        "sha256": "stale",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    updated = module._refresh_measurement_bundle_manifest(payload_path)  # noqa: SLF001

    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    assert updated == 1
    assert payload["files"][0]["sha256"] == module._sha256(sample_path)  # noqa: SLF001


def test_normalize_milestones_runs_pre_commit(monkeypatch, tmp_path: Path) -> None:
    module = _load_script_module()
    milestone_root = tmp_path / "reports" / "specs" / "milestones"
    milestone_root.mkdir(parents=True)
    (milestone_root / "a.json").write_text("{}\n", encoding="utf-8")
    (milestone_root / "b.md").write_text("note\n", encoding="utf-8")
    calls: list[list[str]] = []

    def _fake_run(cmd: list[str], *, cwd: Path) -> None:
        calls.append(cmd)
        assert cwd == tmp_path

    monkeypatch.setattr(module, "_run", _fake_run)

    count = module.normalize_milestones(tmp_path, "python")

    assert count == 2
    assert calls == [[
        "python",
        "-m",
        "pre_commit",
        "run",
        "--files",
        "reports/specs/milestones/a.json",
        "reports/specs/milestones/b.md",
    ]]


def test_main_defaults_to_all_refresh_steps(monkeypatch, tmp_path: Path, capsys) -> None:
    module = _load_script_module()
    fixture_dir = tmp_path / "tests" / "fixtures" / "bundle_a" / "data"
    fixture_dir.mkdir(parents=True)
    sample_path = fixture_dir / "sample.txt"
    sample_path.write_text("alpha\n", encoding="utf-8")
    (fixture_dir.parent / "measurement_bundle.json").write_text(
        json.dumps(
            {
                "dataset_id": "demo",
                "files": [{"path": "data/sample.txt", "sha256": "stale"}],
            }
        ),
        encoding="utf-8",
    )
    milestone_root = tmp_path / "reports" / "specs" / "milestones"
    milestone_root.mkdir(parents=True)
    (milestone_root / "a.json").write_text("{}\n", encoding="utf-8")
    calls: list[list[str]] = []

    def _fake_run(cmd: list[str], *, cwd: Path) -> None:
        calls.append(cmd)
        assert cwd == tmp_path

    monkeypatch.setattr(module, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(module, "_run", _fake_run)
    monkeypatch.setattr(sys, "argv", ["refresh_repo_baselines.py"])

    assert module.main() == 0

    output = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert output["measurement_fixtures"]["manifest_count"] == 1
    assert output["release_gate_refreshed"] is True
    assert output["normalized_milestone_file_count"] == 1
    assert calls == [
        [sys.executable, "scripts/release/refresh_release_gate_packet.py"],
        [sys.executable, "-m", "pre_commit", "run", "--files", "reports/specs/milestones/a.json"],
    ]
