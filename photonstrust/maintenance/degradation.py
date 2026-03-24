"""Degradation models for QKD hardware components."""

from __future__ import annotations

import math

from photonstrust.maintenance.types import ComponentHealth


def detector_pde_degradation(
    initial_pde: float,
    age_hours: float,
    *,
    detector_class: str = "snspd",
) -> float:
    """Exponential PDE decay. Returns current PDE."""
    lambdas = {"snspd": 1e-6, "ingaas": 5e-5, "si_apd": 2e-5}
    lam = lambdas.get(detector_class, 1e-5)
    return initial_pde * math.exp(-lam * age_hours)


def fiber_loss_increase(
    initial_loss_db_per_km: float,
    age_hours: float,
) -> float:
    """Linear fiber loss increase. Returns current loss dB/km."""
    rate = 0.001 / 10000  # 0.001 dB/km per 10 000 hours
    return initial_loss_db_per_km + rate * age_hours


def source_coherence_degradation(
    initial_g2: float,
    age_hours: float,
    *,
    source_type: str = "emitter_cavity",
) -> float:
    """Linear g2 increase (worse multi-photon). Returns current g2."""
    rates = {"emitter_cavity": 0.001 / 10000, "spdc": 0.002 / 10000}
    rate = rates.get(source_type, 0.001 / 10000)
    return min(1.0, initial_g2 + rate * age_hours)


def estimate_component_health(
    component_type: str,
    initial_value: float,
    age_hours: float,
    *,
    threshold: float,
    detector_class: str = "snspd",
    source_type: str = "emitter_cavity",
) -> ComponentHealth:
    """Compute component health as fraction of initial performance."""
    if component_type == "detector":
        current = detector_pde_degradation(
            initial_value, age_hours, detector_class=detector_class
        )
        performance = current / max(initial_value, 1e-30)
        # EOL: solve initial * exp(-lam * t) = threshold
        lambdas = {"snspd": 1e-6, "ingaas": 5e-5, "si_apd": 2e-5}
        lam = lambdas.get(detector_class, 1e-5)
        if initial_value > threshold and lam > 0:
            eol = math.log(initial_value / threshold) / lam
        else:
            eol = 0.0
    elif component_type == "fiber":
        current = fiber_loss_increase(initial_value, age_hours)
        performance = max(
            0, 1 - (current - initial_value) / max(threshold - initial_value, 1e-30)
        )
        rate = 0.001 / 10000
        eol = (threshold - initial_value) / rate if rate > 0 else float("inf")
    elif component_type == "source":
        current = source_coherence_degradation(
            initial_value, age_hours, source_type=source_type
        )
        performance = max(
            0, 1 - (current - initial_value) / max(threshold - initial_value, 1e-30)
        )
        rates = {"emitter_cavity": 0.001 / 10000, "spdc": 0.002 / 10000}
        rate = rates.get(source_type, 0.001 / 10000)
        eol = (threshold - initial_value) / rate if rate > 0 else float("inf")
    else:
        performance = 1.0
        eol = float("inf")

    return ComponentHealth(
        component_id=f"{component_type}_0",
        component_type=component_type,
        current_performance=max(0.0, min(1.0, performance)),
        age_hours=age_hours,
        predicted_eol_hours=eol,
        degradation_model="exponential" if component_type == "detector" else "linear",
    )
