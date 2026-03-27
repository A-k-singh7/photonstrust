"""Tests for waveguide crossing component model."""

from __future__ import annotations

import numpy as np
import pytest

from photonstrust.components.pic.crossing import (
    CROSSING_PORTS,
    crossing_forward_matrix,
    crossing_ports,
    crossing_scattering_matrix,
    cumulative_crossing_loss_db,
)


def test_crossing_low_loss():
    """Through-path power should match ~0.02 dB insertion loss."""
    params = {"insertion_loss_db": 0.02, "crosstalk_db": -40.0}
    m = crossing_forward_matrix(params)
    through_power = abs(m[0, 0]) ** 2
    expected = 10 ** (-0.02 / 10)
    assert through_power == pytest.approx(expected, rel=1e-10)


def test_crossing_low_crosstalk():
    """Cross-path power should be below -40 dB."""
    params = {"insertion_loss_db": 0.02, "crosstalk_db": -40.0}
    m = crossing_forward_matrix(params)
    xt_power = abs(m[1, 0]) ** 2
    xt_power_db = 10 * np.log10(xt_power)
    assert xt_power_db == pytest.approx(-40.0, abs=0.01)


def test_crossing_cumulative():
    """N crossings should give N * IL_per_crossing."""
    n = 12
    il_per = 0.02
    total = cumulative_crossing_loss_db(n, il_per)
    assert total == pytest.approx(n * il_per, rel=1e-12)


def test_crossing_ports():
    """Crossing has 2 inputs and 2 outputs."""
    ports = crossing_ports()
    assert ports.in_ports == ("in1", "in2")
    assert ports.out_ports == ("out1", "out2")
    assert ports == CROSSING_PORTS


def test_crossing_scattering_size():
    """Scattering matrix should be 4x4."""
    params = {"insertion_loss_db": 0.02, "crosstalk_db": -40.0}
    s = crossing_scattering_matrix(params)
    assert s.shape == (4, 4)
    # Should be symmetric (reciprocal)
    np.testing.assert_allclose(s, s.T, atol=1e-14)
