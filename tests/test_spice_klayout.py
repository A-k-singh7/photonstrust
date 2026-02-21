"""Tests for SPICE compact models and KLayout GDS cell generation."""
from __future__ import annotations
import math
import pytest
from photonstrust.spice.compact_models import (
    spice_model_for_kind, all_spice_models, supported_kinds,
    _eta, write_component_library,
)
from photonstrust.layout.pic.klayout_cell import (
    component_gdl_cell, netlist_to_gdl, supported_kinds as gds_kinds,
)


# ── SPICE compact model tests ────────────────────────────────────────────────

class TestSpiceCompactModels:

    def test_supported_kinds_nonempty(self):
        kinds = supported_kinds()
        assert len(kinds) >= 7
        assert "pic.waveguide" in kinds
        assert "pic.coupler" in kinds

    def test_unknown_kind_raises(self):
        with pytest.raises(KeyError, match="No SPICE compact model"):
            spice_model_for_kind("pic.unknown_element")

    def test_waveguide_model_contains_vccs(self):
        model = spice_model_for_kind("pic.waveguide", {"length_um": 50.0, "loss_db_per_cm": 3.0})
        assert ".subckt" in model
        assert ".ends" in model
        assert "Gout_re" in model

    def test_phase_shifter_phase_encoded_in_model(self):
        import math
        model90 = spice_model_for_kind("pic.phase_shifter", {"phase_rad": math.pi / 2})
        model0  = spice_model_for_kind("pic.phase_shifter", {"phase_rad": 0.0})
        # At 90 deg the imaginary part (t_im) should be non-zero
        assert model90 != model0

    def test_coupler_four_port_structure(self):
        model = spice_model_for_kind("pic.coupler", {"coupling_ratio": 0.3})
        assert "in1_re" in model
        assert "in2_re" in model
        assert "out1_re" in model
        assert "out2_re" in model
        # Should have 8 G-element lines
        g_count = sum(1 for ln in model.splitlines() if ln.startswith("G"))
        assert g_count == 8

    def test_isolator_no_reverse_path(self):
        model = spice_model_for_kind("pic.isolator_2port", {"isolation_db": 40.0})
        # Forward G-elements exist but no back-coupling by design
        assert "Gfwd_re" in model
        assert "* NOTE: reverse direction is isolated" in model

    def test_ring_model_contains_transfer(self):
        model = spice_model_for_kind("pic.ring", {
            "coupling_ratio": 0.01, "radius_um": 5.0, "n_eff": 2.4,
            "loss_db_per_cm": 2.0, "wavelength_nm": 1550.0,
        })
        assert "RingResonator" in model
        assert ".subckt" in model

    def test_all_models_compiles_without_error(self):
        lib = all_spice_models()
        assert len(lib) > 500
        assert lib.count(".subckt") == len(supported_kinds())
        assert lib.count(".ends") == len(supported_kinds())

    def test_custom_subckt_name(self):
        model = spice_model_for_kind("pic.waveguide", subckt_name="MY_WG")
        assert ".subckt MY_WG" in model
        assert ".ends MY_WG" in model

    def test_write_component_library(self, tmp_path):
        out = tmp_path / "test.lib"
        write_component_library(str(out))
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert ".subckt" in content
        assert len(content) > 1000

    def test_eta_helper_passivity(self):
        # 0dB -> amplitude 1.0; 20dB -> 0.1; 6dB -> ~0.5
        assert abs(_eta(0.0) - 1.0) < 1e-9
        assert abs(_eta(20.0) - 0.1) < 1e-9
        assert _eta(6.0) > 0.49 and _eta(6.0) < 0.52


# ── KLayout GDS cell tests ───────────────────────────────────────────────────

class TestKLayoutCells:

    def test_supported_gds_kinds(self):
        kinds = gds_kinds()
        assert "pic.waveguide" in kinds
        assert "pic.coupler" in kinds
        assert "pic.ring" in kinds

    def test_unknown_kind_raises(self):
        with pytest.raises(KeyError):
            component_gdl_cell("pic.undefined_component")

    def test_waveguide_cell_has_ports(self):
        cell = component_gdl_cell("pic.waveguide", {"length_um": 100.0})
        ports = cell["ports"]
        assert len(ports) == 2
        names = {p["name"] for p in ports}
        assert names == {"in", "out"}

    def test_coupler_has_four_ports(self):
        cell = component_gdl_cell("pic.coupler", {"coupling_ratio": 0.5})
        names = {p["name"] for p in cell["ports"]}
        assert names == {"in1", "in2", "out1", "out2"}

    def test_ring_cell_geometry(self):
        cell = component_gdl_cell("pic.ring", {"radius_um": 10.0})
        assert len(cell["shapes"]) >= 2
        # All shapes must have a layer
        for s in cell["shapes"]:
            assert "layer" in s

    def test_cell_name_override(self):
        cell = component_gdl_cell("pic.waveguide", cell_name="MY_WG")
        assert cell["cell_name"] == "MY_WG"

    def test_netlist_to_gdl_places_instances(self):
        netlist = {
            "circuit": {
                "nodes": [
                    {"id": "wg1", "kind": "pic.waveguide", "params": {"length_um": 100.0}},
                    {"id": "ps1", "kind": "pic.phase_shifter", "params": {"phase_rad": 0.5}},
                ],
                "edges": [
                    {"from": "wg1", "from_port": "out", "to": "ps1", "to_port": "in"},
                ],
            }
        }
        gdl = netlist_to_gdl(netlist)
        assert len(gdl["instances"]) == 2
        assert len(gdl["cells"]) == 2
        assert len(gdl["wires"]) == 1

    def test_netlist_to_gdl_wire_positions_make_sense(self):
        netlist = {
            "circuit": {
                "nodes": [
                    {"id": "wg1", "kind": "pic.waveguide", "params": {"length_um": 50.0}},
                    {"id": "wg2", "kind": "pic.waveguide", "params": {"length_um": 50.0}},
                ],
                "edges": [
                    {"from": "wg1", "from_port": "out", "to": "wg2", "to_port": "in"},
                ],
            }
        }
        gdl = netlist_to_gdl(netlist)
        wire = gdl["wires"][0]
        # From and to positions should be different
        assert wire["from"] != wire["to"]
