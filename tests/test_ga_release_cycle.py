from __future__ import annotations

import json
from pathlib import Path

from scripts.release.build_release_gate_packet import build_release_gate_packet
from scripts.check_external_reviewer_findings import evaluate_external_reviewer_report
from scripts.lock_rc_baseline import build_rc_baseline_lock
from scripts.publish_ga_release_bundle import build_ga_release_bundle_manifest
from scripts.verify_ga_release_bundle import verify_ga_bundle_manifest


def test_build_rc_baseline_lock_manifest_is_deterministic(tmp_path: Path) -> None:
    fixture_a = tmp_path / "fixtures" / "a.json"
    fixture_b = tmp_path / "fixtures" / "b.json"
    fixture_a.parent.mkdir(parents=True, exist_ok=True)
    fixture_a.write_text('{"value": 1}\n', encoding="utf-8")
    fixture_b.write_text('{"value": 2}\n', encoding="utf-8")

    payload = build_rc_baseline_lock(
        tmp_path,
        fixture_relpaths=("fixtures/b.json", "fixtures/a.json"),
        generated_at="2026-02-16T00:00:00+00:00",
    )

    assert payload["kind"] == "photonstrust.rc_baseline_lock"
    assert [row["path"] for row in payload["fixtures"]] == ["fixtures/a.json", "fixtures/b.json"]
    assert len(str(payload["fixture_set_sha256"])) == 64


def test_external_reviewer_report_fails_on_unresolved_critical() -> None:
    passing_report = {
        "go_recommendation": "conditional_go",
        "findings": [
            {"id": "ER-1", "severity": "critical", "status": "resolved"},
            {"id": "ER-2", "severity": "major", "status": "in_progress"},
        ],
    }
    passing_ok, passing_failures = evaluate_external_reviewer_report(passing_report)
    assert passing_ok
    assert passing_failures == []

    failing_report = {
        "go_recommendation": "conditional_go",
        "findings": [
            {"id": "ER-3", "severity": "critical", "status": "open"},
        ],
    }
    failing_ok, failing_failures = evaluate_external_reviewer_report(failing_report)
    assert not failing_ok
    assert any("critical finding unresolved" in line for line in failing_failures)


def test_build_release_gate_packet_requires_role_approvals(tmp_path: Path) -> None:
    required_files = [
        "artifact_a.txt",
        "artifact_b.txt",
    ]
    for relpath in required_files:
        path = tmp_path / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(relpath, encoding="utf-8")

    approvals_relpath = "approvals.json"
    approvals_path = tmp_path / approvals_relpath
    approvals_path.write_text(
        json.dumps(
            {
                "approvers": [
                    {"role": "TL", "approved": True},
                    {"role": "QA", "approved": True},
                    {"role": "DOC", "approved": True},
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    packet, failures = build_release_gate_packet(
        tmp_path,
        required_artifacts=required_files,
        approvals_relpath=approvals_relpath,
        generated_at="2026-02-16T00:00:00+00:00",
    )
    assert failures == []
    assert packet["artifact_count"] == 2
    assert len(str(packet["artifact_set_sha256"])) == 64

    approvals_path.write_text(
        json.dumps({"approvers": [{"role": "TL", "approved": True}]}, indent=2),
        encoding="utf-8",
    )
    _packet2, failures2 = build_release_gate_packet(
        tmp_path,
        required_artifacts=required_files,
        approvals_relpath=approvals_relpath,
        generated_at="2026-02-16T00:00:00+00:00",
    )
    assert any("missing required approver role" in line for line in failures2)


def test_ga_bundle_manifest_verify_detects_tamper(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir(parents=True, exist_ok=True)
    (bundle_root / "run_registry.json").write_text("[]\n", encoding="utf-8")
    card_path = bundle_root / "demo1" / "nir_850" / "reliability_card.json"
    card_path.parent.mkdir(parents=True, exist_ok=True)
    card_path.write_text('{"scenario_id": "demo1"}\n', encoding="utf-8")

    manifest = build_ga_release_bundle_manifest(
        tmp_path,
        bundle_root=Path("bundle"),
        generated_at="2026-02-16T00:00:00+00:00",
    )
    manifest_path = tmp_path / "ga_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    ok, failures, _loaded = verify_ga_bundle_manifest(tmp_path, manifest_path=manifest_path)
    assert ok
    assert failures == []

    card_path.write_text('{"scenario_id": "demo1", "tampered": true}\n', encoding="utf-8")
    ok2, failures2, _loaded2 = verify_ga_bundle_manifest(tmp_path, manifest_path=manifest_path)
    assert not ok2
    assert any("hash mismatch" in line for line in failures2)
