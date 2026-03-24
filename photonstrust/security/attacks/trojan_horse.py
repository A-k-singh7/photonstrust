"""Trojan Horse Attack (THA) evaluator."""

from __future__ import annotations

from photonstrust.security.types import VulnerabilityAssessment


def evaluate_trojan_horse_attack(
    *,
    isolator_attenuation_db: float,
    filter_bandwidth_nm: float,
    modulator_extinction_ratio_db: float,
    rep_rate_hz: float,
) -> VulnerabilityAssessment:
    """Evaluate vulnerability to a Trojan Horse Attack.

    Parameters
    ----------
    isolator_attenuation_db : float
        One-way attenuation of the optical isolator in dB.
    filter_bandwidth_nm : float
        Spectral filter bandwidth in nm.
    modulator_extinction_ratio_db : float
        Extinction ratio of the modulator in dB.
    rep_rate_hz : float
        Pulse repetition rate in Hz.
    """
    # Round-trip attenuation through the isolator
    att_total_db = 2.0 * isolator_attenuation_db

    # Information leakage: fraction of light that can be reflected back
    # modulated by the modulator's imperfect extinction
    I_leak = 10 ** (-att_total_db / 10.0) * (
        1.0 - 10 ** (-modulator_extinction_ratio_db / 10.0)
    )

    # Exploitability normalised to [0, 1]
    exploitability = min(1.0, I_leak * 1e3)  # scale so 1e-3 maps to ~1.0

    # Severity classification
    if I_leak > 1e-3:
        severity = "critical"
    elif I_leak > 1e-6:
        severity = "high"
    elif I_leak > 1e-10:
        severity = "medium"
    else:
        severity = "low"

    notes: list[str] = [
        f"isolator_attenuation_db={isolator_attenuation_db}",
        f"att_total_db (round-trip)={att_total_db}",
        f"modulator_extinction_ratio_db={modulator_extinction_ratio_db}",
        f"I_leak={I_leak:.6e}",
    ]

    return VulnerabilityAssessment(
        attack_id="trojan_horse",
        attack_name="Trojan Horse Attack",
        severity=severity,
        exploitability_score=exploitability,
        information_gain=I_leak,
        metric_name="I_leak",
        metric_value=I_leak,
        metric_unit="fraction",
        applicable=True,
        notes=notes,
    )
