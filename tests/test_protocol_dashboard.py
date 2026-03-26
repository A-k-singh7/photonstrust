"""Tests for protocol comparison dashboard."""
import pytest
from photonstrust.protocols.protocol_dashboard import (
    run_protocol_dashboard, DashboardResult, _plob_bound, _tgw_bound,
)

def test_dashboard_runs_all_protocols():
    result = run_protocol_dashboard()
    assert isinstance(result, DashboardResult)
    assert len(result.protocol_ids) >= 5
    assert len(result.rate_curves) == len(result.protocol_ids)

def test_dashboard_plob_bound_decreases():
    result = run_protocol_dashboard(distances_km=[0, 50, 100, 200])
    # PLOB bound should decrease with distance
    for i in range(len(result.plob_bound) - 1):
        assert result.plob_bound[i] >= result.plob_bound[i+1]

def test_plob_bound_at_zero():
    bound = _plob_bound(0.0)
    assert bound > 1e6  # very high at zero distance

def test_tgw_bound_positive():
    for d in [10, 50, 100]:
        assert _tgw_bound(d) > 0

def test_tgw_greater_than_plob():
    """TGW bound >= PLOB bound at all distances."""
    for d in [10, 50, 100, 200]:
        assert _tgw_bound(d) >= _plob_bound(d) - 1e-10

def test_winners_by_distance():
    result = run_protocol_dashboard(
        protocol_ids=["bb84", "tf_qkd"],
        distances_km=[50, 100, 300, 500],
    )
    assert len(result.winners_by_distance) == 4
    for d, winner in result.winners_by_distance.items():
        assert winner in ["bb84", "tf_qkd"]

def test_rate_curves_non_negative():
    result = run_protocol_dashboard(protocol_ids=["bb84", "cv_qkd"])
    for pid, rates in result.rate_curves.items():
        for r in rates:
            assert r >= 0
