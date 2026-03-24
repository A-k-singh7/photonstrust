"""Fiber deployment hardening: PMD, temperature drift, FWM, and enhanced timing."""

from __future__ import annotations

import math
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PMDContribution:
    """Polarization-mode dispersion contribution to the timing budget."""

    pmd_coeff_ps_per_sqrt_km: float
    distance_km: float
    mean_dgd_ps: float

    def as_dict(self) -> dict:
        return {
            "pmd_coeff_ps_per_sqrt_km": self.pmd_coeff_ps_per_sqrt_km,
            "distance_km": self.distance_km,
            "mean_dgd_ps": self.mean_dgd_ps,
        }


@dataclass(frozen=True)
class TemperatureDriftContribution:
    """Residual timing drift after synchronisation tracking."""

    drift_coeff_ps_per_km_per_degC: float
    distance_km: float
    temperature_fluctuation_degC: float
    sync_tracking_efficiency: float
    residual_drift_ps: float

    def as_dict(self) -> dict:
        return {
            "drift_coeff_ps_per_km_per_degC": self.drift_coeff_ps_per_km_per_degC,
            "distance_km": self.distance_km,
            "temperature_fluctuation_degC": self.temperature_fluctuation_degC,
            "sync_tracking_efficiency": self.sync_tracking_efficiency,
            "residual_drift_ps": self.residual_drift_ps,
        }


@dataclass(frozen=True)
class FWMNoiseContribution:
    """Four-wave mixing noise contribution in dense-WDM fibers."""

    enabled: bool
    fwm_counts_cps: float
    phase_matching_efficiency: float
    channel_spacing_ghz: float

    def as_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "fwm_counts_cps": self.fwm_counts_cps,
            "phase_matching_efficiency": self.phase_matching_efficiency,
            "channel_spacing_ghz": self.channel_spacing_ghz,
        }


@dataclass(frozen=True)
class EnhancedTimingBudget:
    """Quadrature-sum timing budget with deployment-specific contributions."""

    sigma_jitter_ps: float
    sigma_drift_ps: float
    sigma_dispersion_ps: float
    sigma_pmd_ps: float
    sigma_temperature_ps: float
    sigma_effective_ps: float

    def as_dict(self) -> dict:
        return {
            "sigma_jitter_ps": self.sigma_jitter_ps,
            "sigma_drift_ps": self.sigma_drift_ps,
            "sigma_dispersion_ps": self.sigma_dispersion_ps,
            "sigma_pmd_ps": self.sigma_pmd_ps,
            "sigma_temperature_ps": self.sigma_temperature_ps,
            "sigma_effective_ps": self.sigma_effective_ps,
        }


@dataclass(frozen=True)
class FiberDeploymentDiagnostics:
    """Composite diagnostics for a fiber deployment point."""

    pmd: PMDContribution | None
    temperature_drift: TemperatureDriftContribution | None
    fwm: FWMNoiseContribution | None
    timing_budget: EnhancedTimingBudget
    visibility_floor: float
    effective_visibility: float

    def as_dict(self) -> dict:
        return {
            "pmd": self.pmd.as_dict() if self.pmd is not None else None,
            "temperature_drift": (
                self.temperature_drift.as_dict()
                if self.temperature_drift is not None
                else None
            ),
            "fwm": self.fwm.as_dict() if self.fwm is not None else None,
            "timing_budget": self.timing_budget.as_dict(),
            "visibility_floor": self.visibility_floor,
            "effective_visibility": self.effective_visibility,
        }


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------

def pmd_dgd_ps(
    distance_km: float,
    pmd_coeff_ps_per_sqrt_km: float = 0.0,
) -> float:
    """Mean differential group delay: <dt> = D_PMD * sqrt(L)."""
    if pmd_coeff_ps_per_sqrt_km <= 0 or distance_km <= 0:
        return 0.0
    return pmd_coeff_ps_per_sqrt_km * math.sqrt(distance_km)


