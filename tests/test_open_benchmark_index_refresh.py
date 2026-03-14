from __future__ import annotations

import json
from pathlib import Path

from photonstrust.benchmarks.open_index import check_open_index_consistency, rebuild_open_index
from scripts.validation.check_open_benchmarks import run_checks


def _seed_open_registry(tmp_path: Path) -> Path:
    repo_root = Path(__file__).resolve().parents[1]
    source_bundle = (
        repo_root / "datasets" / "benchmarks" / "open" / "open_demo_qkd_analytic_001" / "benchmark_bundle.json"
    )
    bundle = json.loads(source_bundle.read_text(encoding="utf-8"))

    open_root = tmp_path / "open"
    bundle_dir = open_root / str(bundle["benchmark_id"])
    bundle_dir.mkdir(parents=True, exist_ok=True)
    (bundle_dir / "benchmark_bundle.json").write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    return open_root


def test_rebuild_open_index_and_consistency_check(tmp_path: Path):
    open_root = _seed_open_registry(tmp_path)
    stale_index = [
        {
            "benchmark_id": "open_demo_qkd_analytic_001",
            "kind": "qkd_sweep",
            "title": "stale",
            "created_at": "1970-01-01T00:00:00+00:00",
            "bundle_path": "open_demo_qkd_analytic_001/benchmark_bundle.json",
            "bundle_hash": "not-a-real-hash",
        }
    ]
    (open_root / "index.json").write_text(json.dumps(stale_index, indent=2), encoding="utf-8")

    ok_before, failures_before = check_open_index_consistency(open_root)
    assert not ok_before
    assert any("does not match" in line for line in failures_before)

    rebuilt = rebuild_open_index(open_root)
    assert rebuilt == rebuild_open_index(open_root)
    assert len(rebuilt) == 1
    assert rebuilt[0]["benchmark_id"] == "open_demo_qkd_analytic_001"
    assert rebuilt[0]["bundle_path"] == "open_demo_qkd_analytic_001/benchmark_bundle.json"
    assert len(rebuilt[0]["bundle_hash"]) == 64

    (open_root / "index.json").write_text(json.dumps(rebuilt, indent=2), encoding="utf-8")
    ok_after, failures_after = check_open_index_consistency(open_root)
    assert ok_after
    assert failures_after == []


def test_check_script_style_logic_catches_index_mismatch(tmp_path: Path):
    open_root = _seed_open_registry(tmp_path)
    (open_root / "index.json").write_text("[]", encoding="utf-8")

    ok_with_index, failures_with_index = run_checks(open_root, check_index=True)
    assert not ok_with_index
    assert any("index:" in line for line in failures_with_index)

    ok_without_index, failures_without_index = run_checks(open_root, check_index=False)
    assert ok_without_index
    assert failures_without_index == []
