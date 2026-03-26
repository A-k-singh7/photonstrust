"""Continuous-Variable QKD (GG02) key-rate model.

Implements the Gaussian-modulated coherent-state protocol with homodyne or
heterodyne detection and reverse reconciliation.

Key references:
    - Grosshans & Grangier, PRL 88, 057902 (2002)  -- GG02 protocol
    - Weedbrook et al., RMP 84, 621 (2012)          -- comprehensive CV-QKD review
    - Leverrier, PRL 114, 070501 (2015)              -- composable security
    - Laudenbach et al., Adv. Quantum Tech. 1, 1800011 (2018)  -- practical review

The key rate under collective attacks with reverse reconciliation is:

    K = beta * I(A;B) - chi(B;E)

where beta is the reconciliation efficiency, I(A;B) the mutual information
between Alice and Bob, and chi(B;E) the Holevo bound on Eve's information.

Notes:
    - CV-QKD is a direct-link protocol. The PLOB repeaterless bound applies.
    - Channel transmittance T = eta_channel from the fiber/free-space engine.
    - Excess noise xi is referred to the channel input (shot-noise units, SNU).
    - The protocol uses Gaussian modulation and coherent states.
"""

from __future__ import annotations

import math

from photonstrust.channels.engine import compute_channel_diagnostics
from photonstrust.qkd_types import QKDResult
from photonstrust.utils import clamp


