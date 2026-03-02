from __future__ import annotations

import copy

from photonstrust.pic.drc import run_graph_drc


class _CompiledLike:
    def __init__(self, compiled: dict):
        self.compiled = compiled


def _pdk(
    *,
    min_waveguide_width_um: float = 0.45,
    min_waveguide_gap_um: float = 0.20,
    min_bend_radius_um: float = 5.0,
) -> dict:
    return {
        "design_rules": {
            "min_waveguide_width_um": min_waveguide_width_um,
            "min_waveguide_gap_um": min_waveguide_gap_um,
            "min_bend_radius_um": min_bend_radius_um,
        }
    }


def _clean_netlist() -> dict:
    return {
        "schema_version": "0.1",
        "profile": "pic_circuit",
        "graph_id": "pic_graph_drc_clean",
        "nodes": [
            {"id": "gc_in", "kind": "pic.grating_coupler", "params": {}},
            {"id": "wg1", "kind": "pic.waveguide", "params": {"width_um": 0.50}},
            {"id": "ec_out", "kind": "pic.edge_coupler", "params": {}},
        ],
        "edges": [
            {"id": "e1", "from": "gc_in", "from_port": "out", "to": "wg1", "to_port": "in", "kind": "optical"},
            {"id": "e2", "from": "wg1", "from_port": "out", "to": "ec_out", "to_port": "in", "kind": "optical"},
        ],
    }


def test_run_graph_drc_clean_graph_passes() -> None:
    result = run_graph_drc(_CompiledLike(_clean_netlist()), pdk=_pdk())

    assert result["kind"] == "pic.graph_drc"
    assert result["graph_id"] == "pic_graph_drc_clean"
    assert result["rules"] == {
        "min_waveguide_width_um": 0.45,
        "min_waveguide_gap_um": 0.20,
        "min_bend_radius_um": 5.0,
    }
    assert result["summary"] == {
        "pass": True,
        "error_count": 0,
        "warning_count": 0,
        "info_count": 0,
    }
    assert result["items"] == []


def test_run_graph_drc_width_violation_flagged_error() -> None:
    netlist = _clean_netlist()
    netlist["nodes"][1]["params"]["waveguide_width_um"] = 0.30
    netlist["nodes"][1]["params"].pop("width_um")

    result = run_graph_drc(netlist, pdk=_pdk())
    assert result["summary"]["pass"] is False
    assert any(
        item["code"] == "PIC.DRC.MIN_WIDTH" and item["severity"] == "error"
        for item in result["items"]
    )


def test_run_graph_drc_gap_violation_flagged_error() -> None:
    netlist = _clean_netlist()
    netlist["nodes"][1]["params"]["gap_um"] = 0.10

    result = run_graph_drc(netlist, pdk=_pdk())
    assert result["summary"]["pass"] is False
    assert any(
        item["code"] == "PIC.DRC.MIN_GAP" and item["severity"] == "error"
        for item in result["items"]
    )


def test_run_graph_drc_bend_radius_violation_flagged_error() -> None:
    netlist = _clean_netlist()
    netlist["nodes"][1]["params"]["bend_radius_um"] = 2.0

    result = run_graph_drc(netlist, pdk=_pdk())
    assert result["summary"]["pass"] is False
    assert any(
        item["code"] == "PIC.DRC.MIN_BEND_RADIUS" and item["severity"] == "error"
        for item in result["items"]
    )


def test_run_graph_drc_bad_edge_port_mapping_flagged_error() -> None:
    netlist = _clean_netlist()
    netlist["edges"][0]["from_port"] = "bad_port"

    result = run_graph_drc(netlist, pdk=_pdk())
    assert result["summary"]["pass"] is False
    assert any(
        item["code"] == "PIC.DRC.EDGE_PORT_INVALID" and item.get("edge_id") == "e1"
        for item in result["items"]
    )


def test_run_graph_drc_floating_non_io_port_flagged_warning() -> None:
    netlist = {
        "schema_version": "0.1",
        "profile": "pic_circuit",
        "graph_id": "pic_graph_drc_floating",
        "nodes": [
            {"id": "wg1", "kind": "pic.waveguide", "params": {"width_um": 0.50}},
        ],
        "edges": [],
    }

    result = run_graph_drc(netlist, pdk=_pdk())
    assert result["summary"]["pass"] is True
    assert result["summary"]["error_count"] == 0
    assert result["summary"]["warning_count"] >= 1
    assert any(
        item["code"] == "PIC.DRC.FLOATING_PORT" and item["severity"] == "warning" and item.get("node_id") == "wg1"
        for item in result["items"]
    )


def test_run_graph_drc_item_ids_are_deterministic() -> None:
    netlist = {
        "schema_version": "0.1",
        "profile": "pic_circuit",
        "graph_id": "pic_graph_drc_deterministic",
        "nodes": [
            {"id": "z_wg", "kind": "pic.waveguide", "params": {"width_um": 0.10, "gap_um": 0.10, "bend_radius_um": 1.0}},
            {"id": "a_wg", "kind": "pic.waveguide", "params": {"width_um": 0.10}},
        ],
        "edges": [
            {"id": "e_b", "from": "z_wg", "from_port": "bad", "to": "a_wg", "to_port": "in"},
            {"id": "e_a", "from": "missing", "from_port": "out", "to": "z_wg", "to_port": "in"},
        ],
    }

    first = run_graph_drc(copy.deepcopy(netlist), pdk=_pdk())
    second = run_graph_drc(copy.deepcopy(netlist), pdk=_pdk())

    first_ids = [item["id"] for item in first["items"]]
    second_ids = [item["id"] for item in second["items"]]
    first_codes = [item["code"] for item in first["items"]]
    second_codes = [item["code"] for item in second["items"]]

    assert len(first_ids) >= 2
    assert first_ids == second_ids
    assert first_codes == second_codes
    assert first_ids == [f"item_{i:04d}" for i in range(1, len(first_ids) + 1)]
