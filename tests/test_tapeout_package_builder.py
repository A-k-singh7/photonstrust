from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from photonstrust.pic.signoff import build_pic_signoff_ladder
from photonstrust.pic.tapeout_package import build_tapeout_package


REPO_ROOT = Path(__file__).resolve().parents[1]


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
            "rule_results": {
                "DRC.WG.MIN_WIDTH": {
                    "status": "pass",
                    "required_um": None,
                    "observed_um": None,
                    "violation_count": 0,
                    "entity_refs": [],
                },
                "DRC.WG.MIN_SPACING": {
                    "status": "pass",
                    "required_um": None,
                    "observed_um": None,
                    "violation_count": 0,
                    "entity_refs": [],
                },
                "DRC.WG.MIN_BEND_RADIUS": {
                    "status": "pass",
                    "required_um": None,
                    "observed_um": None,
                    "violation_count": 0,
                    "entity_refs": [],
                },
                "DRC.WG.MIN_ENCLOSURE": {
                    "status": "pass",
                    "required_um": None,
                    "observed_um": None,
                    "violation_count": 0,
                    "entity_refs": [],
                },
            },
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
        run_dir / "foundry_approval_sealed_summary.json",
        {
            "schema_version": "0.1",
            "kind": "pic.foundry_approval_sealed_summary",
            "run_id": "d" * 12,
            "started_at": "2026-03-01T00:00:00+00:00",
            "finished_at": "2026-03-01T00:00:00+00:00",
            "decision": "GO",
            "status": "pass",
            "failed_check_ids": [],
            "failed_check_names": [],
            "source_run_ids": {
                "drc": "a" * 12,
                "lvs": "b" * 12,
                "pex": "c" * 12,
            },
            "deck_fingerprint": "sha256:test",
            "error_code": None,
        },
    )

    drc_summary = json.loads((run_dir / "foundry_drc_sealed_summary.json").read_text(encoding="utf-8"))
    lvs_summary = json.loads((run_dir / "foundry_lvs_sealed_summary.json").read_text(encoding="utf-8"))
    pex_summary = json.loads((run_dir / "foundry_pex_sealed_summary.json").read_text(encoding="utf-8"))
    approval_summary = json.loads((run_dir / "foundry_approval_sealed_summary.json").read_text(encoding="utf-8"))
    signoff_report = build_pic_signoff_ladder(
        {
            "assembly_report": {
                "kind": "pic.chip_assembly",
                "assembly_run_id": "d" * 12,
                "outputs": {
                    "summary": {
                        "status": "pass",
                        "output_hash": "f" * 64,
                    }
                },
                "stitch": {"summary": {"failed_links": 0}},
            },
            "policy": {"multi_stage": True},
            "drc_summary": drc_summary,
            "lvs_summary": lvs_summary,
            "pex_summary": pex_summary,
            "foundry_approval": {
                "decision": approval_summary["decision"],
                "status": approval_summary["status"],
            },
        }
    )["report"]
    _write_json(run_dir / "signoff_ladder.json", signoff_report)
    _write_json(run_dir / "waivers.json", {"schema_version": "0", "kind": "photonstrust.pic_waivers", "waivers": []})
    return run_dir


def _subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{str(REPO_ROOT)}{os.pathsep}{existing}" if existing else str(REPO_ROOT)
    return env


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
    assert (package_dir / "verification" / "foundry_approval_sealed_summary.json").exists()
    assert (package_dir / "signoff" / "signoff_ladder.json").exists()
    assert (package_dir / "signoff" / "waivers.json").exists()
    assert (package_dir / "README.md").exists()
    assert (package_dir / "MANIFEST.sha256").exists()
    assert (package_dir / "tapeout_package_manifest.json").exists()

    manifest_lines = (package_dir / "MANIFEST.sha256").read_text(encoding="utf-8").strip().splitlines()
    assert any("inputs/graph.json" in line for line in manifest_lines)
    assert any("verification/foundry_drc_sealed_summary.json" in line for line in manifest_lines)
    assert any("verification/foundry_approval_sealed_summary.json" in line for line in manifest_lines)
    assert any("signoff/signoff_ladder.json" in line for line in manifest_lines)


