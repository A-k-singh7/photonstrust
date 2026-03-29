"""Classical cryptography integration models for QKD.

Models for integrating QKD-generated keys with classical cryptographic
primitives: AES-256-GCM key refresh, OTP consumption, and hybrid
QKD + post-quantum cryptography (PQC) key derivation.

Key references:
    - NIST SP 800-38D -- GCM mode recommendation
    - ETSI GS QKD 004 V2.1.1 (2020) -- key consumption interface
    - Bindel et al., PQCrypto 2017 -- hybrid QKD+PQC
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# AES-256-GCM key refresh model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AESKeyRefreshResult:
    """Result of AES-256-GCM key refresh rate calculation."""
    key_refresh_rate_hz: float        # keys consumed per second
    key_consumption_bps: float        # bits of key consumed per second
    data_rate_bps: float              # data throughput
    refresh_interval_s: float         # time between key refreshes
    keys_per_day: float               # daily key consumption
    qkd_rate_sufficient: bool         # whether QKD key rate meets demand
    headroom_factor: float            # QKD rate / consumption rate
    diagnostics: dict[str, Any] = field(default_factory=dict)


def aes256_gcm_key_refresh(
    data_rate_mbps: float,
    *,
    max_bytes_per_key: int = 2**36,    # NIST recommends < 2^36 bytes
    key_size_bits: int = 256,
    qkd_key_rate_bps: float = 1000.0,
) -> AESKeyRefreshResult:
    """Compute AES-256-GCM key refresh rate.

    NIST SP 800-38D recommends limiting data encrypted under a single
    key to prevent GCM forgery attacks. The key refresh rate is:

        f_refresh = data_rate / max_bytes_per_key

    Args:
        data_rate_mbps: Encrypted data throughput (Mbps)
        max_bytes_per_key: Maximum bytes per key (NIST limit)
        key_size_bits: Key size in bits (256 for AES-256)
        qkd_key_rate_bps: Available QKD key rate (bits/s)

    Returns:
        AESKeyRefreshResult with consumption analysis
    """
    data_rate_bytes = max(0.0, float(data_rate_mbps)) * 1e6 / 8.0
    max_bytes = max(1, int(max_bytes_per_key))
    key_bits = max(1, int(key_size_bits))
    qkd_rate = max(0.0, float(qkd_key_rate_bps))

    if data_rate_bytes > 0:
        refresh_rate = data_rate_bytes / max_bytes
        refresh_interval = max_bytes / data_rate_bytes
    else:
        refresh_rate = 0.0
        refresh_interval = float("inf")

    consumption_bps = refresh_rate * key_bits
    keys_per_day = refresh_rate * 86400.0

    headroom = qkd_rate / consumption_bps if consumption_bps > 0 else float("inf")
    sufficient = headroom >= 1.0

    return AESKeyRefreshResult(
        key_refresh_rate_hz=refresh_rate,
        key_consumption_bps=consumption_bps,
        data_rate_bps=float(data_rate_mbps) * 1e6,
        refresh_interval_s=refresh_interval,
        keys_per_day=keys_per_day,
        qkd_rate_sufficient=sufficient,
        headroom_factor=headroom,
        diagnostics={
            "max_bytes_per_key": max_bytes,
            "key_size_bits": key_bits,
            "qkd_key_rate_bps": qkd_rate,
        },
    )


# ---------------------------------------------------------------------------
# OTP consumption model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OTPConsumptionResult:
    """Result of one-time pad consumption calculation."""
    key_consumption_bps: float        # key bits consumed per second
    message_rate_hz: float            # messages per second
    key_per_message_bits: int         # key bits per message
    sustainable_duration_s: float     # how long key buffer lasts
    qkd_rate_sufficient: bool         # whether QKD can sustain OTP


def otp_consumption_rate(
    message_size_bits: int,
    message_rate_hz: float,
    *,
    qkd_key_rate_bps: float = 1000.0,
    key_buffer_bits: int = 0,
) -> OTPConsumptionResult:
    """Compute OTP key consumption rate.

    OTP requires exactly one key bit per message bit:

        consumption = message_size * message_rate

    Args:
        message_size_bits: Size of each message (bits)
        message_rate_hz: Messages per second
        qkd_key_rate_bps: Available QKD key rate
        key_buffer_bits: Current key material in buffer

    Returns:
        OTPConsumptionResult
    """
    msg_bits = max(1, int(message_size_bits))
    msg_rate = max(0.0, float(message_rate_hz))
    qkd_rate = max(0.0, float(qkd_key_rate_bps))

    consumption = msg_bits * msg_rate
    sufficient = qkd_rate >= consumption

    # How long the buffer lasts if QKD rate is insufficient
    net_drain = consumption - qkd_rate
    if net_drain > 0 and key_buffer_bits > 0:
        duration = key_buffer_bits / net_drain
    elif consumption <= 0:
        duration = float("inf")
    elif sufficient:
        duration = float("inf")
    else:
        duration = 0.0

    return OTPConsumptionResult(
        key_consumption_bps=consumption,
        message_rate_hz=msg_rate,
        key_per_message_bits=msg_bits,
        sustainable_duration_s=duration,
        qkd_rate_sufficient=sufficient,
    )


# ---------------------------------------------------------------------------
# Hybrid QKD + PQC key derivation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class HybridKeyDerivationResult:
    """Result of hybrid QKD+PQC key derivation."""
    output_key_bits: int
    qkd_contribution_bits: int
    pqc_contribution_bits: int
    derivation_method: str
    security_level: str
    diagnostics: dict[str, Any] = field(default_factory=dict)


def hybrid_qkd_pqc_derivation(
    qkd_key_bits: int = 256,
    pqc_shared_secret_bits: int = 256,
    *,
    output_bits: int = 256,
    pqc_algorithm: str = "kyber-768",
) -> HybridKeyDerivationResult:
    """Model hybrid QKD + PQC key derivation.

    Combines QKD key material with a PQC shared secret via
    key derivation function (KDF):

        K_hybrid = KDF(K_QKD || K_PQC, output_bits)

    Security: information-theoretic if either QKD OR PQC is secure.
    This provides defense-in-depth against both quantum and
    classical attacks.

    Args:
        qkd_key_bits: QKD key material length (bits)
        pqc_shared_secret_bits: PQC shared secret length (bits)
        output_bits: Desired output key length
        pqc_algorithm: PQC algorithm name

    Returns:
        HybridKeyDerivationResult

    Ref: Bindel et al., PQCrypto 2017
    """
    qkd_bits = max(0, int(qkd_key_bits))
    pqc_bits = max(0, int(pqc_shared_secret_bits))
    out_bits = max(1, int(output_bits))

    # Security level from the stronger component
    total_input = qkd_bits + pqc_bits
    if qkd_bits >= 256 and pqc_bits >= 256:
        sec_level = "256-bit hybrid (ITS + PQC)"
    elif qkd_bits >= 128 or pqc_bits >= 128:
        sec_level = "128-bit hybrid"
    else:
        sec_level = "weak"

    # PQC algorithm security levels
    pqc_security: dict[str, int] = {
        "kyber-512": 128,
        "kyber-768": 192,
        "kyber-1024": 256,
        "mceliece-348864": 128,
        "mceliece-6960119": 256,
    }
    pqc_sec = pqc_security.get(pqc_algorithm.lower(), 128)

    return HybridKeyDerivationResult(
        output_key_bits=out_bits,
        qkd_contribution_bits=qkd_bits,
        pqc_contribution_bits=pqc_bits,
        derivation_method=f"HKDF-SHA256(QKD({qkd_bits}b) || {pqc_algorithm}({pqc_bits}b))",
        security_level=sec_level,
        diagnostics={
            "total_input_entropy_bits": total_input,
            "pqc_algorithm": pqc_algorithm,
            "pqc_security_level": pqc_sec,
            "output_bits": out_bits,
        },
    )
