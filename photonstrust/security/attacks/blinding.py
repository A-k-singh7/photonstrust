"""Detector blinding attack evaluator."""

from __future__ import annotations

from photonstrust.security.types import VulnerabilityAssessment

# Blinding threshold power in milliwatts for each detector class.
_BLINDING_THRESHOLDS_MW: dict[str, float] = {
    "snspd": 5.0,
    "ingaas": 0.05,
    "si_apd": 0.1,
}


def evaluate_blinding_attack(
    *,
    detector_class: str,
    detector_cfg: dict,
) -> VulnerabilityAssessment:
    """Evaluate detector blinding vulnerability.

    Parameters
    ----------
    detector_class : str
        Type of single-photon detector (snspd, ingaas, si_apd).
    detector_cfg : dict
        Detector configuration; may include ``watchdog_enabled`` and
        ``random_gating`` boolean flags.
    """
    threshold_mw = _BLINDING_THRESHOLDS_MW.get(detector_class.lower(), 0.1)

    # Lower threshold = easier to blind = higher exploitability
    exploitability = min(1.0, 1.0 / max(0.001, threshold_mw))

    notes: list[str] = [
        f"detector_class={detector_class}",
        f"blinding_threshold={threshold_mw} mW",
    ]

    # Countermeasure modifiers
    if detector_cfg.get("watchdog_enabled", False):
        exploitability *= 0.05
        notes.append("Watchdog detector enabled: exploitability reduced by 95%")

    if detector_cfg.get("random_gating", False):
        exploitability *= 0.15
        notes.append("Random gating enabled: exploitability reduced by 85%")

    # Information gain: full bit if detector is fully controllable
    information_gain = exploitability

    # Severity classification
    if exploitability > 0.7:
        severity = "critical"
    elif exploitability > 0.4:
        severity = "high"
    elif exploitability > 0.1:
        severity = "medium"
    elif exploitability > 0.01:
        severity = "low"
    else:
        severity = "none"

    return VulnerabilityAssessment(
        attack_id="blinding",
        attack_name="Detector Blinding",
        severity=severity,
        exploitability_score=exploitability,
        information_gain=information_gain,
        metric_name="blinding_threshold",
        metric_value=threshold_mw,
        metric_unit="mW",
        applicable=True,
        notes=notes,
    )
