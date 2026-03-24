"""Return-on-investment analysis for QKD deployments."""

from __future__ import annotations

import math

from photonstrust.analytics.types import ROIAnalysis

_SECONDS_PER_YEAR = 31_536_000


def _npv(annual_net: float, discount_rate: float, years: int, investment: float) -> float:
    """Compute net present value."""
    return sum(
        annual_net / (1.0 + discount_rate) ** t
        for t in range(1, years + 1)
    ) - investment


def _irr(annual_net: float, investment: float, years: int) -> float:
    """Estimate IRR via bisection."""
    if annual_net <= 0:
        return 0.0

    lo, hi = 0.0, 10.0
    for _ in range(200):
        mid = (lo + hi) / 2.0
        npv_mid = _npv(annual_net, mid, years, investment)
        if npv_mid > 0:
            lo = mid
        else:
            hi = mid
    return round((lo + hi) / 2.0, 6)


def compute_roi(
    deployment_id: str,
    total_investment_usd: float,
    annual_key_rate_bps: float,
    *,
    key_value_per_bit_usd: float = 1e-6,
    annual_opex_usd: float = 0.0,
    discount_rate: float = 0.08,
    projection_years: int = 10,
) -> ROIAnalysis:
    """Compute ROI metrics for a QKD deployment.

    Parameters
    ----------
    deployment_id:
        Unique deployment identifier.
    total_investment_usd:
        Total upfront capital expenditure.
    annual_key_rate_bps:
        Average key generation rate in bits per second.
    key_value_per_bit_usd:
        Monetary value assigned to each secure key bit.
    annual_opex_usd:
        Annual operational expenditure.
    discount_rate:
        Discount rate for NPV calculation.
    projection_years:
        Number of years to project.
    """
    annual_key_value = annual_key_rate_bps * _SECONDS_PER_YEAR * key_value_per_bit_usd
    annual_net = annual_key_value - annual_opex_usd

    # NPV
    npv = _npv(annual_net, discount_rate, projection_years, total_investment_usd)

    # Payback period
    cumulative = 0.0
    payback = float("inf")
    for year in range(1, projection_years + 1):
        cumulative += annual_net
        if cumulative >= total_investment_usd:
            payback = float(year)
            break

    # IRR
    irr = _irr(annual_net, total_investment_usd, projection_years)

    assumptions = {
        "key_value_per_bit_usd": key_value_per_bit_usd,
        "discount_rate": discount_rate,
        "projection_years": projection_years,
        "annual_opex_usd": annual_opex_usd,
    }

    return ROIAnalysis(
        deployment_id=deployment_id,
        total_investment_usd=total_investment_usd,
        annual_key_value_usd=round(annual_key_value, 2),
        payback_period_years=payback,
        net_present_value_usd=round(npv, 2),
        internal_rate_of_return=irr,
        assumptions=assumptions,
    )
