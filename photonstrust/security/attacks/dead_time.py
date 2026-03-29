"""Detector dead-time attack evaluator."""

from __future__ import annotations

from photonstrust.security.types import VulnerabilityAssessment


def evaluate_dead_time_attack(
    *,
    dead_time_ns: float,
    rep_rate_hz: float,
    detector_count: int = 2,
) -> VulnerabilityAssessment:
    """Evaluate vulnerability to a detector dead-time attack.

    Parameters
    ----------
    dead_time_ns : float
        Detector dead time in nanoseconds.
    rep_rate_hz : float
        Pulse repetition rate in Hz.
    detector_count : int
        Number of detectors in the receiver.
    """
    # Probability that a bright pulse during dead time can force a click
    # on the target detector
    p_control = min(1.0, dead_time_ns * 1e-9 * rep_rate_hz)

    exploitability = p_control
    information_gain = p_control  # full control → full bit

    # Severity classification
    if p_control > 0.5:
        severity = "critical"
    elif p_control > 0.1:
        severity = "high"
    elif p_control > 0.01:
        severity = "medium"
    else:
        severity = "low"

    notes: list[str] = [
        f"dead_time_ns={dead_time_ns}",
        f"rep_rate_hz={rep_rate_hz:.2e}",
        f"detector_count={detector_count}",
        f"p_control={p_control:.6f}",
    ]

    return VulnerabilityAssessment(
        attack_id="dead_time",
        attack_name="Detector Dead-Time Attack",
        severity=severity,
        exploitability_score=exploitability,
        information_gain=information_gain,
        metric_name="p_control",
        metric_value=p_control,
        metric_unit="probability",
        applicable=True,
        notes=notes,
    )
