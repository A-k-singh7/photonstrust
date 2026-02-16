from __future__ import annotations

import copy

import pytest

from photonstrust.channels.coexistence import compute_raman_counts_cps


def _coexistence_cfg() -> dict:
    return {
        "enabled": True,
        "classical_launch_power_dbm": 0.0,
        "classical_channel_count": 1,
        "direction": "co",
        "filter_bandwidth_nm": 0.2,
        "raman_coeff_cps_per_km_per_mw_per_nm": 1200.0,
        "raman_spectral_factor": 1.0,
    }


def test_raman_effective_length_reduces_to_linear_when_alpha_zero() -> None:
    co = _coexistence_cfg()
    co["raman_model"] = "effective_length"

    c10 = compute_raman_counts_cps(10.0, co, fiber_loss_db_per_km=0.0)
    c20 = compute_raman_counts_cps(20.0, co, fiber_loss_db_per_km=0.0)

    assert c10 >= 0.0
    assert c20 >= 0.0
    assert c20 == pytest.approx(2.0 * c10, rel=0.0, abs=1e-12)


def test_raman_effective_length_is_sublinear_with_distance_under_loss() -> None:
    co = _coexistence_cfg()
    co["raman_model"] = "effective_length"
    co["direction"] = "counter"

    c50 = compute_raman_counts_cps(50.0, co, fiber_loss_db_per_km=0.2)
    c100 = compute_raman_counts_cps(100.0, co, fiber_loss_db_per_km=0.2)

    assert c50 > 0.0
    assert c100 > 0.0
    assert c100 < 2.0 * c50


def test_raman_directionality_changes_counts() -> None:
    base = _coexistence_cfg()
    base["raman_model"] = "effective_length"

    co = copy.deepcopy(base)
    co["direction"] = "co"
    counter = copy.deepcopy(base)
    counter["direction"] = "counter"

    c_co = compute_raman_counts_cps(25.0, co, fiber_loss_db_per_km=0.2)
    c_counter = compute_raman_counts_cps(25.0, counter, fiber_loss_db_per_km=0.2)

    assert c_co > 0.0
    assert c_counter > 0.0
    assert c_co != pytest.approx(c_counter, rel=0.0, abs=0.0)
