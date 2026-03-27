from __future__ import annotations

import math

import pytest

from photonstrust.channels.fiber_deployment import (
    CombinedRamanBudget,
    ConnectorSpliceChain,
    PMDContribution,
    TemperatureDriftContribution,
    FWMNoiseContribution,
    EnhancedTimingBudget,
    FiberDeploymentDiagnostics,
    apply_visibility_floor,
    combined_raman_budget,
    compute_fiber_deployment_diagnostics,
    compute_fwm_counts_cps,
    connector_splice_chain,
    enhanced_timing_budget,
    pmd_dgd_ps,
    temperature_drift_residual_ps,
)


# ---- helpers ----

def _base_channel_cfg(**overrides: object) -> dict:
    cfg: dict = {
        "fiber_loss_db_per_km": 0.2,
        "dispersion_ps_per_km": 0.0,
    }
    cfg.update(overrides)
    return cfg


def _base_detector_cfg(**overrides: object) -> dict:
    cfg: dict = {
        "jitter_ps_fwhm": 50.0,
    }
    cfg.update(overrides)
    return cfg


def _base_timing_cfg(**overrides: object) -> dict:
    cfg: dict = {
        "sync_drift_ps_rms": 10.0,
    }
    cfg.update(overrides)
    return cfg


# ---- 1. test_visibility_floor_clamps_qber ----

def test_visibility_floor_clamps_qber() -> None:
    # V_floor=0.95, V_measured=0.90 -> V_eff=0.95
    assert apply_visibility_floor(0.90, 0.95) == pytest.approx(0.95)
    # V_measured=0.98 -> V_eff=0.98 (above floor)
    assert apply_visibility_floor(0.98, 0.95) == pytest.approx(0.98)


# ---- 2. test_visibility_floor_default_no_change ----

def test_visibility_floor_default_no_change() -> None:
    # V_floor=1.0 (default) does not raise V_measured=0.97 above 1.0
    result = apply_visibility_floor(0.97)
    assert result == pytest.approx(1.0)
    # Explicit floor=1.0
    result2 = apply_visibility_floor(0.97, 1.0)
    assert result2 == pytest.approx(1.0)


# ---- 3. test_pmd_increases_timing_budget ----

def test_pmd_increases_timing_budget() -> None:
    dgd = pmd_dgd_ps(100.0, 0.2)
    # 0.2 * sqrt(100) = 0.2 * 10 = 2.0 ps
    assert dgd == pytest.approx(2.0)

    # Baseline (no PMD)
    tb_base = enhanced_timing_budget(
        jitter_ps_fwhm=50.0,
        drift_ps_rms=10.0,
        dispersion_ps=0.0,
        pmd_dgd_ps_val=0.0,
        temperature_residual_ps=0.0,
    )
    # With PMD
    tb_pmd = enhanced_timing_budget(
        jitter_ps_fwhm=50.0,
        drift_ps_rms=10.0,
        dispersion_ps=0.0,
        pmd_dgd_ps_val=dgd,
        temperature_residual_ps=0.0,
    )
    assert tb_pmd.sigma_effective_ps > tb_base.sigma_effective_ps


# ---- 4. test_pmd_zero_unchanged ----

def test_pmd_zero_unchanged() -> None:
    dgd = pmd_dgd_ps(100.0, 0.0)
    assert dgd == 0.0

    tb_base = enhanced_timing_budget(
        jitter_ps_fwhm=50.0,
        drift_ps_rms=10.0,
        dispersion_ps=5.0,
    )
    tb_zero_pmd = enhanced_timing_budget(
        jitter_ps_fwhm=50.0,
        drift_ps_rms=10.0,
        dispersion_ps=5.0,
        pmd_dgd_ps_val=0.0,
    )
    assert tb_base.sigma_effective_ps == pytest.approx(tb_zero_pmd.sigma_effective_ps)


# ---- 5. test_fwm_adds_noise_dense_wdm ----

def test_fwm_adds_noise_dense_wdm() -> None:
    coex = {
        "fwm_enabled": True,
        "classical_channel_count": 8,
        "classical_launch_power_dbm": 0.0,
        "channel_spacing_ghz": 100.0,
        "filter_bandwidth_nm": 0.2,
    }
    counts = compute_fwm_counts_cps(50.0, coex, fiber_loss_db_per_km=0.2)
    assert counts > 0.0


