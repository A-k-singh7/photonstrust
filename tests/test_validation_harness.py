from __future__ import annotations

import json
from pathlib import Path

from photonstrust.benchmarks.validation_harness import ValidationCase, default_cases, run_validation_harness


def test_validation_harness_writes_artifacts_and_passes_for_demo_baseline(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    case = ValidationCase(
        case_id="demo_regression",
        config_path=root / "configs" / "quickstart" / "qkd_default.yml",
        baseline_path=root / "tests" / "fixtures" / "baselines.json",
    )

    summary = run_validation_harness(repo_root=root, output_root=tmp_path, cases=[case])

    assert summary["ok"] is True
    assert summary["case_count"] == 1

    run_dir = Path(summary["artifacts"]["run_dir"])
    assert run_dir.exists()
    assert (run_dir / "summary.json").exists()
    assert (run_dir / "manifest.json").exists()

    case_dir = run_dir / "cases" / "demo_regression"
    assert (case_dir / "observed.json").exists()
    assert (case_dir / "comparison.json").exists()

    comparison = json.loads((case_dir / "comparison.json").read_text(encoding="utf-8"))
    assert comparison["ok"] is True
    assert comparison["failures"] == []


def test_validation_harness_default_cases_include_phase54_when_fixture_present() -> None:
    root = Path(__file__).resolve().parents[1]
    fixture = root / "tests" / "fixtures" / "canonical_phase54_satellite_baselines.json"
    if not fixture.exists():
        return

    cases = default_cases(root)
    case_ids = {c.case_id for c in cases}
    assert any(cid.startswith("phase54::") for cid in case_ids)
