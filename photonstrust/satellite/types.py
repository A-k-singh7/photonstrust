from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GammaGammaParams:
    alpha: float
    beta: float
    rytov_variance: float
    scintillation_index: float
    regime: str

    def as_dict(self) -> dict:
        return {
            "alpha": self.alpha,
            "beta": self.beta,
            "rytov_variance": self.rytov_variance,
            "scintillation_index": self.scintillation_index,
            "regime": self.regime,
        }


@dataclass(frozen=True)
class AtmosphereProfile:
    wavelength_nm: float
    extinction_db_per_km: float
    dominant_mechanism: str
    visibility_km: float
    condition: str

    def as_dict(self) -> dict:
        return {
            "wavelength_nm": self.wavelength_nm,
            "extinction_db_per_km": self.extinction_db_per_km,
            "dominant_mechanism": self.dominant_mechanism,
            "visibility_km": self.visibility_km,
            "condition": self.condition,
        }


@dataclass(frozen=True)
class BackgroundEstimate:
    counts_cps: float
    spectral_radiance_w_m2_sr_nm: float
    fov_sr: float
    rx_area_m2: float
    filter_bandwidth_nm: float
    detector_efficiency: float
    photon_energy_j: float
    day_night: str
    model: str

    def as_dict(self) -> dict:
        return {
            "counts_cps": self.counts_cps,
            "spectral_radiance_w_m2_sr_nm": self.spectral_radiance_w_m2_sr_nm,
            "fov_sr": self.fov_sr,
            "rx_area_m2": self.rx_area_m2,
            "filter_bandwidth_nm": self.filter_bandwidth_nm,
            "detector_efficiency": self.detector_efficiency,
            "photon_energy_j": self.photon_energy_j,
            "day_night": self.day_night,
            "model": self.model,
        }


@dataclass(frozen=True)
class PassKeyBudget:
    time_steps: list[float]
    key_rates_bps: list[float]
    cumulative_key_bits: list[float]
    total_key_bits: float
    pass_duration_s: float
    dt_s: float
    finite_key_enforced: bool

    def as_dict(self) -> dict:
        return {
            "time_steps": list(self.time_steps),
            "key_rates_bps": list(self.key_rates_bps),
            "cumulative_key_bits": list(self.cumulative_key_bits),
            "total_key_bits": self.total_key_bits,
            "pass_duration_s": self.pass_duration_s,
            "dt_s": self.dt_s,
            "finite_key_enforced": self.finite_key_enforced,
        }


@dataclass(frozen=True)
class FadingDistributionResult:
    """Result of turbulence fading distribution analysis."""
    model: str
    scintillation_index: float
    eta_mean: float
    eta_median: float
    outage_probability: float
    outage_threshold_eta: float
    fade_margin_db: float
    samples_used: int
    distribution_params: dict

    def as_dict(self) -> dict:
        return {
            "model": self.model,
            "scintillation_index": self.scintillation_index,
            "eta_mean": self.eta_mean,
            "eta_median": self.eta_median,
            "outage_probability": self.outage_probability,
            "outage_threshold_eta": self.outage_threshold_eta,
            "fade_margin_db": self.fade_margin_db,
            "samples_used": self.samples_used,
            "distribution_params": dict(self.distribution_params),
        }


@dataclass(frozen=True)
class PointingBudgetResult:
    """Result of bias + jitter pointing decomposition."""
    bias_urad: float
    jitter_urad: float
    beam_divergence_urad: float
    eta_mean: float
    eta_boresight: float
    outage_probability: float
    rice_parameter_k: float
    distribution_model: str

    def as_dict(self) -> dict:
        return {
            "bias_urad": self.bias_urad,
            "jitter_urad": self.jitter_urad,
            "beam_divergence_urad": self.beam_divergence_urad,
            "eta_mean": self.eta_mean,
            "eta_boresight": self.eta_boresight,
            "outage_probability": self.outage_probability,
            "rice_parameter_k": self.rice_parameter_k,
            "distribution_model": self.distribution_model,
        }


@dataclass(frozen=True)
class HufnagelValleyProfile:
    """Cn2 turbulence profile result from Hufnagel-Valley model."""
    ground_cn2: float
    rms_wind_speed_m_s: float
    rytov_variance: float
    scintillation_index: float
    fried_parameter_m: float
    isoplanatic_angle_urad: float
    zenith_angle_deg: float
    wavelength_nm: float

    def as_dict(self) -> dict:
        return {
            "ground_cn2": self.ground_cn2,
            "rms_wind_speed_m_s": self.rms_wind_speed_m_s,
            "rytov_variance": self.rytov_variance,
            "scintillation_index": self.scintillation_index,
            "fried_parameter_m": self.fried_parameter_m,
            "isoplanatic_angle_urad": self.isoplanatic_angle_urad,
            "zenith_angle_deg": self.zenith_angle_deg,
            "wavelength_nm": self.wavelength_nm,
        }


@dataclass(frozen=True)
class OrbitPassEnvelope:
    """Elevation profile and link budget over a satellite pass."""
    time_steps_s: list[float]
    elevation_deg: list[float]
    slant_range_km: list[float]
    eta_channel: list[float]
    background_counts_cps: list[float]
    key_rate_bps: list[float]
    cumulative_key_bits: list[float]
    total_key_bits: float
    outage_fraction: float
    pass_duration_s: float
    max_elevation_deg: float
    orbit_altitude_km: float

    def as_dict(self) -> dict:
        return {
            "time_steps_s": list(self.time_steps_s),
            "elevation_deg": list(self.elevation_deg),
            "slant_range_km": list(self.slant_range_km),
            "eta_channel": list(self.eta_channel),
            "background_counts_cps": list(self.background_counts_cps),
            "key_rate_bps": list(self.key_rate_bps),
            "cumulative_key_bits": list(self.cumulative_key_bits),
            "total_key_bits": self.total_key_bits,
            "outage_fraction": self.outage_fraction,
            "pass_duration_s": self.pass_duration_s,
            "max_elevation_deg": self.max_elevation_deg,
            "orbit_altitude_km": self.orbit_altitude_km,
        }