def compute_point_cv_qkd(
    scenario: dict,
    distance_km: float,
    runtime_overrides: dict | None = None,
) -> QKDResult:
    """Compute a CV-QKD (GG02) key-rate point.

    Supports homodyne and heterodyne detection with reverse reconciliation.
    The channel transmittance is computed from the channel engine; the excess
    noise, modulation variance, and detector parameters come from the scenario.
    """

    source = scenario.get("source", {}) or {}
    channel = scenario.get("channel", {}) or {}
    detector = scenario.get("detector", {}) or {}
    timing = scenario.get("timing", {}) or {}
    proto = scenario.get("protocol", {}) or {}
    finite_key_cfg = scenario.get("finite_key")

    # --- Source parameters ---
    rep_rate_hz = float(source.get("rep_rate_mhz", 0.0) or 0.0) * 1e6
    if rep_rate_hz <= 0.0:
        raise ValueError("source.rep_rate_mhz must be > 0 for CV-QKD")

    # Modulation variance in shot-noise units (SNU)
    V_A = max(0.01, float(proto.get("modulation_variance", 4.0) or 4.0))

    # --- Channel transmittance ---
    ch_diag = compute_channel_diagnostics(
        distance_km=float(distance_km),
        wavelength_nm=float(scenario.get("wavelength_nm", 1550.0)),
        channel_cfg=channel,
    )
    T = float(ch_diag.get("eta_channel", 0.0))
    loss_db = float(ch_diag.get("total_loss_db", 0.0))

    # --- Detector parameters ---
    eta_det = clamp(float(detector.get("efficiency", 0.6) or 0.6), 0.0, 1.0)
    v_el = max(0.0, float(detector.get("electronic_noise_snu", 0.01) or 0.01))
    detection_type = str(proto.get("detection", "homodyne")).strip().lower()

    # --- Noise parameters ---
    # Excess noise referred to channel input (SNU)
    xi_excess = max(0.0, float(proto.get("excess_noise_snu", 0.005) or 0.005))

    # Reconciliation efficiency
    beta = clamp(float(proto.get("reconciliation_efficiency", 0.95) or 0.95), 0.0, 1.0)

    # Effective transmittance including detector
    eta_eff = T * eta_det
    if eta_eff <= 0.0:
        return _empty_result(distance_km, loss_db)

    # --- Covariance matrix elements ---
    V = V_A + 1.0  # Alice's total variance (signal + vacuum)

    # Bob's conditional variance after channel
    V_B, C_AB = _covariance_after_channel(V_A, eta_eff, xi_excess, v_el)

    # --- Mutual information I(A;B) ---
    if detection_type == "heterodyne":
        I_AB = _mutual_info_heterodyne(V_A, V_B, C_AB)
    else:
        I_AB = _mutual_info_homodyne(V_A, V_B, C_AB)

    # --- Holevo bound chi(B;E) ---
    chi_BE = _holevo_bound(V, V_B, C_AB, v_el, eta_eff, detection_type)

    # --- Asymptotic key rate ---
    key_rate_per_use = max(0.0, beta * I_AB - chi_BE)
    key_rate_bps = rep_rate_hz * key_rate_per_use

    # --- Finite-size penalty (simplified CV-QKD finite-size model) ---
    fk_enabled = False
    fk_penalty = 0.0
    if finite_key_cfg and finite_key_cfg.get("enabled"):
        fk_enabled = True
        N_total = float(finite_key_cfg.get("signals_per_block", 1e8) or 1e8)
        epsilon = float(finite_key_cfg.get("epsilon_total", 1e-10) or 1e-10)
        pe_fraction = float(finite_key_cfg.get("pe_fraction", 0.5) or 0.5)
        n_key = N_total * (1.0 - pe_fraction)
        fk_penalty = _finite_size_penalty(n_key, epsilon, detection_type)
        key_rate_per_use_fk = max(0.0, key_rate_per_use - fk_penalty)
        key_rate_bps = rep_rate_hz * key_rate_per_use_fk

    # --- QBER equivalent for CV-QKD ---
    # Effective noise-to-signal gives an equivalent QBER
    snr = _signal_to_noise(V_A, eta_eff, xi_excess, v_el, detection_type)
    qber_equiv = 0.5 / (1.0 + snr) if snr > 0 else 0.5

    # --- Background and noise ---
    bg_cps = float(ch_diag.get("background_counts_cps", 0.0) or 0.0)
    raman_cps = float(ch_diag.get("raman_counts_cps", 0.0) or 0.0)

    return QKDResult(
        distance_km=float(distance_km),
        entanglement_rate_hz=0.0,
        key_rate_bps=key_rate_bps,
        qber_total=qber_equiv,
        fidelity=1.0 - qber_equiv,
        p_pair=0.0,
        p_false=0.0,
        q_multi=0.0,
        q_dark=0.0,
        q_timing=0.0,
        q_misalignment=0.0,
        q_source=0.0,
        q_dark_detector=0.0,
        q_background=0.0,
        q_raman=0.0,
        background_counts_cps=bg_cps,
        raman_counts_cps=raman_cps,
        finite_key_enabled=fk_enabled,
        privacy_term_asymptotic=key_rate_per_use,
        privacy_term_effective=max(0.0, key_rate_per_use - fk_penalty),
        finite_key_penalty=fk_penalty,
        loss_db=loss_db,
        protocol_name="cv_qkd",
        protocol_diagnostics={
            "V_A": V_A,
            "T": T,
            "eta_det": eta_det,
            "eta_eff": eta_eff,
            "xi_excess_snu": xi_excess,
            "v_el_snu": v_el,
            "beta": beta,
            "detection_type": detection_type,
            "I_AB": I_AB,
            "chi_BE": chi_BE,
            "key_rate_per_use": key_rate_per_use,
            "snr": snr,
        },
    )


# ---------------------------------------------------------------------------
# Covariance matrix
# ---------------------------------------------------------------------------

def _covariance_after_channel(
    V_A: float, eta: float, xi: float, v_el: float,
) -> tuple[float, float]:
    """Compute Bob's variance V_B and correlation C_AB after channel.

    The covariance matrix of the bipartite state (Alice, Bob) is:

        gamma_AB = [[V*I,  sqrt(T)*Z],
                    [sqrt(T)*Z,  (T*(V + xi) + 1 - T + v_el)*I]]

    where V = V_A + 1, T = eta (total transmittance incl. detector).

    Ref: Weedbrook et al., RMP 84, 621 (2012), Section III.B
    """
    V = V_A + 1.0
    V_B = eta * (V + xi) + (1.0 - eta) + v_el
    C_AB = math.sqrt(max(0.0, eta * (V * V - 1.0)))
    return V_B, C_AB


def _mutual_info_homodyne(V_A: float, V_B: float, C_AB: float) -> float:
    """Mutual information I(A;B) for homodyne detection.

    I(A;B) = 0.5 * log2(V_A_total / V_{A|B})
    V_{A|B} = V_A_total - C_AB^2 / V_B

    Ref: Weedbrook et al., RMP 84, 621 (2012), Eq. (32)
    """
    V = V_A + 1.0
    if V_B <= 0:
        return 0.0
    V_cond = V - (C_AB ** 2) / V_B
    if V_cond <= 0 or V_cond >= V:
        return 0.0
    return max(0.0, 0.5 * math.log2(V / V_cond))


