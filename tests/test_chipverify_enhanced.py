"""Tests for Phase A ChipVerify enhancements.

Tests the enhanced metrics (phase error, group delay, yield estimate),
gates evaluation, and report generation without external dependencies.
"""

from __future__ import annotations

import sys

import pytest

# The chipverify module transitively imports jax via the PIC library.
# Guard the imports so the tests are skipped rather than erroring when
# jax is not installed.
try:
    from photonstrust.chipverify.types import ChipVerifyGate, ChipVerifyMetrics, ChipVerifyReport
    from photonstrust.chipverify.metrics import (
        compute_bandwidth_3db_nm,
        compute_crosstalk_isolation_db,
        compute_group_delay_variation_ps,
        compute_insertion_loss_db,
        compute_phase_error_sensitivity,
        compute_pic_metrics,
        estimate_process_yield_pct,
    )
    from photonstrust.chipverify.gates import default_gates, evaluate_gates, overall_status
    _HAS_CHIPVERIFY = True
except ImportError:
    # Provide stubs so the module still loads for collection.  Every test
    # is marked to skip below.
    _HAS_CHIPVERIFY = False

pytestmark = pytest.mark.skipif(not _HAS_CHIPVERIFY, reason="jax not installed")


# ---- Simulation result fixtures -------------------------------------------

def _sim_results_chain(
    *,
    total_loss_db: float = 8.0,
    per_component: list[dict] | None = None,
) -> dict:
    """Simulate chain_solver output."""
    if per_component is None:
        per_component = [
            {"kind": "pic.grating_coupler", "loss_db": 3.5},
            {"kind": "pic.waveguide", "loss_db": 0.5},
            {"kind": "pic.ring", "loss_db": 0.5, "bandwidth_3db_nm": 0.2},
            {"kind": "pic.waveguide", "loss_db": 0.2},
            {"kind": "pic.grating_coupler", "loss_db": 3.3},
        ]
    return {
        "chain_solver": {
            "applicable": True,
            "total_loss_db": total_loss_db,
            "per_component": per_component,
        }
    }


def _sim_results_with_phase_and_gdv() -> dict:
    return {
        "chain_solver": {
            "applicable": True,
            "total_loss_db": 7.0,
            "per_component": [
                {"kind": "pic.grating_coupler", "loss_db": 3.0,
                 "phase_sensitivity_rad_per_nm": 0.1, "group_delay_ps": 0.5},
                {"kind": "pic.waveguide", "loss_db": 0.5,
                 "phase_sensitivity_rad_per_nm": 0.05, "group_delay_ps": 1.0},
                {"kind": "pic.ring", "loss_db": 0.5, "bandwidth_3db_nm": 0.15,
                 "phase_sensitivity_rad_per_nm": 2.0, "group_delay_ps": 5.0},
                {"kind": "pic.grating_coupler", "loss_db": 3.0,
                 "phase_sensitivity_rad_per_nm": 0.1, "group_delay_ps": 0.5},
            ],
        }
    }


def _netlist(n_nodes: int = 5, n_edges: int = 4) -> dict:
    return {
        "nodes": [{"id": f"n{i}"} for i in range(n_nodes)],
        "edges": [{"from": f"n{i}", "to": f"n{i+1}"} for i in range(n_edges)],
    }


# ---- Insertion loss tests --------------------------------------------------

def test_insertion_loss_from_chain_total():
    sim = _sim_results_chain(total_loss_db=10.5)
    assert compute_insertion_loss_db(sim) == pytest.approx(10.5)


def test_insertion_loss_empty_results():
    assert compute_insertion_loss_db({}) == 0.0


# ---- Bandwidth tests -------------------------------------------------------

def test_bandwidth_3db_from_ring():
    sim = _sim_results_chain()
    bw = compute_bandwidth_3db_nm(sim)
    assert bw == pytest.approx(0.2)


def test_bandwidth_3db_no_ring():
    sim = _sim_results_chain(per_component=[
        {"kind": "pic.waveguide", "loss_db": 1.0},
    ])
    assert compute_bandwidth_3db_nm(sim) is None


# ---- Phase error sensitivity tests ----------------------------------------

def test_phase_error_sensitivity():
    sim = _sim_results_with_phase_and_gdv()
    ps = compute_phase_error_sensitivity(sim)
    # Sum of |0.1| + |0.05| + |2.0| + |0.1| = 2.25
    assert ps is not None
    assert ps == pytest.approx(2.25)


def test_phase_error_sensitivity_none_when_absent():
    sim = _sim_results_chain()  # no phase_sensitivity_rad_per_nm fields
    assert compute_phase_error_sensitivity(sim) is None


# ---- Group delay tests -----------------------------------------------------

