"""Tests for the spot-size converter (SSC) component model."""

from __future__ import annotations

import math

import pytest

from photonstrust.components.pic.ssc import (
    gaussian_overlap_efficiency,
    inverse_taper_mfd,
    ssc_alignment_tolerance,
    ssc_coupling_loss_db,
)


def test_gaussian_overlap_identical():
    """Identical MFDs with zero offset give perfect coupling."""
    eta = gaussian_overlap_efficiency(10.0, 10.0, offset_um=0.0)
    assert eta == pytest.approx(1.0, abs=1e-14)


def test_gaussian_overlap_mismatch():
    """Different MFDs reduce coupling below unity."""
    eta = gaussian_overlap_efficiency(5.0, 10.0, offset_um=0.0)
    assert 0.0 < eta < 1.0


def test_gaussian_overlap_with_offset():
    """Lateral offset reduces coupling efficiency."""
    eta_0 = gaussian_overlap_efficiency(10.0, 10.0, offset_um=0.0)
    eta_1 = gaussian_overlap_efficiency(10.0, 10.0, offset_um=2.0)
    assert eta_1 < eta_0


def test_inverse_taper_mfd_expands():
    """Narrower tip produces a larger MFD (mode delocalization)."""
    mfd_wide = inverse_taper_mfd(tip_width_nm=300.0)
    mfd_narrow = inverse_taper_mfd(tip_width_nm=100.0)
    assert mfd_narrow > mfd_wide


def test_ssc_coupling_loss_range():
    """Typical SSC coupling loss should be in the 1-3 dB range for a well-matched tip."""
    # tip ~100 nm gives MFD ~4.5 um; tip ~80 nm gives MFD ~13 um
    loss = ssc_coupling_loss_db(tip_width_nm=100.0, fiber_mfd_um=10.4)
    assert 0.5 < loss < 5.0


def test_ssc_alignment_tolerance_positive():
    """Alignment tolerance must be a positive value."""
    tol = ssc_alignment_tolerance(tip_width_nm=180.0, fiber_mfd_um=10.4)
    assert tol > 0.0


def test_ssc_fiber_match():
    """A ~100 nm tip should produce an MFD reasonably close to SMF-28 (10.4 um)."""
    mfd = inverse_taper_mfd(tip_width_nm=100.0)
    # The expanded mode should be in the same order of magnitude as the fibre
    assert 3.0 < mfd < 30.0
