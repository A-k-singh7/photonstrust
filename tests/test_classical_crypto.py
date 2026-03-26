"""Tests for classical crypto integration models."""

from __future__ import annotations

import pytest

from photonstrust.integrations.classical_crypto import (
    aes256_gcm_key_refresh,
    hybrid_qkd_pqc_derivation,
    otp_consumption_rate,
)


# ---- AES-256-GCM key refresh tests ----------------------------------------

def test_aes_refresh_rate():
    """1 Gbps data -> refresh every ~8.6 seconds at 2^36 byte limit."""
    r = aes256_gcm_key_refresh(1000.0)  # 1 Gbps
    assert r.key_refresh_rate_hz > 0
    assert r.refresh_interval_s > 0
    assert r.key_consumption_bps > 0


def test_aes_zero_data_rate():
    r = aes256_gcm_key_refresh(0.0)
    assert r.key_refresh_rate_hz == 0.0
    assert r.key_consumption_bps == 0.0


def test_aes_sufficient_qkd_rate():
    r = aes256_gcm_key_refresh(1.0, qkd_key_rate_bps=1000.0)
    assert r.qkd_rate_sufficient
    assert r.headroom_factor > 1.0


def test_aes_insufficient_qkd_rate():
    r = aes256_gcm_key_refresh(10000.0, qkd_key_rate_bps=0.001)
    assert not r.qkd_rate_sufficient


def test_aes_keys_per_day():
    r = aes256_gcm_key_refresh(100.0)
    assert r.keys_per_day > 0


# ---- OTP consumption tests ------------------------------------------------

def test_otp_basic():
    r = otp_consumption_rate(256, 100.0, qkd_key_rate_bps=100000.0)
    assert r.key_consumption_bps == 256 * 100.0
    assert r.qkd_rate_sufficient


def test_otp_insufficient_rate():
    r = otp_consumption_rate(1024, 1000.0, qkd_key_rate_bps=100.0)
    assert not r.qkd_rate_sufficient
    assert r.key_consumption_bps > r.key_per_message_bits


def test_otp_with_buffer():
    r = otp_consumption_rate(
        256, 100.0,
        qkd_key_rate_bps=10.0,
        key_buffer_bits=1000000,
    )
    assert r.sustainable_duration_s > 0
    assert not r.qkd_rate_sufficient


def test_otp_zero_messages():
    r = otp_consumption_rate(256, 0.0)
    assert r.key_consumption_bps == 0.0


# ---- Hybrid QKD+PQC tests -------------------------------------------------

def test_hybrid_default():
    r = hybrid_qkd_pqc_derivation()
    assert r.output_key_bits == 256
    assert r.qkd_contribution_bits == 256
    assert r.pqc_contribution_bits == 256
    assert "hybrid" in r.security_level.lower()


def test_hybrid_kyber_768():
    r = hybrid_qkd_pqc_derivation(pqc_algorithm="kyber-768")
    assert "kyber-768" in r.derivation_method
    assert r.diagnostics["pqc_security_level"] == 192


def test_hybrid_weak_inputs():
    r = hybrid_qkd_pqc_derivation(qkd_key_bits=64, pqc_shared_secret_bits=64)
    assert r.security_level == "weak"


def test_hybrid_its_plus_pqc():
    r = hybrid_qkd_pqc_derivation(qkd_key_bits=256, pqc_shared_secret_bits=256)
    assert "ITS" in r.security_level
