from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_script_module():
    script_path = REPO_ROOT / "scripts" / "build_pic_preflight_policy_packet.py"
    spec = importlib.util.spec_from_file_location("build_pic_preflight_policy_packet_under_test", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_pic_preflight_policy_packet_pass(tmp_path: Path, monkeypatch, capsys) -> None:
    module = _load_script_module()

    artifact_a = tmp_path / "artifact_a.json"
    artifact_b = tmp_path / "artifact_b.json"
    policy_a = tmp_path / "policy_a.md"
    output = tmp_path / "packet.json"

    artifact_a.write_text('{"ok":true}\n', encoding="utf-8")
    artifact_b.write_text('{"ok":true}\n', encoding="utf-8")
    policy_a.write_text("# policy\n", encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "build_pic_preflight_policy_packet.py",
            "--artifact",
            str(artifact_a),
            "--artifact",
            str(artifact_b),
            "--policy-doc",
            str(policy_a),
            "--run-id",
            "rc_test",
            "--output",
            str(output),
        ],
    )

    assert module.main() == 0
    text = capsys.readouterr().out
    assert "PASS" in text
    assert output.exists()

    packet = json.loads(output.read_text(encoding="utf-8"))
    assert packet["kind"] == "photonstrust.pic_preflight_policy_packet"
    assert packet["run_id"] == "rc_test"
    assert packet["artifact_count"] == 2
    assert packet["policy_doc_count"] == 1
    assert isinstance(packet["policy_hash_sha256"], str) and len(packet["policy_hash_sha256"]) == 64
