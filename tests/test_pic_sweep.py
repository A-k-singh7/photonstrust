from __future__ import annotations

import pytest

from photonstrust.pic import simulate_pic_netlist_sweep


def test_pic_netlist_sweep_returns_points():
    netlist = {
        "schema_version": "0.1",
        "profile": "pic_circuit",
        "graph_id": "test_pic_sweep",
        "circuit": {"id": "test_pic_sweep", "wavelength_nm": 1550},
        "nodes": [
            {"id": "gc", "kind": "pic.grating_coupler", "params": {"insertion_loss_db": 2.0}},
            {"id": "wg", "kind": "pic.waveguide", "params": {"length_um": 1000, "loss_db_per_cm": 2.0}},
            {"id": "ec", "kind": "pic.edge_coupler", "params": {"insertion_loss_db": 1.0}},
        ],
        "edges": [
            {"from": "gc", "to": "wg", "from_port": "out", "to_port": "in", "kind": "optical"},
            {"from": "wg", "to": "ec", "from_port": "out", "to_port": "in", "kind": "optical"},
        ],
        "topology": {"is_dag": True, "topological_order": ["gc", "wg", "ec"]},
    }

    res = simulate_pic_netlist_sweep(netlist, wavelengths_nm=[1540.0, 1550.0])
    pts = res["sweep"]["points"]
    assert len(pts) == 2
    for p in pts:
        assert p["chain_solver"]["applicable"] is True
        assert p["chain_solver"]["total_loss_db"] == pytest.approx(3.2, abs=1e-6)
        outs = p["dag_solver"]["external_outputs"]
        assert len(outs) == 1
        assert outs[0]["loss_db"] == pytest.approx(3.2, abs=1e-6)

