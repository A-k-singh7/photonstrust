"""Privacy amplification for QKD post-processing.

Implements FFT-accelerated Toeplitz hashing for extracting a secure key
from a partially-compromised reconciled string.

Key references:
    - Tomamichel et al., Nature Comms 3, 634 (2012) -- leftover hash lemma
    - Hayashi & Tsurumaru, NJP 14, 093014 (2012) -- PA bounds
    - Carter & Wegman, JCSS 18, 143 (1979) -- 2-universal hash families

The secure key length after privacy amplification is:

    l = n * (1 - H(QBER)) - leak_EC - 2*log2(1/eps_PA)

where leak_EC is the information leaked during error correction and
eps_PA is the privacy amplification security parameter.

Notes:
    - FFT Toeplitz hashing achieves O(n log n) complexity vs O(n*m) naive
    - The Toeplitz matrix is specified by n + m - 1 random bits (seed)
    - This is a 2-universal hash family, satisfying the leftover hash lemma
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class PAResult:
    """Result of privacy amplification."""
    method: str                  # "toeplitz_fft" or "toeplitz_naive"
    input_length: int            # length of reconciled key
    output_length: int           # length of secure key
    compression_ratio: float     # output_length / input_length
    security_parameter: float    # epsilon_PA


def compute_pa_output_length(
    n: int,
    qber: float,
    leaked_bits: int,
    *,
    epsilon_pa: float = 1e-10,
    epsilon_ec: float = 1e-10,
) -> int:
    """Compute the secure key length from the leftover hash lemma.

    l = n * [1 - H(QBER)] - leak_EC - 2*log2(1/eps_PA) - log2(2/eps_EC)

    This is the maximum number of secure bits extractable from the
    reconciled key, accounting for:
    - Eve's information from the quantum channel (bounded by H(QBER))
    - Information leaked during error correction
    - Finite-size security parameters

    Args:
        n: Length of the reconciled key (after EC)
        qber: Quantum bit error rate
        leaked_bits: Number of bits leaked during error correction
        epsilon_pa: Privacy amplification security parameter
        epsilon_ec: Error correction security parameter

    Returns:
        Output key length (non-negative integer)

    Ref: Tomamichel et al., Nature Comms 3, 634 (2012), Eq. (1)
    """
    if n <= 0 or qber >= 0.5:
        return 0

    h_q = _binary_entropy(qber)
    secure_fraction = max(0.0, 1.0 - h_q)

    # Leftover hash lemma bound
    pa_penalty = 2.0 * math.log2(1.0 / max(epsilon_pa, 1e-300))
    ec_penalty = math.log2(2.0 / max(epsilon_ec, 1e-300))

    output = n * secure_fraction - leaked_bits - pa_penalty - ec_penalty
    return max(0, int(math.floor(output)))


def fft_toeplitz_hash(
    key_bits: np.ndarray,
    output_length: int,
    *,
    seed: int = 42,
) -> tuple[np.ndarray, PAResult]:
    """FFT-accelerated Toeplitz hashing for privacy amplification.

    Computes y = T * x where T is an m x n Toeplitz matrix and x is
    the input key. Uses circulant embedding + FFT for O(n log n)
    complexity instead of O(n*m).

    A Toeplitz matrix T is defined by its first row r and first column c.
    For privacy amplification, r and c are generated from a random seed,
    forming a 2-universal hash family.

    The circulant embedding trick:
    1. Embed T in a (n+m-1) x (n+m-1) circulant matrix C
    2. C * x' = IFFT(FFT(first_col_C) * FFT(x_padded))
    3. Extract the first m elements

    Args:
        key_bits: Input reconciled key (n,) binary array
        output_length: Desired output length m
        seed: Random seed for Toeplitz matrix construction

    Returns:
        (output_bits, PAResult): hashed output and metadata

    Ref: Hayashi & Tsurumaru, NJP 14, 093014 (2012), Section 3
    """
    x = np.asarray(key_bits, dtype=np.float64) % 2
    n = len(x)
    m = min(output_length, n)
    if m <= 0:
        return np.array([], dtype=np.int8), PAResult(
            method="toeplitz_fft", input_length=n,
            output_length=0, compression_ratio=0.0,
            security_parameter=0.0,
        )

    rng = np.random.default_rng(seed)

    # Toeplitz matrix is defined by n + m - 1 random bits
    # Naive row i: toeplitz_seed[m-1-i : m-1-i+n]
    toeplitz_seed = rng.integers(0, 2, size=n + m - 1).astype(np.float64)

    N = n + m - 1

    # Circulant embedding first column from the Toeplitz structure:
    # c[k] = a[k] for k in [0, m-1], where a[k] = seed[m-1-k]
    # c[m+j] = a[-(n-1-j)] = seed[m+j] for j in [0, n-2]
    c_circ = np.empty(N, dtype=np.float64)
    c_circ[:m] = toeplitz_seed[:m][::-1]     # first column of T
    c_circ[m:] = toeplitz_seed[m:][::-1]     # wrap-around from first row

    # Pad input
    x_padded = np.zeros(N, dtype=np.float64)
    x_padded[:n] = x

    # FFT-based multiplication: y = IFFT(FFT(c) * FFT(x))
    C_fft = np.fft.fft(c_circ)
    X_fft = np.fft.fft(x_padded)
    y_full = np.real(np.fft.ifft(C_fft * X_fft))

    # Extract first m elements and take mod 2
    output = np.round(y_full[:m]).astype(np.int64) % 2
    output = output.astype(np.int8)

    return output, PAResult(
        method="toeplitz_fft",
        input_length=n,
        output_length=m,
        compression_ratio=m / max(n, 1),
        security_parameter=0.0,
    )


def naive_toeplitz_hash(
    key_bits: np.ndarray,
    output_length: int,
    *,
    seed: int = 42,
) -> tuple[np.ndarray, PAResult]:
    """Naive O(n*m) Toeplitz hashing (reference implementation).

    Used for validation against the FFT version.

    Args:
        key_bits: Input reconciled key (n,) binary array
        output_length: Desired output length m
        seed: Random seed for Toeplitz matrix construction

    Returns:
        (output_bits, PAResult): hashed output and metadata
    """
    x = np.asarray(key_bits, dtype=np.int8) % 2
    n = len(x)
    m = min(output_length, n)
    if m <= 0:
        return np.array([], dtype=np.int8), PAResult(
            method="toeplitz_naive", input_length=n,
            output_length=0, compression_ratio=0.0,
            security_parameter=0.0,
        )

    rng = np.random.default_rng(seed)
    toeplitz_seed = rng.integers(0, 2, size=n + m - 1).astype(np.int8)

    # Build full Toeplitz matrix and multiply
    output = np.zeros(m, dtype=np.int8)
    for i in range(m):
        row = toeplitz_seed[m - 1 - i : m - 1 - i + n]
        output[i] = int(np.sum(row * x)) % 2

    return output, PAResult(
        method="toeplitz_naive",
        input_length=n,
        output_length=m,
        compression_ratio=m / max(n, 1),
        security_parameter=0.0,
    )


def _binary_entropy(x: float) -> float:
    if x <= 0.0 or x >= 1.0:
        return 0.0
    return -x * math.log2(x) - (1.0 - x) * math.log2(1.0 - x)
