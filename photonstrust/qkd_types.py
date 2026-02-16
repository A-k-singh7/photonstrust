"""Shared QKD result types.

This module exists to avoid circular imports when adding multiple QKD protocol
implementations.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class QKDResult:
    distance_km: float
    entanglement_rate_hz: float
    key_rate_bps: float
    qber_total: float
    fidelity: float
    p_pair: float
    p_false: float
    q_multi: float
    q_dark: float
    q_timing: float
    q_misalignment: float
    q_source: float
    q_dark_detector: float
    q_background: float
    q_raman: float
    background_counts_cps: float
    raman_counts_cps: float
    finite_key_enabled: bool
    privacy_term_asymptotic: float
    privacy_term_effective: float
    finite_key_penalty: float
    loss_db: float
    protocol_name: str = ""
    single_photon_yield_lb: float = 0.0
    single_photon_error_ub: float = 0.0
    finite_key_epsilon: float = 0.0
