"""Tests for entanglement purification protocols."""

from __future__ import annotations

import pytest

from photonstrust.network.purification import (
    bbpssw_purify,
    dejmps_purify,
    iterative_purification,
)


def test_bbpssw_increases_fidelity():
    """BBPSSW should increase fidelity for F > 0.5."""
    result = bbpssw_purify(0.75, rounds=1)
    assert result.fidelity_out > 0.75
    assert result.protocol == "bbpssw"


def test_bbpssw_multiple_rounds():
    """Multiple rounds should increase fidelity further."""
    r1 = bbpssw_purify(0.75, rounds=1)
    r3 = bbpssw_purify(0.75, rounds=3)
    assert r3.fidelity_out > r1.fidelity_out


def test_bbpssw_converges_toward_one():
    """Many rounds should approach F = 1."""
    result = bbpssw_purify(0.75, rounds=20)
    assert result.fidelity_out > 0.99


def test_bbpssw_no_improvement_below_half():
    """BBPSSW cannot improve fidelity below 0.5."""
    result = bbpssw_purify(0.4, rounds=5)
    assert result.fidelity_out <= 0.5


def test_bbpssw_success_probability():
    """Success probability should be in (0, 1)."""
    result = bbpssw_purify(0.8, rounds=1)
    assert 0 < result.success_probability <= 1


def test_bbpssw_pairs_consumed():
    """More rounds should consume more pairs."""
    r1 = bbpssw_purify(0.8, rounds=1)
    r5 = bbpssw_purify(0.8, rounds=5)
    assert r5.pairs_consumed >= r1.pairs_consumed


def test_dejmps_increases_fidelity():
    """DEJMPS should increase fidelity for F > 0.5."""
    result = dejmps_purify(0.75, rounds=1)
    assert result.fidelity_out > 0.75
    assert result.protocol == "dejmps"


def test_dejmps_converges():
    """DEJMPS should converge toward F = 1."""
    result = dejmps_purify(0.75, rounds=20)
    assert result.fidelity_out > 0.99


def test_dejmps_no_improvement_below_half():
    result = dejmps_purify(0.4, rounds=5)
    assert result.fidelity_out <= 0.5


def test_iterative_reaches_target():
    """Iterative purification should reach the target fidelity."""
    result = iterative_purification(0.75, 0.99, protocol="bbpssw")
    assert result.fidelity_out >= 0.99
    assert result.rounds > 0


def test_iterative_no_rounds_if_already_good():
    """If input already meets target, no rounds needed."""
    result = iterative_purification(0.99, 0.95)
    assert result.rounds == 0
    assert result.fidelity_out == 0.99


def test_iterative_dejmps():
    result = iterative_purification(0.7, 0.95, protocol="dejmps")
    assert result.fidelity_out >= 0.95
