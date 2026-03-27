from __future__ import annotations

from pathlib import Path

import pytest

from photonstrust.pic.simulate import simulate_pic_netlist


def test_pic_touchstone_2port_import_sets_forward_transmission():
    ts_path = Path(__file__).parent / "fixtures" / "touchstone_demo.s2p"
    assert ts_path.exists()

    netlist = {
        "schema_version": "0.1",
        "profile": "pic_circuit",
        "graph_id": "test_pic_touchstone",
        "circuit": {"id": "test_pic_touchstone", "wavelength_nm": 1550},
        "nodes": [
            {"id": "ts", "kind": "pic.touchstone_2port", "params": {"touchstone_path": str(ts_path)}},
        ],
        "edges": [],
        "topology": {"is_dag": True, "topological_order": ["ts"]},
    }

    results = simulate_pic_netlist(netlist)
    outs = results["dag_solver"]["external_outputs"]
    assert len(outs) == 1
    assert outs[0]["node"] == "ts"
    assert outs[0]["port"] == "out"
    # Fixture encodes S21 amplitude 0.5 => power 0.25.
    assert outs[0]["power"] == pytest.approx(0.25, abs=1e-12)


def test_pic_touchstone_nport_import_sets_forward_transmission_for_4port():
    ts_path = Path(__file__).parent / "fixtures" / "touchstone_demo_4port.s4p"
    assert ts_path.exists()

    # Default split for n_ports=4 is in_ports=[p1,p2], out_ports=[p3,p4].
    netlist = {
        "schema_version": "0.1",
        "profile": "pic_circuit",
        "graph_id": "test_pic_touchstone_4port",
        "circuit": {
            "id": "test_pic_touchstone_4port",
            "wavelength_nm": 1550,
            "inputs": [{"node": "ts", "port": "p1", "amplitude": 1.0}],
        },
        "nodes": [
            {
                "id": "ts",
                "kind": "pic.touchstone_nport",
                "params": {"touchstone_path": str(ts_path), "n_ports": 4},
            },
        ],
        "edges": [],
        "topology": {"is_dag": True, "topological_order": ["ts"]},
    }

    results = simulate_pic_netlist(netlist)
    outs = {f"{o['node']}.{o['port']}": o for o in results["dag_solver"]["external_outputs"]}
    assert outs["ts.p3"]["power"] == pytest.approx(0.25, abs=1e-12)
    assert outs["ts.p4"]["power"] == pytest.approx(0.0, abs=1e-12)

    # Also verify scattering mode agrees.
    netlist_sc = {**netlist, "circuit": {**netlist["circuit"], "solver": "scattering"}}
    results2 = simulate_pic_netlist(netlist_sc)
    sc = results2["scattering_solver"]
    assert sc["applicable"] is True
    outs2 = {f"{o['node']}.{o['port']}": o for o in sc["external_outputs"]}
    assert outs2["ts.p3"]["power"] == pytest.approx(0.25, abs=1e-12)
    assert outs2["ts.p4"]["power"] == pytest.approx(0.0, abs=1e-12)


def test_pic_touchstone_2port_requires_wavelength_nm():
    ts_path = Path(__file__).parent / "fixtures" / "touchstone_demo.s2p"
    netlist = {
        "schema_version": "0.1",
        "profile": "pic_circuit",
        "graph_id": "test_pic_touchstone_missing_wavelength",
        "circuit": {"id": "test_pic_touchstone_missing_wavelength"},
        "nodes": [
            {"id": "ts", "kind": "pic.touchstone_2port", "params": {"touchstone_path": str(ts_path)}},
        ],
        "edges": [],
    }

    with pytest.raises(ValueError, match="wavelength_nm"):
        simulate_pic_netlist(netlist)


def test_pic_touchstone_nport_requires_wavelength_nm():
    ts_path = Path(__file__).parent / "fixtures" / "touchstone_demo_4port.s4p"
    netlist = {
        "schema_version": "0.1",
        "profile": "pic_circuit",
        "graph_id": "test_pic_touchstone_nport_missing_wavelength",
        "circuit": {
            "id": "test_pic_touchstone_nport_missing_wavelength",
            "inputs": [{"node": "ts", "port": "p1", "amplitude": 1.0}],
        },
        "nodes": [
            {"id": "ts", "kind": "pic.touchstone_nport", "params": {"touchstone_path": str(ts_path), "n_ports": 4}},
        ],
        "edges": [],
    }

    with pytest.raises(ValueError, match="wavelength_nm"):
        simulate_pic_netlist(netlist)


def test_pic_touchstone_2port_accepts_relative_path_with_touchstone_root(tmp_path, monkeypatch):
    source_path = Path(__file__).parent / "fixtures" / "touchstone_demo.s2p"
    monkeypatch.chdir(tmp_path)
    touchstone_root = tmp_path / "models"
    touchstone_root.mkdir()
    touchstone_path = touchstone_root / source_path.name
    touchstone_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")

    netlist = {
        "schema_version": "0.1",
        "profile": "pic_circuit",
        "graph_id": "test_pic_touchstone_root",
        "circuit": {"id": "test_pic_touchstone_root", "wavelength_nm": 1550},
        "nodes": [
            {
                "id": "ts",
                "kind": "pic.touchstone_2port",
                "params": {"touchstone_root": "models", "touchstone_path": source_path.name},
            },
        ],
        "edges": [],
        "topology": {"is_dag": True, "topological_order": ["ts"]},
    }

    results = simulate_pic_netlist(netlist)
    outs = results["dag_solver"]["external_outputs"]
    assert len(outs) == 1
    assert outs[0]["power"] == pytest.approx(0.25, abs=1e-12)


def test_pic_touchstone_2port_rejects_absolute_path_outside_working_tree(tmp_path, monkeypatch):
    source_path = Path(__file__).parent / "fixtures" / "touchstone_demo.s2p"
    monkeypatch.chdir(Path(__file__).parent)
    external_path = tmp_path / "external-touchstone.s2p"
    external_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")

    netlist = {
        "schema_version": "0.1",
        "profile": "pic_circuit",
        "graph_id": "test_pic_touchstone_outside_root",
        "circuit": {"id": "test_pic_touchstone_outside_root", "wavelength_nm": 1550},
        "nodes": [
            {"id": "ts", "kind": "pic.touchstone_2port", "params": {"touchstone_path": str(external_path)}},
        ],
        "edges": [],
        "topology": {"is_dag": True, "topological_order": ["ts"]},
    }

    with pytest.raises(ValueError, match="touchstone_path must resolve within"):
        simulate_pic_netlist(netlist)
