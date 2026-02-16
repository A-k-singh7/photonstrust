from __future__ import annotations

import io
import json
import zipfile

import pytest


pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from photonstrust.api.server import app  # noqa: E402
from photonstrust.benchmarks.schema import validate_instance  # noqa: E402
from photonstrust.workflow.schema import evidence_bundle_manifest_schema_path  # noqa: E402


def _pic_mzi_graph() -> dict:
    return {
        "schema_version": "0.1",
        "graph_id": "schema_pic_mzi_bundle",
        "profile": "pic_circuit",
        "metadata": {"title": "schema_pic_mzi_bundle", "description": "", "created_at": "2026-02-14"},
        "circuit": {
            "id": "schema_pic_mzi_bundle",
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


def test_evidence_bundle_manifest_validates_against_schema(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
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

    zf = zipfile.ZipFile(io.BytesIO(res.content))
    bundle_root = f"photonstrust_evidence_bundle_{wf_id}"
    bm_path = f"{bundle_root}/bundle_manifest.json"
    assert bm_path in set(zf.namelist())

    bm = json.loads(zf.read(bm_path).decode("utf-8"))
    schema_path = evidence_bundle_manifest_schema_path()
    validate_instance(bm, schema_path)

    sbom = bm.get("sbom") or {}
    assert sbom.get("path") == "sbom/cyclonedx.json"
    assert f"{bundle_root}/sbom/cyclonedx.json" in set(zf.namelist())
