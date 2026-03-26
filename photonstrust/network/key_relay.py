"""Trusted-node key relay for QKD networks.

Implements XOR-based key relay through a chain of trusted intermediate
nodes and computes the achievable end-to-end key rate accounting for
authentication overhead.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RelayResult:
    """Result of relaying a key through trusted nodes."""

    key_bits: int
    end_to_end_rate_bps: float
    auth_consumed_bits: int
    relay_latency_ms: float
    n_trusted_nodes: int
    bottleneck_link: str


def relay_key_through_trusted_nodes(
    path_nodes: list[str],
    link_keys: dict[str, bytes],  # "A->B" -> key bytes
) -> RelayResult:
    """XOR-based key relay through trusted nodes.

    Each intermediate node receives keys from both adjacent links,
    XORs them, and forwards the result.  The end-to-end key is
    reconstructed by XORing all intermediate ciphertexts.

    Parameters
    ----------
    path_nodes:
        Ordered list of nodes ``[Alice, T1, T2, ..., Bob]``.
    link_keys:
        Mapping ``"{node_i}->{node_j}" -> key_bytes`` for every adjacent
        pair in the path.
    """
    if len(path_nodes) < 2:
        raise ValueError("Path must have at least 2 nodes")

    n_links = len(path_nodes) - 1
    n_trusted = max(0, n_links - 1)

    # Find minimum key length across all links (bottleneck)
    min_len: int | None = None
    bottleneck = ""
    for i in range(n_links):
        key_id = f"{path_nodes[i]}->{path_nodes[i + 1]}"
        alt_id = f"{path_nodes[i + 1]}->{path_nodes[i]}"
        key = link_keys.get(key_id) or link_keys.get(alt_id)
        if key is None:
            raise ValueError(f"No link key for {key_id}")
        if min_len is None or len(key) < min_len:
            min_len = len(key)
            bottleneck = key_id

    if min_len is None or min_len == 0:
        return RelayResult(
            key_bits=0,
            end_to_end_rate_bps=0.0,
            auth_consumed_bits=0,
            relay_latency_ms=0.0,
            n_trusted_nodes=n_trusted,
            bottleneck_link=bottleneck,
        )

    # XOR relay: end-to-end key = XOR of all link keys (truncated to min)
    result_key = bytearray(min_len)
    for i in range(n_links):
        key_id = f"{path_nodes[i]}->{path_nodes[i + 1]}"
        alt_id = f"{path_nodes[i + 1]}->{path_nodes[i]}"
        key = link_keys.get(key_id) or link_keys.get(alt_id)
        for j in range(min_len):
            result_key[j] ^= key[j]  # type: ignore[index]

    # Authentication overhead: ~128 bits per link for universal hash
    auth_bits_per_link = 128
    auth_total = auth_bits_per_link * n_links

    key_bits = min_len * 8 - auth_total
    key_bits = max(0, key_bits)

    return RelayResult(
        key_bits=key_bits,
        end_to_end_rate_bps=0.0,  # rate requires timing information
        auth_consumed_bits=auth_total,
        relay_latency_ms=float(n_trusted) * 0.1,  # ~0.1 ms per relay hop
        n_trusted_nodes=n_trusted,
        bottleneck_link=bottleneck,
    )


def compute_relay_rate(
    link_rates_bps: list[float],
    auth_overhead_bits_per_round: int = 128,
    round_size_bits: int = 1024,
) -> float:
    """End-to-end relay rate = bottleneck link rate minus auth overhead.

    The bottleneck is the slowest link, and each round consumes
    *auth_overhead_bits_per_round* bits for authentication of the XOR
    ciphertext.
    """
    if not link_rates_bps:
        return 0.0

    min_rate = min(link_rates_bps)
    if min_rate <= 0:
        return 0.0

    # Fraction of key material that survives authentication
    useful_fraction = max(
        0.0,
        (round_size_bits - auth_overhead_bits_per_round) / round_size_bits,
    )

    return min_rate * useful_fraction