def test_build_tapeout_package_fails_when_required_input_missing(tmp_path: Path) -> None:
    run_dir = _make_source_run(tmp_path)
    (run_dir / "inputs" / "layout.gds").unlink()

    with pytest.raises(FileNotFoundError):
        build_tapeout_package({"run_dir": str(run_dir), "output_root": str(tmp_path / "out")})


@pytest.mark.parametrize(
    "malicious_run_id",
    [
        "../../../outside_target",
        r"..\..\outside_target",
        "abc/def",
        "abc\\def",
        "abc..def",
        "A123",
        "-abc",
        "a" * 65,
    ],
)
def test_build_tapeout_package_rejects_malicious_run_id(tmp_path: Path, malicious_run_id: str) -> None:
    run_dir = _make_source_run(tmp_path)
    output_root = tmp_path / "tapeout_out"

    with pytest.raises(ValueError, match="run_id"):
        build_tapeout_package({"run_dir": str(run_dir), "output_root": str(output_root), "run_id": malicious_run_id})


def test_build_tapeout_package_rejects_escape_run_id_without_deleting_external_marker(tmp_path: Path) -> None:
    run_dir = _make_source_run(tmp_path)
    output_root = tmp_path / "tapeout_out"
    output_root.mkdir(parents=True, exist_ok=True)

    external_dir = tmp_path / "outside_target"
    external_dir.mkdir(parents=True, exist_ok=True)
    marker = external_dir / "marker.txt"
    marker.write_text("do-not-delete", encoding="utf-8")

    with pytest.raises(ValueError, match="run_id"):
        build_tapeout_package(
            {
                "run_dir": str(run_dir),
                "output_root": str(output_root),
                "run_id": "../../../outside_target",
            }
        )

    assert external_dir.exists()
    assert marker.exists()
    assert marker.read_text(encoding="utf-8") == "do-not-delete"


def test_build_tapeout_package_accepts_64_char_run_id(tmp_path: Path) -> None:
    run_dir = _make_source_run(tmp_path)
    output_root = tmp_path / "tapeout_out"
    run_id = "a" + ("b" * 63)

    report = build_tapeout_package({"run_dir": str(run_dir), "output_root": str(output_root), "run_id": run_id})

    assert report["run_id"] == run_id
    assert Path(report["package_dir"]).name == f"tapeout_{run_id}"


def test_build_tapeout_package_allow_missing_signoff_generates_placeholder(tmp_path: Path) -> None:
    run_dir = _make_source_run(tmp_path)
    (run_dir / "signoff_ladder.json").unlink()

    report = build_tapeout_package(
        {
            "run_dir": str(run_dir),
            "output_root": str(tmp_path / "out"),
            "allow_missing_signoff": True,
        }
    )
    package_dir = Path(report["package_dir"])
    payload = json.loads((package_dir / "signoff" / "signoff_ladder.json").read_text(encoding="utf-8"))

    assert payload["kind"] == "pic.signoff_ladder"
    assert payload["final_decision"]["decision"] == "HOLD"
    assert any(str(row.get("status", "")).lower() in {"fail", "hold", "error", "skipped"} for row in payload["ladder"])


def test_build_tapeout_package_allow_missing_signoff_rejects_missing_explicit_override(tmp_path: Path) -> None:
    run_dir = _make_source_run(tmp_path)
    (run_dir / "signoff_ladder.json").unlink()

    with pytest.raises(FileNotFoundError, match="explicit signoff_ladder_path"):
        build_tapeout_package(
            {
                "run_dir": str(run_dir),
                "output_root": str(tmp_path / "out"),
                "allow_missing_signoff": True,
                "signoff_ladder_path": "does_not_exist.json",
            }
        )


def test_build_tapeout_package_allow_stub_pex_required_when_source_missing(tmp_path: Path) -> None:
    run_dir = _make_source_run(tmp_path)
    (run_dir / "foundry_pex_sealed_summary.json").unlink()

    with pytest.raises(FileNotFoundError, match="required verification artifact missing"):
        build_tapeout_package({"run_dir": str(run_dir), "output_root": str(tmp_path / "out")})


