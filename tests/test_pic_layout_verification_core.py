from __future__ import annotations

import math

import pytest

from photonstrust.pic.layout.verification import (
    estimate_process_yield,
    verify_bend_and_routing_loss,
    verify_crosstalk_budget,
    verify_design_rule_envelope,
    verify_layout_signoff_bundle,
    verify_phase_shifter_range,
    verify_process_variation,
    verify_resonance_alignment,
    verify_thermal_crosstalk_matrix,
    verify_thermal_drift,
    verify_wavelength_sweep_signoff,
    verify_wavelength_sweep_signoff_from_trace,
)


def _synthetic_dual_peak_trace() -> tuple[list[float], list[float]]:
    wavelengths = [1549.5 + 0.01 * i for i in range(101)]
    transmission = []
    for w in wavelengths:
        p1 = 19.0 * math.exp(-((w - 1549.8) ** 2) / (2.0 * (0.015**2)))
        p2 = 18.0 * math.exp(-((w - 1550.2) ** 2) / (2.0 * (0.015**2)))
        transmission.append(-20.0 + p1 + p2)
    return wavelengths, transmission


def test_verify_crosstalk_budget_pass_and_fail():
    runs = [
        {"id": "r1", "gap_um": 0.8, "parallel_length_um": 400.0},
        {"id": "r2", "gap_um": 1.0, "parallel_length_um": 250.0},
    ]
    ok = verify_crosstalk_budget(parallel_runs=runs, wavelength_nm=1550.0, target_xt_db=-35.0)
    assert ok["pass"] is True
    assert ok["worst_xt_db"] <= -35.0

    bad = verify_crosstalk_budget(
        parallel_runs=[{"id": "tight", "gap_um": 0.2, "parallel_length_um": 5000.0}],
        wavelength_nm=1550.0,
        target_xt_db=-30.0,
    )
    assert bad["pass"] is False
    assert len(bad["violations"]) >= 1


def test_verify_thermal_drift_pass_and_fail():
    segments = [{"id": "arm_a", "length_um": 200.0, "wavelength_nm": 1550.0, "group_index": 4.2}]
    ok = verify_thermal_drift(
        segments=segments,
        delta_temperature_c=0.2,
        max_phase_drift_rad=0.5,
        max_wavelength_shift_pm=50.0,
    )
    assert ok["pass"] is True

    bad = verify_thermal_drift(
        segments=[{"id": "heater_zone", "length_um": 5000.0, "wavelength_nm": 1550.0, "group_index": 4.2}],
        delta_temperature_c=15.0,
        max_phase_drift_rad=1.0,
        max_wavelength_shift_pm=200.0,
    )
    assert bad["pass"] is False
    assert bad["worst_phase_drift_rad"] > 1.0


def test_verify_bend_and_routing_loss_pass_and_fail():
    ok = verify_bend_and_routing_loss(
        routes=[
            {
                "id": "rt_ok",
                "length_um": 3000.0,
                "bends": [{"radius_um": 12.0, "angle_deg": 90.0}, {"radius_um": 10.0, "angle_deg": 45.0}],
            }
        ],
        max_route_loss_db=1.0,
    )
    assert ok["pass"] is True

    bad = verify_bend_and_routing_loss(
        routes=[
            {
                "id": "rt_bad",
                "length_um": 25000.0,
                "bends": [{"radius_um": 3.0, "angle_deg": 180.0}],
            }
        ],
        max_route_loss_db=0.5,
    )
    assert bad["pass"] is False
    assert any("radius" in v for v in bad["violations"])
    assert any("route_loss_db" in v for v in bad["violations"])


def test_verify_process_variation_pass_and_fail():
    ok = verify_process_variation(
        metrics=[
            {
                "name": "splitter_imbalance_db",
                "nominal": 0.0,
                "sigma": 0.05,
                "sensitivity": 1.0,
                "min_allowed": -0.5,
                "max_allowed": 0.5,
            }
        ],
        sigma_multiplier=3.0,
    )
    assert ok["pass"] is True

    bad = verify_process_variation(
        metrics=[
            {
                "name": "ring_detune_pm",
                "nominal": 0.0,
                "sigma": 8.0,
                "sensitivity": 1.0,
                "min_allowed": -10.0,
                "max_allowed": 10.0,
            }
        ],
        sigma_multiplier=3.0,
    )
    assert bad["pass"] is False
    assert len(bad["violations"]) == 1