def _mutual_info_heterodyne(V_A: float, V_B: float, C_AB: float) -> float:
    """Mutual information I(A;B) for heterodyne detection.

    Heterodyne measures both quadratures simultaneously, adding one unit
    of vacuum noise. The mutual information doubles (both quadratures)
    but each measurement has higher noise.

    I(A;B) = log2((V + 1) / (V_{A|B} + 1))  [both quadratures]

    Ref: Weedbrook et al., RMP 84, 621 (2012), Eq. (33)
    """
    V = V_A + 1.0
    if V_B + 1.0 <= 0:
        return 0.0
    V_cond = V - (C_AB ** 2) / (V_B + 1.0)
    if V_cond + 1.0 <= 0:
        return 0.0
    return max(0.0, math.log2((V + 1.0) / (V_cond + 1.0)))


# ---------------------------------------------------------------------------
# Holevo bound chi(B;E)
# ---------------------------------------------------------------------------

def _g_function(x: float) -> float:
    """Von Neumann entropy of a thermal state with mean photon number (x-1)/2.

    G(x) = ((x+1)/2) * log2((x+1)/2) - ((x-1)/2) * log2((x-1)/2)

    where x >= 1 is a symplectic eigenvalue. Returns 0 for x <= 1.

    Ref: Weedbrook et al., RMP 84, 621 (2012), Eq. (45)
    """
    if x <= 1.0 + 1e-12:
        return 0.0
    plus = (x + 1.0) / 2.0
    minus = (x - 1.0) / 2.0
    if minus <= 0.0:
        return 0.0
    return plus * math.log2(plus) - minus * math.log2(minus)


def _symplectic_eigenvalues(V: float, V_B: float, C_AB: float) -> tuple[float, float]:
    """Compute symplectic eigenvalues nu_1, nu_2 of the covariance matrix.

    Delta = V^2 + V_B^2 - 2*C_AB^2
    D = V*V_B - C_AB^2

    nu_{1,2}^2 = 0.5 * (Delta +/- sqrt(Delta^2 - 4*D^2))

    Ref: Weedbrook et al., RMP 84, 621 (2012), Eq. (A4)-(A5)
    """
    Delta = V ** 2 + V_B ** 2 - 2.0 * C_AB ** 2
    D = V * V_B - C_AB ** 2

    discriminant = Delta ** 2 - 4.0 * D ** 2
    sqrt_disc = math.sqrt(max(0.0, discriminant))

    nu1_sq = 0.5 * (Delta + sqrt_disc)
    nu2_sq = 0.5 * (Delta - sqrt_disc)

    nu1 = math.sqrt(max(1.0, nu1_sq))
    nu2 = math.sqrt(max(1.0, nu2_sq))
    return nu1, nu2


def _conditional_symplectic_eigenvalue_homodyne(
    V: float, V_B: float, C_AB: float, v_el: float, eta: float,
) -> float:
    """Conditional symplectic eigenvalue after homodyne measurement.

    For homodyne detection measuring one quadrature x_B, the conditional
    covariance matrix of mode A is diag(V - C^2/V_B, V). The symplectic
    eigenvalue of a 2x2 diagonal matrix diag(a, b) is sqrt(a*b):

        nu_3 = sqrt(V * (V - C_AB^2 / V_B))

    Ref: Weedbrook et al., RMP 84, 621 (2012), Eq. (A8)
    """
    if V_B <= 0:
        return V
    cond_var = max(0.0, V - (C_AB ** 2) / V_B)
    nu3_sq = V * cond_var
    return max(1.0, math.sqrt(nu3_sq))