def test_build_tapeout_package_allow_stub_pex_writes_valid_stub(tmp_path: Path) -> None:
    run_dir = _make_source_run(tmp_path)
    (run_dir / "foundry_pex_sealed_summary.json").unlink()

    report = build_tapeout_package(
        {
            "run_dir": str(run_dir),
            "output_root": str(tmp_path / "out"),
            "allow_stub_pex": True,
        }
    )
    package_dir = Path(report["package_dir"])
    stub = json.loads((package_dir / "verification" / "foundry_pex_sealed_summary.json").read_text(encoding="utf-8"))

    assert stub["kind"] == "pic.foundry_pex_sealed_summary"
    assert stub["status"] == "error"
    assert stub["execution_backend"] == "mock"
    assert stub["error_code"] == "missing_source_artifact"


def test_build_tapeout_package_requires_foundry_approval_by_default(tmp_path: Path) -> None:
    run_dir = _make_source_run(tmp_path)
    (run_dir / "foundry_approval_sealed_summary.json").unlink()

    with pytest.raises(FileNotFoundError, match="required verification artifact missing"):
        build_tapeout_package({"run_dir": str(run_dir), "output_root": str(tmp_path / "out")})


def test_build_tapeout_package_can_skip_foundry_approval_when_not_required(tmp_path: Path) -> None:
    run_dir = _make_source_run(tmp_path)
    (run_dir / "foundry_approval_sealed_summary.json").unlink()

    report = build_tapeout_package(
        {
            "run_dir": str(run_dir),
            "output_root": str(tmp_path / "out"),
            "require_foundry_approval": False,
        }
    )
    package_dir = Path(report["package_dir"])

    assert not (package_dir / "verification" / "foundry_approval_sealed_summary.json").exists()


def test_build_tapeout_package_rejects_incoherent_foundry_approval_content(tmp_path: Path) -> None:
    run_dir = _make_source_run(tmp_path)
    approval_summary_path = run_dir / "foundry_approval_sealed_summary.json"
    approval_summary = json.loads(approval_summary_path.read_text(encoding="utf-8"))
    approval_summary["decision"] = "GO"
    approval_summary["status"] = "fail"
    approval_summary["failed_check_ids"] = ["FOUNDRY_APPROVAL.HOLD.001"]
    approval_summary["failed_check_names"] = ["fixture hold mismatch"]
    _write_json(approval_summary_path, approval_summary)

    with pytest.raises(ValueError, match="decision=GO"):
        build_tapeout_package({"run_dir": str(run_dir), "output_root": str(tmp_path / "out")})


def test_build_tapeout_package_supports_absolute_override_paths(tmp_path: Path) -> None:
    run_dir = _make_source_run(tmp_path)
    overrides_dir = tmp_path / "overrides"
    overrides_dir.mkdir(parents=True, exist_ok=True)

    signoff_override = overrides_dir / "signoff_override.json"
    waivers_override = overrides_dir / "waivers_override.json"
    signoff_payload = json.loads((run_dir / "signoff_ladder.json").read_text(encoding="utf-8"))
    waivers_payload = {
        "schema_version": "0",
        "kind": "photonstrust.pic_waivers",
        "waivers": [],
    }
    _write_json(signoff_override, signoff_payload)
    _write_json(waivers_override, waivers_payload)

    report = build_tapeout_package(
        {
            "run_dir": str(run_dir),
            "output_root": str(tmp_path / "out"),
            "signoff_ladder_path": str(signoff_override),
            "waivers_path": str(waivers_override),
        }
    )
    package_dir = Path(report["package_dir"])

    assert json.loads((package_dir / "signoff" / "signoff_ladder.json").read_text(encoding="utf-8")) == signoff_payload
    assert json.loads((package_dir / "signoff" / "waivers.json").read_text(encoding="utf-8")) == waivers_payload