def temperature_drift_residual_ps(
    distance_km: float,
    temperature_fluctuation_degC: float = 0.0,
    drift_coeff_ps_per_km_per_degC: float = 37.0,
    sync_tracking_efficiency: float = 0.99,
) -> float:
    """Residual timing drift after synchronisation tracking.

    residual = drift_coeff * L * sigma_T * (1 - eta_sync)
    """
    if temperature_fluctuation_degC <= 0 or distance_km <= 0:
        return 0.0
    raw = (
        drift_coeff_ps_per_km_per_degC
        * distance_km
        * temperature_fluctuation_degC
        * (1.0 - sync_tracking_efficiency)
    )
    return max(0.0, raw)


def compute_fwm_counts_cps(
    distance_km: float,
    coexistence: dict | None,
    *,
    fiber_loss_db_per_km: float = 0.2,
) -> float:
    """Return four-wave mixing noise count rate (cps).

    Returns 0 unless *coexistence* contains ``fwm_enabled = True``.

    Simplified FWM model:
        Phase-matching efficiency  eta_FWM = alpha^2 / (alpha^2 + dk^2)
        where dk depends on dispersion and channel spacing.
        FWM power from nonlinear mixing converted to photon count rate
        via photon energy at 1550 nm.

    Default fiber parameters:
        n2 = 2.6e-20 m^2/W, A_eff = 80 um^2.
    """
    if not coexistence:
        return 0.0
    if not bool(coexistence.get("fwm_enabled", False)):
        return 0.0

    distance_km = max(0.0, float(distance_km))
    if distance_km <= 0.0:
        return 0.0

    # Fiber parameters
    n2 = float(coexistence.get("n2_m2_per_W", 2.6e-20))
    a_eff_m2 = float(coexistence.get("a_eff_um2", 80.0)) * 1e-12  # um^2 -> m^2
    gamma = (2.0 * math.pi * n2) / (1550e-9 * a_eff_m2)  # nonlinear coeff (1/(W*m))

    channel_count = int(coexistence.get("classical_channel_count", 1))
    channel_count = max(0, channel_count)
    if channel_count <= 0:
        return 0.0

    channel_spacing_ghz = float(coexistence.get("channel_spacing_ghz", 100.0))
    channel_spacing_hz = channel_spacing_ghz * 1e9

    launch_power_dbm = float(coexistence.get("classical_launch_power_dbm", 0.0))
    launch_power_w = 1e-3 * 10.0 ** (launch_power_dbm / 10.0)

    # Dispersion parameter for phase-mismatch
    dispersion_ps_per_nm_per_km = float(
        coexistence.get("dispersion_ps_per_nm_per_km", 17.0)
    )
    # Convert to s/(m*Hz): D [ps/(nm*km)] -> s/m^2 via standard conversion
    # dk = 2*pi * lambda^2 / c * D * (delta_f)^2
    c_light = 3e8  # m/s
    lam = 1550e-9  # m
    D_si = dispersion_ps_per_nm_per_km * 1e-12 / (1e-9 * 1e3)  # s/m^2
    delta_f = channel_spacing_hz
    dk = 2.0 * math.pi * (lam ** 2) / c_light * D_si * (delta_f ** 2)  # 1/m

    # Attenuation coefficient
    alpha_np_per_m = fiber_loss_db_per_km * (math.log(10.0) / 10.0) * 1e-3  # 1/m

    # Phase-matching efficiency
    if alpha_np_per_m <= 0 and abs(dk) <= 0:
        eta_fwm = 1.0
    else:
        eta_fwm = alpha_np_per_m ** 2 / (alpha_np_per_m ** 2 + dk ** 2)

    # Effective length
    L_m = distance_km * 1e3
    if alpha_np_per_m > 0:
        L_eff_m = (1.0 - math.exp(-alpha_np_per_m * L_m)) / alpha_np_per_m
    else:
        L_eff_m = L_m

    # FWM power (simplified 3-wave mixing product)
    # P_fwm = eta_fwm * (gamma * L_eff)^2 * P1 * P2 * P3 * exp(-alpha*L)
    # For estimation use P_per_channel for all three input powers.
    # Number of mixing products scales roughly as channel_count^2 for dense WDM.
    P_ch = launch_power_w
    p_fwm = eta_fwm * (gamma * L_eff_m) ** 2 * P_ch ** 3
    p_fwm *= math.exp(-alpha_np_per_m * L_m)
    # Scale by number of FWM products (approx channel_count^2 / 2)
    n_products = max(1.0, (channel_count ** 2) / 2.0)
    p_fwm *= n_products

    # Convert power to count rate: photon energy at 1550 nm
    h_planck = 6.626e-34
    freq = c_light / lam
    photon_energy = h_planck * freq
    if photon_energy <= 0:
        return 0.0

    # Apply filter bandwidth (fraction of channel spacing captured)
    filter_bw_nm = float(coexistence.get("filter_bandwidth_nm", 0.2))
    # Channel spacing in nm: delta_lambda ~ lambda^2/c * delta_f
    spacing_nm = (lam ** 2 / c_light) * delta_f * 1e9  # nm
    bw_fraction = min(1.0, filter_bw_nm / max(spacing_nm, 1e-6))

    counts = (p_fwm / photon_energy) * bw_fraction
    if not math.isfinite(counts):
        return 0.0
    return max(0.0, float(counts))


