from __future__ import annotations

from dataclasses import dataclass


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
