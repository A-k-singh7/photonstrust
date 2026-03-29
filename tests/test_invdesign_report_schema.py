from __future__ import annotations

from photonstrust.benchmarks.schema import validate_instance
from photonstrust.graph.compiler import compile_graph
from photonstrust.invdesign import inverse_design_coupler_ratio, inverse_design_mzi_phase
from photonstrust.invdesign.schema import invdesign_report_schema_path


def test_invdesign_reports_validate_against_schema():
    schema_path = invdesign_report_schema_path()

    mzi_graph = {
        "schema_version": "0.1",
        "graph_id": "inv_mzi_schema",
        "profile": "pic_circuit",
        "metadata": {"title": "inv_mzi_schema", "description": "", "created_at": "2026-02-14"},
        "circuit": {
            "id": "inv_mzi_schema",
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
    mzi_netlist = dict(compile_graph(mzi_graph, require_schema=False).compiled)
    mzi = inverse_design_mzi_phase(
        mzi_netlist,
        phase_node_id="ps1",
        target_output_node="cpl_out",
        target_output_port="out1",
        target_power_fraction=0.9,
        wavelengths_nm=[1550.0],
        steps=64,
        robustness_cases=[{"id": "nominal", "label": "Nominal", "overrides": {}}, {"id": "corner", "label": "Corner", "overrides": {"cpl_out": {"coupling_ratio": 0.45}}}],
        wavelength_objective_agg="mean",
        case_objective_agg="max",
    )
    validate_instance(mzi.report, schema_path)

    coupler_graph = {
        "schema_version": "0.1",
        "graph_id": "inv_cpl_schema",
        "profile": "pic_circuit",
        "metadata": {"title": "inv_cpl_schema", "description": "", "created_at": "2026-02-14"},
        "circuit": {
            "id": "inv_cpl_schema",
            "wavelength_nm": 1550.0,
            "inputs": [
                {"node": "cpl", "port": "in1", "amplitude": 1.0},
                {"node": "cpl", "port": "in2", "amplitude": 0.0},
            ],
        },
        "nodes": [{"id": "cpl", "kind": "pic.coupler", "params": {"coupling_ratio": 0.5, "insertion_loss_db": 0.0}}],
        "edges": [],
    }
    coupler_netlist = dict(compile_graph(coupler_graph, require_schema=False).compiled)
    cpl = inverse_design_coupler_ratio(
        coupler_netlist,
        coupler_node_id="cpl",
        target_output_node="cpl",
        target_output_port="out1",
        target_power_fraction=0.9,
        wavelengths_nm=[1550.0],
        steps=32,
    )
    validate_instance(cpl.report, schema_path)
