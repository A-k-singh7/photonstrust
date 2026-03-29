"""Physics-based detector calibration from measurement data."""
from __future__ import annotations
import math
from dataclasses import dataclass
import numpy as np

@dataclass(frozen=True)
class SNSPDCalibration:
    """Calibration result for SNSPD efficiency vs bias current."""
    eta_max: float  # maximum detection efficiency
    I_50: float     # bias current at 50% of eta_max (A)
    k: float        # sigmoid steepness (1/A)
    r_squared: float

@dataclass(frozen=True)
class InGaAsCalibration:
    """Calibration result for InGaAs APD afterpulsing."""
    amplitudes: list[float]   # A_j
    time_constants_us: list[float]  # tau_j in microseconds
    total_afterpulse_prob: float
    r_squared: float

@dataclass(frozen=True)
class DCRCalibration:
    """Calibration result for dark count rate vs temperature."""
    dcr_0: float    # reference DCR (Hz) at T_0
    T_0_K: float    # reference temperature (K)
    E_a_eV: float   # activation energy (eV)
    r_squared: float


def _sigmoid(I_b, eta_max, I_50, k):
    """Sigmoid model: eta(I_b) = eta_max / (1 + exp(-k*(I_b - I_50)))"""
    return eta_max / (1.0 + np.exp(-k * (I_b - I_50)))


def fit_snspd_efficiency_curve(
    bias_currents_uA: np.ndarray,
    efficiencies: np.ndarray,
) -> SNSPDCalibration:
    """Fit SNSPD detection efficiency vs bias current.

    Sigmoid fit: eta(I_b) = eta_max / (1+exp(-k*(I_b-I_50)))
    Uses least-squares curve fitting.
    """
    from scipy.optimize import curve_fit

    I = np.asarray(bias_currents_uA, dtype=float)
    eta = np.asarray(efficiencies, dtype=float)

    # Initial guesses
    eta_max_0 = float(np.max(eta)) * 1.05
    I_50_0 = float(I[np.argmin(np.abs(eta - eta_max_0/2))])
    k_0 = 1.0

    popt, _ = curve_fit(
        _sigmoid, I, eta,
        p0=[eta_max_0, I_50_0, k_0],
        bounds=([0, I.min(), 0.001], [1.0, I.max(), 100.0]),
        maxfev=5000,
    )

    eta_max, I_50, k = popt

    # R-squared
    ss_res = np.sum((eta - _sigmoid(I, *popt)) ** 2)
    ss_tot = np.sum((eta - np.mean(eta)) ** 2)
    r_sq = 1.0 - ss_res / max(ss_tot, 1e-30)

    return SNSPDCalibration(
        eta_max=float(eta_max), I_50=float(I_50), k=float(k),
        r_squared=float(r_sq),
    )


def _multi_exp(t, *params):
    """Multi-exponential: sum A_j * exp(-t/tau_j)"""
    n = len(params) // 2
    result = np.zeros_like(t, dtype=float)
    for j in range(n):
        A = params[2*j]
        tau = params[2*j + 1]
        result += A * np.exp(-t / max(tau, 1e-6))
    return result


def fit_ingaas_afterpulsing(
    delays_us: np.ndarray,
    afterpulse_rates: np.ndarray,
    n_traps: int = 2,
) -> InGaAsCalibration:
    """Fit InGaAs APD afterpulsing: P_ap(t) = sum A_j*exp(-t/tau_j).

    Extract 2-4 trap levels from least-squares.
    """
    from scipy.optimize import curve_fit

    t = np.asarray(delays_us, dtype=float)
    rates = np.asarray(afterpulse_rates, dtype=float)

    # Initial guesses: log-spaced time constants
    p0 = []
    for j in range(n_traps):
        p0.append(float(np.max(rates)) / n_traps)  # amplitude
        p0.append(float(t[-1]) / (j + 1) / 2)      # tau

    lower = [0] * (2 * n_traps)
    upper_flat = []
    for j in range(n_traps):
        upper_flat.append(float(np.max(rates)) * 10)
        upper_flat.append(float(t[-1]) * 10)

    popt, _ = curve_fit(
        _multi_exp, t, rates, p0=p0,
        bounds=(lower, upper_flat),
        maxfev=10000,
    )

    amplitudes = [float(popt[2*j]) for j in range(n_traps)]
    taus = [float(popt[2*j+1]) for j in range(n_traps)]

    # Total afterpulse probability (integral from 0 to inf)
    total = sum(a * tau for a, tau in zip(amplitudes, taus))

    ss_res = np.sum((rates - _multi_exp(t, *popt)) ** 2)
    ss_tot = np.sum((rates - np.mean(rates)) ** 2)
    r_sq = 1.0 - ss_res / max(ss_tot, 1e-30)

    return InGaAsCalibration(
        amplitudes=amplitudes, time_constants_us=taus,
        total_afterpulse_prob=float(total),
        r_squared=float(r_sq),
    )


def _arrhenius(T, dcr_0, T_0, E_a_eV):
    """Arrhenius: DCR(T) = DCR_0 * exp(E_a/kB * (1/T0 - 1/T))"""
    kB_eV = 8.617333262e-5  # eV/K
    return dcr_0 * np.exp((E_a_eV / kB_eV) * (1.0/T_0 - 1.0/T))


def fit_dcr_temperature(
    temperatures_K: np.ndarray,
    dcr_values_Hz: np.ndarray,
) -> DCRCalibration:
    """Fit dark count rate vs temperature: Arrhenius model.

    DCR(T) = DCR_0 * exp(E_a/kB * (1/T0 - 1/T))
    """
    from scipy.optimize import curve_fit

    T = np.asarray(temperatures_K, dtype=float)
    dcr = np.asarray(dcr_values_Hz, dtype=float)

    T_0 = float(T[0])
    dcr_0_guess = float(dcr[0])
    E_a_guess = 0.3  # eV, typical for InGaAs

    def model(T_arr, dcr_0, E_a):
        return _arrhenius(T_arr, dcr_0, T_0, E_a)

    popt, _ = curve_fit(
        model, T, dcr, p0=[dcr_0_guess, E_a_guess],
        bounds=([0, 0.01], [dcr.max()*100, 2.0]),
        maxfev=5000,
    )

    ss_res = np.sum((dcr - model(T, *popt)) ** 2)
    ss_tot = np.sum((dcr - np.mean(dcr)) ** 2)
    r_sq = 1.0 - ss_res / max(ss_tot, 1e-30)

    return DCRCalibration(
        dcr_0=float(popt[0]), T_0_K=T_0, E_a_eV=float(popt[1]),
        r_squared=float(r_sq),
    )
