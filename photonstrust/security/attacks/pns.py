"""Photon Number Splitting (PNS) attack evaluator."""

from __future__ import annotations

import math

from photonstrust.security.types import VulnerabilityAssessment

_APPLICABLE_PROTOCOLS = ("BB84", "BB84_DECOY")


def evaluate_pns_attack(
    *,
    mu: float,
    eta_channel: float,
    protocol_name: str,
    decoy_enabled: bool,
    nu: float = 0.0,
    omega: float = 0.0,
) -> VulnerabilityAssessment:
    """Evaluate the PNS attack for a given WCP source configuration.

    Parameters
    ----------
    mu : float
        Mean photon number of the signal state.
    eta_channel : float
        Overall channel transmittance.
    protocol_name : str
        Name of the QKD protocol in use.
    decoy_enabled : bool
        Whether decoy-state analysis is enabled.
    nu : float
        Mean photon number of the weak decoy state.
    omega : float
        Mean photon number of the vacuum decoy state.
    """
    if protocol_name not in _APPLICABLE_PROTOCOLS:
        return VulnerabilityAssessment(
            attack_id="pns",
            attack_name="Photon Number Splitting",
            severity="none",
            exploitability_score=0.0,
            information_gain=0.0,
            metric_name="p_multi",
            metric_value=0.0,
            metric_unit="probability",
            applicable=False,
            notes=[f"PNS attack not applicable to protocol {protocol_name}"],
        )

    # Multi-photon fraction for a coherent (Poissonian) source
    p_multi = 1.0 - (1.0 + mu) * math.exp(-mu)

    if decoy_enabled:
        info_leak = 0.0
    else:
        info_leak = p_multi * 1.0  # full bit per multi-photon pulse

    # Exploitability is driven by the multi-photon probability
    exploitability = min(1.0, p_multi)

    # Severity classification
    if info_leak > 0.01:
        severity = "critical"
    elif info_leak > 0.001:
        severity = "high"
    elif info_leak > 0.0001:
        severity = "medium"
    else:
        severity = "low"

    notes: list[str] = [
        f"mu={mu}, p_multi={p_multi:.6e}",
        f"decoy_enabled={decoy_enabled}",
    ]
    if decoy_enabled:
        notes.append("Decoy-state analysis bounds multi-photon information leakage to zero")

    return VulnerabilityAssessment(
        attack_id="pns",
        attack_name="Photon Number Splitting",
        severity=severity,
        exploitability_score=exploitability,
        information_gain=info_leak,
        metric_name="p_multi",
        metric_value=p_multi,
        metric_unit="probability",
        applicable=True,
        notes=notes,
    )
