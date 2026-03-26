"""Error correction for QKD post-processing.

Implements LDPC belief propagation and Cascade error correction protocols
for reconciling Alice's and Bob's sifted key strings.

Key references:
    - Richardson & Urbanke, "Modern Coding Theory" (2008) -- LDPC theory
    - Brassard & Salvail, CRYPTO 1993 -- Cascade protocol
    - Martinez-Mateo et al., Sci. Reports 3, 1576 (2013) -- practical QKD EC
    - Elkouss et al., QIC 11, 226 (2011) -- LDPC for QKD

Notes:
    - LDPC codes achieve near-Shannon-limit efficiency (f_EC ~1.05-1.16)
    - Cascade is simpler but requires more communication rounds
    - Both protocols leak parity information to Eve; this must be accounted
      for in privacy amplification
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ECResult:
    """Result of error correction."""
    method: str                        # "ldpc" or "cascade"
    success: bool                      # whether decoding converged
    reconciliation_efficiency: float   # f_EC = leaked / H(QBER)
    frame_error_rate: float            # fraction of frames that failed
    leaked_bits: int                   # total information leaked to Eve
    corrected_errors: int              # number of errors corrected
    output_length: int                 # length of reconciled key


# ---------------------------------------------------------------------------
# LDPC error correction
# ---------------------------------------------------------------------------

def build_ldpc_parity_check(
    n: int,
    rate: float,
    *,
    seed: int = 0,
    dv: int = 3,
    dc: int = 6,
) -> np.ndarray:
    """Build a random regular LDPC parity-check matrix H.

    Constructs an (n-k) x n binary matrix H using Gallager's random
    construction with variable-node degree dv and check-node degree dc.

    The code rate is approximately 1 - dv/dc.

    Args:
        n: Block length (number of variable nodes)
        rate: Target code rate (0 < rate < 1)
        seed: Random seed for reproducibility
        dv: Variable-node degree (default 3)
        dc: Check-node degree (default 6)

    Returns:
        H: (m x n) binary parity-check matrix, m = n - k

    Ref: Gallager, "Low-Density Parity-Check Codes" (1962)
    """
    if n <= 0 or not (0.0 < rate < 1.0):
        raise ValueError(f"Invalid LDPC parameters: n={n}, rate={rate}")

    m = max(1, int(round(n * (1.0 - rate))))
    rng = np.random.default_rng(seed)

    # Gallager random construction: build dv sub-matrices
    H = np.zeros((m, n), dtype=np.int8)

    for _ in range(dv):
        # Random permutation of column indices, partitioned into blocks of dc
        perm = rng.permutation(n)
        for row_idx in range(m):
            start = row_idx * dc % n
            cols = perm[start : start + dc]
            H[row_idx, cols[:min(dc, len(cols))]] = 1

    # Ensure each column has at least one 1
    for col in range(n):
        if H[:, col].sum() == 0:
            row = rng.integers(0, m)
            H[row, col] = 1

    return H % 2


def belief_propagation_decode(
    syndrome: np.ndarray,
    H: np.ndarray,
    channel_llr: np.ndarray,
    *,
    max_iterations: int = 50,
) -> tuple[np.ndarray, bool]:
    """Sum-product belief propagation decoder for binary LDPC codes.

    Decodes using the standard sum-product algorithm:

    VN → CN message: L_{v→c} = L_ch(v) + sum_{c' != c} L_{c'→v}
    CN → VN message: L_{c→v} = 2 * atanh(prod_{v' != v} tanh(L_{v'→c} / 2))

    Args:
        syndrome: Target syndrome vector (m,)
        H: Parity-check matrix (m x n)
        channel_llr: Channel log-likelihood ratios (n,)
        max_iterations: Maximum BP iterations

    Returns:
        (decoded_bits, converged): decoded hard decision and convergence flag

    Ref: Richardson & Urbanke, "Modern Coding Theory" (2008), Ch. 2
    """
    m, n = H.shape
    channel_llr = np.asarray(channel_llr, dtype=np.float64)
    syndrome = np.asarray(syndrome, dtype=np.int8) % 2

    # Initialize messages
    # L_v2c[c, v]: message from variable v to check c
    # L_c2v[c, v]: message from check c to variable v
    L_v2c = np.zeros((m, n), dtype=np.float64)
    L_c2v = np.zeros((m, n), dtype=np.float64)

    # Initialize VN→CN with channel LLR
    for c in range(m):
        for v in range(n):
            if H[c, v]:
                L_v2c[c, v] = channel_llr[v]

    for iteration in range(max_iterations):
        # --- Check-node update (CN → VN) ---
        for c in range(m):
            vns = np.where(H[c, :] != 0)[0]
            if len(vns) == 0:
                continue
            for v in vns:
                # Product of tanh(L/2) over all other variable nodes
                product = 1.0
                for v2 in vns:
                    if v2 != v:
                        val = np.clip(L_v2c[c, v2] / 2.0, -20.0, 20.0)
                        product *= np.tanh(val)
                product = np.clip(product, -1.0 + 1e-15, 1.0 - 1e-15)
                sign = (-1.0) ** syndrome[c]
                L_c2v[c, v] = sign * 2.0 * np.arctanh(product)

        # --- Variable-node update (VN → CN) ---
        for v in range(n):
            cns = np.where(H[:, v] != 0)[0]
            total = channel_llr[v] + np.sum(L_c2v[cns, v])
            for c in cns:
                L_v2c[c, v] = total - L_c2v[c, v]

        # --- Hard decision and syndrome check ---
        posteriors = channel_llr.copy()
        for v in range(n):
            cns = np.where(H[:, v] != 0)[0]
            posteriors[v] += np.sum(L_c2v[cns, v])

        decoded = (posteriors < 0).astype(np.int8)
        current_syndrome = (H @ decoded) % 2

        if np.array_equal(current_syndrome, syndrome):
            return decoded, True

    return decoded, False


def ldpc_error_correction(
    alice_bits: np.ndarray,
    bob_bits: np.ndarray,
    qber: float,
    *,
    seed: int = 0,
    code_rate: float | None = None,
    max_bp_iterations: int = 50,
) -> ECResult:
    """Perform LDPC-based error correction.

    Alice sends the syndrome of her key string using the parity-check
    matrix H. Bob uses belief propagation to decode Alice's key from
    his noisy version and the syndrome.

    Args:
        alice_bits: Alice's sifted key (n,) binary array
        bob_bits: Bob's sifted key (n,) binary array
        qber: Estimated quantum bit error rate
        seed: Random seed for code construction
        code_rate: Code rate (default: chosen from QBER)
        max_bp_iterations: Max BP iterations

    Returns:
        ECResult with reconciliation efficiency and statistics
    """
    n = len(alice_bits)
    if n <= 0:
        return ECResult(
            method="ldpc", success=False,
            reconciliation_efficiency=float("inf"),
            frame_error_rate=1.0, leaked_bits=0,
            corrected_errors=0, output_length=0,
        )

    alice = np.asarray(alice_bits, dtype=np.int8) % 2
    bob = np.asarray(bob_bits, dtype=np.int8) % 2

    # Choose code rate from QBER if not specified
    if code_rate is None:
        h_q = _binary_entropy(qber)
        # Target rate slightly below capacity: R = 1 - f_EC * H(QBER)
        code_rate = max(0.05, min(0.95, 1.0 - 1.1 * h_q))

    H = build_ldpc_parity_check(n, code_rate, seed=seed)
    m = H.shape[0]

    # Alice computes and sends syndrome
    syndrome = (H @ alice) % 2

    # Channel LLR from QBER
    qber_clipped = np.clip(qber, 1e-10, 0.5 - 1e-10)
    channel_llr = np.where(
        bob == 0,
        np.log((1.0 - qber_clipped) / qber_clipped),
        np.log(qber_clipped / (1.0 - qber_clipped)),
    )

    decoded, converged = belief_propagation_decode(
        syndrome, H, channel_llr, max_iterations=max_bp_iterations,
    )

    errors_before = int(np.sum(alice != bob))
    errors_after = int(np.sum(alice != decoded))
    corrected = errors_before - errors_after

    # Leaked information: m parity bits
    leaked = m
    h_q = _binary_entropy(qber)
    if h_q > 0 and n > 0:
        f_ec = (leaked / n) / h_q
    else:
        f_ec = 1.0

    return ECResult(
        method="ldpc",
        success=converged and errors_after == 0,
        reconciliation_efficiency=f_ec,
        frame_error_rate=0.0 if (converged and errors_after == 0) else 1.0,
        leaked_bits=leaked,
        corrected_errors=max(0, corrected),
        output_length=n,
    )


# ---------------------------------------------------------------------------
# Cascade error correction
# ---------------------------------------------------------------------------

def cascade_error_correction(
    alice_bits: np.ndarray,
    bob_bits: np.ndarray,
    qber: float,
    *,
    num_passes: int = 10,
    seed: int = 0,
) -> ECResult:
    """Cascade interactive error correction protocol.

    In each pass k:
    1. Divide the key into blocks of size ceil(0.73/QBER) * 2^(k-1)
    2. Compare parities of each block
    3. Binary search within blocks with parity mismatch to find errors

    The protocol is interactive (requires multiple communication rounds)
    but simple and reliable.

    Args:
        alice_bits: Alice's sifted key (n,) binary array
        bob_bits: Bob's sifted key (n,) binary array
        qber: Estimated quantum bit error rate
        num_passes: Number of Cascade passes (default 4)
        seed: Random seed for block permutations

    Returns:
        ECResult with reconciliation statistics

    Ref: Brassard & Salvail, "Secret-key reconciliation by public
         discussion", CRYPTO 1993, LNCS 765, pp. 410-423
    """
    n = len(alice_bits)
    if n <= 0 or qber <= 0:
        return ECResult(
            method="cascade", success=True,
            reconciliation_efficiency=1.0,
            frame_error_rate=0.0, leaked_bits=0,
            corrected_errors=0, output_length=n,
        )

    alice = np.asarray(alice_bits, dtype=np.int8).copy() % 2
    bob = np.asarray(bob_bits, dtype=np.int8).copy() % 2
    rng = np.random.default_rng(seed)

    errors_before = int(np.sum(alice != bob))
    total_leaked_bits = 0
    total_corrected = 0

    # Initial block size from Brassard & Salvail
    block_size_base = max(2, int(math.ceil(0.73 / max(qber, 1e-6))))

    for pass_k in range(num_passes):
        block_size = block_size_base * (2 ** pass_k)
        block_size = min(block_size, n)

        # Shuffle for passes > 0
        if pass_k > 0:
            perm = rng.permutation(n)
        else:
            perm = np.arange(n)

        alice_perm = alice[perm]
        bob_perm = bob[perm]

        # Process blocks
        for start in range(0, n, block_size):
            end = min(start + block_size, n)
            block_a = alice_perm[start:end]
            block_b = bob_perm[start:end]

            parity_a = int(np.sum(block_a)) % 2
            parity_b = int(np.sum(block_b)) % 2
            total_leaked_bits += 1  # one parity bit per block

            if parity_a != parity_b:
                # Binary search for the error
                corrected, leaked = _cascade_binary_search(
                    block_a, block_b,
                )
                total_leaked_bits += leaked
                total_corrected += corrected

                # Apply corrections back to bob via inverse permutation
                bob_perm[start:end] = block_b

        # Un-permute
        if pass_k > 0:
            inv_perm = np.argsort(perm)
            bob = bob_perm[inv_perm]
        else:
            bob = bob_perm.copy()

    errors_after = int(np.sum(alice != bob))
    success = errors_after == 0

    h_q = _binary_entropy(qber)
    if h_q > 0 and n > 0:
        f_ec = (total_leaked_bits / n) / h_q
    else:
        f_ec = 1.0

    return ECResult(
        method="cascade",
        success=success,
        reconciliation_efficiency=f_ec,
        frame_error_rate=0.0 if success else float(errors_after / n),
        leaked_bits=total_leaked_bits,
        corrected_errors=total_corrected,
        output_length=n,
    )


def _cascade_binary_search(
    block_a: np.ndarray,
    block_b: np.ndarray,
) -> tuple[int, int]:
    """Binary search within a block to find and correct one error.

    Returns (corrected_count, leaked_parity_bits).
    """
    n = len(block_a)
    if n <= 1:
        if n == 1 and block_a[0] != block_b[0]:
            block_b[0] = block_a[0]
            return 1, 0
        return 0, 0

    leaked = 0
    corrected = 0

    lo, hi = 0, n
    while hi - lo > 1:
        mid = (lo + hi) // 2
        pa = int(np.sum(block_a[lo:mid])) % 2
        pb = int(np.sum(block_b[lo:mid])) % 2
        leaked += 1

        if pa != pb:
            hi = mid
        else:
            lo = mid

    # Correct the error at position lo
    if block_a[lo] != block_b[lo]:
        block_b[lo] = block_a[lo]
        corrected = 1

    return corrected, leaked


def _binary_entropy(x: float) -> float:
    """Binary entropy function H(x)."""
    if x <= 0.0 or x >= 1.0:
        return 0.0
    return -x * math.log2(x) - (1.0 - x) * math.log2(1.0 - x)
