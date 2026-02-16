from __future__ import annotations

from pathlib import Path

from photonstrust.graph.spec import canonicalize_graph, format_graphspec_toml, parse_graphspec_toml, stable_graph_hash
from photonstrust.graph.spec import load_graph_file


def _sample_graph() -> dict:
    return {
        "schema_version": "0.1",
        "graph_id": "rt_graph",
        "profile": "pic_circuit",
        "circuit": {"id": "rt_graph", "wavelength_nm": 1550},
        "nodes": [
            {"id": "b", "kind": "pic.waveguide", "params": {"length_um": 200}},
            {"id": "a", "kind": "pic.waveguide", "params": {"length_um": 100}},
        ],
        "edges": [
            {"from": "a", "to": "b", "kind": "optical", "from_port": None, "to_port": None, "params": None},
        ],
    }


def test_graphspec_format_idempotent_roundtrip() -> None:
    graph = _sample_graph()
    t1 = format_graphspec_toml(graph)
    parsed = parse_graphspec_toml(t1)
    t2 = format_graphspec_toml(parsed)
    assert t1 == t2


def test_graphspec_stable_hash_equivalent_after_toml_roundtrip() -> None:
    graph = _sample_graph()
    digest_a = stable_graph_hash(graph)
    digest_b = stable_graph_hash(parse_graphspec_toml(format_graphspec_toml(graph)))
    assert digest_a == digest_b


def test_canonicalize_graph_fills_pic_edge_defaults() -> None:
    graph = {
        "schema_version": "0.1",
        "graph_id": "defaults_graph",
        "profile": "pic_circuit",
        "circuit": {"id": "defaults_graph"},
        "nodes": [{"id": "a", "kind": "pic.waveguide", "params": {"length_um": 10}}],
        "edges": [{"from": "a", "to": "a"}],
    }
    canonical = canonicalize_graph(graph)
    edge = canonical["edges"][0]
    assert edge["kind"] == "optical"
    assert edge["from_port"] == "out"
    assert edge["to_port"] == "in"
    assert edge["params"] == {}


def test_demo_qkd_json_and_toml_roundtrip_equivalent() -> None:
    root = Path(__file__).resolve().parents[1]
    graph_json = load_graph_file(root / "graphs" / "demo8_qkd_link_graph.json")
    graph_toml = load_graph_file(root / "graphs" / "demo8_qkd_link_graph.ptg.toml")
    assert stable_graph_hash(graph_json) == stable_graph_hash(graph_toml)