def test_build_tapeout_package_resolves_relative_overrides_from_repo_root(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo_root"
    repo_root.mkdir(parents=True, exist_ok=True)
    run_dir = _make_source_run(repo_root)

    overrides_dir = repo_root / "custom_overrides"
    signoff_override = overrides_dir / "signoff_rel.json"
    waivers_override = overrides_dir / "waivers_rel.json"
    signoff_payload = json.loads((run_dir / "signoff_ladder.json").read_text(encoding="utf-8"))
    waivers_payload = {"schema_version": "0", "kind": "photonstrust.pic_waivers", "waivers": []}
    _write_json(signoff_override, signoff_payload)
    _write_json(waivers_override, waivers_payload)

    report = build_tapeout_package(
        {
            "run_dir": "run_pkg",
            "output_root": "out",
            "signoff_ladder_path": "custom_overrides/signoff_rel.json",
            "waivers_path": "custom_overrides/waivers_rel.json",
        },
        repo_root=repo_root,
    )
    package_dir = Path(report["package_dir"])

    assert json.loads((package_dir / "signoff" / "signoff_ladder.json").read_text(encoding="utf-8")) == signoff_payload
    assert json.loads((package_dir / "signoff" / "waivers.json").read_text(encoding="utf-8")) == waivers_payload


def test_build_tapeout_package_rejects_incoherent_verification_content(tmp_path: Path) -> None:
    run_dir = _make_source_run(tmp_path)
    drc_summary_path = run_dir / "foundry_drc_sealed_summary.json"
    drc_summary = json.loads(drc_summary_path.read_text(encoding="utf-8"))
    drc_summary["status"] = "pass"
    drc_summary["check_counts"]["passed"] = 0
    drc_summary["check_counts"]["failed"] = 1
    drc_summary["failed_check_ids"] = ["DRC.FAIL.001"]
    drc_summary["failed_check_names"] = ["drc failed fixture"]
    _write_json(drc_summary_path, drc_summary)

    with pytest.raises(ValueError, match="status=pass"):
        build_tapeout_package({"run_dir": str(run_dir), "output_root": str(tmp_path / "out")})


def test_build_tapeout_package_rejects_invalid_waiver_content(tmp_path: Path) -> None:
    run_dir = _make_source_run(tmp_path)
    _write_json(
        run_dir / "waivers.json",
        {
            "schema_version": "0",
            "kind": "photonstrust.pic_waivers",
            "waivers": [
                {
                    "rule_id": "DRC.MIN_GAP",
                    "entity_ref": "routes:r1:r2",
                    "justification": "expired waiver fixture",
                    "reviewer": "qa.engineer",
                    "approved_at": "2024-01-01T00:00:00Z",
                    "expires_at": "2024-12-31T00:00:00Z",
                    "status": "active",
                }
            ],
        },
    )

    with pytest.raises(ValueError, match="waivers artifact failed validation"):
        build_tapeout_package({"run_dir": str(run_dir), "output_root": str(tmp_path / "out")})


def test_build_tapeout_package_cli_resolves_paths_from_invocation_cwd(tmp_path: Path) -> None:
    workspace = tmp_path / "cli_workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    run_dir = _make_source_run(workspace)

    overrides_dir = workspace / "overrides"
    signoff_override = overrides_dir / "signoff_rel.json"
    waivers_override = overrides_dir / "waivers_rel.json"
    _write_json(signoff_override, json.loads((run_dir / "signoff_ladder.json").read_text(encoding="utf-8")))
    _write_json(waivers_override, {"schema_version": "0", "kind": "photonstrust.pic_waivers", "waivers": []})
    (run_dir / "signoff_ladder.json").unlink()
    (run_dir / "waivers.json").unlink()

    script = REPO_ROOT / "scripts" / "build_tapeout_package.py"
    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--run-dir",
            "run_pkg",
            "--run-id",
            "cliwrap0001",
            "--output-root",
            "pkg_out",
            "--signoff-ladder-path",
            "overrides/signoff_rel.json",
            "--waivers-path",
            "overrides/waivers_rel.json",
            "--report-path",
            "reports/tapeout_package_report.json",
        ],
        cwd=str(workspace),
        env=_subprocess_env(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    report_path = workspace / "reports" / "tapeout_package_report.json"
    assert report_path.exists()

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert Path(report["package_dir"]).exists()
    assert Path(report["package_dir"]).parent == (workspace / "pkg_out").resolve()
