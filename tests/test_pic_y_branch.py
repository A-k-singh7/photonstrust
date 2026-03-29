"""Tests for Y-branch splitter component model."""

from __future__ import annotations

import numpy as np
import pytest

from photonstrust.components.pic.y_branch import (
    Y_BRANCH_PORTS,
    y_branch_forward_matrix,
    y_branch_ports,
    y_branch_scattering_matrix,
)


def test_y_branch_equal_split():
    """Default 50:50 splitting -- each output gets half the transmitted power."""
    params = {"insertion_loss_db": 0.0, "splitting_ratio": 0.5}
    m = y_branch_forward_matrix(params)
    p0 = abs(m[0, 0]) ** 2
    p1 = abs(m[1, 0]) ** 2
    assert p0 == pytest.approx(0.5, rel=1e-12)
    assert p1 == pytest.approx(0.5, rel=1e-12)


def test_y_branch_asymmetric():
    """With splitting_ratio=0.7, out1 should get 70% of transmitted power."""
    params = {"insertion_loss_db": 0.0, "splitting_ratio": 0.7}
    m = y_branch_forward_matrix(params)
    p0 = abs(m[0, 0]) ** 2
    p1 = abs(m[1, 0]) ** 2
    assert p0 == pytest.approx(0.7, rel=1e-10)
    assert p1 == pytest.approx(0.3, rel=1e-10)


def test_y_branch_loss():
    """Total output power should equal eta (input power * transmission)."""
    il_db = 0.2
    params = {"insertion_loss_db": il_db, "splitting_ratio": 0.5}
    m = y_branch_forward_matrix(params)
    total_power = abs(m[0, 0]) ** 2 + abs(m[1, 0]) ** 2
    expected_eta = 10 ** (-il_db / 10)
    assert total_power == pytest.approx(expected_eta, rel=1e-10)


def test_y_branch_ports():
    """Y-branch has 1 input and 2 outputs."""
    ports = y_branch_ports()
    assert ports.in_ports == ("in",)
    assert ports.out_ports == ("out1", "out2")
    assert ports == Y_BRANCH_PORTS


def test_y_branch_scattering_reciprocal():
    """Scattering matrix should be symmetric (reciprocal device)."""
    params = {"insertion_loss_db": 0.2, "splitting_ratio": 0.5}
    s = y_branch_scattering_matrix(params)
    assert s.shape == (3, 3)
    np.testing.assert_allclose(s, s.T, atol=1e-14)
