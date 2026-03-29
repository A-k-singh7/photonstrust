"""Tests for gdsfactory import/export interop."""
import pytest
from photonstrust.interop.gdsfactory_import import (
    import_gdsfactory_component,
    import_gdsfactory_netlist,
    _infer_kind_from_cell_name,
    _map_port_name,
    ImportedComponent,
    ImportedCircuit,
)
from photonstrust.interop.gdsfactory_export import (
    export_to_netlist,
    export_to_netlist_yaml,
    ExportedNetlist,
    _kind_to_gds_cell,
)


# -- Mock gdsfactory objects for testing without gdsfactory installed --

class _MockPort:
    def __init__(self, name, orientation=0):
        self.name = name
        self.orientation = orientation

class _MockComponent:
    def __init__(self, name, ports=None, settings=None, function_name=None):
        self.name = name
        self.function_name = function_name or name
        self.ports = ports or {}
        self.settings = settings or {}


# -- Port mapping tests --

def test_port_map_o1_to_in():
    assert _map_port_name("o1") == "in"

def test_port_map_o2_to_out():
    assert _map_port_name("o2") == "out"

def test_port_map_custom():
    assert _map_port_name("custom", {"custom": "special"}) == "special"

def test_port_map_passthrough():
    assert _map_port_name("unknown_port") == "unknown_port"


# -- Kind inference tests --

def test_infer_kind_mmi():
    assert _infer_kind_from_cell_name("mmi1x2") == "pic.mmi"

def test_infer_kind_y_branch():
    assert _infer_kind_from_cell_name("y_branch_te") == "pic.y_branch"

def test_infer_kind_from_pdk_cells():
    pdk_cells = {"my_custom_cell": {"maps_to_internal_kind": "pic.mzm"}}
    assert _infer_kind_from_cell_name("my_custom_cell", pdk_cells) == "pic.mzm"

def test_infer_kind_crossing():
    assert _infer_kind_from_cell_name("waveguide_crossing") == "pic.crossing"


# -- Import component tests --

def test_import_mock_component():
    ports = {"o1": _MockPort("o1", 180), "o2": _MockPort("o2", 0)}
    comp = _MockComponent("mmi1x2", ports=ports, settings={"width": 2.5})
    result = import_gdsfactory_component(comp)
    assert result.kind == "pic.mmi"
    assert "in" in result.ports
    assert "out" in result.ports

def test_import_preserves_params():
    comp = _MockComponent("straight", settings={"length": 10.0, "width": 0.5})
    result = import_gdsfactory_component(comp)
    assert result.params.get("length") == 10.0


# -- Import netlist tests --

def test_import_netlist_basic():
    netlist = {
        "name": "mzi",
        "instances": {
            "splitter": {"component": "mmi1x2", "settings": {}},
            "combiner": {"component": "mmi1x2", "settings": {}},
        },
        "connections": {
            "splitter,o2": "combiner,o1",
        },
        "ports": {"in": "splitter,o1", "out": "combiner,o2"},
    }
    result = import_gdsfactory_netlist(netlist)
    assert result.circuit_id == "mzi"
    assert len(result.nodes) == 2
    assert len(result.edges) == 1
    assert result.n_ports == 2

def test_import_netlist_kind_mapping():
    netlist = {
        "instances": {"gc1": {"component": "grating_coupler_te"}},
        "connections": {},
        "ports": {},
    }
    result = import_gdsfactory_netlist(netlist)
    assert result.nodes[0]["kind"] == "pic.grating_coupler"


# -- Export tests --

def test_export_basic():
    graph = {
        "id": "test_circuit",
        "nodes": [
            {"id": "gc1", "kind": "pic.grating_coupler", "params": {}},
            {"id": "wg1", "kind": "pic.waveguide", "params": {"length_um": 100}},
        ],
        "edges": [
            {"from": "gc1", "to": "wg1", "from_port": "out", "to_port": "in"},
        ],
    }
    result = export_to_netlist(graph)
    assert result.name == "test_circuit"
    assert len(result.instances) == 2
    assert len(result.connections) == 1

def test_export_kind_to_gds_cell():
    assert _kind_to_gds_cell("pic.mmi") == "mmi1x2"
    assert _kind_to_gds_cell("pic.waveguide") == "straight"

def test_export_yaml_format():
    graph = {
        "id": "yaml_test",
        "nodes": [{"id": "n1", "kind": "pic.waveguide", "params": {"length": 10}}],
        "edges": [],
    }
    yaml_str = export_to_netlist_yaml(graph)
    assert "name: yaml_test" in yaml_str
    assert "instances:" in yaml_str
    assert "straight" in yaml_str


# -- Round-trip test --

def test_import_export_roundtrip_preserves_port_count():
    """Import a netlist, export it back, and verify structure is preserved."""
    original = {
        "name": "roundtrip_test",
        "instances": {
            "s1": {"component": "mmi1x2", "settings": {"width": 2.5}},
            "s2": {"component": "mmi1x2", "settings": {"width": 2.5}},
        },
        "connections": {"s1,o2": "s2,o1"},
        "ports": {"p_in": "s1,o1", "p_out": "s2,o2"},
    }
    imported = import_gdsfactory_netlist(original)

    # Build graph dict from imported
    graph = {
        "id": imported.circuit_id,
        "nodes": imported.nodes,
        "edges": imported.edges,
    }

    exported = export_to_netlist(graph)
    assert len(exported.instances) == len(original["instances"])
    assert len(exported.connections) == len(original["connections"])
