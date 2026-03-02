from __future__ import annotations

import json

from photonstrust.pic.lvs_lite import run_lvs_lite


def _base_graph() -> dict:
    return {
        "schema_version": "0.1",
        "graph_id": "lvs_lite_m1_graph",
        "profile": "pic_circuit",
        "circuit": {"id": "lvs_lite_m1_graph"},
        "nodes": [
            {"id": "src", "kind": "pic.grating_coupler", "params": {}},
            {"id": "wg", "kind": "pic.waveguide", "params": {"length_um": 50}},
            {"id": "sink", "kind": "pic.edge_coupler", "params": {}},
        ],
        "edges": [
            {"from": "src", "from_port": "out", "to": "wg", "to_port": "in", "kind": "optical"},
            {"from": "wg", "from_port": "out", "to": "sink", "to_port": "in", "kind": "optical"},
        ],
    }


def _compiled_from_graph(graph: dict) -> dict:
    return {
        "schema_version": "0.1",
        "profile": "pic_circuit",
        "graph_id": graph.get("graph_id"),
        "nodes": [
            {"id": "src", "kind": "pic.grating_coupler", "params": {}},
            {"id": "wg", "kind": "pic.waveguide", "params": {"length_um": 50}},
            {"id": "sink", "kind": "pic.edge_coupler", "params": {}},
        ],
        "edges": [
            {"from": "src", "from_port": "out", "to": "wg", "to_port": "in", "kind": "optical"},
            {"from": "wg", "from_port": "out", "to": "sink", "to_port": "in", "kind": "optical"},
        ],
    }


class _CompiledWrapper:
    def __init__(self, compiled: dict) -> None:
        self.compiled = compiled


def test_pic_lvs_lite_m1_exact_match_passes() -> None:
    graph = _base_graph()
    compiled = _compiled_from_graph(graph)

    report = run_lvs_lite(graph, _CompiledWrapper(compiled))

    assert report["kind"] == "pic.lvs_lite_m1"
    assert report["pass"] is True
    assert report["summary"]["failed_checks"] == []
    assert report["summary"]["failure_count"] == 0
    assert report["checks"]["block_count"]["pass"] is True
    assert report["checks"]["connection_count"]["pass"] is True
    assert report["checks"]["port_mapping"]["pass"] is True
    assert report["checks"]["kind_preservation"]["pass"] is True
    assert report["mismatches"]["block_count"] == []
    assert report["mismatches"]["connection_count"] == []
    assert report["mismatches"]["port_mapping"] == []
    assert report["mismatches"]["kind_preservation"] == []


def test_pic_lvs_lite_m1_block_count_mismatch_fails_l1() -> None:
    graph = _base_graph()
    compiled = _compiled_from_graph(graph)
    compiled["nodes"].append({"id": "aux", "kind": "pic.waveguide", "params": {}})

    report = run_lvs_lite(graph, compiled)

    assert report["checks"]["block_count"]["pass"] is False
    assert "block_count" in report["summary"]["failed_checks"]
    assert any(str(row.get("id", "")).startswith("block_count:") for row in report["mismatches"]["block_count"])


def test_pic_lvs_lite_m1_connection_count_mismatch_fails_l2() -> None:
    graph = _base_graph()
    compiled = _compiled_from_graph(graph)
    compiled["edges"] = [dict(compiled["edges"][0])]

    report = run_lvs_lite(graph, compiled)

    assert report["checks"]["connection_count"]["pass"] is False
    assert "connection_count" in report["summary"]["failed_checks"]
    assert report["checks"]["connection_count"]["graph_count"] == 2
    assert report["checks"]["connection_count"]["compiled_count"] == 1
    assert report["mismatches"]["connection_count"]


def test_pic_lvs_lite_m1_mutated_port_mapping_fails_l3() -> None:
    graph = _base_graph()
    compiled = _compiled_from_graph(graph)
    compiled["edges"][0]["to_port"] = "out"

    report = run_lvs_lite(graph, compiled)

    assert report["checks"]["connection_count"]["pass"] is True
    assert report["checks"]["port_mapping"]["pass"] is False
    assert "port_mapping" in report["summary"]["failed_checks"]
    assert report["mismatches"]["port_mapping"]
    assert all("edge" in row for row in report["mismatches"]["port_mapping"])


def test_pic_lvs_lite_m1_kind_mismatch_fails_l4() -> None:
    graph = _base_graph()
    compiled = _compiled_from_graph(graph)
    compiled["nodes"][1]["kind"] = "pic.ring_resonator"

    report = run_lvs_lite(graph, compiled)

    assert report["checks"]["kind_preservation"]["pass"] is False
    assert "kind_preservation" in report["summary"]["failed_checks"]
    mismatches = report["mismatches"]["kind_preservation"]
    assert mismatches
    assert any(row.get("type") == "kind_mismatch" and row.get("instance_id") == "wg" for row in mismatches)


def test_pic_lvs_lite_m1_output_ordering_is_deterministic() -> None:
    graph = _base_graph()
    # Deliberately scrambled input order and two mapping mismatches.
    graph["nodes"] = [graph["nodes"][2], graph["nodes"][0], graph["nodes"][1]]
    graph["edges"] = [graph["edges"][1], graph["edges"][0]]

    compiled = _compiled_from_graph(_base_graph())
    compiled["nodes"] = [compiled["nodes"][1], compiled["nodes"][2], compiled["nodes"][0]]
    compiled["edges"] = [compiled["edges"][1], compiled["edges"][0]]
    compiled["edges"][0]["from_port"] = "in"
    compiled["edges"][1]["to_port"] = "out"

    report_a = run_lvs_lite(graph, compiled)
    report_b = run_lvs_lite(graph, compiled)

    assert json.dumps(report_a, sort_keys=True) == json.dumps(report_b, sort_keys=True)
    ids = [str(row.get("id", "")) for row in report_a["mismatches"]["port_mapping"]]
    assert ids == sorted(ids, key=lambda t: (t.lower(), t))
