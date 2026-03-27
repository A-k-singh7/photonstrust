"""PhotonTrust package."""

__all__ = [
    "catalog",
    "cli",
    "cost",
    "network",
    "config",
    "presets",
    "qkd",
    "report",
    "sweep",
    "plots",
    "physics",
    # High-level "easy" API (Phase D1)
    "simulate_qkd_link",
    "compare_protocols",
    "design_pic",
    "plan_network",
    "plan_satellite",
]

from photonstrust.easy import (
    simulate_qkd_link,
    compare_protocols,
    design_pic,
    plan_network,
    plan_satellite,
)
