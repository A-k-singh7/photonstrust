"""Tests for platform-specific quantum memory models."""

from __future__ import annotations

import math

import pytest

from photonstrust.physics.memory_platforms import (
    PLATFORM_PRESETS,
    nv_diamond_memory,
    rare_earth_afc_memory,
    trapped_ion_memory,
)


# ---- NV diamond tests ------------------------------------------------------

def test_nv_stretched_exponential():
    """NV diamond should show stretched exponential decay."""
    r0 = nv_diamond_memory(0.0)
    r1 = nv_diamond_memory(1.0)
    r5 = nv_diamond_memory(5.0)

    assert r0.fidelity > 0.99  # near-perfect at t=0
    assert r1.fidelity > 0.5   # still good at 1s (T2=1.58s)
    assert r5.fidelity > 0.5   # decayed but above 0.5
    assert r0.fidelity > r1.fidelity > r5.fidelity


def test_nv_stretch_exponent_effect():
    """Higher stretch exponent should change decay shape."""
    r_exp1 = nv_diamond_memory(1.0, stretch_exponent=1.0)
    r_exp2 = nv_diamond_memory(1.0, stretch_exponent=2.0)
    # Both should give valid fidelities
    assert 0.5 <= r_exp1.fidelity <= 1.0
    assert 0.5 <= r_exp2.fidelity <= 1.0


def test_nv_efficiency():
    r = nv_diamond_memory(0.0)
    assert r.p_store > 0
    assert r.p_retrieve > 0


def test_nv_backend_name():
    r = nv_diamond_memory(0.1)
    assert r.backend == "nv_diamond_analytic"


# ---- Trapped ion tests -----------------------------------------------------

def test_trapped_ion_long_coherence():
    """Trapped ion should maintain high fidelity for minutes."""
    r = trapped_ion_memory(60.0)  # 1 minute
    assert r.fidelity > 0.9  # T2 = 600s, so 60s << T2


def test_trapped_ion_coherence_decay():
    r0 = trapped_ion_memory(0.0)
    r300 = trapped_ion_memory(300.0)  # 5 minutes
    r600 = trapped_ion_memory(600.0)  # 10 minutes (= T2)
    assert r0.fidelity > r300.fidelity > r600.fidelity


def test_trapped_ion_high_efficiency():
    r = trapped_ion_memory(0.0)
    assert r.p_retrieve > 0.98  # 171Yb+ has very high readout


def test_trapped_ion_custom_T1():
    """Optical qubits (e.g., 40Ca+) have finite T1."""
    r = trapped_ion_memory(0.5, T1_s=1.168, T2_s=0.05)
    assert r.fidelity > 0.5
    assert r.fidelity < 1.0


# ---- Rare-earth AFC tests --------------------------------------------------

def test_afc_efficiency_formula():
    """AFC efficiency should follow d^2 * exp(-d) * exp(-7/F^2)."""
    r = rare_earth_afc_memory(0.0, optical_depth=3.0, finesse=5.0)
    d_eff = 3.0 / 5.0  # = 0.6
    expected_eta = d_eff ** 2 * math.exp(-d_eff) * math.exp(-7.0 / 25.0)
    assert abs(r.diagnostics["eta_afc"] - expected_eta) < 1e-10


def test_afc_coherence_decay():
    r0 = rare_earth_afc_memory(0.0)
    r1 = rare_earth_afc_memory(1.0)
    assert r0.fidelity > r1.fidelity


def test_afc_retrieval_positive():
    r = rare_earth_afc_memory(0.0)
    assert r.p_retrieve > 0


# ---- Platform presets tests ------------------------------------------------

def test_memory_standard_presets_are_registered():
    assert "nv_diamond" in PLATFORM_PRESETS
    assert "trapped_ion_171yb" in PLATFORM_PRESETS
    assert "rare_earth_151eu_yso" in PLATFORM_PRESETS


def test_presets_have_valid_parameters():
    for name, profile in PLATFORM_PRESETS.items():
        assert profile.T2_s > 0, f"{name}: T2 must be positive"
        assert 0 < profile.gate_fidelity <= 1, f"{name}: gate fidelity"
        assert 0 < profile.read_efficiency <= 1, f"{name}: read efficiency"
        assert 0 < profile.write_efficiency <= 1, f"{name}: write efficiency"


def test_nv_preset_matches_published():
    nv = PLATFORM_PRESETS["nv_diamond"]
    assert nv.T2_s == pytest.approx(1.58, abs=0.01)  # Bradley et al.