def test_verify_design_rule_envelope_pass_and_fail():
    ok = verify_design_rule_envelope(
        waveguides=[{"id": "wg_ok", "width_um": 0.50}],
        couplers=[{"id": "cp_ok", "gap_um": 0.25}],
        bends=[{"id": "b_ok", "radius_um": 8.0}],
    )
    assert ok["pass"] is True

    bad = verify_design_rule_envelope(
        waveguides=[{"id": "wg_bad", "width_um": 0.30}],
        couplers=[{"id": "cp_bad", "gap_um": 0.10}],
        bends=[{"id": "b_bad", "radius_um": 3.0}],
    )
    assert bad["pass"] is False
    assert any("min_waveguide_width_um" in v for v in bad["violations"])
    assert any("min_waveguide_gap_um" in v for v in bad["violations"])
    assert any("min_bend_radius_um" in v for v in bad["violations"])


def test_verify_thermal_crosstalk_matrix_pass_and_fail():
    ok = verify_thermal_crosstalk_matrix(
        heaters=[{"id": "h1", "power_mw": 10.0}, {"id": "h2", "power_mw": 5.0}],
        victims=[{"id": "ring1", "length_um": 300.0, "wavelength_nm": 1550.0}],
        coupling_matrix_c_per_mw=[[0.01], [0.02]],
        max_victim_delta_temperature_c=0.5,
        max_victim_phase_drift_rad=0.5,
    )
    assert ok["pass"] is True

    bad = verify_thermal_crosstalk_matrix(
        heaters=[{"id": "h1", "power_mw": 10.0}, {"id": "h2", "power_mw": 5.0}],
        victims=[{"id": "ring_hot", "length_um": 5000.0, "wavelength_nm": 1550.0}],
        coupling_matrix_c_per_mw=[[0.20], [0.30]],
        max_victim_delta_temperature_c=1.0,
        max_victim_phase_drift_rad=1.0,
    )
    assert bad["pass"] is False
    assert bad["worst_victim_delta_temperature_c"] > 1.0


def test_verify_resonance_alignment_pass_and_fail():
    ok = verify_resonance_alignment(
        channels=[
            {
                "id": "ch1",
                "target_wavelength_nm": 1550.0,
                "observed_wavelength_nm": 1550.003,
                "linewidth_pm": 45.0,
            }
        ],
        max_detune_pm=5.0,
        min_linewidth_pm=10.0,
        max_linewidth_pm=100.0,
    )
    assert ok["pass"] is True

    bad = verify_resonance_alignment(
        channels=[
            {
                "id": "ch_bad",
                "target_wavelength_nm": 1550.0,
                "observed_wavelength_nm": 1550.020,
                "linewidth_pm": 5.0,
            }
        ],
        max_detune_pm=5.0,
        min_linewidth_pm=10.0,
    )
    assert bad["pass"] is False
    assert bad["worst_detune_pm"] > 5.0


def test_verify_phase_shifter_range_pass_and_fail():
    ok = verify_phase_shifter_range(
        shifters=[
            {
                "id": "ps1",
                "tuning_efficiency_rad_per_mw": 0.2,
                "max_power_mw": 20.0,
                "required_phase_span_rad": 3.0,
            }
        ],
        max_total_power_mw=30.0,
    )
    assert ok["pass"] is True

    bad = verify_phase_shifter_range(
        shifters=[
            {
                "id": "ps_bad",
                "tuning_efficiency_rad_per_mw": 0.05,
                "max_power_mw": 20.0,
                "required_phase_span_rad": 2.0,
            },
            {
                "id": "ps_budget",
                "tuning_efficiency_rad_per_mw": 0.2,
                "max_power_mw": 40.0,
                "required_phase_span_rad": 1.0,
            },
        ],
        max_total_power_mw=50.0,
    )
    assert bad["pass"] is False
    assert any("achievable_phase_span_rad" in v for v in bad["violations"])
    assert any("total_max_power_mw" in v for v in bad["violations"])


def test_verify_wavelength_sweep_signoff_pass_and_fail():
    ok = verify_wavelength_sweep_signoff(
        channels=[
            {
                "id": "ch_a",
                "center_wavelength_nm": 1549.8,
                "insertion_loss_db": 1.8,
                "extinction_ratio_db": 25.0,
                "linewidth_pm": 45.0,
            },
            {
                "id": "ch_b",
                "center_wavelength_nm": 1550.2,
                "insertion_loss_db": 2.1,
                "extinction_ratio_db": 23.0,
                "linewidth_pm": 52.0,
            },
        ],
        min_channel_spacing_pm=200.0,
        max_insertion_loss_db=3.0,
        min_extinction_ratio_db=20.0,
        min_linewidth_pm=10.0,
        max_linewidth_pm=100.0,
    )
    assert ok["pass"] is True

    bad = verify_wavelength_sweep_signoff(
        channels=[
            {
                "id": "ch_bad1",
                "center_wavelength_nm": 1550.000,
                "insertion_loss_db": 4.0,
                "extinction_ratio_db": 18.0,
                "linewidth_pm": 8.0,
            },
            {
                "id": "ch_bad2",
                "center_wavelength_nm": 1550.050,
                "insertion_loss_db": 2.0,
                "extinction_ratio_db": 25.0,
                "linewidth_pm": 40.0,
            },
        ],
        min_channel_spacing_pm=100.0,
        max_insertion_loss_db=3.0,
        min_extinction_ratio_db=20.0,
        min_linewidth_pm=10.0,
    )
    assert bad["pass"] is False
    assert any("insertion_loss_db" in v for v in bad["violations"])
    assert any("extinction_ratio_db" in v for v in bad["violations"])
    assert any("spacing" in v for v in bad["violations"])


