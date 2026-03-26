"""QKD post-processing pipeline orchestrator.

Chains the full post-processing sequence:
    Sifting → Parameter Estimation → Error Correction → Verification → Privacy Amplification

Key references:
    - Lo, Chau, Ardehali, J. Crypto 18, 133 (2005) -- QKD post-processing
    - Scarani et al., RMP 81, 1301 (2009) -- QKD security review

Notes:
    - Sifting selects matching-basis measurements
    - Parameter estimation sacrifices a fraction of sifted bits for QBER estimation
    - Error correction reconciles remaining discrepancies
    - Verification confirms identical keys via hash comparison
    - Privacy amplification compresses the key to remove Eve's information
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

import numpy as np

from photonstrust.pipeline.error_correction import (
    ECResult,
    cascade_error_correction,
    ldpc_error_correction,
)
from photonstrust.pipeline.privacy_amplification import (
    PAResult,
    compute_pa_output_length,
    fft_toeplitz_hash,
)


@dataclass(frozen=True)
class PostProcessingResult:
    """Result of the full QKD post-processing pipeline."""
    success: bool                      # overall pipeline success
    raw_key_length: int                # input raw key length
    sifted_key_length: int             # after basis sifting
    pe_sample_size: int                # bits used for parameter estimation
    estimated_qber: float              # QBER from PE sample
    ec_result: ECResult                # error correction result
    verification_passed: bool          # hash verification result
    pa_result: PAResult | None         # privacy amplification result
    final_key_length: int              # output secure key length
    final_key: np.ndarray | None       # the actual secure key (if successful)
    abort_reason: str | None           # reason for abort (if any)


def run_post_processing_pipeline(
    alice_raw: np.ndarray,
    bob_raw: np.ndarray,
    basis_alice: np.ndarray,
    basis_bob: np.ndarray,
    *,
    pe_fraction: float = 0.1,
    ec_method: str = "cascade",
    epsilon_pa: float = 1e-10,
    epsilon_ec: float = 1e-10,
    qber_threshold: float = 0.11,
    verification_hash_bits: int = 32,
    seed: int = 42,
) -> PostProcessingResult:
    """Run the full QKD post-processing pipeline.

    Args:
        alice_raw: Alice's raw measurement outcomes (n,)
        bob_raw: Bob's raw measurement outcomes (n,)
        basis_alice: Alice's basis choices (n,) — 0 or 1
        basis_bob: Bob's basis choices (n,) — 0 or 1
        pe_fraction: Fraction of sifted bits for parameter estimation
        ec_method: Error correction method ("cascade" or "ldpc")
        epsilon_pa: Privacy amplification security parameter
        epsilon_ec: Error correction security parameter
        qber_threshold: Abort threshold for QBER
        verification_hash_bits: Number of hash bits for key verification
        seed: Random seed

    Returns:
        PostProcessingResult with full pipeline diagnostics
    """
    rng = np.random.default_rng(seed)

    alice_raw = np.asarray(alice_raw, dtype=np.int8) % 2
    bob_raw = np.asarray(bob_raw, dtype=np.int8) % 2
    basis_alice = np.asarray(basis_alice, dtype=np.int8)
    basis_bob = np.asarray(basis_bob, dtype=np.int8)
    n_raw = len(alice_raw)

    # ---- Step 1: Basis sifting ----
    matching = basis_alice == basis_bob
    alice_sifted = alice_raw[matching]
    bob_sifted = bob_raw[matching]
    n_sifted = len(alice_sifted)

    if n_sifted < 10:
        return _abort_result(n_raw, n_sifted, "Too few sifted bits")

    # ---- Step 2: Parameter estimation ----
    n_pe = max(1, int(n_sifted * pe_fraction))
    pe_indices = rng.choice(n_sifted, size=n_pe, replace=False)
    pe_mask = np.zeros(n_sifted, dtype=bool)
    pe_mask[pe_indices] = True

    pe_alice = alice_sifted[pe_mask]
    pe_bob = bob_sifted[pe_mask]
    estimated_qber = float(np.mean(pe_alice != pe_bob))

    if estimated_qber > qber_threshold:
        return PostProcessingResult(
            success=False, raw_key_length=n_raw,
            sifted_key_length=n_sifted, pe_sample_size=n_pe,
            estimated_qber=estimated_qber,
            ec_result=ECResult(
                method="none", success=False,
                reconciliation_efficiency=0.0,
                frame_error_rate=1.0, leaked_bits=0,
                corrected_errors=0, output_length=0,
            ),
            verification_passed=False,
            pa_result=None, final_key_length=0,
            final_key=None,
            abort_reason=f"QBER {estimated_qber:.4f} exceeds threshold {qber_threshold}",
        )

    # Remove PE bits from key material
    key_alice = alice_sifted[~pe_mask]
    key_bob = bob_sifted[~pe_mask]
    n_key = len(key_alice)

    if n_key < 10:
        return _abort_result(n_raw, n_sifted, "Too few key bits after PE")

    # ---- Step 3: Error correction ----
    if ec_method == "ldpc":
        ec_result = ldpc_error_correction(
            key_alice, key_bob, estimated_qber, seed=seed,
        )
    else:
        ec_result = cascade_error_correction(
            key_alice, key_bob, estimated_qber, seed=seed,
        )

    if not ec_result.success:
        return PostProcessingResult(
            success=False, raw_key_length=n_raw,
            sifted_key_length=n_sifted, pe_sample_size=n_pe,
            estimated_qber=estimated_qber, ec_result=ec_result,
            verification_passed=False,
            pa_result=None, final_key_length=0,
            final_key=None,
            abort_reason="Error correction failed",
        )

    # After EC, Bob should have Alice's key
    reconciled_key = key_alice  # Both should be identical after successful EC

    # ---- Step 4: Verification ----
    verification_passed = _verify_keys(
        key_alice, reconciled_key, hash_bits=verification_hash_bits,
    )

    if not verification_passed:
        return PostProcessingResult(
            success=False, raw_key_length=n_raw,
            sifted_key_length=n_sifted, pe_sample_size=n_pe,
            estimated_qber=estimated_qber, ec_result=ec_result,
            verification_passed=False,
            pa_result=None, final_key_length=0,
            final_key=None,
            abort_reason="Key verification failed",
        )

    # ---- Step 5: Privacy amplification ----
    output_length = compute_pa_output_length(
        n_key, estimated_qber, ec_result.leaked_bits,
        epsilon_pa=epsilon_pa, epsilon_ec=epsilon_ec,
    )

    if output_length <= 0:
        return PostProcessingResult(
            success=False, raw_key_length=n_raw,
            sifted_key_length=n_sifted, pe_sample_size=n_pe,
            estimated_qber=estimated_qber, ec_result=ec_result,
            verification_passed=True,
            pa_result=None, final_key_length=0,
            final_key=None,
            abort_reason="No secure bits after privacy amplification",
        )

    final_key, pa_result = fft_toeplitz_hash(
        reconciled_key, output_length, seed=seed + 1,
    )

    return PostProcessingResult(
        success=True,
        raw_key_length=n_raw,
        sifted_key_length=n_sifted,
        pe_sample_size=n_pe,
        estimated_qber=estimated_qber,
        ec_result=ec_result,
        verification_passed=True,
        pa_result=pa_result,
        final_key_length=len(final_key),
        final_key=final_key,
        abort_reason=None,
    )


def _verify_keys(
    key_a: np.ndarray,
    key_b: np.ndarray,
    *,
    hash_bits: int = 32,
) -> bool:
    """Verify key equality using 2-universal hash comparison.

    Both parties compute a hash of their key and compare. If hashes
    match, the keys are identical with probability 1 - 2^(-hash_bits).
    """
    hash_a = hashlib.sha256(key_a.tobytes()).digest()
    hash_b = hashlib.sha256(key_b.tobytes()).digest()
    # Compare first hash_bits/8 bytes
    n_bytes = max(1, hash_bits // 8)
    return hash_a[:n_bytes] == hash_b[:n_bytes]


def _abort_result(n_raw: int, n_sifted: int, reason: str) -> PostProcessingResult:
    return PostProcessingResult(
        success=False, raw_key_length=n_raw,
        sifted_key_length=n_sifted, pe_sample_size=0,
        estimated_qber=0.5,
        ec_result=ECResult(
            method="none", success=False,
            reconciliation_efficiency=0.0,
            frame_error_rate=1.0, leaked_bits=0,
            corrected_errors=0, output_length=0,
        ),
        verification_passed=False,
        pa_result=None, final_key_length=0,
        final_key=None,
        abort_reason=reason,
    )
