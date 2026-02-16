from __future__ import annotations

from photonstrust.graph.compiler import compile_graph
from photonstrust.invdesign.coupler_ratio import inverse_design_coupler_ratio
from photonstrust.pic import simulate_pic_netlist


def test_invdesign_coupler_ratio_hits_target_fraction_reasonably():
    graph = {
        "schema_version": "0.1",
        "graph_id": "inv_coupler_ratio",
        "profile": "pic_circuit",
        "metadata": {"title": "inv_coupler_ratio", "description": "", "created_at": "2026-02-14"},
        "circuit": {
            "id": "inv_coupler_ratio",
            "wavelength_nm": 1550.0,
            "inputs": [
                {"node": "cpl", "port": "in1", "amplitude": 1.0},
                {"node": "cpl", "port": "in2", "amplitude": 0.0},
            ],
        },
        "nodes": [{"id": "cpl", "kind": "pic.coupler", "params": {"coupling_ratio": 0.5, "insertion_loss_db": 0.0}}],
        "edges": [],
    }

    compiled = compile_graph(graph, require_schema=False)
    netlist = dict(compiled.compiled)

    result = inverse_design_coupler_ratio(
        netlist,
        coupler_node_id="cpl",
        target_output_node="cpl",
        target_output_port="out1",
        target_power_fraction=0.90,
        wavelengths_nm=[1550.0],
        steps=101,
    )

    assert result.report.get("schema_version") == "0.1"
    assert result.report.get("kind") == "pic.invdesign.coupler_ratio"
    assert (result.report.get("inputs", {}) or {}).get("robustness")
    assert ((result.report.get("best", {}) or {}).get("robustness_eval", {}) or {}).get("worst_case")
    assert ((result.report.get("best", {}) or {}).get("robustness_eval", {}) or {}).get("threshold_eval")
    assert ((result.report.get("execution", {}) or {}).get("solver", {}) or {}).get("backend_used") == "core"
    assert "objective_case_max" in ((result.report.get("curve") or [])[0])

    # For a standalone coupler with input on in1 only, out1 fraction ~= 1 - kappa.
    assert 0.0 <= float(result.best_coupling_ratio) <= 1.0
    assert float(result.best_coupling_ratio) <= 0.2

    sim = simulate_pic_netlist(result.updated_netlist, wavelength_nm=1550.0)
    outs = (sim.get("dag_solver", {}) or {}).get("external_outputs", []) or []
    total = sum(float(row.get("power", 0.0) or 0.0) for row in outs if isinstance(row, dict))
    p_target = 0.0
    for row in outs:
        if not isinstance(row, dict):
            continue
        if str(row.get("node")) == "cpl" and str(row.get("port")) == "out1":
            p_target += float(row.get("power", 0.0) or 0.0)
    frac = p_target / total if total > 0 else 0.0

    assert frac >= 0.88