def apply_visibility_floor(
    visibility_measured: float,
    visibility_floor: float = 1.0,
) -> float:
    """Effective visibility with a deployment floor.

    V_eff = max(V_floor, V_measured), clamped to [0, 1].
    """
    return min(1.0, max(visibility_floor, visibility_measured))


def enhanced_timing_budget(
    *,
    jitter_ps_fwhm: float,
    drift_ps_rms: float,
    dispersion_ps: float,
    pmd_dgd_ps_val: float = 0.0,
    temperature_residual_ps: float = 0.0,
) -> EnhancedTimingBudget:
    """Build an enhanced timing budget via quadrature sum."""
    sigma_jitter = jitter_ps_fwhm / 2.355 if jitter_ps_fwhm > 0 else 0.0
    sigma_drift = max(0.0, float(drift_ps_rms))
    sigma_disp = max(0.0, float(dispersion_ps))
    sigma_pmd = max(0.0, float(pmd_dgd_ps_val))
    sigma_temp = max(0.0, float(temperature_residual_ps))

    sigma_eff = math.sqrt(
        sigma_jitter ** 2
        + sigma_drift ** 2
        + sigma_disp ** 2
        + sigma_pmd ** 2
        + sigma_temp ** 2
    )

    return EnhancedTimingBudget(
        sigma_jitter_ps=sigma_jitter,
        sigma_drift_ps=sigma_drift,
        sigma_dispersion_ps=sigma_disp,
        sigma_pmd_ps=sigma_pmd,
        sigma_temperature_ps=sigma_temp,
        sigma_effective_ps=sigma_eff,
    )


