"""Satellite channel realism pack for PhotonTrust."""

from __future__ import annotations

from photonstrust.satellite.background import estimate_background_counts_cps
from photonstrust.satellite.extinction import get_atmosphere_profiles, lookup_extinction_db_per_km
from photonstrust.satellite.pass_budget import (
    compute_pass_key_budget,
    enforce_finite_key_for_pass,
    gamma_gamma_params_from_rytov,
    sample_gamma_gamma,
)
from photonstrust.satellite.types import (
    AtmosphereProfile,
    BackgroundEstimate,
    GammaGammaParams,
    PassKeyBudget,
)

__all__ = [
    "AtmosphereProfile",
    "BackgroundEstimate",
    "GammaGammaParams",
    "PassKeyBudget",
    "compute_pass_key_budget",
    "enforce_finite_key_for_pass",
    "estimate_background_counts_cps",
    "gamma_gamma_params_from_rytov",
    "get_atmosphere_profiles",
    "lookup_extinction_db_per_km",
    "sample_gamma_gamma",
]
