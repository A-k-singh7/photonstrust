from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_script_module():
    script_path = REPO_ROOT / "scripts" / "init_pic_claim_evidence_matrix.py"
    spec = importlib.util.spec_from_file_location("init_pic_claim_evidence_matrix_under_test", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_init_pic_claim_evidence_matrix_writes_valid_payload(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    module = _load_script_module()
    output = tmp_path / "claim_matrix.json"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "init_pic_claim_evidence_matrix.py",
            "--output",
            str(output),
            "--release-candidate",
            "rc_test",
        ],
    )

    assert module.main() == 0
    printed = json.loads(capsys.readouterr().out.strip())
    assert Path(printed["matrix"]).exists()

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["kind"] == "photonstrust.pic_claim_evidence_matrix"
    assert payload["release_candidate"] == "rc_test"
    claims = payload.get("claims")
    assert isinstance(claims, list) and len(claims) >= 1
    coverage = payload.get("coverage")
    assert isinstance(coverage, dict)
    assert int(coverage["external_claims"]) >= 1
    assert int(coverage["mapped_external_claims"]) >= 1
