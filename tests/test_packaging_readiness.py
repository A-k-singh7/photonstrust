from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

try:
    import tomllib  # type: ignore[attr-defined]
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_citation_cff_contains_required_metadata() -> None:
    citation_path = REPO_ROOT / "CITATION.cff"
    assert citation_path.exists(), "CITATION.cff should exist at repository root"

    content = citation_path.read_text(encoding="utf-8")
    assert "cff-version:" in content
    assert "title: \"PhotonTrust\"" in content
    assert "type: software" in content
    assert "license: AGPL-3.0-only" in content
    assert "authors:" in content
    assert "repository-code:" in content

    version_match = re.search(r"^version:\s*0\.1\.0\s*$", content, flags=re.MULTILINE)
    assert version_match, "CITATION.cff must pin version 0.1.0"


def test_pyproject_has_packaging_metadata_fields() -> None:
    pyproject_path = REPO_ROOT / "pyproject.toml"
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    project = data["project"]

    for key in ("license", "authors", "keywords", "classifiers", "urls"):
        assert key in project, f"Missing [project] metadata field: {key}"

    assert "dependencies" in project
    assert "scripts" in project
    assert project["scripts"].get("photonstrust") == "photonstrust.cli:main"


def test_measure_quickstart_timing_script_runs_trivial_command() -> None:
    script = REPO_ROOT / "scripts" / "measure_quickstart_timing.py"
    assert script.exists(), "Timing script should exist"

    trivial_command = f'"{sys.executable}" -c "print(123)"'
    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--command",
            trivial_command,
            "--timeout",
            "5",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    assert payload["timed_out"] is False
    assert payload["returncode"] == 0
    assert payload["elapsed_seconds"] >= 0
    assert "123" in payload["stdout"]


def test_start_product_local_script_dry_run_prints_commands() -> None:
    script = REPO_ROOT / "scripts" / "dev" / "start_product_local.py"
    assert script.exists(), "Week 4 local launcher script should exist"

    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--dry-run",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "api_cmd:" in completed.stdout
    assert "ui_cmd:" in completed.stdout
    assert "PhotonTrust local product launcher" in completed.stdout


def test_run_product_pilot_demo_script_dry_run_writes_requests(tmp_path: Path) -> None:
    script = REPO_ROOT / "scripts" / "product" / "run_product_pilot_demo.py"
    assert script.exists(), "Week 4 pilot demo script should exist"

    results_root = tmp_path / "pilot_results"
    label = "dryrun_test"
    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--dry-run",
            "--results-root",
            str(results_root),
            "--label",
            label,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "[dry-run] case=bbm92_metro_50km" in completed.stdout
    assert "[dry-run] case=mdi_intercity_150km" in completed.stdout
    assert "[dry-run] case=tf_backbone_300km" in completed.stdout

    raw_dir = results_root / label / "raw"
    assert (raw_dir / "bbm92_metro_50km.request.json").exists()
    assert (raw_dir / "mdi_intercity_150km.request.json").exists()
    assert (raw_dir / "tf_backbone_300km.request.json").exists()


def test_product_readiness_gate_script_dry_run() -> None:
    script = REPO_ROOT / "scripts" / "product" / "product_readiness_gate.py"
    assert script.exists(), "Product readiness gate script should exist"

    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--dry-run",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "[dry-run] Product readiness gate plan" in completed.stdout
    assert "report_path:" in completed.stdout
