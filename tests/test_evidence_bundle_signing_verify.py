from __future__ import annotations

import io
import json
import zipfile

import pytest


pytest.importorskip("fastapi")
pytest.importorskip("cryptography")

from fastapi.testclient import TestClient  # noqa: E402

from photonstrust.api.server import app  # noqa: E402
from photonstrust.evidence.bundle import sign_bundle_zip, verify_bundle_zip  # noqa: E402
from photonstrust.evidence.signing import write_keypair  # noqa: E402


def _pic_mzi_graph() -> dict:
    return {
        "schema_version": "0.1",
        "graph_id": "sigverify_pic_mzi_bundle",
        "profile": "pic_circuit",
        "metadata": {"title": "sigverify_pic_mzi_bundle", "description": "", "created_at": "2026-02-14"},
        "circuit": {
            "id": "sigverify_pic_mzi_bundle",
            "wavelength_nm": 1550,
            "inputs": [
                {"node": "cpl_in", "port": "in1", "amplitude": 1.0},
                {"node": "cpl_in", "port": "in2", "amplitude": 0.0},
            ],
        },
        "nodes": [
            {"id": "cpl_in", "kind": "pic.coupler", "params": {"coupling_ratio": 0.5, "insertion_loss_db": 0.2}},
            {"id": "ps1", "kind": "pic.phase_shifter", "params": {"phase_rad": 0.0, "insertion_loss_db": 0.1}},
            {"id": "ps2", "kind": "pic.phase_shifter", "params": {"phase_rad": 1.0, "insertion_loss_db": 0.1}},
            {"id": "cpl_out", "kind": "pic.coupler", "params": {"coupling_ratio": 0.5, "insertion_loss_db": 0.2}},
        ],
        "edges": [
            {"from": "cpl_in", "from_port": "out1", "to": "ps1", "to_port": "in", "kind": "optical"},
            {"from": "cpl_in", "from_port": "out2", "to": "ps2", "to_port": "in", "kind": "optical"},
            {"from": "ps1", "from_port": "out", "to": "cpl_out", "to_port": "in1", "kind": "optical"},
            {"from": "ps2", "from_port": "out", "to": "cpl_out", "to_port": "in2", "kind": "optical"},
        ],
    }


def _mutate_zip_entry(src_zip: bytes, *, match_suffix: str, new_bytes: bytes) -> bytes:
    src = zipfile.ZipFile(io.BytesIO(src_zip), "r")
    out_buf = io.BytesIO()
    with zipfile.ZipFile(out_buf, "w") as dst:
        for info in src.infolist():
            data = src.read(info.filename)
            if str(info.filename).replace("\\", "/").endswith(match_suffix):
                data = bytes(new_bytes)
            out_info = zipfile.ZipInfo(info.filename)
            out_info.date_time = info.date_time
            out_info.compress_type = info.compress_type
            dst.writestr(out_info, data)
    return out_buf.getvalue()


def test_bundle_sign_then_verify_and_detect_mutation(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))

    # Keep tests hermetic: do not invoke external KLayout even if installed locally.
    import photonstrust.layout.pic.klayout_runner as klr

    monkeypatch.setattr(klr, "find_klayout_exe", lambda: None)

    client = TestClient(app)
    res = client.post(
        "/v0/pic/workflow/invdesign_chain",
        json={
            "graph": _pic_mzi_graph(),
            "invdesign": {"kind": "mzi_phase"},
            "layout": {"pdk": {"name": "generic_silicon_photonics"}},
        },
    )
    assert res.status_code == 200
    wf_id = str(res.json()["run_id"])

    res = client.get(f"/v0/runs/{wf_id}/bundle")
    assert res.status_code == 200

    in_zip = tmp_path / "bundle.zip"
    in_zip.write_bytes(res.content)

    priv = tmp_path / "k.pem"
    pub = tmp_path / "k.pub.pem"
    write_keypair(private_key_path=priv, public_key_path=pub)

    signed_zip = tmp_path / "bundle.signed.zip"
    sign_bundle_zip(in_zip, private_key_pem_path=priv, output_zip_path=signed_zip, created_at="2026-02-14T00:00:00Z")

    ok = verify_bundle_zip(signed_zip, public_key_pem_path=pub, require_signature=True)
    assert ok.ok
    assert ok.signature_verified
    assert ok.missing_files == 0
    assert ok.mismatched_files == 0
    assert ok.verified_files > 0

    # Mutate README.md (it is included in the manifest file list).
    mutated = _mutate_zip_entry(
        signed_zip.read_bytes(),
        match_suffix="/README.md",
        new_bytes=b"# PhotonTrust Evidence Bundle\n\nMUTATED\n",
    )
    mutated_zip = tmp_path / "bundle.mutated.zip"
    mutated_zip.write_bytes(mutated)

    bad = verify_bundle_zip(mutated_zip, public_key_pem_path=pub, require_signature=True)
    assert not bad.ok
    assert bad.signature_verified  # signature covers manifest, not file bytes
    assert bad.mismatched_files >= 1
    assert any(e.get("code") in ("sha256_mismatch", "size_mismatch") for e in bad.errors)
