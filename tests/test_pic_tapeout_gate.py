from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
_MANDATORY_DRC_RULE_IDS = (
    "DRC.WG.MIN_WIDTH",
    "DRC.WG.MIN_SPACING",
    "DRC.WG.MIN_BEND_RADIUS",
    "DRC.WG.MIN_ENCLOSURE",
)


def _write_payload(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _create_synthetic_run_dir(root: Path) -> Path:
    run_dir = root / "run_pkg"
    inputs = run_dir / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    (inputs / "graph.json").write_text("{}", encoding="utf-8")
    (inputs / "ports.json").write_text("[]", encoding="utf-8")
    (inputs / "routes.json").write_text("[]", encoding="utf-8")
    (inputs / "layout.gds").write_bytes(b"GDSII")
    return run_dir


def _write_valid_waiver(path: Path) -> Path:
    payload = {
        "schema_version": "0",
        "kind": "photonstrust.pic_waivers",
        "waivers": [
            {
                "rule_id": "drc.min_waveguide_gap",
                "entity_ref": "routes:r1:r2",
                "justification": "Approved exception for synthetic fixture",
                "reviewer": "qa.engineer",
                "approved_at": "2026-01-01T00:00:00Z",
                "expires_at": "2027-01-01T00:00:00Z",
                "status": "active",
            }
        ],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _drc_rule_results_from_failed_ids(failed_ids: list[str] | None = None) -> dict:
    failed = set(failed_ids or [])
    return {
        rule_id: {
            "status": "fail" if rule_id in failed else "pass",
            "required_um": None,
            "observed_um": None,
            "violation_count": 1 if rule_id in failed else 0,
            "entity_refs": [],
        }
        for rule_id in _MANDATORY_DRC_RULE_IDS
    }


def _write_foundry_summary(
    path: Path,
    *,
    kind: str,
    status: str,
    backend: str,
    failed_ids: list[str] | None = None,
    drc_rule_results: dict | None = None,
) -> Path:
    failed_ids = list(failed_ids or [])
    payload = {
        "schema_version": "0.1",
        "kind": f"pic.foundry_{kind}_sealed_summary",
        "run_id": f"{kind}_run_001",
        "status": status,
        "execution_backend": backend,
        "started_at": "2026-02-21T00:00:00+00:00",
        "finished_at": "2026-02-21T00:00:10+00:00",
        "check_counts": {
            "total": max(1, len(failed_ids)),
            "passed": 0 if failed_ids else 1,
            "failed": len(failed_ids),
            "errored": 0,
        },
        "failed_check_ids": failed_ids,
        "failed_check_names": [f"name_{x}" for x in failed_ids],
        "deck_fingerprint": "sha256:testdeck",
        "error_code": None,
    }
    if kind == "drc":
        payload["rule_results"] = drc_rule_results if isinstance(drc_rule_results, dict) else _drc_rule_results_from_failed_ids(failed_ids)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def test_pic_tapeout_gate_dry_run() -> None:
    script = REPO_ROOT / "scripts" / "check_pic_tapeout_gate.py"
    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--run-dir",
            "results/does_not_matter",
            "--dry-run",
        ],
        cwd=str(REPO_ROOT),
        check=True,
        capture_output=True,
        text=True,
    )
    assert "[dry-run] PIC tapeout gate plan" in completed.stdout
    assert "required_artifacts:" in completed.stdout


