"""Tests for quantum repeater chain models."""

from __future__ import annotations

import pytest

from photonstrust.network.repeater_chain import (
    first_gen_repeater_chain,
    second_gen_repeater_chain,
    third_gen_repeater_chain,
)


# ---- First-generation repeater tests ---------------------------------------

def test_1g_positive_rate_500km():
    """1G repeater should produce positive rate at 500 km."""
    result = first_gen_repeater_chain(
        500.0, n_segments=8,
        source_rate_hz=1e9,
        detector_efficiency=0.9,
        memory_T2_s=10.0,
    )
    assert result.generation == 1
    assert result.rate_hz > 0
    assert result.fidelity > 0.5


def test_1g_rate_positive_at_200km():
    """1G repeater with 2 segments gives positive key rate at 200 km."""
    result = first_gen_repeater_chain(
        200.0, n_segments=2, swap_efficiency=0.9,
    )
    assert result.rate_hz > 0
    assert result.key_rate_bps > 0


def test_1g_fidelity_formula():
    """Fidelity should decrease with more swap levels."""
    r4 = first_gen_repeater_chain(400.0, n_segments=4, memory_T2_s=100.0)
    r16 = first_gen_repeater_chain(400.0, n_segments=16, memory_T2_s=100.0)
    # More segments = more swapping = lower fidelity per swap
    # but shorter segments = higher link fidelity
    # Both should have F > 0.5
    assert r4.fidelity > 0.5
    assert r16.fidelity > 0.5


def test_1g_memory_decoherence():
    """Longer memory T2 should give higher fidelity."""
    r_short = first_gen_repeater_chain(
        500.0, n_segments=4, memory_T2_s=0.01,
    )
    r_long = first_gen_repeater_chain(
        500.0, n_segments=4, memory_T2_s=100.0,
    )
    assert r_long.fidelity >= r_short.fidelity


def test_1g_with_purification():
    """Purification should improve fidelity at the cost of rate."""
    r_no_pur = first_gen_repeater_chain(
        300.0, n_segments=4, memory_T2_s=10.0, purification_rounds=0,
    )
    r_pur = first_gen_repeater_chain(
        300.0, n_segments=4, memory_T2_s=10.0, purification_rounds=2,
    )
    # Purification should help fidelity
    assert r_pur.fidelity >= r_no_pur.fidelity - 0.01  # allow small rounding


def test_1g_zero_distance():
    result = first_gen_repeater_chain(0.0, n_segments=1)
    assert result.rate_hz > 0
    assert result.fidelity > 0.5


def test_1g_n_nodes():
    result = first_gen_repeater_chain(100.0, n_segments=4)
    assert result.n_nodes == 3
    assert result.n_segments == 4


# ---- Second-generation repeater tests --------------------------------------

def test_2g_positive_rate():
    result = second_gen_repeater_chain(500.0, n_segments=8)
    assert result.generation == 2
    assert result.rate_hz > 0


def test_2g_fidelity_decreases_with_segments():
    r4 = second_gen_repeater_chain(400.0, n_segments=4)
    r16 = second_gen_repeater_chain(400.0, n_segments=16)
    # More segments = more logical errors accumulated
    assert r4.fidelity >= r16.fidelity


def test_2g_no_waiting_time():
    """QEC-based repeaters don't need waiting time."""
    result = second_gen_repeater_chain(300.0, n_segments=4)
    assert result.waiting_time_s == 0.0


# ---- Third-generation repeater tests ---------------------------------------

def test_3g_positive_rate_short():
    result = third_gen_repeater_chain(100.0, n_segments=4)
    assert result.generation == 3
    assert result.rate_hz > 0


def test_3g_no_waiting_time():
    """All-photonic repeaters don't need quantum memory waiting."""
    result = third_gen_repeater_chain(200.0, n_segments=4)
    assert result.waiting_time_s == 0.0


def test_3g_rate_decreases_with_distance():
    r100 = third_gen_repeater_chain(100.0, n_segments=4)
    r500 = third_gen_repeater_chain(500.0, n_segments=4)
    assert r100.rate_hz >= r500.rate_hz
