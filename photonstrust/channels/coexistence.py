"""Fiber coexistence noise models (classical + QKD).

This module currently focuses on spontaneous Raman background in fiber when
classical traffic coexists with a quantum channel.

The Raman model keeps a calibration-friendly coefficient but uses an analytic
attenuation-aware effective interaction length so received noise does not grow
unbounded linearly with distance.
"""

from __future__ import annotations

import math


def compute_raman_counts_cps(
    distance_km: float,
    coexistence: dict | None,
    *,
    fiber_loss_db_per_km: float | None = None,
) -> float:
    """Return spontaneous Raman background count rate at the QKD receiver (cps).

    Analytic integral model (still calibration-friendly):

    Let z be distance along fiber from the classical launch point (z=0) to the
    QKD receiver (z=L). The classical pump power is P_p(z) = P_launch*exp(-a_p z)
    where a_p is the *power* attenuation coefficient (Np/km). Spontaneous Raman
    generation into the receiver filter bandwidth dLambda is modeled as:

        dR_gen(z) = k * P_p(z) * dLambda * dz

    where k has units cps/(km*mW*nm) when P is in mW and dz is in km. A photon
    generated at z experiences propagation loss to the receiver.

    Co-propagation (forward Raman to receiver at z=L):

        dR_rx(z) = k * P_launch * exp(-a_p z) * exp(-a_s (L-z)) * dLambda * dz

        => R_rx = k * P_launch * dLambda * L_eff_co

        L_eff_co = exp(-a_s L) * (1 - exp(-(a_p-a_s)L)) / (a_p-a_s)
        with limit a_p -> a_s: L_eff_co = L * exp(-a_s L)

    Counter-propagation (backward Raman from a pump launched at the receiver end):

        L_eff_counter = (1 - exp(-(a_p+a_s)L)) / (a_p+a_s)

    This function keeps the existing config surface and uses band/channel fiber
    attenuation (dB/km) if provided by the caller.

    Expected coexistence config (all optional):
      enabled: bool
      classical_launch_power_dbm: float
      classical_channel_count: int
      direction: "co" | "counter"
      filter_bandwidth_nm: float
      raman_coeff_cps_per_km_per_mw_per_nm: float
      raman_spectral_factor: float

    Optional (not required, advanced):
      raman_model: "effective_length" | "legacy"
      alpha_p_db_per_km: float  (default 0.2)
      alpha_s_db_per_km: float  (default alpha_p_db_per_km)
      raman_direction_factor_co: float (default 1.0)
      raman_direction_factor_counter: float (default 1.0)
    """

    if not coexistence:
        return 0.0

    if not bool(coexistence.get("enabled", False)):
        return 0.0

    coeff = float(coexistence.get("raman_coeff_cps_per_km_per_mw_per_nm", 0.0))
    if coeff <= 0.0:
        return 0.0

    length_km = max(0.0, float(distance_km))

    launch_power_dbm = float(coexistence.get("classical_launch_power_dbm", 0.0))
    launch_power_mw = 10 ** (launch_power_dbm / 10.0)
    launch_power_mw = max(0.0, float(launch_power_mw))

    channel_count = int(coexistence.get("classical_channel_count", 1))
    channel_count = max(0, channel_count)
    if channel_count <= 0:
        return 0.0

    filter_bw_nm = float(coexistence.get("filter_bandwidth_nm", 0.2))
    filter_bw_nm = max(0.0, filter_bw_nm)
    if filter_bw_nm <= 0.0:
        return 0.0

    spectral_factor = float(coexistence.get("raman_spectral_factor", 1.0))
    spectral_factor = max(0.0, spectral_factor)

    model = str(coexistence.get("raman_model", "effective_length")).strip().lower()
    direction = str(coexistence.get("direction", "co")).strip().lower()
    is_counter = bool(direction.startswith("counter"))

    # Power attenuation coefficients (Np/km). Default corresponds to ~0.2 dB/km.
    # Use power attenuation (not field attenuation).
    def _db_per_km_to_np_per_km(alpha_db_per_km: float) -> float:
        return float(alpha_db_per_km) * (math.log(10.0) / 10.0)

    if model in {"legacy", "linear"}:
        # Legacy v0 model: linear in length, with a coarse direction factor.
        if is_counter:
            direction_factor = float(coexistence.get("raman_direction_factor_counter", 1.5) or 1.5)
        else:
            direction_factor = float(coexistence.get("raman_direction_factor_co", 1.0) or 1.0)
        direction_factor = max(0.0, direction_factor)

        counts = (
            coeff
            * length_km
            * launch_power_mw
            * filter_bw_nm
            * channel_count
            * direction_factor
            * spectral_factor
        )
        if not math.isfinite(counts):
            return 0.0
        return max(0.0, float(counts))

    # Attenuation-integral model uses per-band fiber loss if provided.
    alpha_fiber = None
    if fiber_loss_db_per_km is not None:
        try:
            alpha_fiber = float(fiber_loss_db_per_km)
        except Exception:
            alpha_fiber = None
    alpha_p_db_per_km = coexistence.get("alpha_p_db_per_km")
    if alpha_p_db_per_km is None:
        alpha_p_db_per_km = 0.2 if alpha_fiber is None else alpha_fiber
    alpha_s_db_per_km = coexistence.get("alpha_s_db_per_km")
    if alpha_s_db_per_km is None:
        alpha_s_db_per_km = alpha_p_db_per_km

    alpha_p_db_per_km = max(0.0, float(alpha_p_db_per_km))
    alpha_s_db_per_km = max(0.0, float(alpha_s_db_per_km))

    a_p = _db_per_km_to_np_per_km(alpha_p_db_per_km)
    a_s = _db_per_km_to_np_per_km(alpha_s_db_per_km)

    # Effective interaction length (km), including pump attenuation and Raman
    # photon attenuation to the receiver.
    L = length_km
    if L <= 0.0:
        return 0.0

    def _leff_co(L_km: float, a_p_np: float, a_s_np: float) -> float:
        # exp(-a_s L) * (1 - exp(-(a_p-a_s)L))/(a_p-a_s), stable near equality.
        delta = a_p_np - a_s_np
        if abs(delta) < 1e-12:
            return float(L_km) * math.exp(-a_s_np * L_km)
        # 1 - exp(-delta*L) computed stably.
        numer = -math.expm1(-delta * L_km)
        return math.exp(-a_s_np * L_km) * (numer / delta)

    def _leff_counter(L_km: float, a_p_np: float, a_s_np: float) -> float:
        denom = a_p_np + a_s_np
        if denom <= 0.0:
            return float(L_km)
        numer = -math.expm1(-denom * L_km)
        return numer / denom

    if is_counter:
        leff_km = _leff_counter(L, a_p, a_s)
        direction_factor = float(coexistence.get("raman_direction_factor_counter", 1.0))
    else:
        leff_km = _leff_co(L, a_p, a_s)
        direction_factor = float(coexistence.get("raman_direction_factor_co", 1.0))
    direction_factor = max(0.0, direction_factor)

    counts = (
        coeff
        * leff_km
        * launch_power_mw
        * filter_bw_nm
        * channel_count
        * direction_factor
        * spectral_factor
    )
    if not math.isfinite(counts):
        return 0.0
    return max(0.0, float(counts))
