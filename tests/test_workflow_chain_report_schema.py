from __future__ import annotations

import pytest


pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from photonstrust.api.server import app  # noqa: E402
from photonstrust.benchmarks.schema import validate_instance  # noqa: E402
from photonstrust.workflow.schema import workflow_invdesign_chain_report_schema_path  # noqa: E402


def _pic_mzi_graph() -> dict:
    return {
        "schema_version": "0.1",
        "graph_id": "schema_pic_mzi_workflow",
        "profile": "pic_circuit",
        "metadata": {"title": "schema_pic_mzi_workflow", "description": "", "created_at": "2026-02-14"},
        "circuit": {
            "id": "schema_pic_mzi_workflow",
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


def test_workflow_chain_report_validates_against_schema(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
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
            "spice": {"settings": {"top_name": "PT_TOP", "subckt_prefix": "PT", "include_stub_subckts": True}},
        },
    )
    assert res.status_code == 200
    payload = res.json()

    schema_path = workflow_invdesign_chain_report_schema_path()
    validate_instance(payload["report"], schema_path)
