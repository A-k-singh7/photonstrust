from __future__ import annotations

from photonstrust.graph.compiler import compile_graph
from photonstrust.invdesign.mzi_phase import inverse_design_mzi_phase
from photonstrust.pic import simulate_pic_netlist


def test_invdesign_mzi_phase_hits_target_fraction_reasonably():
    graph = {
        "schema_version": "0.1",
        "graph_id": "inv_mzi",
        "profile": "pic_circuit",
        "metadata": {"title": "inv_mzi", "description": "", "created_at": "2026-02-13"},
        "circuit": {
            "id": "inv_mzi",
            "wavelength_nm": 1550.0,
            "inputs": [
                {"node": "cpl_in", "port": "in1", "amplitude": 1.0},
                {"node": "cpl_in", "port": "in2", "amplitude": 0.0},
            ],
        },
        "nodes": [
            {"id": "cpl_in", "kind": "pic.coupler", "params": {"coupling_ratio": 0.5, "insertion_loss_db": 0.2}},
            {"id": "ps1", "kind": "pic.phase_shifter", "params": {"phase_rad": 0.0, "insertion_loss_db": 0.1}},
            {"id": "ps2", "kind": "pic.phase_shifter", "params": {"phase_rad": 0.0, "insertion_loss_db": 0.1}},
            {"id": "cpl_out", "kind": "pic.coupler", "params": {"coupling_ratio": 0.5, "insertion_loss_db": 0.2}},
        ],
        "edges": [
            {"from": "cpl_in", "from_port": "out1", "to": "ps1", "to_port": "in"},
            {"from": "cpl_in", "from_port": "out2", "to": "ps2", "to_port": "in"},
            {"from": "ps1", "from_port": "out", "to": "cpl_out", "to_port": "in1"},
            {"from": "ps2", "from_port": "out", "to": "cpl_out", "to_port": "in2"},
        ],
    }

    compiled = compile_graph(graph, require_schema=False)
    netlist = dict(compiled.compiled)

    result = inverse_design_mzi_phase(
        netlist,
        phase_node_id="ps1",
        target_output_node="cpl_out",
        target_output_port="out1",
        target_power_fraction=0.90,
        wavelengths_nm=[1550.0],
        steps=181,
    )

    assert result.report.get("schema_version") == "0.1"
    assert result.report.get("kind") == "pic.invdesign.mzi_phase"
    assert (result.report.get("inputs", {}) or {}).get("robustness")
    assert ((result.report.get("best", {}) or {}).get("robustness_eval", {}) or {}).get("worst_case")
    assert ((result.report.get("best", {}) or {}).get("robustness_eval", {}) or {}).get("threshold_eval")
    assert ((result.report.get("execution", {}) or {}).get("solver", {}) or {}).get("backend_used") == "core"
    assert "objective_case_max" in ((result.report.get("curve") or [])[0])

    sim = simulate_pic_netlist(result.updated_netlist, wavelength_nm=1550.0)
    outs = (sim.get("dag_solver", {}) or {}).get("external_outputs", []) or []
    total = sum(float(row.get("power", 0.0) or 0.0) for row in outs if isinstance(row, dict))
    p_target = 0.0
    for row in outs:
        if not isinstance(row, dict):
            continue
        if str(row.get("node")) == "cpl_out" and str(row.get("port")) == "out1":
            p_target += float(row.get("power", 0.0) or 0.0)
    frac = p_target / total if total > 0 else 0.0

    assert frac >= 0.85
