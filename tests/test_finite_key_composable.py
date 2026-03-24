"""Tests for the composable finite-key security framework."""

from __future__ import annotations

import math

import pytest

from photonstrust.qkd_protocols.finite_key import (
    FiniteKeyAdjustment,
    apply_composable_finite_key,
    apply_finite_key_dispatch,
)
from photonstrust.qkd_protocols.finite_key_composable import (
    ComposableFiniteKeyResult,
    EpsilonBudget,
    apply_composable_finite_key_v2,
    compute_ec_leakage,
    compute_pa_output_length,
    compute_smooth_min_entropy_lb,
    split_epsilon,
)
from photonstrust.qkd_protocols.pe_bounds import (
    phase_error_upper_bound,
    random_sampling_bound,
)


def test_v2_epsilon_budget_sums_correctly():
    budget = split_epsilon(epsilon_total=1e-10, split_strategy="balanced")
    assert budget.epsilon_total == pytest.approx(1e-10)
    components = budget.epsilon_sec + budget.epsilon_cor + budget.epsilon_pa + budget.epsilon_pe + budget.epsilon_ec
    assert components == pytest.approx(1e-10)


def test_v2_pa_heavy_split_allocates_more_to_pa():
    balanced = split_epsilon(epsilon_total=1e-10, split_strategy="balanced")
    pa_heavy = split_epsilon(epsilon_total=1e-10, split_strategy="pa_heavy")
    assert pa_heavy.epsilon_pa > balanced.epsilon_pa


def test_v2_custom_split():
    budget = split_epsilon(
        epsilon_total=1e-10,
        split_strategy="custom",
        epsilon_sec=1e-11,
        epsilon_cor=2e-11,
        epsilon_pa=3e-11,
        epsilon_pe=2e-11,
        epsilon_ec=2e-11,
    )
    assert budget.epsilon_sec == pytest.approx(1e-11)
    assert budget.epsilon_cor == pytest.approx(2e-11)
    assert budget.epsilon_pa == pytest.approx(3e-11)


def test_v2_reduces_key_rate_vs_asymptotic():
    cfg = {
        "enabled": True,
        "signals_per_block": 1e10,
        "security_epsilon": 1e-10,
        "parameter_estimation_fraction": 0.1,
        "composable_version": "v2",
    }
    result = apply_composable_finite_key_v2(
        finite_key_cfg=cfg,
        sifting=0.5,
        privacy_term_asymptotic=0.8,
        protocol_name="bb84_decoy",
        single_photon_yield_lb=0.5,
        single_photon_error_ub=0.03,
        qber=0.03,
        f_ec=1.16,
    )
    assert result.enabled
    assert result.privacy_term_effective <= 0.8
    assert result.finite_key_penalty >= 0.0


def test_v2_backward_compat_without_composable_version():
    cfg = {
        "enabled": True,
        "signals_per_block": 1e10,
        "security_epsilon": 1e-10,
        "parameter_estimation_fraction": 0.1,
    }
    result = apply_finite_key_dispatch(
        finite_key_cfg=cfg,
        sifting=0.5,
        privacy_term_asymptotic=0.8,
    )
    assert isinstance(result, FiniteKeyAdjustment)
    assert result.enabled
    assert result.privacy_term_effective <= 0.8


def test_v2_dispatch_routes_to_v2():
    cfg = {
        "enabled": True,
        "signals_per_block": 1e10,
        "security_epsilon": 1e-10,
        "parameter_estimation_fraction": 0.1,
        "composable_version": "v2",
    }
    result = apply_finite_key_dispatch(
        finite_key_cfg=cfg,
        sifting=0.5,
        privacy_term_asymptotic=0.8,
        protocol_name="bb84_decoy",
        single_photon_yield_lb=0.5,
        single_photon_error_ub=0.03,
        qber=0.03,
        f_ec=1.16,
    )
    assert isinstance(result, FiniteKeyAdjustment)
    assert result.enabled


