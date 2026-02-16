from __future__ import annotations

from photonstrust.pic import simulate_pic_netlist_sweep


def test_ring_resonance_not_flat_in_sweep():
    netlist = {
        "schema_version": "0.1",
        "graph_id": "test_ring_resonance",
        "profile": "pic_circuit",
        "circuit": {"id": "test_ring_resonance", "wavelength_nm": 1550},
        "nodes": [
            {"id": "gc_in", "kind": "pic.grating_coupler", "params": {"insertion_loss_db": 0.0}},
            {
                "id": "ring",
                "kind": "pic.ring",
                "params": {
                    "coupling_ratio": 0.002,
                    "radius_um": 10.0,
                    "n_eff": 2.4,
                    "loss_db_per_cm": 2.0,
                },
            },
            {"id": "ec_out", "kind": "pic.edge_coupler", "params": {"insertion_loss_db": 0.0}},
        ],
        "edges": [
            {"from": "gc_in", "to": "ring", "kind": "optical"},
            {"from": "ring", "to": "ec_out", "kind": "optical"},
        ],
    }

    wavelengths = [1548.0 + 0.2 * i for i in range(71)]  # 1548..1562 nm
    sweep = simulate_pic_netlist_sweep(netlist, wavelengths_nm=wavelengths)

    etas = []
    for p in sweep["sweep"]["points"]:
        chain = p["chain_solver"]
        assert chain["applicable"] is True
        etas.append(float(chain["eta_total"]))

    lo = min(etas)
    hi = max(etas)
    assert hi > 0.5
    assert lo < 0.25 * hi