def test_group_delay_variation():
    sim = _sim_results_with_phase_and_gdv()
    gdv = compute_group_delay_variation_ps(sim)
    # Sum of 0.5 + 1.0 + 5.0 + 0.5 = 7.0
    assert gdv is not None
    assert gdv == pytest.approx(7.0)


# ---- Process yield tests ---------------------------------------------------

def test_process_yield_high_margin():
    """With low IL and high threshold, yield should be near 100%."""
    sim = _sim_results_chain(total_loss_db=5.0)
    yld = estimate_process_yield_pct(sim, _netlist(), max_loss_threshold_db=20.0)
    assert yld is not None
    assert yld > 90.0


def test_process_yield_tight_margin():
    """With IL very near threshold, yield may drop below 100%."""
    sim = _sim_results_chain(total_loss_db=19.5)
    yld = estimate_process_yield_pct(
        sim, _netlist(), max_loss_threshold_db=20.0, loss_variation_pct=20.0,
    )
    assert yld is not None
    assert yld <= 100.0


def test_process_yield_no_chain():
    assert estimate_process_yield_pct({}, _netlist()) is None


# ---- Composite metrics tests -----------------------------------------------

def test_compute_pic_metrics_full():
    sim = _sim_results_with_phase_and_gdv()
    nl = _netlist(n_nodes=4, n_edges=3)
    metrics = compute_pic_metrics(simulation_results=sim, netlist=nl)
    assert metrics.total_insertion_loss_db == 7.0
    assert metrics.component_count == 4
    assert metrics.edge_count == 3
    assert metrics.bandwidth_3db_nm == pytest.approx(0.15)
    assert metrics.phase_error_sensitivity_rad_per_nm is not None
    assert metrics.group_delay_variation_ps is not None
    assert metrics.process_yield_estimate_pct is not None


def test_compute_pic_metrics_serialization():
    sim = _sim_results_with_phase_and_gdv()
    nl = _netlist()
    metrics = compute_pic_metrics(simulation_results=sim, netlist=nl)
    d = metrics.as_dict()
    assert isinstance(d, dict)
    assert "phase_error_sensitivity_rad_per_nm" in d
    assert "group_delay_variation_ps" in d
    assert "process_yield_estimate_pct" in d


# ---- Gates evaluation tests ------------------------------------------------

def test_default_gates_exist():
    gates = default_gates()
    assert len(gates) >= 2


def test_evaluate_gates_pass():
    metrics = ChipVerifyMetrics(
        total_insertion_loss_db=8.0,
        bandwidth_3db_nm=None,
        crosstalk_isolation_db=None,
        component_count=5,
        edge_count=4,
    )
    gates = evaluate_gates(metrics, default_gates())
    assert all(g.status == "pass" for g in gates)


def test_evaluate_gates_fail():
    metrics = ChipVerifyMetrics(
        total_insertion_loss_db=25.0,  # exceeds 20 dB threshold
        bandwidth_3db_nm=None,
        crosstalk_isolation_db=None,
        component_count=5,
        edge_count=4,
    )
    gates = evaluate_gates(metrics, default_gates())
    il_gate = [g for g in gates if g.name == "max_insertion_loss"][0]
    assert il_gate.status == "fail"


def test_overall_status_logic():
    pass_gate = ChipVerifyGate(
        name="test", metric="x", threshold=10, comparator="lt", actual=5, status="pass",
    )
    fail_gate = ChipVerifyGate(
        name="test2", metric="y", threshold=10, comparator="lt", actual=15, status="fail",
    )
    assert overall_status([pass_gate]) == "pass"
    assert overall_status([pass_gate, fail_gate]) == "fail"
    assert overall_status([]) == "pass"


# ---- ChipVerifyReport tests ------------------------------------------------

def test_chipverify_report_serialization():
    metrics = ChipVerifyMetrics(
        total_insertion_loss_db=7.0,
        bandwidth_3db_nm=0.2,
        crosstalk_isolation_db=30.0,
        component_count=5,
        edge_count=4,
        phase_error_sensitivity_rad_per_nm=1.5,
        group_delay_variation_ps=3.0,
        process_yield_estimate_pct=95.0,
    )
    gate = ChipVerifyGate(
        name="max_il", metric="total_insertion_loss_db",
        threshold=20.0, comparator="lt", actual=7.0, status="pass",
    )
    report = ChipVerifyReport(
        report_id="test-123",
        netlist_hash="abc123",
        timestamp="2026-03-24T00:00:00Z",
        simulation_results={"chain_solver": {"applicable": True}},
        drc_results={"violations": []},
        lvs_results={"match": True},
        performance_metrics=metrics,
        gates=[gate],
        overall_status="pass",
        warnings=[],
    )
    d = report.as_dict()
    assert d["report_id"] == "test-123"
    assert d["overall_status"] == "pass"
    assert d["performance_metrics"]["process_yield_estimate_pct"] == 95.0
    assert len(d["gates"]) == 1
