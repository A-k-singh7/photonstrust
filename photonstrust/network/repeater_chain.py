"""Quantum repeater chain models (1G, 2G, 3G).

Implements three generations of quantum repeater architectures for
extending quantum communication beyond direct-link limits.

Key references:
    - Briegel et al., PRL 81, 5932 (1998) -- 1G repeaters
    - Muralidharan et al., Sci. Reports 6, 20463 (2016) -- repeater generations
    - Azuma et al., Nature Comms 6, 6787 (2015) -- all-photonic repeaters
    - Jiang et al., PRA 79, 032325 (2009) -- 2G repeaters

1G Repeaters (heralded entanglement + purification + swapping):
    - Rate limited by waiting time: t_wait = H_n / R_link
    - Fidelity through m swap levels: F = 0.5 + 0.5*(2*F_link - 1)^(2^m)
    - Memory decoherence: F(t) = 0.5 + 0.5*(2*F - 1)*exp(-t/T2)

2G Repeaters (QEC-based):
    - Rate = R_link * code_rate / encoding_overhead
    - Fidelity limited by logical error rate of QEC code

3G Repeaters (all-photonic):
    - Rate ~ R_source * p_fusion^n_fusions
    - No quantum memories needed (GHZ state approach)
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class RepeaterChainResult:
    """Result of a repeater chain computation."""
    generation: int              # 1, 2, or 3
    total_distance_km: float     # end-to-end distance
    n_segments: int              # number of elementary links
    n_nodes: int                 # number of repeater nodes
    rate_hz: float               # end-to-end entanglement rate
    fidelity: float              # end-to-end Bell pair fidelity
    key_rate_bps: float          # secure key rate (bits/s)
    waiting_time_s: float        # average waiting time per link
    pairs_consumed_per_key_bit: float  # resource overhead


def first_gen_repeater_chain(
    total_distance_km: float,
    n_segments: int = 4,
    *,
    fiber_loss_db_per_km: float = 0.2,
    source_rate_hz: float = 1e9,
    source_fidelity: float = 0.98,
    detector_efficiency: float = 0.9,
    memory_T2_s: float = 1.0,
    memory_efficiency: float = 0.9,
    purification_rounds: int = 0,
    swap_efficiency: float = 0.5,
    f_ec: float = 1.16,
) -> RepeaterChainResult:
    """First-generation quantum repeater chain.

    Uses heralded entanglement distribution, optional purification,
    and nested entanglement swapping.

    The rate is limited by the slowest segment's waiting time:

        t_wait = H_n / R_link

    where H_n is the n-th harmonic number (H_n = sum_{k=1}^{n} 1/k)
    and R_link is the elementary link generation rate.

    Fidelity through m swap levels:

        F_swap = 0.5 + 0.5 * (2*F_link - 1)^(2^m)

    Memory decoherence reduces fidelity:

        F(t) = 0.5 + 0.5 * (2*F - 1) * exp(-t/T2)

    Args:
        total_distance_km: Total Alice-Bob distance
        n_segments: Number of elementary links (power of 2 preferred)
        fiber_loss_db_per_km: Fiber attenuation
        source_rate_hz: Entangled pair source repetition rate
        source_fidelity: Source Bell pair fidelity
        detector_efficiency: Single-photon detector efficiency
        memory_T2_s: Memory coherence time (seconds)
        memory_efficiency: Memory read/write efficiency
        purification_rounds: Number of BBPSSW purification rounds per link
        swap_efficiency: Bell state measurement success probability
        f_ec: Error correction efficiency factor

    Returns:
        RepeaterChainResult with rate and fidelity

    Ref: Briegel et al., PRL 81, 5932 (1998)
    """
    total_distance_km = max(0.0, float(total_distance_km))
    n_segments = max(1, int(n_segments))
    n_nodes = n_segments - 1  # repeater nodes between Alice and Bob

    # Segment length
    L_seg = total_distance_km / n_segments

    # Segment transmittance (one-way, each half goes to the midpoint)
    half_L = L_seg / 2.0
    eta_half = 10.0 ** (-fiber_loss_db_per_km * half_L / 10.0)

    # Elementary link generation probability
    # Both photons must arrive and both detectors must click
    p_link = eta_half ** 2 * detector_efficiency ** 2 * memory_efficiency ** 2
    p_link = max(1e-30, min(1.0, p_link))

    # Elementary link rate
    R_link = source_rate_hz * p_link

    # Swap levels (nested binary swapping)
    m_swap = max(0, int(math.ceil(math.log2(max(1, n_segments)))))

    # Waiting time: need all n_segments links simultaneously
    # Average waiting time = H_n / R_link where H_n is harmonic number
    H_n = sum(1.0 / k for k in range(1, n_segments + 1))
    t_wait_s = H_n / max(R_link, 1e-30)

    # Entanglement swapping: each level halves the fidelity excess above 0.5
    F_link = min(1.0, source_fidelity)

    # Purification (optional)
    pairs_per_link = 1
    if purification_rounds > 0:
        from photonstrust.network.purification import bbpssw_purify
        pur = bbpssw_purify(F_link, rounds=purification_rounds)
        F_link = pur.fidelity_out
        pairs_per_link = pur.pairs_consumed

    # Nested swapping fidelity: F = 0.5 + 0.5*(2F-1)^(2^m)
    # Each swap level: F' = 0.5 + 0.5*(2F-1)^2 * swap_eff + (1-swap_eff)*0.25
    F_chain = F_link
    for _ in range(m_swap):
        excess = max(0.0, 2.0 * F_chain - 1.0)
        F_chain = 0.5 + 0.5 * excess ** 2 * swap_efficiency

    # Memory decoherence during waiting
    if memory_T2_s > 0 and t_wait_s > 0:
        decoherence = math.exp(-t_wait_s / memory_T2_s)
        F_chain = 0.5 + (F_chain - 0.5) * decoherence

    F_chain = max(0.5, min(1.0, F_chain))

    # End-to-end rate (including swapping success)
    swap_success_total = swap_efficiency ** m_swap
    rate_hz = R_link / (H_n * pairs_per_link) * swap_success_total

    # Key rate from fidelity
    key_rate_bps = _key_rate_from_fidelity(rate_hz, F_chain, f_ec)

    return RepeaterChainResult(
        generation=1,
        total_distance_km=total_distance_km,
        n_segments=n_segments,
        n_nodes=n_nodes,
        rate_hz=rate_hz,
        fidelity=F_chain,
        key_rate_bps=key_rate_bps,
        waiting_time_s=t_wait_s,
        pairs_consumed_per_key_bit=max(1.0, 1.0 / max(key_rate_bps / max(rate_hz, 1e-30), 1e-30)),
    )


def second_gen_repeater_chain(
    total_distance_km: float,
    n_segments: int = 8,
    *,
    fiber_loss_db_per_km: float = 0.2,
    source_rate_hz: float = 1e6,
    code_distance: int = 3,
    logical_error_rate: float = 1e-3,
    encoding_overhead: int = 7,
    detector_efficiency: float = 0.99,
    f_ec: float = 1.16,
) -> RepeaterChainResult:
    """Second-generation quantum repeater chain (QEC-based).

    Uses quantum error correction to protect quantum information during
    transmission, eliminating the need for long-lived quantum memories.

    Rate = R_link * code_rate / encoding_overhead

    where code_rate = k/n for an [[n,k,d]] QEC code.

    Args:
        total_distance_km: Total Alice-Bob distance
        n_segments: Number of elementary links
        fiber_loss_db_per_km: Fiber attenuation
        source_rate_hz: Encoded qubit source rate
        code_distance: QEC code distance d
        logical_error_rate: Logical error probability per operation
        encoding_overhead: Physical qubits per logical qubit
        detector_efficiency: Detector efficiency
        f_ec: Error correction efficiency

    Returns:
        RepeaterChainResult with rate and fidelity

    Ref: Jiang et al., PRA 79, 032325 (2009)
    """
    total_distance_km = max(0.0, float(total_distance_km))
    n_segments = max(1, int(n_segments))
    n_nodes = n_segments - 1

    L_seg = total_distance_km / n_segments
    eta_seg = 10.0 ** (-fiber_loss_db_per_km * L_seg / 10.0)
    eta_total = eta_seg * detector_efficiency

    # Code rate: 1/encoding_overhead (e.g., Steane [[7,1,3]] has rate 1/7)
    code_rate = 1.0 / max(1, encoding_overhead)

    # Rate through the chain
    rate_hz = source_rate_hz * eta_total * code_rate

    # Fidelity: each segment adds logical errors
    p_logical = logical_error_rate * n_segments
    fidelity = max(0.5, 1.0 - p_logical)

    key_rate_bps = _key_rate_from_fidelity(rate_hz, fidelity, f_ec)

    return RepeaterChainResult(
        generation=2,
        total_distance_km=total_distance_km,
        n_segments=n_segments,
        n_nodes=n_nodes,
        rate_hz=rate_hz,
        fidelity=fidelity,
        key_rate_bps=key_rate_bps,
        waiting_time_s=0.0,  # no waiting (QEC-based)
        pairs_consumed_per_key_bit=float(encoding_overhead),
    )


def third_gen_repeater_chain(
    total_distance_km: float,
    n_segments: int = 4,
    *,
    fiber_loss_db_per_km: float = 0.2,
    source_rate_hz: float = 1e9,
    p_fusion: float = 0.5,
    cluster_size: int = 6,
    detector_efficiency: float = 0.99,
    f_ec: float = 1.16,
) -> RepeaterChainResult:
    """Third-generation quantum repeater chain (all-photonic).

    Uses photonic graph states (GHZ/cluster states) and fusion gates
    to perform repeater operations without quantum memories.

    Rate ~ R_source * (p_fusion * eta)^n_fusions

    where n_fusions is the number of fusion operations needed.

    Args:
        total_distance_km: Total Alice-Bob distance
        n_segments: Number of elementary links
        fiber_loss_db_per_km: Fiber attenuation
        source_rate_hz: GHZ/cluster state source rate
        p_fusion: Fusion gate success probability
        cluster_size: Number of photons per cluster state
        detector_efficiency: Detector efficiency
        f_ec: Error correction efficiency

    Returns:
        RepeaterChainResult with rate and fidelity

    Ref: Azuma et al., Nature Comms 6, 6787 (2015)
    """
    total_distance_km = max(0.0, float(total_distance_km))
    n_segments = max(1, int(n_segments))
    n_nodes = n_segments - 1

    L_seg = total_distance_km / n_segments
    eta_seg = 10.0 ** (-fiber_loss_db_per_km * L_seg / 10.0)
    eta_det = detector_efficiency

    # Number of fusion operations per repeater node
    n_fusions_per_node = max(1, cluster_size - 2)
    n_fusions_total = n_nodes * n_fusions_per_node

    # Success probability: each fusion must succeed and photons must arrive
    p_segment = eta_seg * eta_det
    p_total = (p_fusion * p_segment) ** n_fusions_total

    # Rate
    rate_hz = source_rate_hz * max(0.0, p_total)

    # Fidelity: limited by fusion imperfections
    F_per_fusion = 1.0 - (1.0 - p_fusion) * 0.1  # simplified
    fidelity = max(0.5, F_per_fusion ** n_fusions_total)

    key_rate_bps = _key_rate_from_fidelity(rate_hz, fidelity, f_ec)

    return RepeaterChainResult(
        generation=3,
        total_distance_km=total_distance_km,
        n_segments=n_segments,
        n_nodes=n_nodes,
        rate_hz=rate_hz,
        fidelity=fidelity,
        key_rate_bps=key_rate_bps,
        waiting_time_s=0.0,  # all-photonic, no memory
        pairs_consumed_per_key_bit=float(cluster_size * n_segments),
    )


def _key_rate_from_fidelity(rate_hz: float, fidelity: float, f_ec: float) -> float:
    """Convert entanglement rate and fidelity to secure key rate.

    Using the BBM92 key rate formula:
        K = R * [1 - H(QBER) - f_EC * H(QBER)]
    where QBER = 1 - F.
    """
    if rate_hz <= 0 or fidelity <= 0.5:
        return 0.0
    qber = max(0.0, 1.0 - fidelity)
    if qber <= 0:
        return rate_hz
    h_q = _binary_entropy(qber)
    r_bit = max(0.0, 1.0 - (1.0 + f_ec) * h_q)
    return rate_hz * r_bit


def _binary_entropy(x: float) -> float:
    if x <= 0.0 or x >= 1.0:
        return 0.0
    return -x * math.log2(x) - (1.0 - x) * math.log2(1.0 - x)
