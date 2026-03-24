"""Pre-defined surrogate domains with physics functions."""

from __future__ import annotations

import math
from typing import Callable

SURROGATE_DOMAINS: dict[str, dict] = {
    "qkd_key_rate": {
        "description": "QKD key rate prediction from link parameters",
        "input_features": [
            "distance_km",
            "mu",
            "pde",
            "dark_counts_cps",
            "fiber_loss_db_per_km",
            "rep_rate_mhz",
        ],
        "output_features": ["key_rate_bps"],
        "default_ranges": {
            "distance_km": (1.0, 200.0),
            "mu": (0.1, 0.8),
            "pde": (0.05, 0.90),
            "dark_counts_cps": (10.0, 10000.0),
            "fiber_loss_db_per_km": (0.16, 0.35),
            "rep_rate_mhz": (10.0, 1000.0),
        },
    },
    "qkd_qber": {
        "description": "QBER prediction from link parameters",
        "input_features": [
            "distance_km",
            "dark_counts_cps",
            "fiber_loss_db_per_km",
            "misalignment_rad",
        ],
        "output_features": ["qber"],
        "default_ranges": {
            "distance_km": (1.0, 200.0),
            "dark_counts_cps": (10.0, 10000.0),
            "fiber_loss_db_per_km": (0.16, 0.35),
            "misalignment_rad": (0.0, 0.1),
        },
    },
}


def get_physics_fn(domain: str) -> Callable[[dict], dict]:
    """Return a simple analytical physics function for training."""
    if domain == "qkd_key_rate":

        def _fn(params: dict) -> dict:
            d = params["distance_km"]
            mu = params.get("mu", 0.5)
            pde = params.get("pde", 0.3)
            dark = params.get("dark_counts_cps", 100)
            alpha = params.get("fiber_loss_db_per_km", 0.2)
            rep = params.get("rep_rate_mhz", 100)
            eta = pde * 10 ** (-alpha * d / 10)
            rate = max(
                0,
                rep
                * 1e6
                * mu
                * eta
                * (1 - 1.16 * (dark / (rep * 1e6 * eta + dark + 1e-30))),
            )
            return {"key_rate_bps": rate}

        return _fn

    if domain == "qkd_qber":

        def _fn(params: dict) -> dict:
            d = params["distance_km"]
            dark = params.get("dark_counts_cps", 100)
            alpha = params.get("fiber_loss_db_per_km", 0.2)
            mis = params.get("misalignment_rad", 0.01)
            eta = 0.3 * 10 ** (-alpha * d / 10)
            q_dark = dark / (dark + 1e6 * eta + 1e-30) * 0.5
            q_mis = 0.5 * math.sin(mis) ** 2
            return {"qber": min(0.5, q_dark + q_mis)}

        return _fn

    raise ValueError(f"Unknown surrogate domain: {domain}")
