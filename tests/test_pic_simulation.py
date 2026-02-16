from __future__ import annotations

import math
from pathlib import Path

from photonstrust.pic.simulate import simulate_pic_netlist


def test_pic_chain_solver_total_loss_db():
    netlist = {
        "schema_version": "0.1",
        "profile": "pic_circuit",
        "graph_id": "test_pic_chain",
        "circuit": {"id": "test_pic_chain", "wavelength_nm": 1550},
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

    results = simulate_pic_netlist(netlist)
    chain = results["chain_solver"]
    assert chain["applicable"] is True
    assert chain["node_order"] == ["gc", "wg", "ec"]
    assert chain["total_loss_db"] == pytest_approx(3.2, abs_tol=1e-6)

    dag = results["dag_solver"]
    # Single output: ec.out
    outs = dag["external_outputs"]
    assert len(outs) == 1
    assert outs[0]["node"] == "ec"
    assert outs[0]["port"] == "out"
    assert outs[0]["loss_db"] == pytest_approx(3.2, abs_tol=1e-6)


def test_pic_mzi_interference_routes_power():
    # 50/50 couplers with phase difference should route power between output ports.
    base = {
        "schema_version": "0.1",
        "profile": "pic_circuit",
        "graph_id": "test_pic_mzi",
        "circuit": {
            "id": "test_pic_mzi",
            "wavelength_nm": 1550,
            "inputs": [{"node": "cpl_in", "port": "in1", "amplitude": 1.0}],
        },
        "nodes": [
            {"id": "cpl_in", "kind": "pic.coupler", "params": {"coupling_ratio": 0.5}},
            {"id": "ps1", "kind": "pic.phase_shifter", "params": {"phase_rad": 0.0}},
            {"id": "ps2", "kind": "pic.phase_shifter", "params": {"phase_rad": 0.0}},
            {"id": "cpl_out", "kind": "pic.coupler", "params": {"coupling_ratio": 0.5}},
        ],
        "edges": [
            {"from": "cpl_in", "from_port": "out1", "to": "ps1", "to_port": "in"},
            {"from": "cpl_in", "from_port": "out2", "to": "ps2", "to_port": "in"},
            {"from": "ps1", "from_port": "out", "to": "cpl_out", "to_port": "in1"},
            {"from": "ps2", "from_port": "out", "to": "cpl_out", "to_port": "in2"},
        ],
        "topology": {"is_dag": True, "topological_order": ["cpl_in", "ps1", "ps2", "cpl_out"]},
    }

    same_phase = simulate_pic_netlist(base)
    outs = {f"{o['node']}.{o['port']}": o for o in same_phase["dag_solver"]["external_outputs"]}
    # With our coupler convention, equal phases route to cpl_out.out2.
    assert outs["cpl_out.out2"]["power"] == pytest_approx(1.0, abs_tol=1e-12)
    assert outs["cpl_out.out1"]["power"] == pytest_approx(0.0, abs_tol=1e-12)

    # Add pi phase difference on arm 2 -> swap to out1.
    shifted = dict(base)
    shifted = {**base, "nodes": [*base["nodes"]]}
    shifted["nodes"][2] = {"id": "ps2", "kind": "pic.phase_shifter", "params": {"phase_rad": math.pi}}
    pi_phase = simulate_pic_netlist(shifted)
    outs2 = {f"{o['node']}.{o['port']}": o for o in pi_phase["dag_solver"]["external_outputs"]}
    assert outs2["cpl_out.out1"]["power"] == pytest_approx(1.0, abs_tol=1e-12)
    assert outs2["cpl_out.out2"]["power"] == pytest_approx(0.0, abs_tol=1e-12)


def test_pic_dag_solver_applies_edge_insertion_loss_db():
    netlist = {
        "schema_version": "0.1",
        "profile": "pic_circuit",
        "graph_id": "test_pic_edge_loss",
        "circuit": {"id": "test_pic_edge_loss", "wavelength_nm": 1550, "inputs": [{"node": "a", "port": "in", "amplitude": 1.0}]},
        "nodes": [
            {"id": "a", "kind": "pic.waveguide", "params": {"length_um": 0.0, "loss_db_per_cm": 0.0}},
            {"id": "b", "kind": "pic.waveguide", "params": {"length_um": 0.0, "loss_db_per_cm": 0.0}},
        ],
        "edges": [
            {
                "from": "a",
                "from_port": "out",
                "to": "b",
                "to_port": "in",
                "kind": "optical",
                "params": {"insertion_loss_db": 3.0},
            }
        ],
    }

    results = simulate_pic_netlist(netlist)
    dag = results["dag_solver"]
    outs = dag["external_outputs"]
    assert len(outs) == 1
    assert outs[0]["node"] == "b"
    assert outs[0]["port"] == "out"
    assert outs[0]["power"] == pytest_approx(10 ** (-3.0 / 10.0), abs_tol=1e-12)
    assert outs[0]["loss_db"] == pytest_approx(3.0, abs_tol=1e-9)

    chain = results["chain_solver"]
    assert chain["applicable"] is True
    assert chain["total_loss_db"] == pytest_approx(3.0, abs_tol=1e-9)


def test_pic_edge_phase_can_replace_phase_shifter_in_mzi():
    base = {
        "schema_version": "0.1",
        "profile": "pic_circuit",
        "graph_id": "test_pic_mzi_edge_phase",
        "circuit": {
            "id": "test_pic_mzi_edge_phase",
            "wavelength_nm": 1550,
            "inputs": [{"node": "cpl_in", "port": "in1", "amplitude": 1.0}],
        },
        "nodes": [
            {"id": "cpl_in", "kind": "pic.coupler", "params": {"coupling_ratio": 0.5}},
            {"id": "ps1", "kind": "pic.phase_shifter", "params": {"phase_rad": 0.0}},
            {"id": "ps2", "kind": "pic.phase_shifter", "params": {"phase_rad": 0.0}},
            {"id": "cpl_out", "kind": "pic.coupler", "params": {"coupling_ratio": 0.5}},
        ],
        "edges": [
            {"from": "cpl_in", "from_port": "out1", "to": "ps1", "to_port": "in"},
            {"from": "cpl_in", "from_port": "out2", "to": "ps2", "to_port": "in", "params": {"phase_rad": math.pi}},
            {"from": "ps1", "from_port": "out", "to": "cpl_out", "to_port": "in1"},
            {"from": "ps2", "from_port": "out", "to": "cpl_out", "to_port": "in2"},
        ],
    }

    r = simulate_pic_netlist(base)
    outs = {f"{o['node']}.{o['port']}": o for o in r["dag_solver"]["external_outputs"]}
    assert outs["cpl_out.out1"]["power"] == pytest_approx(1.0, abs_tol=1e-12)
    assert outs["cpl_out.out2"]["power"] == pytest_approx(0.0, abs_tol=1e-12)


def test_pic_scattering_solver_models_touchstone_reflection_and_transmission():
    ts_path = Path(__file__).parent / "fixtures" / "touchstone_reflective.s2p"
    assert ts_path.exists()

    netlist = {
        "schema_version": "0.1",
        "profile": "pic_circuit",
        "graph_id": "test_pic_scattering_reflection",
        "circuit": {
            "id": "test_pic_scattering_reflection",
            "wavelength_nm": 1550,
            "solver": "scattering",
            "inputs": [{"node": "ts", "port": "in", "amplitude": 1.0}],
            "outputs": [{"node": "ts", "port": "in"}, {"node": "ts", "port": "out"}],
        },
        "nodes": [
            {"id": "ts", "kind": "pic.touchstone_2port", "params": {"touchstone_path": str(ts_path)}},
        ],
        "edges": [],
    }

    results = simulate_pic_netlist(netlist)
    sc = results["scattering_solver"]
    assert sc["applicable"] is True
    outs = {f"{o['node']}.{o['port']}": o for o in sc["external_outputs"]}

    # Fixture encodes S11=0.2, S21=0.5 at ~1550 nm.
    assert outs["ts.in"]["power"] == pytest_approx(0.04, abs_tol=1e-12)
    assert outs["ts.out"]["power"] == pytest_approx(0.25, abs_tol=1e-12)


def test_pic_scattering_solver_models_native_reflection_via_return_loss_db():
    # Use a native 2-port element with insertion loss so the scattering matrix stays passive.
    netlist = {
        "schema_version": "0.1",
        "profile": "pic_circuit",
        "graph_id": "test_pic_scattering_native_reflection",
        "circuit": {
            "id": "test_pic_scattering_native_reflection",
            "wavelength_nm": 1550,
            "solver": "scattering",
            "inputs": [{"node": "gc", "port": "in", "amplitude": 1.0}],
            "outputs": [{"node": "gc", "port": "in"}, {"node": "gc", "port": "out"}],
        },
        "nodes": [
            {
                "id": "gc",
                "kind": "pic.grating_coupler",
                "params": {"insertion_loss_db": 3.0, "return_loss_db": 20.0, "reflection_phase_rad": 0.0},
            }
        ],
        "edges": [],
    }

    r = simulate_pic_netlist(netlist)
    sc = r["scattering_solver"]
    assert sc["applicable"] is True
    outs = {f"{o['node']}.{o['port']}": o for o in sc["external_outputs"]}

    # RL=20 dB => |S11|=0.1 => reflected power 0.01.
    assert outs["gc.in"]["power"] == pytest_approx(0.01, abs_tol=1e-12)
    # IL=3 dB => transmitted power 10^(-3/10).
    assert outs["gc.out"]["power"] == pytest_approx(10 ** (-3.0 / 10.0), abs_tol=1e-12)


def test_pic_scattering_solver_models_isolator_nonreciprocal_transmission():
    base = {
        "schema_version": "0.1",
        "profile": "pic_circuit",
        "graph_id": "test_pic_scattering_isolator",
        "circuit": {
            "id": "test_pic_scattering_isolator",
            "wavelength_nm": 1550,
            "solver": "scattering",
        },
        "nodes": [
            {
                "id": "iso",
                "kind": "pic.isolator_2port",
                "params": {"insertion_loss_db": 1.0, "isolation_db": 30.0},
            }
        ],
        "edges": [],
    }

    # Forward: inject at iso.in, read iso.out.
    fwd = {**base, "circuit": {**base["circuit"], "inputs": [{"node": "iso", "port": "in", "amplitude": 1.0}], "outputs": [{"node": "iso", "port": "out"}]}}
    r1 = simulate_pic_netlist(fwd)["scattering_solver"]
    assert r1["applicable"] is True
    p_fwd = float(r1["external_outputs"][0]["power"])
    assert p_fwd == pytest_approx(10 ** (-1.0 / 10.0), abs_tol=1e-12)

    # Reverse: inject at iso.out, read iso.in.
    rev = {**base, "circuit": {**base["circuit"], "inputs": [{"node": "iso", "port": "out", "amplitude": 1.0}], "outputs": [{"node": "iso", "port": "in"}]}}
    r2 = simulate_pic_netlist(rev)["scattering_solver"]
    assert r2["applicable"] is True
    p_rev = float(r2["external_outputs"][0]["power"])

    # Reverse loss defaults to IL + ISO.
    assert p_rev == pytest_approx(10 ** (-(1.0 + 30.0) / 10.0), abs_tol=1e-18)
    assert p_fwd > p_rev


def test_pic_scattering_solver_supports_simple_feedback_cycle():
    # Two reciprocal 2-ports connected in a loop. With transmission t=0.5,
    # the loop gives b_out = t/(1-t^2) for an injection at ts1.in.
    ts_path = Path(__file__).parent / "fixtures" / "touchstone_bidir.s2p"
    assert ts_path.exists()

    netlist = {
        "schema_version": "0.1",
        "profile": "pic_circuit",
        "graph_id": "test_pic_scattering_cycle",
        "circuit": {
            "id": "test_pic_scattering_cycle",
            "wavelength_nm": 1550,
            "solver": "scattering",
            "inputs": [{"node": "ts1", "port": "in", "amplitude": 1.0}],
            "outputs": [{"node": "ts1", "port": "out"}],
        },
        "nodes": [
            {"id": "ts1", "kind": "pic.touchstone_2port", "params": {"touchstone_path": str(ts_path)}},
            {"id": "ts2", "kind": "pic.touchstone_2port", "params": {"touchstone_path": str(ts_path)}},
        ],
        "edges": [
            {"from": "ts1", "from_port": "out", "to": "ts2", "to_port": "in", "kind": "optical"},
            {"from": "ts2", "from_port": "out", "to": "ts1", "to_port": "in", "kind": "optical"},
        ],
    }

    results = simulate_pic_netlist(netlist)
    sc = results["scattering_solver"]
    assert sc["applicable"] is True
    out = sc["external_outputs"][0]
    assert out["node"] == "ts1"
    assert out["port"] == "out"

    expected_amp = 0.5 / (1.0 - 0.25)  # t/(1-t^2)
    expected_power = expected_amp**2
    assert out["power"] == pytest_approx(expected_power, abs_tol=1e-12)


def pytest_approx(value: float, *, abs_tol: float):
    # Avoid importing pytest for a single approx assertion helper.
    def _cmp(x: float) -> bool:
        return abs(float(x) - float(value)) <= abs_tol

    class _Approx:
        def __eq__(self, other):  # type: ignore[override]
            return _cmp(float(other))

    return _Approx()
