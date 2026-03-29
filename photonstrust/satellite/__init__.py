"""Satellite channel realism pack for PhotonTrust."""

from __future__ import annotations

from photonstrust.satellite.background import estimate_background_counts_cps
from photonstrust.satellite.extinction import get_atmosphere_profiles, lookup_extinction_db_per_km
from photonstrust.satellite.orbit import (
    compute_orbit_pass_envelope,
    elevation_profile,
    slant_range_km,
)
from photonstrust.satellite.pass_budget import (
    compute_pass_key_budget,
    enforce_finite_key_for_pass,
    gamma_gamma_params_from_rytov,
    sample_gamma_gamma,
)
from photonstrust.satellite.pointing import (
    joint_pointing_turbulence_outage,
    pointing_budget,
)
from photonstrust.satellite.turbulence import (
    compute_rytov_variance,
    gamma_gamma_fading,
    hufnagel_valley_cn2,
    lognormal_fading,
    select_fading_model,
)
from photonstrust.satellite.types import (
    AtmosphereProfile,
    BackgroundEstimate,
    FadingDistributionResult,
    GammaGammaParams,
    HufnagelValleyProfile,
    OrbitPassEnvelope,
    PassKeyBudget,
    PointingBudgetResult,
)

__all__ = [
    "AtmosphereProfile",
    "BackgroundEstimate",
    "FadingDistributionResult",
    "GammaGammaParams",
    "HufnagelValleyProfile",
    "OrbitPassEnvelope",
    "PassKeyBudget",
    "PointingBudgetResult",
    "compute_orbit_pass_envelope",
    "compute_pass_key_budget",
    "compute_rytov_variance",
    "elevation_profile",
    "enforce_finite_key_for_pass",
    "estimate_background_counts_cps",
    "gamma_gamma_fading",
    "gamma_gamma_params_from_rytov",
    "get_atmosphere_profiles",
    "hufnagel_valley_cn2",
    "joint_pointing_turbulence_outage",
    "lognormal_fading",
    "lookup_extinction_db_per_km",
    "pointing_budget",
    "sample_gamma_gamma",
    "select_fading_model",
    "slant_range_km",
]
