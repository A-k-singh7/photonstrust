from __future__ import annotations

import jax
jax.config.update("jax_enable_x64", True)

from photonstrust.chipverify.orchestrator import run_chipverify
from photonstrust.chipverify.gates import default_gates, evaluate_gates, overall_status
from photonstrust.chipverify.metrics import compute_pic_metrics, compute_insertion_loss_db
from photonstrust.chipverify.types import ChipVerifyGate, ChipVerifyMetrics, ChipVerifyReport


# ---------------------------------------------------------------------------
# Test fixture: a simple 3-component PIC chain
# The compiler expects nodes and edges at top level, plus a circuit dict.
# ---------------------------------------------------------------------------
SIMPLE_PIC_GRAPH = {
    "schema_version": "0.1",
    "graph_id": "test_chipverify_ring",
    "profile": "pic_circuit",
    "circuit": {
        "id": "test_chipverify_ring",
    },
    "nodes": [
        {"id": "gc_in", "kind": "pic.grating_coupler", "params": {"insertion_loss_db": 3.5}},
        {"id": "wg1", "kind": "pic.waveguide", "params": {"length_um": 500, "loss_db_per_cm": 2.0}},
        {"id": "gc_out", "kind": "pic.grating_coupler", "params": {"insertion_loss_db": 3.5}},
    ],
    "edges": [
        {"from": "gc_in", "to": "wg1"},
        {"from": "wg1", "to": "gc_out"},
    ],
}


def test_orchestrator_full_pipeline():
    """Simple graph produces a ChipVerifyReport with all required fields."""
    report = run_chipverify(graph=SIMPLE_PIC_GRAPH)

    assert isinstance(report, ChipVerifyReport)
    assert report.report_id
    assert report.netlist_hash
    assert report.timestamp
    assert isinstance(report.simulation_results, dict)
    assert isinstance(report.drc_results, dict)
    assert isinstance(report.performance_metrics, ChipVerifyMetrics)
    assert isinstance(report.gates, list)
    assert report.overall_status in ("pass", "fail", "conditional")
    assert isinstance(report.warnings, list)


def test_report_serialization():
    """as_dict() produces a valid dict with no dataclass instances."""
    report = run_chipverify(graph=SIMPLE_PIC_GRAPH)
    d = report.as_dict()

    assert isinstance(d, dict)
    assert isinstance(d["performance_metrics"], dict)
    assert isinstance(d["gates"], list)
    for g in d["gates"]:
        assert isinstance(g, dict)
    assert isinstance(d["warnings"], list)
    assert d["report_id"] == report.report_id
    assert d["overall_status"] == report.overall_status


def test_insertion_loss_positive():
    """total_insertion_loss_db > 0 for a multi-component circuit."""
    report = run_chipverify(graph=SIMPLE_PIC_GRAPH)
    assert report.performance_metrics.total_insertion_loss_db > 0


def test_gate_pass_below_threshold():
    """IL around 8 dB, threshold=20 dB -> gate passes."""
    report = run_chipverify(
        graph=SIMPLE_PIC_GRAPH,
        gates=[
            {
                "name": "max_insertion_loss",
                "metric": "total_insertion_loss_db",
                "threshold": 20.0,
                "comparator": "lt",
            },
        ],
    )
    gate = report.gates[0]
    assert gate.status == "pass"
    assert gate.actual < 20.0


def test_gate_fail_above_threshold():
    """Custom gate with threshold=5 dB, IL around 8 dB -> fails."""
    report = run_chipverify(
        graph=SIMPLE_PIC_GRAPH,
        gates=[
            {
                "name": "tight_insertion_loss",
                "metric": "total_insertion_loss_db",
                "threshold": 5.0,
                "comparator": "lt",
            },
        ],
    )
    gate = report.gates[0]
    assert gate.status == "fail"
    assert gate.actual >= 5.0


def test_gate_custom_config():
    """Custom gates completely replace the defaults."""
    custom = [
        {
            "name": "my_gate",
            "metric": "component_count",
            "threshold": 0,
            "comparator": "gt",
        },
    ]
    report = run_chipverify(graph=SIMPLE_PIC_GRAPH, gates=custom)
    assert len(report.gates) == 1
    assert report.gates[0].name == "my_gate"


def test_overall_status_fail_any():
    """One failed gate makes overall status 'fail'."""
    gates_cfg = [
        {
            "name": "will_pass",
            "metric": "component_count",
            "threshold": 0,
            "comparator": "gt",
        },
        {
            "name": "will_fail",
            "metric": "total_insertion_loss_db",
            "threshold": 0.001,
            "comparator": "lt",
        },
    ]
    report = run_chipverify(graph=SIMPLE_PIC_GRAPH, gates=gates_cfg)
    assert report.overall_status == "fail"


def test_overall_status_pass_all():
    """All gates pass -> overall 'pass'."""
    gates_cfg = [
        {
            "name": "generous_loss",
            "metric": "total_insertion_loss_db",
            "threshold": 100.0,
            "comparator": "lt",
        },
        {
            "name": "has_components",
            "metric": "component_count",
            "threshold": 0,
            "comparator": "gt",
        },
    ]
    report = run_chipverify(graph=SIMPLE_PIC_GRAPH, gates=gates_cfg)
    assert report.overall_status == "pass"


def test_metrics_component_count():
    """component_count matches the number of graph nodes."""
    report = run_chipverify(graph=SIMPLE_PIC_GRAPH)
    assert report.performance_metrics.component_count == len(SIMPLE_PIC_GRAPH["nodes"])


def test_metrics_edge_count():
    """edge_count matches the number of graph edges."""
    report = run_chipverify(graph=SIMPLE_PIC_GRAPH)
    assert report.performance_metrics.edge_count == len(SIMPLE_PIC_GRAPH["edges"])


def test_default_gates_structure():
    """default_gates() returns a list of dicts with required keys."""
    dg = default_gates()
    assert isinstance(dg, list)
    assert len(dg) >= 1
    required_keys = {"name", "metric", "threshold", "comparator"}
    for g in dg:
        assert isinstance(g, dict)
        assert required_keys.issubset(g.keys())


def test_gate_comparators():
    """The 'gt' comparator works correctly."""
    metrics = ChipVerifyMetrics(
        total_insertion_loss_db=8.0,
        bandwidth_3db_nm=None,
        crosstalk_isolation_db=None,
        component_count=5,
        edge_count=4,
    )
    gates_cfg = [
        {
            "name": "gt_pass",
            "metric": "component_count",
            "threshold": 3,
            "comparator": "gt",
        },
        {
            "name": "gt_fail",
            "metric": "component_count",
            "threshold": 10,
            "comparator": "gt",
        },
    ]
    result = evaluate_gates(metrics, gates_cfg)
    assert result[0].status == "pass"
    assert result[1].status == "fail"
