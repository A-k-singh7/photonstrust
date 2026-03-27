"""Countermeasure effectiveness evaluators."""

from __future__ import annotations

from photonstrust.security.types import CountermeasureEffectiveness

# Detection probability look-up per detector class for the watchdog CM.
_WATCHDOG_DETECTION_PROB: dict[str, float] = {
    "snspd": 0.99,
    "ingaas": 0.95,
    "si_apd": 0.93,
}


def evaluate_countermeasure_decoy_state(
    mu: float,
    nu: float,
    omega: float,
) -> CountermeasureEffectiveness:
    """Decoy-state protocol countermeasure against PNS attack."""
    if mu > 0 and nu > 0 and omega > 0:
        detection_prob = 0.999
        residual_risk = 0.001
        notes = ["All three decoy intensities provided and positive"]
    else:
        detection_prob = 0.0
        residual_risk = 1.0
        notes = ["Incomplete decoy-state configuration"]

    return CountermeasureEffectiveness(
        countermeasure_id="decoy_state",
        name="Decoy-State Protocol",
        detection_probability=detection_prob,
        residual_risk=residual_risk,
        notes=notes,
    )


def evaluate_countermeasure_watchdog(
    detector_class: str,
) -> CountermeasureEffectiveness:
    """Watchdog detector countermeasure against blinding."""
    detection_prob = _WATCHDOG_DETECTION_PROB.get(
        detector_class.lower(), 0.90
    )
    residual_risk = 1.0 - detection_prob

    return CountermeasureEffectiveness(
        countermeasure_id="watchdog_detector",
        name="Watchdog Detector",
        detection_probability=detection_prob,
        residual_risk=residual_risk,
        notes=[f"detector_class={detector_class}, detection_prob={detection_prob}"],
    )


def evaluate_countermeasure_optical_isolator(
    isolator_attenuation_db: float,
) -> CountermeasureEffectiveness:
    """Optical isolator countermeasure against Trojan Horse Attack."""
    detection_prob = min(1.0, isolator_attenuation_db / 100.0)
    residual_risk = 10 ** (-isolator_attenuation_db / 10.0)

    return CountermeasureEffectiveness(
        countermeasure_id="optical_isolator",
        name="Optical Isolator",
        detection_probability=detection_prob,
        residual_risk=residual_risk,
        notes=[f"isolator_attenuation_db={isolator_attenuation_db}"],
    )


def evaluate_countermeasure_random_gating(
    gate_width_ns: float,
    gate_period_ns: float,
) -> CountermeasureEffectiveness:
    """Random gating countermeasure against blinding."""
    ratio = gate_width_ns / gate_period_ns if gate_period_ns > 0 else 1.0
    detection_prob = 1.0 - ratio
    residual_risk = ratio

    return CountermeasureEffectiveness(
        countermeasure_id="random_gating",
        name="Random Gating",
        detection_probability=detection_prob,
        residual_risk=residual_risk,
        notes=[f"gate_width_ns={gate_width_ns}, gate_period_ns={gate_period_ns}"],
    )


def evaluate_countermeasure_active_dead_time(
    dead_time_ns: float,
) -> CountermeasureEffectiveness:
    """Active dead-time management countermeasure."""
    detection_prob = 0.9
    residual_risk = 0.1

    return CountermeasureEffectiveness(
        countermeasure_id="active_dead_time",
        name="Active Dead-Time Management",
        detection_probability=detection_prob,
        residual_risk=residual_risk,
        notes=[f"dead_time_ns={dead_time_ns}"],
    )


def evaluate_countermeasure_efficiency_equalization() -> CountermeasureEffectiveness:
    """Efficiency equalization countermeasure against time-shift attack."""
    return CountermeasureEffectiveness(
        countermeasure_id="efficiency_equalization",
        name="Efficiency Equalization",
        detection_probability=0.999,
        residual_risk=0.001,
        notes=["Hardware-level detector efficiency equalization applied"],
    )
