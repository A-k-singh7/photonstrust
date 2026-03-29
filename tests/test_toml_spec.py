"""Tests for TOML graph specification."""
import os
import tempfile
import pytest

# Check if TOML parsing is available
try:
    import tomllib
    HAS_TOML = True
except ModuleNotFoundError:
    try:
        import tomli
        HAS_TOML = True
    except ModuleNotFoundError:
        HAS_TOML = False

from photonstrust.graph.toml_spec import (
    load_graph_toml_str, save_graph_toml_str, load_graph_toml, save_graph_toml,
)

SAMPLE_TOML = '''
[circuit]
id = "mzi_test"
wavelength_nm = 1550.0

[[nodes]]
id = "gc_in"
kind = "pic.grating_coupler"
[nodes.params]
insertion_loss_db = 2.5

[[nodes]]
id = "wg1"
kind = "pic.waveguide"
[nodes.params]
length_um = 100.0

[[edges]]
from = "gc_in"
to = "wg1"
from_port = "out"
to_port = "in"
'''

@pytest.mark.skipif(not HAS_TOML, reason="No TOML parser available")
class TestTomlSpec:
    def test_load_basic(self):
        graph = load_graph_toml_str(SAMPLE_TOML)
        assert graph["id"] == "mzi_test"
        assert graph["wavelength_nm"] == 1550.0
        assert len(graph["nodes"]) == 2
        assert len(graph["edges"]) == 1

    def test_node_params(self):
        graph = load_graph_toml_str(SAMPLE_TOML)
        gc = graph["nodes"][0]
        assert gc["kind"] == "pic.grating_coupler"
        assert gc["params"]["insertion_loss_db"] == 2.5

    def test_edge_ports(self):
        graph = load_graph_toml_str(SAMPLE_TOML)
        edge = graph["edges"][0]
        assert edge["from"] == "gc_in"
        assert edge["to"] == "wg1"
        assert edge["from_port"] == "out"
        assert edge["to_port"] == "in"

    def test_roundtrip(self):
        """load(save(graph)) == graph"""
        original = load_graph_toml_str(SAMPLE_TOML)
        toml_str = save_graph_toml_str(original)
        reloaded = load_graph_toml_str(toml_str)

        assert reloaded["id"] == original["id"]
        assert reloaded["wavelength_nm"] == original["wavelength_nm"]
        assert len(reloaded["nodes"]) == len(original["nodes"])
        assert len(reloaded["edges"]) == len(original["edges"])

        for orig_node, new_node in zip(original["nodes"], reloaded["nodes"]):
            assert orig_node["id"] == new_node["id"]
            assert orig_node["kind"] == new_node["kind"]

    def test_file_roundtrip(self, tmp_path):
        original = load_graph_toml_str(SAMPLE_TOML)
        path = str(tmp_path / "test.toml")
        save_graph_toml(original, path)
        reloaded = load_graph_toml(path)
        assert reloaded["id"] == original["id"]
        assert len(reloaded["nodes"]) == len(original["nodes"])

    def test_save_format(self):
        graph = {"id": "test", "wavelength_nm": 1550.0,
                 "nodes": [{"id": "n1", "kind": "pic.waveguide", "params": {"length_um": 50}}],
                 "edges": []}
        text = save_graph_toml_str(graph)
        assert "[circuit]" in text
        assert 'id = "test"' in text
        assert "[[nodes]]" in text

    def test_empty_graph(self):
        graph = load_graph_toml_str('[circuit]\nid = "empty"\n')
        assert graph["id"] == "empty"
        assert len(graph.get("nodes", [])) == 0
