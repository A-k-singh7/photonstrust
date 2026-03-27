"""Time-shift attack evaluator."""

from __future__ import annotations

import math

from photonstrust.security.types import VulnerabilityAssessment


def _binary_entropy(p: float) -> float:
    """Compute the binary entropy h(p) = -p*log2(p) - (1-p)*log2(1-p)."""
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -p * math.log2(p) - (1.0 - p) * math.log2(1.0 - p)


def evaluate_time_shift_attack(
    *,
    detector_cfg: dict,
    efficiency_mismatch_factor: float | None = None,
) -> VulnerabilityAssessment:
    """Evaluate vulnerability to a time-shift attack.

    Parameters
    ----------
    detector_cfg : dict
        Detector configuration; should contain ``jitter_ps_fwhm``.
    efficiency_mismatch_factor : float | None
        Pre-computed efficiency mismatch.  If *None*, it is estimated
        from the detector timing jitter.
    """
    if efficiency_mismatch_factor is not None:
        mismatch = efficiency_mismatch_factor
    else:
        jitter_ps_fwhm = float(detector_cfg.get("jitter_ps_fwhm", 50.0))
        mismatch = min(0.5, jitter_ps_fwhm / 1000.0)

    # Additional information an adversary gains
    I_add = (
        _binary_entropy(0.5 * (1.0 + mismatch))
        - _binary_entropy(0.5)
    )

    exploitability = min(1.0, mismatch * 10.0)

    # Severity classification
    if mismatch > 0.1:
        severity = "high"
    elif mismatch > 0.05:
        severity = "medium"
    else:
        severity = "low"

    notes: list[str] = [
        f"efficiency_mismatch_factor={mismatch:.6f}",
        f"I_add={I_add:.6e}",
    ]

    return VulnerabilityAssessment(
        attack_id="time_shift",
        attack_name="Time-Shift Attack",
        severity=severity,
        exploitability_score=exploitability,
        information_gain=I_add,
        metric_name="efficiency_mismatch",
        metric_value=mismatch,
        metric_unit="dimensionless",
        applicable=True,
        notes=notes,
    )