# ---- 6. test_fwm_disabled_returns_zero ----

def test_fwm_disabled_returns_zero() -> None:
    coex = {
        "fwm_enabled": False,
        "classical_channel_count": 8,
        "classical_launch_power_dbm": 0.0,
        "channel_spacing_ghz": 100.0,
    }
    counts = compute_fwm_counts_cps(50.0, coex, fiber_loss_db_per_km=0.2)
    assert counts == 0.0

    # Also None coexistence returns zero
    assert compute_fwm_counts_cps(50.0, None) == 0.0


# ---- 7. test_temperature_drift_contribution ----

def test_temperature_drift_contribution() -> None:
    # 50 km, 10 degC fluctuation, sync_eff=0.99, drift_coeff=37
    # residual = 37 * 50 * 10 * (1 - 0.99) = 37 * 50 * 10 * 0.01 = 185
    residual = temperature_drift_residual_ps(
        distance_km=50.0,
        temperature_fluctuation_degC=10.0,
        drift_coeff_ps_per_km_per_degC=37.0,
        sync_tracking_efficiency=0.99,
    )
    assert residual == pytest.approx(185.0)


# ---- 8. test_temperature_drift_zero_fluctuation ----

def test_temperature_drift_zero_fluctuation() -> None:
    residual = temperature_drift_residual_ps(
        distance_km=50.0,
        temperature_fluctuation_degC=0.0,
    )
    assert residual == 0.0


# ---- 9. test_backward_compat_no_new_params ----

def test_backward_compat_no_new_params() -> None:
    """Empty/default config produces diagnostics with no PMD/FWM/temp contributions."""
    diag = compute_fiber_deployment_diagnostics(
        distance_km=50.0,
        channel_cfg=_base_channel_cfg(),
        detector_cfg=_base_detector_cfg(),
        timing_cfg=_base_timing_cfg(),
    )
    # No PMD, no temperature drift, no FWM
    assert diag.pmd is None
    assert diag.temperature_drift is None
    assert diag.fwm is None

    # Timing budget should match baseline (jitter + drift only)
    sigma_j = 50.0 / 2.355
    sigma_d = 10.0
    expected = math.sqrt(sigma_j ** 2 + sigma_d ** 2)
    assert diag.timing_budget.sigma_effective_ps == pytest.approx(expected, rel=1e-6)


# ---- 10. test_enhanced_timing_quadrature ----

def test_enhanced_timing_quadrature() -> None:
    tb = enhanced_timing_budget(
        jitter_ps_fwhm=100.0,
        drift_ps_rms=20.0,
        dispersion_ps=15.0,
        pmd_dgd_ps_val=5.0,
        temperature_residual_ps=3.0,
    )
    sigma_j = 100.0 / 2.355
    expected = math.sqrt(sigma_j ** 2 + 20.0 ** 2 + 15.0 ** 2 + 5.0 ** 2 + 3.0 ** 2)
    assert tb.sigma_effective_ps == pytest.approx(expected, rel=1e-9)


# ---- 11. test_diagnostics_serialization ----

def test_diagnostics_serialization() -> None:
    diag = compute_fiber_deployment_diagnostics(
        distance_km=80.0,
        channel_cfg=_base_channel_cfg(
            pmd_coeff_ps_per_sqrt_km=0.1,
            temperature_fluctuation_degC=5.0,
            coexistence={
                "fwm_enabled": True,
                "classical_channel_count": 4,
                "classical_launch_power_dbm": 0.0,
                "channel_spacing_ghz": 100.0,
                "filter_bandwidth_nm": 0.2,
            },
        ),
        detector_cfg=_base_detector_cfg(),
        timing_cfg=_base_timing_cfg(),
    )
    d = diag.as_dict()
    assert isinstance(d, dict)
    assert "pmd" in d
    assert "temperature_drift" in d
    assert "fwm" in d
    assert "timing_budget" in d
    assert isinstance(d["timing_budget"], dict)
    assert "sigma_effective_ps" in d["timing_budget"]
    assert d["pmd"] is not None
    assert d["pmd"]["mean_dgd_ps"] > 0
    assert d["temperature_drift"] is not None
    assert d["temperature_drift"]["residual_drift_ps"] > 0
    assert d["fwm"] is not None
    assert d["fwm"]["fwm_counts_cps"] > 0