def compute_fiber_deployment_diagnostics(
    *,
    distance_km: float,
    channel_cfg: dict,
    detector_cfg: dict,
    timing_cfg: dict,
) -> FiberDeploymentDiagnostics:
    """Compute composite fiber deployment diagnostics.

    All deployment-hardening parameters default to 0 / disabled so that
    existing callers get identical behaviour when they do not supply them.
    """
    distance_km = max(0.0, float(distance_km))

    # --- PMD ---
    pmd_coeff = float(channel_cfg.get("pmd_coeff_ps_per_sqrt_km", 0.0) or 0.0)
    dgd = pmd_dgd_ps(distance_km, pmd_coeff)
    pmd_contrib: PMDContribution | None = None
    if pmd_coeff > 0:
        pmd_contrib = PMDContribution(
            pmd_coeff_ps_per_sqrt_km=pmd_coeff,
            distance_km=distance_km,
            mean_dgd_ps=dgd,
        )

    # --- Temperature drift ---
    temp_fluct = float(
        channel_cfg.get("temperature_fluctuation_degC", 0.0) or 0.0
    )
    drift_coeff = float(
        channel_cfg.get("drift_coeff_ps_per_km_per_degC", 37.0) or 37.0
    )
    sync_eff = float(
        timing_cfg.get("sync_tracking_efficiency", 0.99) or 0.99
    )
    temp_residual = temperature_drift_residual_ps(
        distance_km, temp_fluct, drift_coeff, sync_eff
    )
    temp_contrib: TemperatureDriftContribution | None = None
    if temp_fluct > 0:
        temp_contrib = TemperatureDriftContribution(
            drift_coeff_ps_per_km_per_degC=drift_coeff,
            distance_km=distance_km,
            temperature_fluctuation_degC=temp_fluct,
            sync_tracking_efficiency=sync_eff,
            residual_drift_ps=temp_residual,
        )

    # --- FWM ---
    coexistence = channel_cfg.get("coexistence")
    fwm_counts = compute_fwm_counts_cps(
        distance_km,
        coexistence,
        fiber_loss_db_per_km=float(
            channel_cfg.get("fiber_loss_db_per_km", 0.2) or 0.2
        ),
    )
    fwm_contrib: FWMNoiseContribution | None = None
    fwm_enabled = bool(
        coexistence.get("fwm_enabled", False) if coexistence else False
    )
    if fwm_enabled:
        # Recompute phase-matching efficiency for the record
        channel_spacing_ghz = float(
            (coexistence or {}).get("channel_spacing_ghz", 100.0)
        )
        disp = float(
            (coexistence or {}).get("dispersion_ps_per_nm_per_km", 17.0)
        )
        c_light = 3e8
        lam = 1550e-9
        D_si = disp * 1e-12 / (1e-9 * 1e3)
        delta_f = channel_spacing_ghz * 1e9
        dk = 2.0 * math.pi * (lam ** 2) / c_light * D_si * (delta_f ** 2)
        alpha_db = float(channel_cfg.get("fiber_loss_db_per_km", 0.2) or 0.2)
        alpha_np_m = alpha_db * (math.log(10.0) / 10.0) * 1e-3
        if alpha_np_m <= 0 and abs(dk) <= 0:
            eta_fwm = 1.0
        else:
            eta_fwm = alpha_np_m ** 2 / (alpha_np_m ** 2 + dk ** 2)
        fwm_contrib = FWMNoiseContribution(
            enabled=True,
            fwm_counts_cps=fwm_counts,
            phase_matching_efficiency=eta_fwm,
            channel_spacing_ghz=channel_spacing_ghz,
        )

    # --- Enhanced timing budget ---
    jitter_fwhm = float(detector_cfg.get("jitter_ps_fwhm", 0.0) or 0.0)
    drift_rms = float(timing_cfg.get("sync_drift_ps_rms", 0.0) or 0.0)
    disp_ps_per_km = float(channel_cfg.get("dispersion_ps_per_km", 0.0) or 0.0)
    disp_ps = distance_km * disp_ps_per_km

    tb = enhanced_timing_budget(
        jitter_ps_fwhm=jitter_fwhm,
        drift_ps_rms=drift_rms,
        dispersion_ps=disp_ps,
        pmd_dgd_ps_val=dgd,
        temperature_residual_ps=temp_residual,
    )

    # --- Visibility floor ---
    v_floor = float(channel_cfg.get("visibility_floor", 1.0) or 1.0)
    v_measured = float(channel_cfg.get("optical_visibility", 0.98) or 0.98)
    v_eff = apply_visibility_floor(v_measured, v_floor)

    return FiberDeploymentDiagnostics(
        pmd=pmd_contrib,
        temperature_drift=temp_contrib,
        fwm=fwm_contrib,
        timing_budget=tb,
        visibility_floor=v_floor,
        effective_visibility=v_eff,
    )
