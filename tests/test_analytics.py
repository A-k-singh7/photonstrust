"""Tests for Feature 13: Advanced Analytics & Executive Reporting."""

from __future__ import annotations

import json

from photonstrust.analytics.benchmark import benchmark_vendors
from photonstrust.analytics.kpis import compute_link_kpis
from photonstrust.analytics.report import generate_analytics_report
from photonstrust.analytics.roi import compute_roi
from photonstrust.analytics.types import AnalyticsReport


# ---------------------------------------------------------------------------
# KPI tests
# ---------------------------------------------------------------------------

def test_link_kpi_computation():
    """KPIs are computed from sim and cost results."""
    sim_result = {
        "key_rate": 5000,
        "entanglement_rate_hz": 1e6,
        "qber": 0.03,
        "loss_db": 10.0,
    }
    cost_result = {"cost_per_key_bit_usd": 5e-7}

    kpis = compute_link_kpis("link-1", sim_result, cost_result)

    assert len(kpis) == 4
    by_id = {k.kpi_id: k for k in kpis}
    assert by_id["key_rate_efficiency"].value == round(5000 / 1e6, 6)
    assert by_id["cost_per_key_bit"].value == 5e-7
    assert by_id["qber_margin"].value == round(1 - 0.03 / 0.11, 6)
    assert by_id["link_loss_db"].value == 10.0


def test_kpi_status_on_target():
    """Value meeting or exceeding target yields on_target."""
    sim_result = {
        "key_rate": 600_000,
        "entanglement_rate_hz": 1e6,
        "qber": 0.01,
        "loss_db": 5.0,
    }
    cost_result = {"cost_per_key_bit_usd": 1e-7}

    kpis = compute_link_kpis("link-2", sim_result, cost_result)
    by_id = {k.kpi_id: k for k in kpis}

    assert by_id["key_rate_efficiency"].status == "on_target"
    assert by_id["cost_per_key_bit"].status == "on_target"
    assert by_id["qber_margin"].status == "on_target"
    assert by_id["link_loss_db"].status == "on_target"


def test_kpi_status_below_target():
    """Value below target (higher-is-better) yields below_target."""
    sim_result = {
        "key_rate": 100,
        "entanglement_rate_hz": 1e6,
        "qber": 0.08,
        "loss_db": 5.0,
    }
    cost_result = {"cost_per_key_bit_usd": 1e-7}

    kpis = compute_link_kpis("link-3", sim_result, cost_result)
    by_id = {k.kpi_id: k for k in kpis}

    # key_rate_efficiency = 100/1e6 = 0.0001, target 0.5 -> below_target
    assert by_id["key_rate_efficiency"].status == "below_target"
    # qber_margin = 1 - 0.08/0.11 ~ 0.2727, target 0.5 -> below_target
    assert by_id["qber_margin"].status == "below_target"


# ---------------------------------------------------------------------------
# ROI tests
# ---------------------------------------------------------------------------

def test_roi_positive_npv():
    """High key rate and low cost yield positive NPV."""
    roi = compute_roi(
        deployment_id="dep-1",
        total_investment_usd=100_000,
        annual_key_rate_bps=10_000,
        key_value_per_bit_usd=1e-6,
    )
    assert roi.net_present_value_usd > 0


def test_roi_payback_period():
    """Profitable deployment has payback within projection window."""
    roi = compute_roi(
        deployment_id="dep-2",
        total_investment_usd=100_000,
        annual_key_rate_bps=10_000,
        key_value_per_bit_usd=1e-6,
        projection_years=10,
    )
    assert roi.payback_period_years < 10


def test_roi_irr_positive():
    """Profitable scenario yields positive IRR."""
    roi = compute_roi(
        deployment_id="dep-3",
        total_investment_usd=100_000,
        annual_key_rate_bps=10_000,
        key_value_per_bit_usd=1e-6,
    )
    assert roi.internal_rate_of_return > 0


# ---------------------------------------------------------------------------
# Benchmark test
# ---------------------------------------------------------------------------

def test_benchmark_groups_by_vendor():
    """Four components from two vendors produce two benchmarks."""
    components = [
        {"vendor": "AlphaQ", "component_id": "a1", "params": {"pde": 0.90}},
        {"vendor": "AlphaQ", "component_id": "a2", "params": {"pde": 0.88}},
        {"vendor": "BetaPhoton", "component_id": "b1", "params": {"pde": 0.80}},
        {"vendor": "BetaPhoton", "component_id": "b2", "params": {"pde": 0.82}},
    ]

    benchmarks = benchmark_vendors(components, category="detector")

    assert len(benchmarks) == 2
    vendors = {b.vendor for b in benchmarks}
    assert vendors == {"AlphaQ", "BetaPhoton"}
    for b in benchmarks:
        assert b.sample_size == 2
        assert len(b.components_tested) == 2


# ---------------------------------------------------------------------------
# Report serialisation test
# ---------------------------------------------------------------------------

def test_report_serialization():
    """AnalyticsReport.as_dict() produces a JSON-serialisable dict."""
    report = generate_analytics_report(
        entity_type="link",
        entity_id="link-serial",
        sim_result={
            "key_rate": 5000,
            "entanglement_rate_hz": 1e6,
            "qber": 0.03,
            "loss_db": 10.0,
        },
        cost_result={"cost_per_key_bit_usd": 5e-7},
    )

    d = report.as_dict()
    # Must be JSON-serialisable
    serialised = json.dumps(d)
    assert isinstance(serialised, str)
    assert "report_id" in d
    assert "kpi_snapshot" in d
