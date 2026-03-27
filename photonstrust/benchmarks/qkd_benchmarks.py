"""QKD protocol benchmarking and fundamental bounds.

Provides PLOB bound computation, protocol benchmark curves,
and figure-of-merit calculations for comparing QKD protocols.

Key references:
    - Pirandola et al., Nature Comms 8, 15043 (2017) -- PLOB bound
    - Takeoka et al., Nature Comms 5, 5235 (2014) -- TGW bound
    - Lucamarini et al., Nature 557, 400 (2018) -- TF-QKD beating PLOB

Fundamental bounds:
    - PLOB: C(eta) = -log2(1 - eta)  [repeaterless capacity]
    - TGW:  C(eta) = log2((1+eta)/(1-eta))  [slightly tighter]
    - Direct transmission: R <= eta  [no error correction]
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Fundamental bounds
# ---------------------------------------------------------------------------

def plob_bound(eta: float) -> float:
    """PLOB repeaterless secret key capacity bound.

    C(eta) = -log2(1 - eta)

    This is the ultimate rate limit for any point-to-point QKD
    protocol without quantum repeaters.

    Args:
        eta: Total channel transmittance (0 to 1)

    Returns:
        Secret key capacity in bits per channel use

    Ref: Pirandola et al., Nature Comms 8, 15043 (2017)
    """
    eta = max(0.0, min(1.0 - 1e-15, float(eta)))
    if eta <= 0:
        return 0.0
    return -math.log2(1.0 - eta)


def tgw_bound(eta: float) -> float:
    """TGW (Takeoka-Guha-Wilde) repeaterless bound.

    C(eta) = log2((1 + eta) / (1 - eta))

    Slightly tighter than PLOB for some ranges.

    Args:
        eta: Channel transmittance

    Returns:
        Capacity bound (bits/use)

    Ref: Takeoka et al., Nature Comms 5, 5235 (2014)
    """
    eta = max(0.0, min(1.0 - 1e-15, float(eta)))
    if eta <= 0:
        return 0.0
    return math.log2((1.0 + eta) / (1.0 - eta))


def direct_transmission_bound(eta: float) -> float:
    """Direct transmission bound (no error correction).

    R <= eta (trivial upper bound).

    Args:
        eta: Channel transmittance

    Returns:
        Rate bound (bits/use)
    """
    return max(0.0, min(1.0, float(eta)))


def fiber_transmittance(
    distance_km: float,
    loss_db_per_km: float = 0.2,
) -> float:
    """Fiber channel transmittance.

    eta = 10^(-alpha * L / 10)

    Args:
        distance_km: Fiber length (km)
        loss_db_per_km: Fiber attenuation (dB/km)

    Returns:
        Transmittance (0 to 1)
    """
    L = max(0.0, float(distance_km))
    alpha = max(0.0, float(loss_db_per_km))
    return 10.0 ** (-alpha * L / 10.0)


# ---------------------------------------------------------------------------
# Benchmark curve computation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BenchmarkPoint:
    """Single point on a benchmark curve."""
    distance_km: float
    key_rate_bps: float
    key_rate_per_pulse: float
    plob_bound_per_pulse: float
    efficiency_vs_plob: float       # rate / PLOB bound
    transmittance: float


@dataclass(frozen=True)
class BenchmarkCurve:
    """Complete benchmark curve for a protocol."""
    protocol_name: str
    distances_km: list[float]
    key_rates_bps: list[float]
    key_rates_per_pulse: list[float]
    plob_bounds: list[float]
    max_distance_km: float          # distance where rate -> 0
    figure_of_merit: float          # area under rate curve
    beats_plob: bool                # True if any rate > PLOB
    diagnostics: dict[str, Any] = field(default_factory=dict)


def compute_benchmark_curve(
    protocol_name: str,
    scenario: dict,
    *,
    distances_km: list[float] | None = None,
    loss_db_per_km: float = 0.2,
) -> BenchmarkCurve:
    """Compute SKR vs distance benchmark curve for a protocol.

    Evaluates the protocol at multiple distances and compares
    against the PLOB bound.

    Args:
        protocol_name: Protocol identifier
        scenario: Scenario dict for the protocol
        distances_km: List of distances to evaluate
        loss_db_per_km: Fiber loss for PLOB bound computation

    Returns:
        BenchmarkCurve with rates and comparison to PLOB
    """
    from photonstrust.qkd_protocols.common import normalize_protocol_name
    from photonstrust.qkd_protocols.registry import resolve_protocol_module

    proto_name = normalize_protocol_name(protocol_name)
    module = resolve_protocol_module(proto_name)

    if distances_km is None:
        distances_km = [float(d) for d in range(0, 505, 5)]

    rates_bps: list[float] = []
    rates_per_pulse: list[float] = []
    plob_list: list[float] = []

    src = dict((scenario or {}).get("source", {}) or {})
    rep_rate_hz = float(src.get("rep_rate_mhz", 1.0)) * 1e6

    for d in distances_km:
        result = module.evaluator(scenario, d, None)
        rates_bps.append(result.key_rate_bps)
        if rep_rate_hz > 0:
            rates_per_pulse.append(result.key_rate_bps / rep_rate_hz)
        else:
            rates_per_pulse.append(0.0)

        eta = fiber_transmittance(d, loss_db_per_km)
        plob_list.append(plob_bound(eta))

    # Max distance (where rate > 0)
    max_dist = 0.0
    for d, r in zip(distances_km, rates_bps):
        if r > 0:
            max_dist = d

    # Figure of merit: normalized area under SKR/pulse curve
    fom = 0.0
    for i in range(len(distances_km) - 1):
        dx = distances_km[i + 1] - distances_km[i]
        fom += 0.5 * (rates_per_pulse[i] + rates_per_pulse[i + 1]) * dx

    # Does it beat PLOB?
    beats = any(rp > pb for rp, pb in zip(rates_per_pulse, plob_list) if pb > 0)

    return BenchmarkCurve(
        protocol_name=proto_name,
        distances_km=distances_km,
        key_rates_bps=rates_bps,
        key_rates_per_pulse=rates_per_pulse,
        plob_bounds=plob_list,
        max_distance_km=max_dist,
        figure_of_merit=fom,
        beats_plob=beats,
        diagnostics={
            "n_points": len(distances_km),
            "loss_db_per_km": loss_db_per_km,
            "rep_rate_hz": rep_rate_hz,
        },
    )


# ---------------------------------------------------------------------------
# Protocol comparison
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ProtocolComparison:
    """Comparison of multiple protocols."""
    protocol_names: list[str]
    max_distances_km: list[float]
    figures_of_merit: list[float]
    beats_plob: list[bool]
    best_rate_protocol: str         # highest FoM
    longest_range_protocol: str     # longest max distance


def compare_protocols(
    protocols: dict[str, dict],
    *,
    distances_km: list[float] | None = None,
) -> ProtocolComparison:
    """Compare multiple QKD protocols.

    Args:
        protocols: {protocol_name: scenario_dict}
        distances_km: Common distance grid

    Returns:
        ProtocolComparison summary
    """
    names: list[str] = []
    max_dists: list[float] = []
    foms: list[float] = []
    plob_beats: list[bool] = []

    for name, scenario in protocols.items():
        curve = compute_benchmark_curve(name, scenario, distances_km=distances_km)
        names.append(name)
        max_dists.append(curve.max_distance_km)
        foms.append(curve.figure_of_merit)
        plob_beats.append(curve.beats_plob)

    best_fom_idx = foms.index(max(foms)) if foms else 0
    best_range_idx = max_dists.index(max(max_dists)) if max_dists else 0

    return ProtocolComparison(
        protocol_names=names,
        max_distances_km=max_dists,
        figures_of_merit=foms,
        beats_plob=plob_beats,
        best_rate_protocol=names[best_fom_idx] if names else "",
        longest_range_protocol=names[best_range_idx] if names else "",
    )
