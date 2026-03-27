"""Tests for MMI coupler component models."""

from __future__ import annotations

import math

import numpy as np
import pytest

from photonstrust.components.pic.mmi import (
    MMI_1X2_PORTS,
    MMI_2X2_PORTS,
    mmi_1x2_forward_matrix,
    mmi_2x2_forward_matrix,
    mmi_beat_length,
    mmi_effective_width,
    mmi_ports,
)


def test_mmi_beat_length_formula():
    """L_pi = 4 * n_eff * W_eff^2 / (3 * lambda)."""
    n_eff = 2.85
    W_eff = 6.0  # um
    lam = 1.55  # um
    L_pi = mmi_beat_length(n_eff, W_eff, lam)
    expected = 4.0 * n_eff * W_eff ** 2 / (3.0 * lam)
    assert L_pi == pytest.approx(expected, rel=1e-12)


def test_mmi_effective_width_te():
    """W_eff must be larger than the physical width for TE."""
    W_mmi = 6.0
    lam = 1.55
    n_core = 3.47
    n_clad = 1.44
    W_eff = mmi_effective_width(W_mmi, lam, n_core, n_clad, polarization="TE")
    assert W_eff > W_mmi


def test_mmi_1x2_equal_splitting():
    """Each output of a 1x2 MMI should carry ~50% of the transmitted power."""
    params = {"insertion_loss_db": 0.3, "imbalance_db": 0.0}
    m = mmi_1x2_forward_matrix(params)
    p0 = abs(m[0, 0]) ** 2
    p1 = abs(m[1, 0]) ** 2
    assert p0 == pytest.approx(p1, rel=1e-10)
    assert p0 == pytest.approx(0.5 * 10 ** (-0.3 / 10), rel=1e-6)


def test_mmi_2x2_unitary():
    """M^dagger M should approximate eta * I for a lossless-ish 2x2 MMI."""
    params = {"insertion_loss_db": 0.0}
    m = mmi_2x2_forward_matrix(params)
    product = m.conj().T @ m
    assert product == pytest.approx(np.eye(2, dtype=np.complex128), abs=1e-12)


def test_mmi_2x2_phase_relation():
    """Cross-coupled outputs should have a pi/2 phase difference relative to bar."""
    params = {"insertion_loss_db": 0.0}
    m = mmi_2x2_forward_matrix(params)
    # m[0,0] is bar (real), m[1,0] is cross (imaginary)
    phase_bar = np.angle(m[0, 0])
    phase_cross = np.angle(m[1, 0])
    delta = abs(phase_cross - phase_bar)
    assert delta == pytest.approx(math.pi / 2, abs=1e-12)


def test_mmi_insertion_loss():
    """Total output power should match the expected insertion loss."""
    il_db = 0.5
    params = {"insertion_loss_db": il_db, "imbalance_db": 0.0}
    m = mmi_1x2_forward_matrix(params)
    total_power = abs(m[0, 0]) ** 2 + abs(m[1, 0]) ** 2
    expected_eta = 10 ** (-il_db / 10)
    assert total_power == pytest.approx(expected_eta, rel=1e-10)


def test_mmi_1x2_ports():
    """1x2 MMI should have in=('in',) out=('out1','out2')."""
    ports = mmi_ports({"n_ports_in": 1, "n_ports_out": 2})
    assert ports.in_ports == ("in",)
    assert ports.out_ports == ("out1", "out2")
    assert ports == MMI_1X2_PORTS


def test_mmi_2x2_ports():
    """2x2 MMI should have in=('in1','in2') out=('out1','out2')."""
    ports = mmi_ports({"n_ports_in": 2, "n_ports_out": 2})
    assert ports.in_ports == ("in1", "in2")
    assert ports.out_ports == ("out1", "out2")
    assert ports == MMI_2X2_PORTS
