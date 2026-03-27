"""Superconducting nanowire single-photon detector (SNSPD) models.

Physics-based models for SNSPD count rate saturation, kinetic inductance
recovery, and detection efficiency as functions of bias current and
wavelength.

Key references:
    - Natarajan et al., Supercond. Sci. Tech. 25, 063001 (2012) -- review
    - Marsili et al., Nature Photon. 7, 210 (2013) -- 93% system DE
    - Kerman et al., APL 88, 111116 (2006) -- kinetic inductance model
    - Vodolazov, PRB 92, 054510 (2015) -- hotspot relaxation model
    - You et al., Nanophotonics 9, 2673 (2020) -- materials review

Models:
    - Count rate saturation: CR_out = CR_in * eta / (1 + CR_in * eta * tau)
    - Recovery time: tau = L_k / R_load (kinetic inductance limited)
    - Wavelength-dependent DE: sigmoid cutoff at gap energy
    - Timing jitter: dependent on nanowire geometry and bias
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SNSPDProfile:
    """SNSPD material and geometry profile."""
    material: str                    # e.g. "NbN", "WSi", "MoSi"
    system_detection_efficiency: float  # peak SDE at optimal bias
    dark_count_rate_cps: float       # intrinsic dark count rate (counts/s)
    timing_jitter_ps: float          # FWHM jitter (ps)
    recovery_time_ns: float          # dead time / recovery time (ns)
    kinetic_inductance_nH: float     # nanowire kinetic inductance (nH)
    load_resistance_ohm: float       # readout impedance (Ohm)
    operating_temp_K: float          # operating temperature (K)
    critical_temp_K: float           # superconducting Tc (K)
    cutoff_wavelength_nm: float      # long-wavelength cutoff (nm)
    active_area_um2: float           # sensitive area (um^2)


# ---------------------------------------------------------------------------
# Material presets from published experiments
# ---------------------------------------------------------------------------

SNSPD_MATERIAL_PRESETS: dict[str, SNSPDProfile] = {
    "NbN": SNSPDProfile(
        material="NbN",
        system_detection_efficiency=0.93,   # Marsili et al. 2013
        dark_count_rate_cps=100.0,
        timing_jitter_ps=68.0,              # Marsili et al. 2013
        recovery_time_ns=40.0,
        kinetic_inductance_nH=800.0,        # typical 100 um meander
        load_resistance_ohm=50.0,
        operating_temp_K=1.8,
        critical_temp_K=10.0,
        cutoff_wavelength_nm=2000.0,
        active_area_um2=225.0,              # 15 x 15 um
    ),
    "WSi": SNSPDProfile(
        material="WSi",
        system_detection_efficiency=0.93,   # Marsili et al. 2013 (at 1550nm)
        dark_count_rate_cps=10.0,           # lower DCR than NbN
        timing_jitter_ps=150.0,
        recovery_time_ns=100.0,             # higher Lk
        kinetic_inductance_nH=2000.0,
        load_resistance_ohm=50.0,
        operating_temp_K=0.12,              # sub-Kelvin
        critical_temp_K=3.5,
        cutoff_wavelength_nm=5000.0,        # broader spectral response
        active_area_um2=400.0,
    ),
    "MoSi": SNSPDProfile(
        material="MoSi",
        system_detection_efficiency=0.87,   # Verma et al. 2015
        dark_count_rate_cps=30.0,
        timing_jitter_ps=76.0,
        recovery_time_ns=50.0,
        kinetic_inductance_nH=1000.0,
        load_resistance_ohm=50.0,
        operating_temp_K=0.8,
        critical_temp_K=7.4,
        cutoff_wavelength_nm=3000.0,
        active_area_um2=225.0,
    ),
}


# ---------------------------------------------------------------------------
# Count rate saturation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SNSPDCountRateResult:
    """Result of SNSPD count rate calculation."""
    input_rate_cps: float
    output_rate_cps: float
    detection_efficiency: float
    saturated_efficiency: float
    recovery_time_ns: float
    max_count_rate_cps: float
    saturation_fraction: float
    diagnostics: dict[str, Any] = field(default_factory=dict)


def snspd_count_rate_saturation(
    input_rate_cps: float,
    *,
    detection_efficiency: float = 0.93,
    recovery_time_ns: float = 40.0,
) -> SNSPDCountRateResult:
    """Compute SNSPD output count rate with dead-time saturation.

    The output count rate follows the blocking model:

        CR_out = CR_in * eta / (1 + CR_in * eta * tau)

    At high input rates, the detector saturates at CR_max = 1/tau.

    Args:
        input_rate_cps: Input photon rate (counts/s)
        detection_efficiency: Intrinsic detection efficiency
        recovery_time_ns: Recovery/dead time (ns)

    Returns:
        SNSPDCountRateResult with saturated count rate

    Ref: Kerman et al., APL 88, 111116 (2006)
    """
    cr_in = max(0.0, float(input_rate_cps))
    eta = max(0.0, min(1.0, float(detection_efficiency)))
    tau_s = max(1e-15, float(recovery_time_ns) * 1e-9)

    # Maximum count rate (1/tau)
    cr_max = 1.0 / tau_s

    # Blocking model
    cr_detected = cr_in * eta
    cr_out = cr_detected / (1.0 + cr_detected * tau_s)

    # Effective (saturated) efficiency
    if cr_in > 0:
        eta_eff = cr_out / cr_in
    else:
        eta_eff = eta

    # Saturation fraction: how close to max rate
    sat_frac = cr_out / cr_max if cr_max > 0 else 0.0

    return SNSPDCountRateResult(
        input_rate_cps=cr_in,
        output_rate_cps=cr_out,
        detection_efficiency=eta,
        saturated_efficiency=eta_eff,
        recovery_time_ns=float(recovery_time_ns),
        max_count_rate_cps=cr_max,
        saturation_fraction=min(1.0, sat_frac),
        diagnostics={
            "tau_s": tau_s,
            "cr_detected_no_deadtime": cr_detected,
        },
    )


# ---------------------------------------------------------------------------
# Recovery time from kinetic inductance
# ---------------------------------------------------------------------------

def snspd_recovery_time(
    kinetic_inductance_nH: float,
    load_resistance_ohm: float = 50.0,
) -> float:
    """Compute SNSPD recovery time from kinetic inductance.

    The recovery time is determined by the L/R time constant:

        tau = L_k / R_load

    where L_k is the kinetic inductance of the nanowire and R_load
    is the readout impedance.

    Args:
        kinetic_inductance_nH: Kinetic inductance in nanohenries
        load_resistance_ohm: Load/readout resistance in ohms

    Returns:
        Recovery time in nanoseconds

    Ref: Kerman et al., APL 88, 111116 (2006)
    """
    L_k = max(0.0, float(kinetic_inductance_nH))  # nH
    R = max(1e-6, float(load_resistance_ohm))      # Ohm
    # L_k(nH) / R(Ohm) = tau(ns)
    return L_k / R


# ---------------------------------------------------------------------------
# Wavelength-dependent detection efficiency
# ---------------------------------------------------------------------------

def snspd_wavelength_efficiency(
    wavelength_nm: float,
    *,
    peak_efficiency: float = 0.93,
    cutoff_wavelength_nm: float = 2000.0,
    cutoff_width_nm: float = 200.0,
) -> float:
    """Wavelength-dependent SNSPD detection efficiency.

    Uses a sigmoid rolloff model near the cutoff wavelength:

        eta(lambda) = eta_peak / (1 + exp((lambda - lambda_c) / w))

    Below cutoff, efficiency is approximately constant. Above cutoff,
    it drops as photon energy falls below the superconducting gap.

    Args:
        wavelength_nm: Photon wavelength in nm
        peak_efficiency: Peak detection efficiency
        cutoff_wavelength_nm: Wavelength at 50% of peak
        cutoff_width_nm: Transition width of sigmoid (nm)

    Returns:
        Detection efficiency at given wavelength
    """
    wl = float(wavelength_nm)
    eta_peak = max(0.0, min(1.0, float(peak_efficiency)))
    lam_c = max(1.0, float(cutoff_wavelength_nm))
    w = max(1.0, float(cutoff_width_nm))

    # Sigmoid rolloff
    x = (wl - lam_c) / w
    # Clamp to prevent overflow
    x = max(-50.0, min(50.0, x))
    sigmoid = 1.0 / (1.0 + math.exp(x))

    return eta_peak * sigmoid


# ---------------------------------------------------------------------------
# Timing jitter model
# ---------------------------------------------------------------------------

def snspd_timing_jitter(
    bias_ratio: float = 0.95,
    *,
    jitter_at_optimal_ps: float = 68.0,
    jitter_exponent: float = 1.5,
) -> float:
    """SNSPD timing jitter as a function of bias current ratio.

    Jitter increases at lower bias currents approximately as:

        jitter(I_b) = jitter_opt * (I_opt / I_b)^alpha

    where I_b/I_opt is the bias ratio and alpha ~ 1-2.

    Args:
        bias_ratio: I_bias / I_critical (0 to 1)
        jitter_at_optimal_ps: Jitter at optimal bias (ps FWHM)
        jitter_exponent: Power law exponent

    Returns:
        Timing jitter in ps (FWHM)
    """
    I_ratio = max(0.01, min(1.0, float(bias_ratio)))
    j0 = max(0.0, float(jitter_at_optimal_ps))
    alpha = max(0.0, float(jitter_exponent))

    # At optimal bias (ratio ~0.95), jitter is minimal
    optimal_ratio = 0.95
    return j0 * (optimal_ratio / I_ratio) ** alpha


# ---------------------------------------------------------------------------
# Dark count rate vs temperature
# ---------------------------------------------------------------------------

def snspd_dark_count_rate(
    temperature_K: float,
    *,
    dcr_at_operating: float = 100.0,
    operating_temp_K: float = 1.8,
    critical_temp_K: float = 10.0,
) -> float:
    """Temperature-dependent SNSPD dark count rate.

    DCR increases exponentially as temperature approaches Tc:

        DCR(T) = DCR_0 * exp(Delta * (T - T_op) / (k_B * T_c^2))

    Simplified as exponential growth with T/Tc ratio.

    Args:
        temperature_K: Operating temperature
        dcr_at_operating: DCR at nominal operating temperature
        operating_temp_K: Nominal operating temperature
        critical_temp_K: Superconducting critical temperature

    Returns:
        Dark count rate (counts/s)
    """
    T = max(0.01, float(temperature_K))
    T_op = max(0.01, float(operating_temp_K))
    T_c = max(T_op + 0.1, float(critical_temp_K))
    dcr_0 = max(0.0, float(dcr_at_operating))

    # Exponential growth factor
    # BCS gap energy: Delta ~ 1.764 * k_B * T_c
    # Rate ~ exp(-Delta / (k_B * T))
    # Ratio: DCR(T)/DCR(T_op) = exp(Delta * (1/T_op - 1/T) / k_B)
    # Simplified: use T_c as energy scale
    exponent = (T_c / T_op - T_c / T) * 1.764
    # Clamp to prevent overflow
    exponent = max(-50.0, min(50.0, exponent))

    return dcr_0 * math.exp(exponent)