def test_v2_monotonic_with_block_size():
    base = {
        "enabled": True,
        "security_epsilon": 1e-10,
        "parameter_estimation_fraction": 0.1,
        "composable_version": "v2",
    }
    rates = []
    for n in [1e8, 1e10, 1e12]:
        cfg = {**base, "signals_per_block": n}
        r = apply_composable_finite_key_v2(
            finite_key_cfg=cfg,
            sifting=0.5,
            privacy_term_asymptotic=0.8,
            protocol_name="bb84_decoy",
            single_photon_yield_lb=0.5,
            single_photon_error_ub=0.03,
            qber=0.03,
            f_ec=1.16,
        )
        rates.append(r.net_key_length_bits)
    assert rates[0] <= rates[1] <= rates[2]


def test_smooth_min_entropy_positive():
    h = compute_smooth_min_entropy_lb(
        n_sifted=int(1e9),
        single_photon_yield_lb=0.5,
        single_photon_error_ub=0.03,
        epsilon_smooth=1e-11,
    )
    assert h > 0


def test_smooth_min_entropy_zero_for_high_error():
    h = compute_smooth_min_entropy_lb(
        n_sifted=int(1e9),
        single_photon_yield_lb=0.5,
        single_photon_error_ub=0.5,
        epsilon_smooth=1e-11,
    )
    assert h == 0.0


def test_pe_bound_covers_observed_rate():
    bound = random_sampling_bound(
        n_sample=10000,
        n_total=100000,
        observed_rate=0.03,
        epsilon_pe=1e-10,
    )
    assert bound.lower_bound <= 0.03 <= bound.upper_bound
    assert bound.confidence_interval_half_width > 0


def test_composable_key_length_non_negative():
    cfg = {
        "enabled": True,
        "signals_per_block": 1e6,
        "security_epsilon": 1e-10,
        "parameter_estimation_fraction": 0.1,
        "composable_version": "v2",
    }
    result = apply_composable_finite_key_v2(
        finite_key_cfg=cfg,
        sifting=0.5,
        privacy_term_asymptotic=0.8,
        protocol_name="bb84_decoy",
        single_photon_yield_lb=0.5,
        single_photon_error_ub=0.03,
        qber=0.03,
        f_ec=1.16,
    )
    assert result.net_key_length_bits >= 0


def test_disabled_returns_zero():
    result = apply_composable_finite_key_v2(
        finite_key_cfg={"enabled": False, "composable_version": "v2"},
        sifting=0.5,
        privacy_term_asymptotic=0.8,
    )
    assert not result.enabled
    assert result.net_key_length_bits == 0
    assert result.privacy_term_effective == pytest.approx(0.8)


def test_ec_leakage_positive_for_nonzero_qber():
    leak = compute_ec_leakage(
        n_sifted=int(1e9),
        qber=0.03,
        f_ec=1.16,
        epsilon_cor=1e-11,
    )
    assert leak > 0


def test_pa_output_length_decreases_with_leakage():
    h_min = 1e8
    leak_low = compute_ec_leakage(n_sifted=int(1e9), qber=0.01, f_ec=1.16, epsilon_cor=1e-11)
    leak_high = compute_ec_leakage(n_sifted=int(1e9), qber=0.05, f_ec=1.16, epsilon_cor=1e-11)
    pa_low = compute_pa_output_length(smooth_min_entropy=h_min, ec_leakage_bits=leak_low, epsilon_pa=1e-11, epsilon_cor=1e-11)
    pa_high = compute_pa_output_length(smooth_min_entropy=h_min, ec_leakage_bits=leak_high, epsilon_pa=1e-11, epsilon_cor=1e-11)
    assert pa_low >= pa_high


def test_phase_error_upper_bound():
    bound = phase_error_upper_bound(
        n_sifted=100000,
        n_test=10000,
        observed_qber=0.03,
        epsilon_pe=1e-10,
    )
    assert bound.upper_bound >= 0.03
    assert bound.upper_bound <= 0.5
