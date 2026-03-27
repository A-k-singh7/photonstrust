"""Tests for Phase A benchmark scenarios and acceptance gates.

Validates that each benchmark scenario runs to completion, produces
gate evaluations, and that the default parameters pass all acceptance gates.
"""

from __future__ import annotations

import sys

import pytest

# Import directly from the module file, not the package __init__,
# to avoid transitive jax dependency via config.py.
try:
    from photonstrust.benchmarks.phase_a_scenarios import (
        AcceptanceGate,
        BenchmarkResult,
        _evaluate_gate,
        run_all_benchmarks,
        run_metro_fiber_bb84,
        run_pic_ring_resonator,
        run_satellite_downlink_bbm92,
    )
    _HAS_BENCHMARKS = True
except ImportError:
    _HAS_BENCHMARKS = False

pytestmark = pytest.mark.skipif(not _HAS_BENCHMARKS, reason="benchmark deps not available")


# ---- Metro Fiber BB84 tests ------------------------------------------------

def test_metro_fiber_bb84_passes():
    result = run_metro_fiber_bb84(distance_km=50.0, seed=42)
    assert result.scenario_id == "phase_a.metro_fiber_bb84"
    assert result.overall_status == "pass"
    assert len(result.gates) >= 4


def test_metro_fiber_bb84_gates_complete():
    result = run_metro_fiber_bb84(seed=42)
    gate_names = {g.name for g in result.gates}
    assert "max_total_loss" in gate_names
    assert "raman_below_threshold" in gate_names
    assert "connector_loss_budget" in gate_names
    assert "timing_budget_ok" in gate_names


def test_metro_fiber_bb84_serialization():
    result = run_metro_fiber_bb84(seed=42)
    d = result.as_dict()
    assert isinstance(d, dict)
    assert "gates" in d
    assert "diagnostics" in d
    assert d["scenario_id"] == "phase_a.metro_fiber_bb84"


def test_metro_fiber_bb84_long_distance_fails():
    """Very long metro link should exceed loss budget."""
    result = run_metro_fiber_bb84(distance_km=200.0, seed=42)
    loss_gate = [g for g in result.gates if g.name == "max_total_loss"][0]
    # At 200 km, total loss > 25 dB
    assert loss_gate.status == "fail"


def test_metro_fiber_bb84_diagnostics_present():
    result = run_metro_fiber_bb84(seed=42)
    assert "channel" in result.diagnostics
    assert "deployment" in result.diagnostics
    assert "connector_splice" in result.diagnostics
    assert "raman_budget" in result.diagnostics


# ---- Satellite Downlink BBM92 tests ----------------------------------------

def test_satellite_downlink_bbm92_passes():
    result = run_satellite_downlink_bbm92(seed=42)
    assert result.scenario_id == "phase_a.satellite_downlink_bbm92"
    assert result.overall_status == "pass"
    assert len(result.gates) >= 5


def test_satellite_downlink_gates_complete():
    result = run_satellite_downlink_bbm92(seed=42)
    gate_names = {g.name for g in result.gates}
    assert "fried_parameter_positive" in gate_names
    assert "fading_outage_bounded" in gate_names
    assert "pointing_efficiency_ok" in gate_names
    assert "background_below_limit" in gate_names
    assert "pass_generates_key" in gate_names


def test_satellite_downlink_serialization():
    result = run_satellite_downlink_bbm92(seed=42)
    d = result.as_dict()
    assert "hufnagel_valley" in d["diagnostics"]
    assert "fading" in d["diagnostics"]
    assert "pointing" in d["diagnostics"]
    assert "orbit_pass" in d["diagnostics"]


def test_satellite_downlink_diagnostics_physics():
    result = run_satellite_downlink_bbm92(seed=42)
    hv = result.diagnostics["hufnagel_valley"]
    assert hv["fried_parameter_m"] > 0
    assert hv["rytov_variance"] > 0
    assert hv["scintillation_index"] > 0


# ---- PIC Ring Resonator tests ----------------------------------------------

def test_pic_ring_resonator_completes():
    """May pass or skip depending on jax availability."""
    result = run_pic_ring_resonator(seed=42)
    assert result.scenario_id == "phase_a.pic_ring_resonator"
    assert result.overall_status in ("pass", "skip")


def test_pic_ring_serialization():
    result = run_pic_ring_resonator(seed=42)
    d = result.as_dict()
    assert isinstance(d, dict)
    assert "scenario_id" in d


# ---- Run-all tests ---------------------------------------------------------

def test_run_all_benchmarks():
    results = run_all_benchmarks(seed=42)
    assert len(results) == 3
    ids = {r.scenario_id for r in results}
    assert "phase_a.metro_fiber_bb84" in ids
    assert "phase_a.satellite_downlink_bbm92" in ids
    assert "phase_a.pic_ring_resonator" in ids


def test_run_all_deterministic():
    """Running twice with same seed should give identical results."""
    r1 = run_all_benchmarks(seed=42)
    r2 = run_all_benchmarks(seed=42)
    for a, b in zip(r1, r2):
        assert a.overall_status == b.overall_status
        for ga, gb in zip(a.gates, b.gates):
            assert ga.actual == gb.actual
            assert ga.status == gb.status


# ---- AcceptanceGate tests --------------------------------------------------

def test_gate_comparators():
    assert _evaluate_gate("t", "m", 10.0, "lt", 5.0).status == "pass"
    assert _evaluate_gate("t", "m", 10.0, "lt", 15.0).status == "fail"
    assert _evaluate_gate("t", "m", 10.0, "gt", 15.0).status == "pass"
    assert _evaluate_gate("t", "m", 10.0, "gt", 5.0).status == "fail"
    assert _evaluate_gate("t", "m", 10.0, "le", 10.0).status == "pass"
    assert _evaluate_gate("t", "m", 10.0, "ge", 10.0).status == "pass"
    assert _evaluate_gate("t", "m", 10.0, "eq", 10.0).status == "pass"
    assert _evaluate_gate("t", "m", 10.0, "eq", 10.5).status == "fail"