def test_verify_wavelength_sweep_signoff_from_trace_pass_and_fail():
    wavelengths, transmission = _synthetic_dual_peak_trace()

    ok = verify_wavelength_sweep_signoff_from_trace(
        wavelengths_nm=wavelengths,
        transmission_db=transmission,
        channel_windows=[
            {"id": "ch_a", "start_wavelength_nm": 1549.70, "stop_wavelength_nm": 1549.90},
            {"id": "ch_b", "start_wavelength_nm": 1550.10, "stop_wavelength_nm": 1550.30},
        ],
        min_channel_spacing_pm=200.0,
        max_insertion_loss_db=3.0,
        min_extinction_ratio_db=10.0,
        min_linewidth_pm=10.0,
        max_linewidth_pm=80.0,
    )
    assert ok["pass"] is True
    assert len(ok["extracted_channels"]) == 2
    assert ok["signoff"] is not None and ok["signoff"]["pass"] is True

    bad = verify_wavelength_sweep_signoff_from_trace(
        wavelengths_nm=wavelengths,
        transmission_db=transmission,
        channel_windows=[
            {"id": "ch_missing", "start_wavelength_nm": 1549.501, "stop_wavelength_nm": 1549.503},
        ],
        min_channel_spacing_pm=200.0,
        max_insertion_loss_db=3.0,
        min_extinction_ratio_db=10.0,
    )
    assert bad["pass"] is False
    assert any("insufficient points" in v for v in bad["violations"])


def test_estimate_process_yield_pass_and_fail():
    ok = estimate_process_yield(
        metrics=[
            {
                "name": "splitter_imbalance_db",
                "nominal": 0.0,
                "sigma": 0.05,
                "sensitivity": 1.0,
                "min_allowed": -0.5,
                "max_allowed": 0.5,
            },
            {
                "name": "ring_detune_pm",
                "nominal": 0.0,
                "sigma": 1.0,
                "sensitivity": 1.0,
                "min_allowed": -5.0,
                "max_allowed": 5.0,
            },
        ],
        min_required_yield=0.95,
        monte_carlo_samples=2000,
        seed=17,
    )
    assert ok["pass"] is True
    assert ok["estimated_yield"] >= 0.95

    bad = estimate_process_yield(
        metrics=[
            {
                "name": "tight_detune_pm",
                "nominal": 0.0,
                "sigma": 5.0,
                "sensitivity": 1.0,
                "min_allowed": -2.0,
                "max_allowed": 2.0,
            }
        ],
        min_required_yield=0.9,
        monte_carlo_samples=2000,
        seed=17,
    )
    assert bad["pass"] is False
    assert bad["estimated_yield"] < 0.9


def test_estimate_process_yield_correlation_mode_and_validation():
    correlated = estimate_process_yield(
        metrics=[
            {
                "name": "m1",
                "nominal": 0.0,
                "sigma": 1.0,
                "sensitivity": 1.0,
                "min_allowed": -2.0,
                "max_allowed": 2.0,
            },
            {
                "name": "m2",
                "nominal": 0.0,
                "sigma": 1.0,
                "sensitivity": 1.0,
                "min_allowed": -2.0,
                "max_allowed": 2.0,
            },
        ],
        min_required_yield=0.7,
        monte_carlo_samples=3000,
        seed=23,
        correlation_matrix=[[1.0, 0.8], [0.8, 1.0]],
    )
    assert correlated["correlation"]["used"] is True
    assert correlated["monte_carlo"]["mode"] == "correlated"
    assert correlated["monte_carlo"]["estimated_yield"] is not None
    assert 0.0 <= correlated["estimated_yield"] <= 1.0

    auto_samples = estimate_process_yield(
        metrics=[
            {
                "name": "m1",
                "nominal": 0.0,
                "sigma": 1.0,
                "sensitivity": 1.0,
                "min_allowed": -2.0,
                "max_allowed": 2.0,
            }
        ],
        min_required_yield=0.6,
        seed=5,
        correlation_matrix=[[1.0]],
    )
    assert auto_samples["monte_carlo"]["samples_requested"] == 0
    assert auto_samples["monte_carlo"]["samples_used"] == 5000
    assert auto_samples["monte_carlo"]["mode"] == "correlated"

    with pytest.raises(ValueError):
        estimate_process_yield(
            metrics=[
                {
                    "name": "m1",
                    "nominal": 0.0,
                    "sigma": 1.0,
                    "sensitivity": 1.0,
                    "min_allowed": -2.0,
                    "max_allowed": 2.0,
                },
                {
                    "name": "m2",
                    "nominal": 0.0,
                    "sigma": 1.0,
                    "sensitivity": 1.0,
                    "min_allowed": -2.0,
                    "max_allowed": 2.0,
                },
            ],
            correlation_matrix=[[1.0, 0.2], [0.3, 1.0]],
        )


