"""Tests for Feature 6: Quantum Hacking & Countermeasure Modeling."""

from __future__ import annotations

import json

from photonstrust.security.attacks.blinding import evaluate_blinding_attack
from photonstrust.security.attacks.dead_time import evaluate_dead_time_attack
from photonstrust.security.attacks.pns import evaluate_pns_attack
from photonstrust.security.attacks.time_shift import evaluate_time_shift_attack
from photonstrust.security.attacks.trojan_horse import evaluate_trojan_horse_attack
from photonstrust.security.assessment import run_threat_assessment


# ---------------------------------------------------------------------------
# 1. PNS attack: high mu, no decoy -> critical or high
# ---------------------------------------------------------------------------
def test_pns_attack_high_mu_no_decoy() -> None:
    result = evaluate_pns_attack(
        mu=0.8,
        eta_channel=0.1,
        protocol_name="BB84",
        decoy_enabled=False,
    )
    assert result.applicable is True
    assert result.severity in ("critical", "high")


# ---------------------------------------------------------------------------
# 2. PNS attack: with decoy -> low or none
# ---------------------------------------------------------------------------
def test_pns_attack_with_decoy() -> None:
    result = evaluate_pns_attack(
        mu=0.5,
        eta_channel=0.1,
        protocol_name="BB84_DECOY",
        decoy_enabled=True,
        nu=0.1,
        omega=0.001,
    )
    assert result.applicable is True
    assert result.severity in ("low", "none")


# ---------------------------------------------------------------------------
# 3. Blinding: SNSPD detector -> low exploitability
# ---------------------------------------------------------------------------
def test_blinding_snspd_low_risk() -> None:
    result = evaluate_blinding_attack(
        detector_class="snspd",
        detector_cfg={},
    )
    assert result.exploitability_score < 0.5


# ---------------------------------------------------------------------------
# 4. Blinding: InGaAs detector, no watchdog -> high or critical
# ---------------------------------------------------------------------------
def test_blinding_ingaas_high_risk() -> None:
    result = evaluate_blinding_attack(
        detector_class="ingaas",
        detector_cfg={},
    )
    assert result.severity in ("critical", "high")


# ---------------------------------------------------------------------------
# 5. Trojan horse: 60 dB isolator -> low or none
# ---------------------------------------------------------------------------
def test_trojan_horse_good_isolator() -> None:
    result = evaluate_trojan_horse_attack(
        isolator_attenuation_db=60.0,
        filter_bandwidth_nm=1.0,
        modulator_extinction_ratio_db=30.0,
        rep_rate_hz=1e9,
    )
    assert result.severity in ("low", "none")


# ---------------------------------------------------------------------------
# 6. Trojan horse: 0 dB isolator -> critical or high
# ---------------------------------------------------------------------------
def test_trojan_horse_no_isolator() -> None:
    result = evaluate_trojan_horse_attack(
        isolator_attenuation_db=0.0,
        filter_bandwidth_nm=1.0,
        modulator_extinction_ratio_db=30.0,
        rep_rate_hz=1e9,
    )
    assert result.severity in ("critical", "high")


# ---------------------------------------------------------------------------
# 7. Time-shift: jitter=30ps -> low severity
# ---------------------------------------------------------------------------
def test_time_shift_low_mismatch() -> None:
    result = evaluate_time_shift_attack(
        detector_cfg={"jitter_ps_fwhm": 30.0},
    )
    assert result.severity == "low"


# ---------------------------------------------------------------------------
# 8. Dead time: 1000ns at 1 GHz -> high or critical
# ---------------------------------------------------------------------------
def test_dead_time_high_rate() -> None:
    result = evaluate_dead_time_attack(
        dead_time_ns=1000.0,
        rep_rate_hz=1e9,
    )
    assert result.severity in ("critical", "high")


# ---------------------------------------------------------------------------
# 9. Full end-to-end threat assessment for BB84_DECOY
# ---------------------------------------------------------------------------
def test_full_threat_assessment_bb84_decoy() -> None:
    scenario = {
        "scenario_id": "test_bb84_decoy",
        "protocol_name": "BB84_DECOY",
        "detector_class": "snspd",
        "source": {
            "mu": 0.5,
            "nu": 0.1,
            "omega": 0.001,
            "eta_channel": 0.1,
            "decoy_enabled": True,
        },
        "detector": {
            "dead_time_ns": 50.0,
            "jitter_ps_fwhm": 30.0,
            "rep_rate_hz": 1e9,
        },
        "optics": {
            "isolator_attenuation_db": 40.0,
            "filter_bandwidth_nm": 1.0,
            "modulator_extinction_ratio_db": 30.0,
        },
        "countermeasures": {
            "decoy_state": True,
        },
    }
    result = run_threat_assessment(scenario)
    assert result.protocol_name == "BB84_DECOY"
    assert result.scenario_id == "test_bb84_decoy"
    assert len(result.vulnerabilities) > 0
    assert isinstance(result.overall_risk_score, float)
    assert result.overall_severity in ("none", "low", "medium", "high", "critical")


# ---------------------------------------------------------------------------
# 10. Serialisation round-trip
# ---------------------------------------------------------------------------
def test_threat_assessment_serialization() -> None:
    scenario = {
        "scenario_id": "serial_test",
        "protocol_name": "BB84_DECOY",
        "detector_class": "snspd",
        "source": {"mu": 0.5, "nu": 0.1, "omega": 0.001, "eta_channel": 0.1},
        "detector": {"dead_time_ns": 50.0, "jitter_ps_fwhm": 30.0},
        "optics": {"isolator_attenuation_db": 40.0, "modulator_extinction_ratio_db": 30.0},
    }
    result = run_threat_assessment(scenario)
    d = result.as_dict()
    # Must be JSON-serializable
    serialized = json.dumps(d)
    assert isinstance(serialized, str)
    parsed = json.loads(serialized)
    assert parsed["scenario_id"] == "serial_test"
    assert "vulnerabilities" in parsed
    assert "countermeasures" in parsed


# ---------------------------------------------------------------------------
# 11. Countermeasures reduce risk
# ---------------------------------------------------------------------------
def test_countermeasure_reduces_risk() -> None:
    base_scenario = {
        "scenario_id": "no_cm",
        "protocol_name": "BB84",
        "detector_class": "ingaas",
        "source": {
            "mu": 0.8,
            "eta_channel": 0.1,
            "decoy_enabled": False,
        },
        "detector": {
            "dead_time_ns": 200.0,
            "jitter_ps_fwhm": 100.0,
            "rep_rate_hz": 1e9,
        },
        "optics": {
            "isolator_attenuation_db": 10.0,
            "modulator_extinction_ratio_db": 10.0,
        },
        "countermeasures": {},
    }
    hardened_scenario = {
        "scenario_id": "with_cm",
        "protocol_name": "BB84",
        "detector_class": "ingaas",
        "source": {
            "mu": 0.8,
            "eta_channel": 0.1,
            "decoy_enabled": False,
        },
        "detector": {
            "dead_time_ns": 200.0,
            "jitter_ps_fwhm": 100.0,
            "rep_rate_hz": 1e9,
            "watchdog_enabled": True,
        },
        "optics": {
            "isolator_attenuation_db": 10.0,
            "modulator_extinction_ratio_db": 10.0,
        },
        "countermeasures": {
            "watchdog_detector": True,
            "efficiency_equalization": True,
            "active_dead_time": True,
        },
    }
    base_result = run_threat_assessment(base_scenario)
    hardened_result = run_threat_assessment(hardened_scenario)
    assert hardened_result.overall_risk_score < base_result.overall_risk_score
