"""Entanglement purification protocols.

Implements BBPSSW and DEJMPS entanglement purification for increasing
the fidelity of shared Bell pairs at the cost of consuming extra pairs.

Key references:
    - Bennett et al., PRL 76, 722 (1996) -- BBPSSW protocol
    - Deutsch et al., PRL 77, 2818 (1996) -- DEJMPS protocol
    - Dür & Briegel, Rep. Prog. Phys. 70, 1381 (2007) -- review

In the BBPSSW protocol, two copies of a Werner state with fidelity F are
consumed to produce one copy with higher fidelity:

    F' = (F^2 + (1-F)^2/9) / (F^2 + 2F(1-F)/3 + 5(1-F)^2/9)

The success probability is:
    p_success = F^2 + 2F(1-F)/3 + 5(1-F)^2/9

Notes:
    - Purification increases fidelity but reduces the rate by at least 2x
    - DEJMPS uses Bell-diagonal coefficient updates for better performance
    - Iterative purification converges to F → 1 as rounds → ∞ (if F > 0.5)
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class PurificationResult:
    """Result of entanglement purification."""
    protocol: str              # "bbpssw" or "dejmps"
    rounds: int                # number of purification rounds applied
    fidelity_in: float         # input fidelity
    fidelity_out: float        # output fidelity
    success_probability: float # probability of success per round (last)
    yield_fraction: float      # fraction of pairs surviving all rounds
    pairs_consumed: int        # total input pairs needed per output pair


def bbpssw_purify(F_in: float, rounds: int = 1) -> PurificationResult:
    """BBPSSW entanglement purification protocol.

    Each round takes two pairs with fidelity F and produces one pair
    with higher fidelity F' (on success).

    The recurrence relation for Werner states:

        F' = (F^2 + (1-F)^2/9) / (F^2 + 2F(1-F)/3 + 5(1-F)^2/9)

    with success probability:

        p = F^2 + 2F(1-F)/3 + 5(1-F)^2/9

    Args:
        F_in: Input Bell-pair fidelity (must be > 0.5 for improvement)
        rounds: Number of purification rounds

    Returns:
        PurificationResult with output fidelity and statistics

    Ref: Bennett et al., PRL 76, 722 (1996), Eq. (2)
    """
    F_in = max(0.0, min(1.0, float(F_in)))
    rounds = max(0, int(rounds))

    F = F_in
    total_yield = 1.0
    p_last = 1.0

    for _ in range(rounds):
        if F <= 0.5:
            break
        F_new, p_success = _bbpssw_step(F)
        total_yield *= p_success / 2.0  # consume 2 pairs per attempt
        p_last = p_success
        F = F_new

    pairs_consumed = max(1, int(math.ceil(1.0 / max(total_yield, 1e-30))))

    return PurificationResult(
        protocol="bbpssw",
        rounds=rounds,
        fidelity_in=F_in,
        fidelity_out=F,
        success_probability=p_last,
        yield_fraction=total_yield,
        pairs_consumed=pairs_consumed,
    )


def _bbpssw_step(F: float) -> tuple[float, float]:
    """Single BBPSSW purification step.

    Returns (F_new, p_success).
    """
    F2 = F * F
    oF = 1.0 - F
    oF2 = oF * oF

    numerator = F2 + oF2 / 9.0
    denominator = F2 + 2.0 * F * oF / 3.0 + 5.0 * oF2 / 9.0
    if denominator <= 0:
        return F, 0.0

    F_new = numerator / denominator
    return F_new, denominator


def dejmps_purify(F_in: float, rounds: int = 1) -> PurificationResult:
    """DEJMPS entanglement purification protocol.

    Uses Bell-diagonal state representation for more efficient purification.
    The state is parameterized by coefficients (A, B, C, D) with
    A = F, B = C = D = (1-F)/3 for a Werner state.

    The DEJMPS recurrence:
        A' = (A^2 + B^2) / N
        B' = 2*C*D / N
        C' = (C^2 + D^2) / N  (note: unused for fidelity but tracked)
        D' = 2*A*B / N
        N = (A+B)^2 + (C+D)^2

    The fidelity is F = A' after normalization.

    Args:
        F_in: Input fidelity (> 0.5)
        rounds: Number of purification rounds

    Returns:
        PurificationResult with output fidelity and statistics

    Ref: Deutsch et al., PRL 77, 2818 (1996)
    """
    F_in = max(0.0, min(1.0, float(F_in)))
    rounds = max(0, int(rounds))

    # Initialize Bell-diagonal coefficients for Werner state
    A = F_in
    B = (1.0 - F_in) / 3.0
    C = B
    D = B

    total_yield = 1.0
    p_last = 1.0

    for _ in range(rounds):
        if A <= 0.5:
            break
        A, B, C, D, p_success = _dejmps_step(A, B, C, D)
        total_yield *= p_success / 2.0
        p_last = p_success

    pairs_consumed = max(1, int(math.ceil(1.0 / max(total_yield, 1e-30))))

    return PurificationResult(
        protocol="dejmps",
        rounds=rounds,
        fidelity_in=F_in,
        fidelity_out=A,
        success_probability=p_last,
        yield_fraction=total_yield,
        pairs_consumed=pairs_consumed,
    )


def _dejmps_step(
    A: float, B: float, C: float, D: float,
) -> tuple[float, float, float, float, float]:
    """Single DEJMPS purification step.

    Returns (A', B', C', D', p_success).
    """
    N = (A + B) ** 2 + (C + D) ** 2
    if N <= 0:
        return A, B, C, D, 0.0

    A_new = (A ** 2 + B ** 2) / N
    B_new = 2.0 * C * D / N
    C_new = (C ** 2 + D ** 2) / N
    D_new = 2.0 * A * B / N

    return A_new, B_new, C_new, D_new, N


def iterative_purification(
    F_in: float,
    target_fidelity: float,
    *,
    protocol: str = "bbpssw",
    max_rounds: int = 100,
) -> PurificationResult:
    """Iteratively purify until target fidelity is reached.

    Args:
        F_in: Input fidelity
        target_fidelity: Target output fidelity
        protocol: "bbpssw" or "dejmps"
        max_rounds: Maximum number of rounds

    Returns:
        PurificationResult with the number of rounds needed
    """
    if F_in >= target_fidelity:
        return PurificationResult(
            protocol=protocol, rounds=0,
            fidelity_in=F_in, fidelity_out=F_in,
            success_probability=1.0, yield_fraction=1.0,
            pairs_consumed=1,
        )

    if F_in <= 0.5:
        return PurificationResult(
            protocol=protocol, rounds=0,
            fidelity_in=F_in, fidelity_out=F_in,
            success_probability=0.0, yield_fraction=0.0,
            pairs_consumed=1,
        )

    for r in range(1, max_rounds + 1):
        if protocol == "dejmps":
            result = dejmps_purify(F_in, rounds=r)
        else:
            result = bbpssw_purify(F_in, rounds=r)

        if result.fidelity_out >= target_fidelity:
            return result

    # Max rounds reached
    if protocol == "dejmps":
        return dejmps_purify(F_in, rounds=max_rounds)
    return bbpssw_purify(F_in, rounds=max_rounds)