def test_verify_layout_signoff_bundle_pass_and_fail():
    wavelengths, transmission = _synthetic_dual_peak_trace()

    ok = verify_layout_signoff_bundle(
        design_rule_envelope={"waveguides": [{"id": "wg", "width_um": 0.5}]},
        process_variation={
            "metrics": [
                {
                    "name": "splitter_imbalance_db",
                    "nominal": 0.0,
                    "sigma": 0.05,
                    "sensitivity": 1.0,
                    "min_allowed": -0.5,
                    "max_allowed": 0.5,
                }
            ]
        },
        resonance_alignment={
            "channels": [
                {
                    "id": "ch1",
                    "target_wavelength_nm": 1550.0,
                    "observed_wavelength_nm": 1550.003,
                }
            ],
            "max_detune_pm": 10.0,
        },
        wavelength_sweep_signoff={
            "channels": [
                {
                    "id": "ch_a",
                    "center_wavelength_nm": 1549.8,
                    "insertion_loss_db": 1.8,
                    "extinction_ratio_db": 25.0,
                    "linewidth_pm": 45.0,
                },
                {
                    "id": "ch_b",
                    "center_wavelength_nm": 1550.2,
                    "insertion_loss_db": 2.1,
                    "extinction_ratio_db": 23.0,
                    "linewidth_pm": 52.0,
                },
            ],
            "min_channel_spacing_pm": 200.0,
            "max_insertion_loss_db": 3.0,
            "min_extinction_ratio_db": 20.0,
            "min_linewidth_pm": 10.0,
            "max_linewidth_pm": 100.0,
        },
        wavelength_sweep_trace_signoff={
            "wavelengths_nm": wavelengths,
            "transmission_db": transmission,
            "channel_windows": [
                {"id": "ch_a", "start_wavelength_nm": 1549.70, "stop_wavelength_nm": 1549.90},
                {"id": "ch_b", "start_wavelength_nm": 1550.10, "stop_wavelength_nm": 1550.30},
            ],
            "min_channel_spacing_pm": 200.0,
            "max_insertion_loss_db": 3.0,
            "min_extinction_ratio_db": 10.0,
            "min_linewidth_pm": 10.0,
            "max_linewidth_pm": 80.0,
        },
        process_yield={
            "metrics": [
                {
                    "name": "splitter_imbalance_db",
                    "nominal": 0.0,
                    "sigma": 0.05,
                    "sensitivity": 1.0,
                    "min_allowed": -0.5,
                    "max_allowed": 0.5,
                }
            ],
            "min_required_yield": 0.95,
            "correlation_matrix": [[1.0]],
        },
    )
    assert ok["pass"] is True
    assert ok["summary"]["failed_checks"] == 0
    assert any(c["check"].endswith("wavelength_sweep_signoff_from_trace") for c in ok["checks"])

    bad = verify_layout_signoff_bundle(
        crosstalk_budget={
            "parallel_runs": [{"id": "tight", "gap_um": 0.2, "parallel_length_um": 5000.0}],
            "wavelength_nm": 1550.0,
            "target_xt_db": -30.0,
        },
        design_rule_envelope={"waveguides": [{"id": "wg", "width_um": 0.5}]},
        phase_shifter_range={
            "shifters": [
                {
                    "id": "ps_bad",
                    "tuning_efficiency_rad_per_mw": 0.05,
                    "max_power_mw": 20.0,
                    "required_phase_span_rad": 2.0,
                }
            ]
        },
    )
    assert bad["pass"] is False
    assert bad["summary"]["failed_checks"] >= 1
    assert any("crosstalk_budget" in v or "phase_shifter_range" in v for v in bad["violations"])
