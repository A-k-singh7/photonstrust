"""Protocol comparison dashboard -- automated sweep across protocols."""
from __future__ import annotations
import math
from dataclasses import dataclass, field

from photonstrust.protocols.reliability_card import PROTOCOL_CARDS, build_reliability_card

@dataclass(frozen=True)
class DashboardResult:
    """Result of protocol comparison dashboard."""
    protocol_ids: list[str]
    distances_km: list[float]
    rate_curves: dict[str, list[float]]  # protocol_id -> [rate at each distance]
    plob_bound: list[float]  # PLOB bound at each distance
    tgw_bound: list[float]   # TGW bound at each distance
    crossover_distances: dict[str, float]  # protocol pair -> crossover distance
    winners_by_distance: dict[float, str]  # distance -> best protocol


def _plob_bound(distance_km: float, fiber_loss_db_per_km: float = 0.2) -> float:
    """PLOB (Pirandola-Laurenza-Ottaviani-Banchi) repeaterless bound.

    R_PLOB = -log2(1 - eta) ~ 1.44 * eta for small eta
    where eta = 10^(-loss_dB/10)
    """
    loss_db = fiber_loss_db_per_km * distance_km
    eta = 10.0 ** (-loss_db / 10.0)
    if eta >= 1.0:
        return 1e8  # practically infinite
    if eta < 1e-15:
        return 0.0
    return -math.log2(1.0 - eta)


def _tgw_bound(distance_km: float, fiber_loss_db_per_km: float = 0.2) -> float:
    """TGW (Takeoka-Guha-Wilde) bound: R_TGW = log2((1+eta)/(1-eta)).

    For eta << 1, this ~ 2*eta/ln(2).
    """
    loss_db = fiber_loss_db_per_km * distance_km
    eta = 10.0 ** (-loss_db / 10.0)
    if eta >= 1.0:
        return 1e8
    if eta < 1e-15:
        return 0.0
    return math.log2((1.0 + eta) / (1.0 - eta))


def _simple_rate_model(
    distance_km: float,
    max_distance_km: float,
    rate_at_100km: float,
    scaling: str = "eta",  # "eta", "sqrt_eta", "eta_squared"
    fiber_loss_db_per_km: float = 0.2,
) -> float:
    """Simple rate model for protocol comparison.

    Calibrated to match rate_at_100km, then scaled by:
    - O(eta): standard prepare-and-measure
    - O(sqrt(eta)): twin-field / repeater-assisted
    """
    if distance_km > max_distance_km:
        return 0.0
    if distance_km <= 0:
        return rate_at_100km * 100  # rough scale-up at zero distance

    loss_db_100 = fiber_loss_db_per_km * 100
    loss_db = fiber_loss_db_per_km * distance_km

    if scaling == "sqrt_eta":
        # O(sqrt(eta)) -- twin-field scaling
        exponent = (loss_db - loss_db_100) / 20.0  # half the dB
    elif scaling == "eta_squared":
        exponent = (loss_db - loss_db_100) / 5.0
    else:
        # O(eta) -- standard scaling
        exponent = (loss_db - loss_db_100) / 10.0

    return rate_at_100km * 10.0 ** (-exponent)


# Protocol to rate-scaling classification
_SCALING = {
    "bb84": "eta",
    "bbm92": "eta",
    "cv_qkd": "eta",
    "mdi_qkd": "eta",
    "tf_qkd": "sqrt_eta",
    "sns_tf": "sqrt_eta",
    "pm_qkd": "sqrt_eta",
    "di_qkd": "eta_squared",
}


def run_protocol_dashboard(
    protocol_ids: list[str] | None = None,
    distances_km: list[float] | None = None,
    fiber_loss_db_per_km: float = 0.2,
) -> DashboardResult:
    """Sweep all protocols across distance range and compute bounds.

    Parameters
    ----------
    protocol_ids : list or None
        Protocols to include. None = all known.
    distances_km : list or None
        Distance points. None = default range.
    """
    if protocol_ids is None:
        protocol_ids = sorted(PROTOCOL_CARDS.keys())
    if distances_km is None:
        distances_km = [0, 10, 25, 50, 75, 100, 150, 200, 300, 400, 500, 600]

    rate_curves: dict[str, list[float]] = {}
    for pid in protocol_ids:
        card = build_reliability_card(pid)
        scaling = _SCALING.get(pid, "eta")
        rates = []
        for d in distances_km:
            r = _simple_rate_model(
                d, card.max_distance_km, card.typical_rate_at_100km_bps,
                scaling=scaling, fiber_loss_db_per_km=fiber_loss_db_per_km,
            )
            rates.append(r)
        rate_curves[pid] = rates

    plob = [_plob_bound(d, fiber_loss_db_per_km) for d in distances_km]
    tgw = [_tgw_bound(d, fiber_loss_db_per_km) for d in distances_km]

    # Find crossover distances (where one protocol overtakes another)
    crossovers: dict[str, float] = {}
    for i, p1 in enumerate(protocol_ids):
        for p2 in protocol_ids[i+1:]:
            for j in range(len(distances_km) - 1):
                r1_j = rate_curves[p1][j]
                r1_j1 = rate_curves[p1][j+1]
                r2_j = rate_curves[p2][j]
                r2_j1 = rate_curves[p2][j+1]
                if (r1_j - r2_j) * (r1_j1 - r2_j1) < 0:
                    # Linear interpolation for crossover
                    d1 = distances_km[j]
                    d2 = distances_km[j+1]
                    diff1 = r1_j - r2_j
                    diff2 = r1_j1 - r2_j1
                    cross_d = d1 + (d2 - d1) * diff1 / (diff1 - diff2)
                    crossovers[f"{p1}_vs_{p2}"] = cross_d

    # Winner at each distance
    winners: dict[float, str] = {}
    for j, d in enumerate(distances_km):
        best_pid = ""
        best_rate = -1.0
        for pid in protocol_ids:
            if rate_curves[pid][j] > best_rate:
                best_rate = rate_curves[pid][j]
                best_pid = pid
        winners[d] = best_pid

    return DashboardResult(
        protocol_ids=protocol_ids,
        distances_km=distances_km,
        rate_curves=rate_curves,
        plob_bound=plob,
        tgw_bound=tgw,
        crossover_distances=crossovers,
        winners_by_distance=winners,
    )
