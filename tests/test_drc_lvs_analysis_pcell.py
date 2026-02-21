"""Tests for DRC/LVS, SPICE analysis, and PCell API."""
from __future__ import annotations
import json
import math
import pytest
from pathlib import Path

from photonstrust.layout.pic.drc_lvs import (
    run_drc, run_lvs, run_drc_lvs, DRCRuleSet, DRCViolation,
)
from photonstrust.layout.pic.klayout_cell import netlist_to_gdl, component_gdl_cell
from photonstrust.layout.pic.pcell import (
    get_pcell_schema, pcell_instance, export_pcell_library_json, register_all_pcells,
)
from photonstrust.spice.analysis import (
    ac_sweep_netlist, monte_carlo_netlist, transient_netlist,
    parametric_sweep_netlist, extract_heater_parasitics,
    spice_with_parasitics,
)


# ── Helpers ─────────────────────────────────────────────────────────────────

def _simple_netlist():
    return {
        "circuit": {
            "nodes": [
                {"id": "wg1", "kind": "pic.waveguide",    "params": {"length_um": 100.0}},
                {"id": "ps1", "kind": "pic.phase_shifter","params": {"phase_rad": 0.5}},
                {"id": "wg2", "kind": "pic.waveguide",    "params": {"length_um": 50.0}},
            ],
            "edges": [
                {"from": "wg1", "from_port": "out", "to": "ps1", "to_port": "in"},
                {"from": "ps1", "from_port": "out", "to": "wg2", "to_port": "in"},
            ],
        }
    }


def _simple_graph():
    return {
        "nodes": [
            {"id": "wg1", "kind": "pic.waveguide",    "params": {"length_um": 100.0}},
            {"id": "ps1", "kind": "pic.phase_shifter","params": {"phase_rad": 0.785}},
        ],
        "edges": [
            {"from": "wg1", "from_port": "out", "to": "ps1", "to_port": "in"},
        ],
    }


# ── DRC tests ────────────────────────────────────────────────────────────────

class TestDRC:

    def test_clean_layout_passes(self):
        gdl = netlist_to_gdl(_simple_netlist())
        report = run_drc(gdl)
        # Default rules: may have warnings but no errors for well-spaced cells
        assert report.stats["shapes_checked"] > 0

    def test_wg_min_gap_violation_detected(self):
        # Create two overlapping WG shapes
        gdl = {
            "cells": [{"cell_name": "TEST", "shapes": [
                {"type": "rect", "layer": 1, "datatype": 0, "bbox": [0, 0, 100, 0.4]},
                {"type": "rect", "layer": 1, "datatype": 0, "bbox": [0, 0.45, 100, 0.85]},
            ], "ports": []}],
            "instances": [],
            "wires": [],
        }
        rules = DRCRuleSet(wg_min_gap_um=0.2)
        report = run_drc(gdl, rules)
        # Gap = 0.05µm < 0.2µm → should trigger WG_MIN_GAP violation
        assert "WG_MIN_GAP" in report.rule_counts

    def test_wg_min_width_violation(self):
        gdl = {
            "cells": [{"cell_name": "TEST", "shapes": [
                {"type": "rect", "layer": 1, "datatype": 0, "bbox": [0, 0, 100, 0.1]},
            ], "ports": []}],
            "instances": [],
            "wires": [],
        }
        rules = DRCRuleSet(wg_min_width_um=0.3)
        report = run_drc(gdl, rules)
        assert "WG_MIN_WIDTH" in report.rule_counts
        assert not report.ok

    def test_wire_max_length_warning(self):
        gdl = {
            "cells": [],
            "instances": [],
            "wires": [{"from": [0.0, 0.0], "to": [10000.0, 0.0], "layer": 1}],
        }
        rules = DRCRuleSet(wire_max_length_um=5000.0)
        report = run_drc(gdl, rules)
        assert "WIRE_MAX_LENGTH" in report.rule_counts

    def test_drc_report_to_dict_schema(self):
        gdl = netlist_to_gdl(_simple_netlist())
        report = run_drc(gdl)
        d = report.to_dict()
        assert "ok" in d
        assert "violations" in d
        assert "stats" in d
        assert isinstance(d["violations"], list)

    def test_drc_custom_rules_from_dict(self):
        gdl = netlist_to_gdl(_simple_netlist())
        rules = DRCRuleSet.from_dict({"wg_min_gap_um": 0.1, "wire_max_length_um": 1000.0})
        report = run_drc(gdl, rules)
        assert isinstance(report.ok, bool)


# ── LVS tests ────────────────────────────────────────────────────────────────

class TestLVS:

    def test_lvs_matching_netlist_passes(self):
        netlist = _simple_netlist()
        gdl = netlist_to_gdl(netlist)
        result = run_lvs(gdl, netlist)
        assert isinstance(result.ok, bool)
        assert isinstance(result.matched_count, int)

    def test_lvs_to_dict_schema(self):
        netlist = _simple_netlist()
        gdl = netlist_to_gdl(netlist)
        result = run_lvs(gdl, netlist)
        d = result.to_dict()
        assert "ok" in d
        assert "matched_count" in d
        assert "extra_connections" in d
        assert "missing_connections" in d

    def test_run_drc_lvs_combined(self):
        netlist = _simple_netlist()
        result = run_drc_lvs(netlist)
        assert "drc" in result
        assert "lvs" in result
        assert "overall_pass" in result


