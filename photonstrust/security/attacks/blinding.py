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


# ---------------------------------------------------------------------------
# CW blinding threshold model (physics-based)
# ---------------------------------------------------------------------------

def cw_blinding_threshold_mw(
    *,
    detector_class: str,
    detection_efficiency: float = 0.25,
    bias_ratio: float = 0.95,
    gate_width_ns: float = 2.5,
) -> float:
    """Physics-based CW blinding power threshold.

    For APDs, the blinding power must exceed the quench/recharge
    current to keep the detector in linear mode:

        P_blind ~ V_bias * I_quench / eta_coupling

    For SNSPDs, blinding requires exceeding the critical current
    via photon-induced hotspot:

        P_blind ~ Phi_0 * I_c * w / (eta * lambda)

    Simplified model: threshold scales with detector hardness
    and bias conditions.

    Args:
        detector_class: "snspd", "ingaas", or "si_apd"
        detection_efficiency: Detector efficiency (affects coupling)
        bias_ratio: Bias current / critical current ratio
        gate_width_ns: Gate width (narrower gate = harder to blind)

    Returns:
        Blinding threshold power in milliwatts

    Ref: Lydersen et al., Nature Photon. 4, 686 (2010)
    """
    base = _BLINDING_THRESHOLDS_MW.get(detector_class.lower(), 0.1)

    # Higher DE = easier coupling for attacker -> lower threshold
    de_factor = max(0.01, float(detection_efficiency))
    # Lower bias ratio = farther from breakdown -> harder to blind
    bias_factor = max(0.01, min(1.0, float(bias_ratio)))
    # Narrower gate window = harder to time the attack
    gate_factor = max(0.1, float(gate_width_ns)) / 10.0

    threshold = base / de_factor * (1.0 - 0.5 * bias_factor) / max(0.01, gate_factor)
    return max(0.001, threshold)


def countermeasure_effectiveness(
    *,
    watchdog_enabled: bool = False,
    random_gating: bool = False,
    photocurrent_monitoring: bool = False,
    detector_class: str = "ingaas",
) -> dict:
    """Evaluate combined countermeasure effectiveness against blinding.

    Each countermeasure reduces the attack success probability
    independently (multiplicative model).

    Args:
        watchdog_enabled: Secondary detector monitoring
        random_gating: Randomized gate timing
        photocurrent_monitoring: DC photocurrent watchdog
        detector_class: Detector type

    Returns:
        Dict with residual exploitability and countermeasure breakdown
    """
    residual = 1.0
    measures: list[dict] = []

    if watchdog_enabled:
        # Watchdog detects anomalous photocurrent
        reduction = 0.95
        residual *= (1.0 - reduction)
        measures.append({"name": "watchdog_detector", "reduction": reduction})

    if random_gating:
        # Random gate timing prevents synchronization
        reduction = 0.85
        residual *= (1.0 - reduction)
        measures.append({"name": "random_gating", "reduction": reduction})

    if photocurrent_monitoring:
        # DC photocurrent monitoring detects CW illumination
        reduction = 0.90
        residual *= (1.0 - reduction)
        measures.append({"name": "photocurrent_monitoring", "reduction": reduction})

    return {
        "detector_class": detector_class,
        "residual_exploitability": residual,
        "countermeasures_applied": len(measures),
        "countermeasure_details": measures,
        "assessment": "secure" if residual < 0.01 else "vulnerable",
    }