# ---- 12. test_pmd_monotonic_with_distance ----

def test_pmd_monotonic_with_distance() -> None:
    coeff = 0.2
    distances = [10.0, 50.0, 100.0, 200.0]
    dgds = [pmd_dgd_ps(d, coeff) for d in distances]
    for i in range(len(dgds) - 1):
        assert dgds[i + 1] > dgds[i], (
            f"DGD not monotonic: {dgds[i + 1]} <= {dgds[i]} "
            f"at distances {distances[i + 1]} vs {distances[i]}"
        )


# ---- 13. test_connector_splice_chain_auto ----

def test_connector_splice_chain_auto() -> None:
    """Auto-count connectors/splices from distance and spacing."""
    cs = connector_splice_chain(
        distance_km=20.0,
        connector_loss_db=0.5,
        splice_loss_db=0.1,
        connector_spacing_km=5.0,
        splice_spacing_km=4.0,
    )
    # 20 km / 5 = 4 intervals -> 5 connectors (+ 1)
    assert cs.n_connectors == 5
    # 20 km / 4 = 5 splices
    assert cs.n_splices == 5
    assert cs.total_connector_loss_db == pytest.approx(5 * 0.5)
    assert cs.total_splice_loss_db == pytest.approx(5 * 0.1)
    assert cs.total_loss_db == pytest.approx(5 * 0.5 + 5 * 0.1)


# ---- 14. test_connector_splice_chain_explicit ----

def test_connector_splice_chain_explicit() -> None:
    cs = connector_splice_chain(
        distance_km=50.0,
        connector_loss_db=0.3,
        splice_loss_db=0.05,
        n_connectors=4,
        n_splices=12,
    )
    assert cs.n_connectors == 4
    assert cs.n_splices == 12
    assert cs.total_loss_db == pytest.approx(4 * 0.3 + 12 * 0.05)


# ---- 15. test_connector_splice_serialization ----

def test_connector_splice_serialization() -> None:
    cs = connector_splice_chain(distance_km=10.0)
    d = cs.as_dict()
    assert isinstance(d, dict)
    assert "n_connectors" in d
    assert "total_loss_db" in d


# ---- 16. test_combined_raman_budget ----

def test_combined_raman_budget() -> None:
    coex = {
        "enabled": True,
        "classical_launch_power_dbm": 0.0,
        "classical_channel_count": 4,
        "filter_bandwidth_nm": 0.2,
        "raman_coeff_cps_per_km_per_mw_per_nm": 1e-4,
    }
    budget = combined_raman_budget(
        distance_km=50.0,
        coexistence=coex,
        fiber_loss_db_per_km=0.2,
    )
    assert budget.forward_counts_cps >= 0
    assert budget.backward_counts_cps >= 0
    assert budget.total_raman_counts_cps >= 0
    assert budget.total_noise_counts_cps >= budget.total_raman_counts_cps


# ---- 17. test_combined_raman_serialization ----

def test_combined_raman_serialization() -> None:
    coex = {
        "enabled": True,
        "classical_launch_power_dbm": 0.0,
        "classical_channel_count": 4,
        "filter_bandwidth_nm": 0.2,
    }
    budget = combined_raman_budget(
        distance_km=30.0,
        coexistence=coex,
    )
    d = budget.as_dict()
    assert isinstance(d, dict)
    assert "forward_counts_cps" in d
    assert "total_noise_counts_cps" in d


# ---- 18. test_diagnostics_with_connectors_and_raman ----

def test_diagnostics_with_connectors_and_raman() -> None:
    diag = compute_fiber_deployment_diagnostics(
        distance_km=40.0,
        channel_cfg=_base_channel_cfg(
            connector_loss_db=0.5,
            splice_loss_db=0.1,
            coexistence={
                "enabled": True,
                "classical_launch_power_dbm": 0.0,
                "classical_channel_count": 4,
                "filter_bandwidth_nm": 0.2,
            },
        ),
        detector_cfg=_base_detector_cfg(),
        timing_cfg=_base_timing_cfg(),
    )
    assert diag.connector_splice is not None
    assert diag.connector_splice.total_loss_db > 0
    assert diag.raman_budget is not None
    assert diag.raman_budget.total_raman_counts_cps >= 0

    d = diag.as_dict()
    assert d["connector_splice"] is not None
    assert d["raman_budget"] is not None