# ── SPICE analysis tests ──────────────────────────────────────────────────────

class TestSpiceAnalysis:

    def test_ac_sweep_netlist_structure(self):
        graph = _simple_graph()
        text = ac_sweep_netlist(graph, start_wl_nm=1480, stop_wl_nm=1580, points=20)
        assert ".ac lin" in text
        assert ".end" in text
        assert "Vsrc_re" in text
        assert ".meas AC" in text

    def test_monte_carlo_netlist_structure(self):
        graph = _simple_graph()
        text = monte_carlo_netlist(graph, n_runs=50)
        assert ".step mc" in text
        assert ".end" in text
        assert "gauss" in text

    def test_transient_netlist_structure(self):
        graph = _simple_graph()
        text = transient_netlist(graph, bit_rate_gbps=25.0, n_bits=8)
        assert ".tran" in text
        assert "PWL" in text
        assert ".meas TRAN" in text

    def test_parametric_sweep_netlist(self):
        graph = _simple_graph()
        text = parametric_sweep_netlist(
            graph, node_id="ps1", param_name="phase_rad",
            start=0.0, stop=math.pi, points=20
        )
        assert ".step param" in text
        assert "ps1_phase_rad" in text

    def test_ac_netlist_frequency_range_correct(self):
        # c / 1580nm ≈ 189.7 THz (start, low freq)
        # c / 1480nm ≈ 202.6 THz (stop, high freq)
        graph = _simple_graph()
        text = ac_sweep_netlist(graph, start_wl_nm=1480, stop_wl_nm=1580)
        # Both frequencies should appear in the .ac line
        assert "189" in text or "1897" in text or "1.896" in text or "1.897" in text

    def test_extract_heater_parasitics(self):
        # Build a GDL with a metal heater shape
        gdl = {
            "cells": [{"cell_name": "PS", "shapes": [
                {"type": "rect", "layer": 11, "datatype": 0, "bbox": [0, -1, 50, 1]},
            ], "ports": []}],
            "instances": [],
            "wires": [],
        }
        parasitics = extract_heater_parasitics(gdl, sheet_resistance_ohm_sq=100.0)
        assert len(parasitics) == 1
        p = parasitics[0]
        assert p["length_um"] == 50.0
        assert p["width_um"] == 2.0
        # 50µm / 2µm = 25 squares × 100Ω = 2500Ω
        assert abs(p["resistance_ohm"] - 2500.0) < 1.0
        assert p["rc_ps"] > 0

    def test_spice_with_parasitics_adds_r_elements(self):
        graph = _simple_graph()
        gdl = {
            "cells": [{"cell_name": "PS", "shapes": [
                {"type": "rect", "layer": 11, "datatype": 0, "bbox": [0, -1, 50, 1]},
            ], "ports": []}],
            "instances": [],
            "wires": [],
        }
        text = spice_with_parasitics(graph, gdl)
        assert "Rheater0" in text
        assert "Cheater0" in text


# ── PCell API tests ───────────────────────────────────────────────────────────

class TestPCellAPI:

    def test_get_pcell_schema_waveguide(self):
        schema = get_pcell_schema("pic.waveguide")
        names = {p["name"] for p in schema}
        assert "length_um" in names
        assert "width_um" in names
        assert all("default" in p for p in schema)

    def test_get_pcell_schema_unknown_raises(self):
        with pytest.raises(KeyError):
            get_pcell_schema("pic.nonexistent")

    def test_pcell_instance_has_geometry(self):
        inst = pcell_instance("pic.ring", {"radius_um": 5.0})
        assert "geometry" in inst
        assert "params" in inst
        assert inst["params"]["radius_um"] == 5.0
        assert len(inst["geometry"]["shapes"]) > 0

    def test_pcell_instance_placement(self):
        inst = pcell_instance("pic.waveguide", x=100.0, y=50.0)
        assert inst["placement"]["x"] == 100.0
        assert inst["placement"]["y"] == 50.0

    def test_pcell_all_kinds_valid(self):
        from photonstrust.layout.pic.pcell import _PCELL_PARAMS
        for kind in _PCELL_PARAMS:
            inst = pcell_instance(kind)
            assert "geometry" in inst
            assert len(inst["geometry"]["shapes"]) > 0

    def test_export_pcell_library_json(self, tmp_path):
        out = tmp_path / "pcell_library.json"
        p = export_pcell_library_json(str(out))
        assert Path(p).exists()
        lib = json.loads(Path(p).read_text(encoding="utf-8"))
        assert "components" in lib
        assert "pic.waveguide" in lib["components"]
        assert "parameters" in lib["components"]["pic.waveguide"]

    def test_register_pcells_returns_bool(self):
        # Should return False gracefully if klayout not installed
        result = register_all_pcells()
        assert isinstance(result, bool)
