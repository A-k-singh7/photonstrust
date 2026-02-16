from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.check_milestone_archive import check_milestone_archive, required_archive_paths
from scripts.run_ga_replay_matrix import run_ga_replay_matrix
from scripts.sign_release_gate_packet import sign_release_gate_packet
from scripts.verify_release_gate_packet import verify_release_gate_packet
from scripts.verify_release_gate_packet_signature import verify_release_gate_packet_signature


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_verify_release_gate_packet_detects_artifact_mismatch(tmp_path: Path) -> None:
    artifact_rel = Path("artifacts/demo.txt")
    artifact_path = tmp_path / artifact_rel
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text("ok\n", encoding="utf-8")
    artifact_sha = hashlib.sha256(artifact_path.read_bytes()).hexdigest()

    packet = {
        "schema_version": "0.1",
        "kind": "photonstrust.release_gate_packet",
        "required_artifact_count": 1,
        "artifact_count": 1,
        "artifacts": [
                {
                    "path": str(artifact_rel).replace("\\", "/"),
                    "sha256": artifact_sha,
                    "bytes": 3,
                }
        ],
        "approvals": {
            "approvers": [
                {"role": "TL", "approved": True},
                {"role": "QA", "approved": True},
                {"role": "DOC", "approved": True},
            ]
        },
    }
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet, indent=2), encoding="utf-8")

    ok, failures, _loaded = verify_release_gate_packet(tmp_path, packet_path=packet_path)
    assert ok
    assert failures == []

    artifact_path.write_text("tampered\n", encoding="utf-8")
    ok2, failures2, _loaded2 = verify_release_gate_packet(tmp_path, packet_path=packet_path)
    assert not ok2
    assert any("artifact hash mismatch" in line for line in failures2)


def test_sign_and_verify_release_gate_packet_signature_roundtrip(tmp_path: Path) -> None:
    pytest.importorskip("cryptography")

    packet_path = tmp_path / "packet.json"
    packet_path.write_text('{"kind": "packet", "value": 1}\n', encoding="utf-8")

    signature_path = tmp_path / "packet.sig.json"
    private_key = tmp_path / "keys" / "private.pem"
    public_key = tmp_path / "keys" / "public.pem"

    sign_ok, _detail = sign_release_gate_packet(
        repo_root=tmp_path,
        packet_path=packet_path,
        signature_path=signature_path,
        private_key_path=private_key,
        public_key_path=public_key,
        generate_keypair=True,
        key_id="unit-test",
    )
    assert sign_ok

    verify_ok, verify_failures = verify_release_gate_packet_signature(
        repo_root=tmp_path,
        packet_path=packet_path,
        signature_path=signature_path,
        public_key_path=None,
    )
    assert verify_ok
    assert verify_failures == []

    packet_path.write_text('{"kind": "packet", "value": 2}\n', encoding="utf-8")
    verify_ok2, verify_failures2 = verify_release_gate_packet_signature(
        repo_root=tmp_path,
        packet_path=packet_path,
        signature_path=signature_path,
        public_key_path=None,
    )
    assert not verify_ok2
    assert any("packet_sha256 mismatch" in line for line in verify_failures2)


def test_check_milestone_archive_requires_expected_files(tmp_path: Path) -> None:
    cycle_date = "2026-02-16"
    for relpath in required_archive_paths(cycle_date):
        path = tmp_path / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == ".json":
            path.write_text("{}\n", encoding="utf-8")
        else:
            path.write_text("ok\n", encoding="utf-8")

    ok, failures = check_milestone_archive(tmp_path, cycle_date=cycle_date)
    assert ok
    assert failures == []

    (tmp_path / required_archive_paths(cycle_date)[0]).unlink()
    ok2, failures2 = check_milestone_archive(tmp_path, cycle_date=cycle_date)
    assert not ok2
    assert any("missing archive artifact" in line for line in failures2)


def test_run_ga_replay_matrix_aggregates_case_results(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import scripts.run_ga_replay_matrix as replay_mod

    def _fake_run_replay_case(**kwargs):
        case_id = str(kwargs.get("case_id"))
        return {
            "case_id": case_id,
            "config_path": "cfg",
            "output_path": "out",
            "returncode": 0,
            "elapsed_seconds": 0.01,
            "run_registry_exists": True,
            "run_registry_rows": 1,
            "ok": case_id != "bad_case",
            "stdout": "",
            "stderr": "",
        }

    monkeypatch.setattr(replay_mod, "run_replay_case", _fake_run_replay_case)

    summary_ok = run_ga_replay_matrix(
        tmp_path,
        timeout_seconds=1.0,
        cases=(("case_a", "cfg_a.yml", "out/a"),),
    )
    assert summary_ok["ok"] is True
    assert summary_ok["case_count"] == 1

    summary_fail = run_ga_replay_matrix(
        tmp_path,
        timeout_seconds=1.0,
        cases=(("bad_case", "cfg_b.yml", "out/b"),),
    )
    assert summary_fail["ok"] is False
