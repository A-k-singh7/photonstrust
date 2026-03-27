"""Tests for enhanced blinding attack models."""

from __future__ import annotations

import pytest

from photonstrust.security.attacks.blinding import (
    countermeasure_effectiveness,
    cw_blinding_threshold_mw,
)


# ---- CW blinding threshold tests ------------------------------------------

def test_snspd_higher_threshold():
    """SNSPDs are harder to blind than InGaAs APDs."""
    t_snspd = cw_blinding_threshold_mw(detector_class="snspd")
    t_ingaas = cw_blinding_threshold_mw(detector_class="ingaas")
    assert t_snspd > t_ingaas


def test_threshold_positive():
    for dc in ["snspd", "ingaas", "si_apd"]:
        t = cw_blinding_threshold_mw(detector_class=dc)
        assert t > 0


def test_higher_de_lower_threshold():
    """Higher detection efficiency -> easier to couple blinding light."""
    t_low = cw_blinding_threshold_mw(detector_class="ingaas", detection_efficiency=0.10)
    t_high = cw_blinding_threshold_mw(detector_class="ingaas", detection_efficiency=0.30)
    assert t_low > t_high


def test_narrow_gate_harder_to_blind():
    """Narrower gate window should increase threshold."""
    t_wide = cw_blinding_threshold_mw(detector_class="ingaas", gate_width_ns=10.0)
    t_narrow = cw_blinding_threshold_mw(detector_class="ingaas", gate_width_ns=0.5)
    assert t_narrow > t_wide


# ---- Countermeasure effectiveness tests ------------------------------------

def test_no_countermeasures_vulnerable():
    r = countermeasure_effectiveness()
    assert r["residual_exploitability"] == 1.0
    assert r["assessment"] == "vulnerable"


def test_single_countermeasure_reduces():
    r = countermeasure_effectiveness(watchdog_enabled=True)
    assert r["residual_exploitability"] < 1.0
    assert r["countermeasures_applied"] == 1


def test_all_countermeasures_secure():
    r = countermeasure_effectiveness(
        watchdog_enabled=True,
        random_gating=True,
        photocurrent_monitoring=True,
    )
    assert r["residual_exploitability"] < 0.01
    assert r["assessment"] == "secure"
    assert r["countermeasures_applied"] == 3


def test_countermeasures_multiplicative():
    """Each countermeasure should further reduce exploitability."""
    r1 = countermeasure_effectiveness(watchdog_enabled=True)
    r2 = countermeasure_effectiveness(watchdog_enabled=True, random_gating=True)
    assert r2["residual_exploitability"] < r1["residual_exploitability"]