def test_pic_tapeout_gate_synthetic_fixture_passes(tmp_path: Path) -> None:
    script = REPO_ROOT / "scripts" / "check_pic_tapeout_gate.py"
    run_dir = _create_synthetic_run_dir(tmp_path)
    waiver_path = _write_valid_waiver(tmp_path / "waivers.json")
    report_path = tmp_path / "report.json"

    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--run-dir",
            str(run_dir),
            "--waiver-file",
            str(waiver_path),
            "--report-path",
            str(report_path),
        ],
        cwd=str(REPO_ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert report_path.exists()

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["kind"] == "photonstrust.pic_tapeout_gate"
    assert report["all_passed"] is True


def test_pic_tapeout_gate_fails_on_missing_required_artifact(tmp_path: Path) -> None:
    script = REPO_ROOT / "scripts" / "check_pic_tapeout_gate.py"
    run_dir = _create_synthetic_run_dir(tmp_path)
    (run_dir / "inputs" / "layout.gds").unlink()
    report_path = tmp_path / "report_fail.json"

    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--run-dir",
            str(run_dir),
            "--report-path",
            str(report_path),
        ],
        cwd=str(REPO_ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 1
    assert report_path.exists()

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["all_passed"] is False
    names = [str(item.get("name")) for item in report.get("checks", [])]
    assert "required_artifacts" in names


def test_pic_tapeout_gate_foundry_signoff_passes(tmp_path: Path) -> None:
    script = REPO_ROOT / "scripts" / "check_pic_tapeout_gate.py"
    run_dir = _create_synthetic_run_dir(tmp_path)
    _write_foundry_summary(run_dir / "foundry_drc_sealed_summary.json", kind="drc", status="pass", backend="generic_cli")
    _write_foundry_summary(run_dir / "foundry_lvs_sealed_summary.json", kind="lvs", status="pass", backend="generic_cli")
    _write_foundry_summary(run_dir / "foundry_pex_sealed_summary.json", kind="pex", status="pass", backend="generic_cli")

    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--run-dir",
            str(run_dir),
            "--require-foundry-signoff",
            "--require-non-mock-backend",
        ],
        cwd=str(REPO_ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_pic_tapeout_gate_foundry_signoff_fails_without_waiver(tmp_path: Path) -> None:
    script = REPO_ROOT / "scripts" / "check_pic_tapeout_gate.py"
    run_dir = _create_synthetic_run_dir(tmp_path)
    _write_foundry_summary(
        run_dir / "foundry_drc_sealed_summary.json",
        kind="drc",
        status="fail",
        backend="generic_cli",
        failed_ids=["DRC.WG.MIN_SPACING"],
    )
    _write_foundry_summary(run_dir / "foundry_lvs_sealed_summary.json", kind="lvs", status="pass", backend="generic_cli")
    _write_foundry_summary(run_dir / "foundry_pex_sealed_summary.json", kind="pex", status="pass", backend="generic_cli")

    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--run-dir",
            str(run_dir),
            "--require-foundry-signoff",
        ],
        cwd=str(REPO_ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 1


def test_pic_tapeout_gate_foundry_signoff_allows_waived_failures(tmp_path: Path) -> None:
    script = REPO_ROOT / "scripts" / "check_pic_tapeout_gate.py"
    run_dir = _create_synthetic_run_dir(tmp_path)
    _write_foundry_summary(
        run_dir / "foundry_drc_sealed_summary.json",
        kind="drc",
        status="fail",
        backend="generic_cli",
        failed_ids=["DRC.WG.MIN_SPACING"],
    )
    _write_foundry_summary(run_dir / "foundry_lvs_sealed_summary.json", kind="lvs", status="pass", backend="generic_cli")
    _write_foundry_summary(run_dir / "foundry_pex_sealed_summary.json", kind="pex", status="pass", backend="generic_cli")

    waiver_path = _write_payload(
        tmp_path / "waivers_foundry.json",
        {
            "schema_version": "0",
            "kind": "photonstrust.pic_waivers",
            "waivers": [
                {
                    "rule_id": "DRC.WG.MIN_SPACING",
                    "entity_ref": "routes:r1:r2",
                    "justification": "Approved foundry waiver",
                    "reviewer": "qa.engineer",
                    "approved_at": "2026-01-01T00:00:00Z",
                    "expires_at": "2027-01-01T00:00:00Z",
                    "status": "active",
                }
            ],
        },
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--run-dir",
            str(run_dir),
            "--require-foundry-signoff",
            "--require-non-mock-backend",
            "--allow-waived-failures",
            "--waiver-file",
            str(waiver_path),
        ],
        cwd=str(REPO_ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_pic_tapeout_gate_rejects_require_non_mock_without_foundry_signoff(tmp_path: Path) -> None:
    script = REPO_ROOT / "scripts" / "check_pic_tapeout_gate.py"
    run_dir = _create_synthetic_run_dir(tmp_path)

    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--run-dir",
            str(run_dir),
            "--require-non-mock-backend",
        ],
        cwd=str(REPO_ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 2
    assert "--require-non-mock-backend requires --require-foundry-signoff" in completed.stderr


def test_pic_tapeout_gate_rejects_allow_waived_without_waiver_file(tmp_path: Path) -> None:
    script = REPO_ROOT / "scripts" / "check_pic_tapeout_gate.py"
    run_dir = _create_synthetic_run_dir(tmp_path)

    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--run-dir",
            str(run_dir),
            "--require-foundry-signoff",
            "--allow-waived-failures",
        ],
        cwd=str(REPO_ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 2
    assert "--allow-waived-failures requires --waiver-file" in completed.stderr


def test_pic_tapeout_gate_non_mock_enforced_even_with_waivers(tmp_path: Path) -> None:
    script = REPO_ROOT / "scripts" / "check_pic_tapeout_gate.py"
    run_dir = _create_synthetic_run_dir(tmp_path)
    _write_foundry_summary(
        run_dir / "foundry_drc_sealed_summary.json",
        kind="drc",
        status="fail",
        backend="generic_cli",
        failed_ids=["DRC.WG.MIN_SPACING"],
    )
    _write_foundry_summary(
        run_dir / "foundry_lvs_sealed_summary.json",
        kind="lvs",
        status="pass",
        backend="mock",
    )
    _write_foundry_summary(run_dir / "foundry_pex_sealed_summary.json", kind="pex", status="pass", backend="generic_cli")

    waiver_path = _write_payload(
        tmp_path / "waivers_non_mock.json",
        {
            "schema_version": "0",
            "kind": "photonstrust.pic_waivers",
            "waivers": [
                {
                    "rule_id": "DRC.WG.MIN_SPACING",
                    "entity_ref": "routes:r1:r2",
                    "justification": "Approved foundry waiver",
                    "reviewer": "qa.engineer",
                    "approved_at": "2026-01-01T00:00:00Z",
                    "expires_at": "2027-01-01T00:00:00Z",
                    "status": "active",
                }
            ],
        },
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--run-dir",
            str(run_dir),
            "--require-foundry-signoff",
            "--require-non-mock-backend",
            "--allow-waived-failures",
            "--waiver-file",
            str(waiver_path),
        ],
        cwd=str(REPO_ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 1


def test_pic_tapeout_gate_fail_status_requires_failed_check_ids(tmp_path: Path) -> None:
    script = REPO_ROOT / "scripts" / "check_pic_tapeout_gate.py"
    run_dir = _create_synthetic_run_dir(tmp_path)
    _write_foundry_summary(
        run_dir / "foundry_drc_sealed_summary.json",
        kind="drc",
        status="fail",
        backend="generic_cli",
        failed_ids=[],
    )
    _write_foundry_summary(run_dir / "foundry_lvs_sealed_summary.json", kind="lvs", status="pass", backend="generic_cli")
    _write_foundry_summary(run_dir / "foundry_pex_sealed_summary.json", kind="pex", status="pass", backend="generic_cli")

    waiver_path = _write_payload(
        tmp_path / "waivers_empty_fail_ids.json",
        {
            "schema_version": "0",
            "kind": "photonstrust.pic_waivers",
            "waivers": [
                {
                    "rule_id": "DRC.WG.MIN_SPACING",
                    "entity_ref": "routes:r1:r2",
                    "justification": "Approved foundry waiver",
                    "reviewer": "qa.engineer",
                    "approved_at": "2026-01-01T00:00:00Z",
                    "expires_at": "2027-01-01T00:00:00Z",
                    "status": "active",
                }
            ],
        },
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--run-dir",
            str(run_dir),
            "--require-foundry-signoff",
            "--allow-waived-failures",
            "--waiver-file",
            str(waiver_path),
        ],
        cwd=str(REPO_ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 1


def test_pic_tapeout_gate_drc_failed_check_ids_must_match_failed_rule_results(tmp_path: Path) -> None:
    script = REPO_ROOT / "scripts" / "check_pic_tapeout_gate.py"
    run_dir = _create_synthetic_run_dir(tmp_path)
    _write_foundry_summary(
        run_dir / "foundry_drc_sealed_summary.json",
        kind="drc",
        status="fail",
        backend="generic_cli",
        failed_ids=["DRC.WG.MIN_SPACING"],
        drc_rule_results=_drc_rule_results_from_failed_ids(["DRC.WG.MIN_WIDTH"]),
    )
    _write_foundry_summary(run_dir / "foundry_lvs_sealed_summary.json", kind="lvs", status="pass", backend="generic_cli")
    _write_foundry_summary(run_dir / "foundry_pex_sealed_summary.json", kind="pex", status="pass", backend="generic_cli")

    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--run-dir",
            str(run_dir),
            "--require-foundry-signoff",
        ],
        cwd=str(REPO_ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 1


def test_pic_tapeout_gate_drc_missing_rule_results_fails_closed(tmp_path: Path) -> None:
    script = REPO_ROOT / "scripts" / "check_pic_tapeout_gate.py"
    run_dir = _create_synthetic_run_dir(tmp_path)
    drc_path = _write_foundry_summary(
        run_dir / "foundry_drc_sealed_summary.json",
        kind="drc",
        status="pass",
        backend="generic_cli",
    )
    payload = json.loads(drc_path.read_text(encoding="utf-8"))
    payload.pop("rule_results", None)
    drc_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    _write_foundry_summary(run_dir / "foundry_lvs_sealed_summary.json", kind="lvs", status="pass", backend="generic_cli")
    _write_foundry_summary(run_dir / "foundry_pex_sealed_summary.json", kind="pex", status="pass", backend="generic_cli")

    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--run-dir",
            str(run_dir),
            "--require-foundry-signoff",
        ],
        cwd=str(REPO_ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 1
