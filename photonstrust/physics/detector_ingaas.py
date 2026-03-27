"""InGaAs avalanche photodiode (APD) detector models.

Physics-based models for InGaAs/InP single-photon APDs used in
telecom-wavelength (1310/1550 nm) QKD systems, including afterpulsing,
temperature-dependent dark count rate, and gated detection.

Key references:
    - Cova et al., J. Mod. Opt. 51, 1267 (2004) -- APD review
    - Yuan et al., APL 91, 041114 (2007) -- afterpulsing model
    - Zhang et al., APL 95, 091103 (2009) -- high-speed gated InGaAs
    - Namekata et al., Opt. Express 14, 10043 (2006) -- sinusoidal gating
    - Comandar et al., APL 104, 021101 (2014) -- self-differencing

Models:
    - Afterpulsing: p_AP = P_AP0 * exp(-t_hold / tau_trap)
    - Temperature DCR: DCR = DCR_0 * exp(-E_a / (k_B * T))
    - Gated detection: per-gate click probability
    - Detection efficiency: eta(V_ex) with overbias dependence
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


# Boltzmann constant in eV/K
K_B_EV = 8.617333262e-5  # physics-constant-ok


@dataclass(frozen=True)
class InGaAsAPDProfile:
    """InGaAs APD detector profile."""
    detection_efficiency: float     # peak PDE
    dark_count_rate_cps: float      # DCR at operating temperature
    afterpulse_probability: float   # P_AP0 (initial afterpulse prob)
    trap_lifetime_us: float         # carrier trapping lifetime (us)
    gate_frequency_mhz: float      # gating frequency (MHz)
    gate_width_ns: float            # gate window width (ns)
    hold_off_us: float              # afterpulse hold-off time (us)
    operating_temp_K: float         # operating temperature
    breakdown_voltage_V: float      # avalanche breakdown voltage
    excess_bias_V: float            # overbias above breakdown
    activation_energy_eV: float     # thermal activation energy for DCR


# ---------------------------------------------------------------------------
# Preset profiles
# ---------------------------------------------------------------------------

INGAAS_APD_PRESETS: dict[str, InGaAsAPDProfile] = {
    "id230": InGaAsAPDProfile(
        detection_efficiency=0.25,
        dark_count_rate_cps=2000.0,
        afterpulse_probability=0.05,
        trap_lifetime_us=5.0,
        gate_frequency_mhz=1.0,     # free-running mode
        gate_width_ns=50.0,
        hold_off_us=10.0,
        operating_temp_K=223.0,     # -50 C
        breakdown_voltage_V=55.0,
        excess_bias_V=3.0,
        activation_energy_eV=0.22,  # InGaAs bandgap-related
    ),
    "id210": InGaAsAPDProfile(
        detection_efficiency=0.10,
        dark_count_rate_cps=500.0,
        afterpulse_probability=0.03,
        trap_lifetime_us=3.0,
        gate_frequency_mhz=100.0,   # gated mode
        gate_width_ns=2.5,
        hold_off_us=20.0,
        operating_temp_K=233.0,
        breakdown_voltage_V=50.0,
        excess_bias_V=2.0,
        activation_energy_eV=0.22,
    ),
    "high_rate_spad": InGaAsAPDProfile(
        detection_efficiency=0.30,
        dark_count_rate_cps=5000.0,
        afterpulse_probability=0.10,
        trap_lifetime_us=4.0,
        gate_frequency_mhz=1000.0,  # GHz gating (Zhang 2009)
        gate_width_ns=0.2,
        hold_off_us=1.0,
        operating_temp_K=243.0,
        breakdown_voltage_V=52.0,
        excess_bias_V=1.5,
        activation_energy_eV=0.22,
    ),
}


# ---------------------------------------------------------------------------
# Afterpulse probability
# ---------------------------------------------------------------------------

def ingaas_afterpulse_probability(
    hold_off_us: float,
    *,
    p_ap0: float = 0.05,
    trap_lifetime_us: float = 5.0,
) -> float:
    """Afterpulse probability after a given hold-off time.

    Trapped carriers release with exponential decay:

        p_AP(t) = P_AP0 * exp(-t_hold / tau_trap)

    Longer hold-off reduces afterpulsing at the cost of reduced
    maximum count rate.

    Args:
        hold_off_us: Hold-off (dead) time in microseconds
        p_ap0: Initial afterpulse probability (at t=0)
        trap_lifetime_us: Carrier trap lifetime in microseconds

    Returns:
        Afterpulse probability

    Ref: Yuan et al., APL 91, 041114 (2007)
    """
    t = max(0.0, float(hold_off_us))
    p0 = max(0.0, min(1.0, float(p_ap0)))
    tau = max(1e-6, float(trap_lifetime_us))

    return p0 * math.exp(-t / tau)


# ---------------------------------------------------------------------------
# Temperature-dependent dark count rate
# ---------------------------------------------------------------------------

def ingaas_dcr_temperature(
    temperature_K: float,
    *,
    dcr_ref: float = 2000.0,
    temp_ref_K: float = 223.0,
    activation_energy_eV: float = 0.22,
) -> float:
    """Temperature-dependent dark count rate for InGaAs APD.

    The DCR follows an Arrhenius-type thermal activation:

        DCR(T) = DCR_0 * exp(-E_a / (k_B * T))

    Normalized to the reference temperature:

        DCR(T) = DCR_ref * exp(E_a/k_B * (1/T_ref - 1/T))

    Args:
        temperature_K: Operating temperature (K)
        dcr_ref: DCR at reference temperature (counts/s)
        temp_ref_K: Reference temperature (K)
        activation_energy_eV: Thermal activation energy (eV)

    Returns:
        Dark count rate (counts/s)

    Ref: Cova et al., J. Mod. Opt. 51, 1267 (2004)
    """
    T = max(1.0, float(temperature_K))
    T_ref = max(1.0, float(temp_ref_K))
    E_a = max(0.0, float(activation_energy_eV))
    dcr_0 = max(0.0, float(dcr_ref))

    exponent = (E_a / K_B_EV) * (1.0 / T_ref - 1.0 / T)
    # Clamp to prevent overflow
    exponent = max(-100.0, min(100.0, exponent))

    return dcr_0 * math.exp(exponent)


# ---------------------------------------------------------------------------
# Detection efficiency vs excess bias
# ---------------------------------------------------------------------------

def ingaas_efficiency_vs_bias(
    excess_bias_V: float,
    *,
    eta_max: float = 0.30,
    v_characteristic: float = 2.0,
) -> float:
    """Detection efficiency as a function of excess bias voltage.

    The detection efficiency rises with excess bias:

        eta(V_ex) = eta_max * (1 - exp(-V_ex / V_c))

    where V_c is a characteristic voltage scale.

    Args:
        excess_bias_V: Voltage above breakdown (V)
        v_characteristic: Characteristic voltage (V)
        eta_max: Maximum achievable efficiency

    Returns:
        Detection efficiency
    """
    V_ex = max(0.0, float(excess_bias_V))
    V_c = max(0.01, float(v_characteristic))
    eta_m = max(0.0, min(1.0, float(eta_max)))

    return eta_m * (1.0 - math.exp(-V_ex / V_c))


# ---------------------------------------------------------------------------
# Gated detection probability
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GatedDetectionResult:
    """Result of gated InGaAs APD detection calculation."""
    p_click: float               # per-gate click probability (signal)
    p_dark: float                # per-gate dark click probability
    p_afterpulse: float          # afterpulse probability
    p_total_click: float         # total per-gate click probability
    effective_rate_cps: float    # effective detection rate
    max_rate_cps: float          # maximum rate (limited by hold-off)
    qber_contribution: float     # QBER from dark counts + afterpulses
    diagnostics: dict[str, Any] = field(default_factory=dict)


def ingaas_gated_detection(
    mean_photon_per_gate: float,
    *,
    detection_efficiency: float = 0.25,
    dark_count_rate_cps: float = 2000.0,
    gate_frequency_mhz: float = 1.0,
    gate_width_ns: float = 2.5,
    afterpulse_probability: float = 0.05,
    hold_off_us: float = 10.0,
    trap_lifetime_us: float = 5.0,
) -> GatedDetectionResult:
    """Per-gate detection model for gated InGaAs APD.

    Computes the click probability per gate window including signal,
    dark counts, and afterpulsing contributions.

    Signal click: p_click = 1 - exp(-mu * eta)
    Dark click:   p_dark = DCR * gate_width
    Afterpulse:   p_ap from hold-off model

    Args:
        mean_photon_per_gate: Mean photon number per gate window
        detection_efficiency: Detection efficiency
        dark_count_rate_cps: Dark count rate (counts/s)
        gate_frequency_mhz: Gate repetition rate (MHz)
        gate_width_ns: Gate window width (ns)
        afterpulse_probability: P_AP0
        hold_off_us: Hold-off time (us)
        trap_lifetime_us: Trap carrier lifetime (us)

    Returns:
        GatedDetectionResult with per-gate probabilities
    """
    mu = max(0.0, float(mean_photon_per_gate))
    eta = max(0.0, min(1.0, float(detection_efficiency)))
    dcr = max(0.0, float(dark_count_rate_cps))
    f_gate = max(1e-3, float(gate_frequency_mhz)) * 1e6  # Hz
    t_gate = max(1e-3, float(gate_width_ns)) * 1e-9  # s

    # Signal click probability (Poissonian)
    p_click = 1.0 - math.exp(-mu * eta)

    # Dark click probability per gate
    p_dark = min(1.0, dcr * t_gate)

    # Afterpulse probability
    p_ap = ingaas_afterpulse_probability(
        hold_off_us, p_ap0=afterpulse_probability, trap_lifetime_us=trap_lifetime_us,
    )

    # Total per-gate click probability
    # p_total = 1 - (1-p_click)(1-p_dark)(1-p_ap)
    p_total = 1.0 - (1.0 - p_click) * (1.0 - p_dark) * (1.0 - p_ap)
    p_total = max(0.0, min(1.0, p_total))

    # Maximum rate limited by hold-off
    hold_off_s = max(1e-12, float(hold_off_us) * 1e-6)
    max_rate = min(f_gate, 1.0 / hold_off_s)

    # Effective detection rate
    eff_rate = p_total * min(f_gate, max_rate)

    # QBER contribution from noise clicks
    noise_clicks = p_dark + p_ap
    if p_total > 0:
        qber_noise = 0.5 * noise_clicks / p_total
    else:
        qber_noise = 0.0
    qber_noise = min(0.5, qber_noise)

    return GatedDetectionResult(
        p_click=p_click,
        p_dark=p_dark,
        p_afterpulse=p_ap,
        p_total_click=p_total,
        effective_rate_cps=eff_rate,
        max_rate_cps=max_rate,
        qber_contribution=qber_noise,
        diagnostics={
            "mu": mu,
            "eta": eta,
            "gate_frequency_hz": f_gate,
            "gate_width_s": t_gate,
            "hold_off_s": hold_off_s,
        },
    )
