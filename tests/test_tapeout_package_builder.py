from __future__ import annotations

import json
from pathlib import Path

import pytest

from photonstrust.pic.tapeout_package import build_tapeout_package


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _make_source_run(tmp_path: Path) -> Path:
    run_dir = tmp_path / "run_pkg"
    inputs = run_dir / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    (inputs / "graph.json").write_text("{}", encoding="utf-8")
    (inputs / "ports.json").write_text("[]", encoding="utf-8")
    (inputs / "routes.json").write_text("[]", encoding="utf-8")
    (inputs / "layout.gds").write_bytes(b"GDSII")

    _write_json(
        run_dir / "foundry_drc_sealed_summary.json",
        {
            "schema_version": "0.1",
            "kind": "pic.foundry_drc_sealed_summary",
            "run_id": "a" * 12,
            "status": "pass",
            "execution_backend": "generic_cli",
            "started_at": "2026-03-01T00:00:00+00:00",
            "finished_at": "2026-03-01T00:00:00+00:00",
            "check_counts": {"total": 1, "passed": 1, "failed": 0, "errored": 0},
            "failed_check_ids": [],
            "failed_check_names": [],
            "deck_fingerprint": "sha256:test",
            "error_code": None,
        },
    )
    _write_json(
        run_dir / "foundry_lvs_sealed_summary.json",
        {
            "schema_version": "0.1",
            "kind": "pic.foundry_lvs_sealed_summary",
            "run_id": "b" * 12,
            "status": "pass",
            "execution_backend": "generic_cli",
            "started_at": "2026-03-01T00:00:00+00:00",
            "finished_at": "2026-03-01T00:00:00+00:00",
            "check_counts": {"total": 1, "passed": 1, "failed": 0, "errored": 0},
            "failed_check_ids": [],
            "failed_check_names": [],
            "deck_fingerprint": "sha256:test",
            "error_code": None,
        },
    )
    _write_json(
        run_dir / "foundry_pex_sealed_summary.json",
        {
            "schema_version": "0.1",
            "kind": "pic.foundry_pex_sealed_summary",
            "run_id": "c" * 12,
            "status": "pass",
            "execution_backend": "generic_cli",
            "started_at": "2026-03-01T00:00:00+00:00",
            "finished_at": "2026-03-01T00:00:00+00:00",
            "check_counts": {"total": 1, "passed": 1, "failed": 0, "errored": 0},
            "failed_check_ids": [],
            "failed_check_names": [],
            "deck_fingerprint": "sha256:test",
            "error_code": None,
        },
    )

    _write_json(
        run_dir / "signoff_ladder.json",
        {
            "schema_version": "0.1",
            "generated_at": "2026-03-01T00:00:00+00:00",
            "kind": "pic.signoff_ladder",
            "run_id": "d" * 12,
            "inputs": {
                "chip_assembly_run_id": "e" * 12,
                "chip_assembly_hash": "f" * 64,
                "policy_hash": "1" * 64,
            },
            "ladder": [{"level": 1, "stage": "chip_assembly", "status": "pass"}],
            "final_decision": {"decision": "GO", "reasons": ["ok"]},
            "provenance": {"photonstrust_version": "test", "python": "3.12", "platform": "test"},
        },
    )
    _write_json(run_dir / "waivers.json", {"schema_version": "0", "kind": "photonstrust.pic_waivers", "waivers": []})
    return run_dir


def test_build_tapeout_package_creates_expected_structure(tmp_path: Path) -> None:
    run_dir = _make_source_run(tmp_path)
    output_root = tmp_path / "tapeout_out"

    report = build_tapeout_package({"run_dir": str(run_dir), "output_root": str(output_root)})
    package_dir = Path(report["package_dir"])

    assert (package_dir / "inputs" / "graph.json").exists()
    assert (package_dir / "inputs" / "ports.json").exists()
    assert (package_dir / "inputs" / "routes.json").exists()
    assert (package_dir / "inputs" / "layout.gds").exists()
    assert (package_dir / "verification" / "foundry_drc_sealed_summary.json").exists()
    assert (package_dir / "verification" / "foundry_lvs_sealed_summary.json").exists()
    assert (package_dir / "verification" / "foundry_pex_sealed_summary.json").exists()
    assert (package_dir / "signoff" / "signoff_ladder.json").exists()
    assert (package_dir / "signoff" / "waivers.json").exists()
    assert (package_dir / "README.md").exists()
    assert (package_dir / "MANIFEST.sha256").exists()
    assert (package_dir / "tapeout_package_manifest.json").exists()

    manifest_lines = (package_dir / "MANIFEST.sha256").read_text(encoding="utf-8").strip().splitlines()
    assert any("inputs/graph.json" in line for line in manifest_lines)
    assert any("verification/foundry_drc_sealed_summary.json" in line for line in manifest_lines)
    assert any("signoff/signoff_ladder.json" in line for line in manifest_lines)


def test_build_tapeout_package_fails_when_required_input_missing(tmp_path: Path) -> None:
    run_dir = _make_source_run(tmp_path)
    (run_dir / "inputs" / "layout.gds").unlink()

    with pytest.raises(FileNotFoundError):
        build_tapeout_package({"run_dir": str(run_dir), "output_root": str(tmp_path / "out")})