def _conditional_symplectic_eigenvalue_heterodyne(
    V: float, V_B: float, C_AB: float, v_el: float, eta: float,
) -> float:
    """Conditional symplectic eigenvalue after heterodyne measurement.

    Heterodyne measures both quadratures with added vacuum noise.
    The conditional covariance matrix of mode A is proportional to I:

        gamma_{A|het} = (V - C^2 / (V_B + 1)) * I

    giving a single symplectic eigenvalue nu_3 = V - C^2 / (V_B + 1).

    Ref: Weedbrook et al., RMP 84, 621 (2012), Section V.D.2
    """
    V_B_het = V_B + 1.0  # heterodyne adds one vacuum unit
    if V_B_het <= 0:
        return V
    nu3 = V - (C_AB ** 2) / V_B_het
    return max(1.0, nu3)


def _holevo_bound(
    V: float, V_B: float, C_AB: float,
    v_el: float, eta: float, detection_type: str,
) -> float:
    """Compute chi(B;E) — the Holevo bound on Eve's information.

    chi(B;E) = S(rho_E) - S(rho_{E|B})
             = S(rho_AB) - S(rho_{A|B})

    Using symplectic eigenvalues:
        chi = G(nu_1) + G(nu_2) - G(nu_3)             [homodyne]
        chi = G(nu_1) + G(nu_2) - G(nu_3) - G(nu_4)   [heterodyne]

    Ref: Weedbrook et al., RMP 84, 621 (2012), Eq. (50)-(52)
    """
    nu1, nu2 = _symplectic_eigenvalues(V, V_B, C_AB)

    S_AB = _g_function(nu1) + _g_function(nu2)

    if detection_type == "heterodyne":
        nu3 = _conditional_symplectic_eigenvalue_heterodyne(
            V, V_B, C_AB, v_el, eta,
        )
    else:
        nu3 = _conditional_symplectic_eigenvalue_homodyne(
            V, V_B, C_AB, v_el, eta,
        )
    S_cond = _g_function(nu3)

    return max(0.0, S_AB - S_cond)


# ---------------------------------------------------------------------------
# Signal-to-noise and finite-size
# ---------------------------------------------------------------------------

def _signal_to_noise(
    V_A: float, eta: float, xi: float, v_el: float, detection_type: str,
) -> float:
    """Compute the signal-to-noise ratio for CV-QKD.

    Homodyne:
        SNR = eta * V_A / (1 + eta*xi + v_el)

    Heterodyne:
        SNR = eta * V_A / (2 + eta*xi + 2*v_el)

    Ref: Laudenbach et al., Adv. Quantum Tech. 1, 1800011 (2018), Eq. (6)
    """
    noise_hom = 1.0 + eta * xi + v_el
    if detection_type == "heterodyne":
        noise = 2.0 + eta * xi + 2.0 * v_el
    else:
        noise = noise_hom
    if noise <= 0:
        return 0.0
    return max(0.0, eta * V_A / noise)


def _finite_size_penalty(n: float, epsilon: float, detection_type: str) -> float:
    """Finite-size penalty for CV-QKD parameter estimation.

    Delta(n) = (2*d + 1) * sqrt(log2(2/eps) / n) + corrections

    where d = 2 for CV-QKD (two parameters: transmittance and excess noise).

    Ref: Leverrier, PRA 81, 062343 (2010), Theorem 1
    """
    if n <= 0 or epsilon <= 0:
        return float("inf")
    d = 2  # dimension of parameter estimation space
    term1 = (2.0 * d + 1.0) * math.sqrt(math.log2(2.0 / epsilon) / n)
    term2 = math.log2(2.0 / epsilon) / n  # higher-order correction
    return max(0.0, term1 + term2)


# ---------------------------------------------------------------------------
# Empty result helper
# ---------------------------------------------------------------------------

def _empty_result(distance_km: float, loss_db: float) -> QKDResult:
    return QKDResult(
        distance_km=float(distance_km),
        entanglement_rate_hz=0.0,
        key_rate_bps=0.0,
        qber_total=0.5,
        fidelity=0.5,
        p_pair=0.0,
        p_false=0.0,
        q_multi=0.0,
        q_dark=0.0,
        q_timing=0.0,
        q_misalignment=0.0,
        q_source=0.0,
        q_dark_detector=0.0,
        q_background=0.0,
        q_raman=0.0,
        background_counts_cps=0.0,
        raman_counts_cps=0.0,
        finite_key_enabled=False,
        privacy_term_asymptotic=0.0,
        privacy_term_effective=0.0,
        finite_key_penalty=0.0,
        loss_db=loss_db,
        protocol_name="cv_qkd",
    )
