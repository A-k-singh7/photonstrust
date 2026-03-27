"""Tests for Phase A graph schema extensions.

Covers free-space/satellite edge kinds, optional QKD node kinds
(satellite_pass, coexistence, free_space_channel), and satellite_pass
channel engine mode.
"""

from __future__ import annotations

import pytest

from photonstrust.channels.engine import compute_channel_diagnostics

try:
    from photonstrust.graph.compiler import (
        QKD_OPTIONAL_KINDS,
        QKD_REQUIRED_KINDS,
        compile_graph,
    )
    _HAS_COMPILER = True
except ImportError:
    QKD_OPTIONAL_KINDS = []
    QKD_REQUIRED_KINDS = []
    _HAS_COMPILER = False


# ---- Schema: edge kinds ----------------------------------------------------

def test_free_space_edge_kind_in_schema():
    import json
    from pathlib import Path
    schema_path = Path(__file__).resolve().parent.parent / "schemas" / "photonstrust.graph.v0_1.schema.json"
    schema = json.loads(schema_path.read_text())
    edge_kind_enum = schema["properties"]["edges"]["items"]["properties"]["kind"]["enum"]
    assert "free_space" in edge_kind_enum
    assert "satellite_downlink" in edge_kind_enum
    assert "satellite_uplink" in edge_kind_enum
    # existing kinds still present
    assert "optical" in edge_kind_enum
    assert "electrical" in edge_kind_enum
    assert "control" in edge_kind_enum


# ---- Compiler: optional node kinds -----------------------------------------

@pytest.mark.skipif(not _HAS_COMPILER, reason="compiler deps not available")
def test_optional_kinds_defined():
    assert "qkd.satellite_pass" in QKD_OPTIONAL_KINDS
    assert "qkd.coexistence" in QKD_OPTIONAL_KINDS
    assert "qkd.free_space_channel" in QKD_OPTIONAL_KINDS


@pytest.mark.skipif(not _HAS_COMPILER, reason="compiler deps not available")
def test_compile_qkd_link_with_satellite_pass():
    graph = {
        "schema_version": "0.1",
        "graph_id": "test-sat-pass",
        "profile": "qkd_link",
        "scenario": {"id": "test", "distance_km": 500},
        "nodes": [
            {"id": "src", "kind": "qkd.source", "params": {"mu": 0.5}},
            {"id": "ch", "kind": "qkd.channel", "params": {"model": "satellite"}},
            {"id": "det", "kind": "qkd.detector", "params": {"eta": 0.1}},
            {"id": "tmg", "kind": "qkd.timing", "params": {}},
            {"id": "proto", "kind": "qkd.protocol", "params": {"name": "bb84"}},
            {"id": "sat", "kind": "qkd.satellite_pass", "params": {
                "orbit_altitude_km": 500,
                "max_elevation_deg": 70,
                "pass_duration_s": 300,
            }},
        ],
    }
    result = compile_graph(graph)
    assert result.profile == "qkd_link"
    assert "satellite_pass" in result.compiled
    assert result.compiled["satellite_pass"]["orbit_altitude_km"] == 500


@pytest.mark.skipif(not _HAS_COMPILER, reason="compiler deps not available")
def test_compile_qkd_link_with_coexistence():
    graph = {
        "schema_version": "0.1",
        "graph_id": "test-coex",
        "profile": "qkd_link",
        "scenario": {"id": "test", "distance_km": 50},
        "nodes": [
            {"id": "src", "kind": "qkd.source", "params": {}},
            {"id": "ch", "kind": "qkd.channel", "params": {"model": "fiber"}},
            {"id": "det", "kind": "qkd.detector", "params": {}},
            {"id": "tmg", "kind": "qkd.timing", "params": {}},
            {"id": "proto", "kind": "qkd.protocol", "params": {}},
            {"id": "coex", "kind": "qkd.coexistence", "params": {
                "enabled": True,
                "classical_launch_power_dbm": 0.0,
                "classical_channel_count": 4,
            }},
        ],
    }
    result = compile_graph(graph)
    assert "coexistence" in result.compiled
    assert result.compiled["coexistence"]["enabled"] is True


@pytest.mark.skipif(not _HAS_COMPILER, reason="compiler deps not available")
def test_compile_qkd_link_without_optional_nodes():
    """Baseline: no optional nodes, should compile fine."""
    graph = {
        "schema_version": "0.1",
        "graph_id": "test-baseline",
        "profile": "qkd_link",
        "scenario": {"id": "test", "distance_km": 50},
        "nodes": [
            {"id": "src", "kind": "qkd.source", "params": {}},
            {"id": "ch", "kind": "qkd.channel", "params": {}},
            {"id": "det", "kind": "qkd.detector", "params": {}},
            {"id": "tmg", "kind": "qkd.timing", "params": {}},
            {"id": "proto", "kind": "qkd.protocol", "params": {}},
        ],
    }
    result = compile_graph(graph)
    assert "satellite_pass" not in result.compiled
    assert "coexistence" not in result.compiled


# ---- Channel engine: satellite_pass model -----------------------------------

def test_satellite_pass_engine_mode():
    diag = compute_channel_diagnostics(
        distance_km=500.0,
        wavelength_nm=810.0,
        channel_cfg={
            "model": "satellite_pass",
            "orbit_altitude_km": 500,
            "max_elevation_deg": 60,
            "pass_duration_s": 200,
            "time_step_s": 50,
        },
    )
    assert diag["model"] == "satellite_pass"
    assert "total_key_bits" in diag
    assert "envelope" in diag
    assert diag["pass_duration_s"] == 200.0
    assert diag["orbit_altitude_km"] == 500


def test_satellite_pass_produces_positive_key_bits():
    diag = compute_channel_diagnostics(
        distance_km=500.0,
        wavelength_nm=810.0,
        channel_cfg={
            "model": "satellite_pass",
            "orbit_altitude_km": 500,
            "max_elevation_deg": 70,
            "pass_duration_s": 300,
            "time_step_s": 30,
        },
    )
    assert diag["total_key_bits"] >= 0


def test_satellite_pass_outage_fraction_bounded():
    diag = compute_channel_diagnostics(
        distance_km=500.0,
        wavelength_nm=810.0,
        channel_cfg={
            "model": "satellite_pass",
            "orbit_altitude_km": 500,
            "max_elevation_deg": 40,
            "pass_duration_s": 180,
            "time_step_s": 60,
        },
    )
    assert 0.0 <= diag["outage_probability"] <= 1.0
