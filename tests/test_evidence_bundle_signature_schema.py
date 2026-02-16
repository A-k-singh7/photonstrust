from __future__ import annotations

import base64
import io
import json
import zipfile

import pytest


pytest.importorskip("fastapi")
pytest.importorskip("cryptography")

from fastapi.testclient import TestClient  # noqa: E402

from photonstrust.api.server import app  # noqa: E402
from photonstrust.benchmarks.schema import validate_instance  # noqa: E402
from photonstrust.evidence.bundle import sign_bundle_zip  # noqa: E402
from photonstrust.evidence.signing import write_keypair  # noqa: E402
from photonstrust.workflow.schema import evidence_bundle_signature_schema_path  # noqa: E402


def _pic_mzi_graph() -> dict:
    return {
        "schema_version": "0.1",
        "graph_id": "schema_pic_mzi_bundle_sig",
        "profile": "pic_circuit",
        "metadata": {"title": "schema_pic_mzi_bundle_sig", "description": "", "created_at": "2026-02-14"},
        "circuit": {
            "id": "schema_pic_mzi_bundle_sig",
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


def test_evidence_bundle_signature_validates_against_schema(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
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
    wf = res.json()
    wf_id = str(wf["run_id"])

    res = client.get(f"/v0/runs/{wf_id}/bundle")
    assert res.status_code == 200

    in_zip = tmp_path / "bundle.zip"
    in_zip.write_bytes(res.content)

    priv = tmp_path / "bundle_signing_key.pem"
    pub = tmp_path / "bundle_signing_key.pub.pem"
    write_keypair(private_key_path=priv, public_key_path=pub)

    out_zip = tmp_path / "bundle.signed.zip"
    sign_bundle_zip(in_zip, private_key_pem_path=priv, output_zip_path=out_zip, created_at="2026-02-14T00:00:00Z")

    zf = zipfile.ZipFile(io.BytesIO(out_zip.read_bytes()))
    bundle_root = f"photonstrust_evidence_bundle_{wf_id}"
    sig_path = f"{bundle_root}/signatures/bundle_manifest.ed25519.sig.json"
    assert sig_path in set(zf.namelist())
    sig = json.loads(zf.read(sig_path).decode("utf-8"))
    schema_path = evidence_bundle_signature_schema_path()
    validate_instance(sig, schema_path)

    # Quick sanity: signature_b64 is parseable.
    base64.b64decode(str(sig["signature_b64"]).encode("ascii"))
