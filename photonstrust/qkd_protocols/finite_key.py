"""Composable finite-key helper scaffolding for QKD protocols."""

from __future__ import annotations

import math
from dataclasses import dataclass

from photonstrust.utils import clamp


@dataclass(frozen=True)
class FiniteKeyAdjustment:
    """Result of finite-key adjustment for privacy amplification terms."""

    enabled: bool
    sifting_effective: float
    privacy_term_effective: float
    finite_key_penalty: float
    security_epsilon: float
    signals_per_block: float


def apply_composable_finite_key(
    *,
    finite_key_cfg: dict | None,
    sifting: float,
    privacy_term_asymptotic: float,
) -> FiniteKeyAdjustment:
    """Apply a lightweight composable finite-key penalty scaffold.

    This helper intentionally keeps the same semantics already used by legacy
    BBM92 code: a block-size and epsilon-dependent square-root penalty is
    subtracted from the asymptotic privacy term.
    """

    sifting = clamp(float(sifting), 0.0, 1.0)
    privacy_term_asymptotic = max(0.0, float(privacy_term_asymptotic))

    cfg = finite_key_cfg or {}
    enabled = bool(cfg.get("enabled", False))
    if not enabled:
        return FiniteKeyAdjustment(
            enabled=False,
            sifting_effective=sifting,
            privacy_term_effective=privacy_term_asymptotic,
            finite_key_penalty=0.0,
            security_epsilon=0.0,
            signals_per_block=0.0,
        )

    signals_per_block = max(1.0, float(cfg.get("signals_per_block", 1.0e10)))
    security_epsilon = float(cfg.get("security_epsilon", 1.0e-10))
    if not math.isfinite(security_epsilon) or security_epsilon <= 0.0:
        security_epsilon = 1.0e-10
    security_epsilon = clamp(security_epsilon, 1e-24, 0.5)

    pe_fraction = clamp(float(cfg.get("parameter_estimation_fraction", 0.1)), 0.0, 0.9)
    sifting_effective = sifting * (1.0 - pe_fraction)

    n_eff = max(1.0, signals_per_block * max(1e-15, sifting_effective))
    finite_key_penalty = math.sqrt(2.0 * math.log(2.0 / security_epsilon)) / math.sqrt(n_eff)
    privacy_term_effective = max(0.0, privacy_term_asymptotic - finite_key_penalty)

    return FiniteKeyAdjustment(
        enabled=True,
        sifting_effective=float(sifting_effective),
        privacy_term_effective=float(privacy_term_effective),
        finite_key_penalty=float(finite_key_penalty),
        security_epsilon=float(security_epsilon),
        signals_per_block=float(signals_per_block),
    )


def apply_finite_key_dispatch(
    *,
    finite_key_cfg: dict | None,
    sifting: float,
    privacy_term_asymptotic: float,
    protocol_name: str = "",
    single_photon_yield_lb: float = 0.0,
    single_photon_error_ub: float = 0.0,
    qber: float = 0.0,
    f_ec: float = 1.16,
) -> FiniteKeyAdjustment:
    """Dispatch to v1 or v2 composable finite-key analysis.

    If the config contains ``composable_version: "v2"`` the full composable
    framework is used; otherwise the legacy square-root scaffold runs.
    Returns a v1-compatible :class:`FiniteKeyAdjustment` in both cases so
    that protocol callers need minimal changes.
    """
    cfg = finite_key_cfg or {}
    if str(cfg.get("composable_version", "")).strip() == "v2":
        from photonstrust.qkd_protocols.finite_key_composable import (
            apply_composable_finite_key_v2,
        )

        v2 = apply_composable_finite_key_v2(
            finite_key_cfg=cfg,
            sifting=sifting,
            privacy_term_asymptotic=privacy_term_asymptotic,
            protocol_name=protocol_name,
            single_photon_yield_lb=single_photon_yield_lb,
            single_photon_error_ub=single_photon_error_ub,
            qber=qber,
            f_ec=f_ec,
        )
        return FiniteKeyAdjustment(
            enabled=v2.enabled,
            sifting_effective=v2.sifting_effective,
            privacy_term_effective=v2.privacy_term_effective,
            finite_key_penalty=v2.finite_key_penalty,
            security_epsilon=v2.epsilon_budget.epsilon_total,
            signals_per_block=v2.signals_per_block,
        )

    return apply_composable_finite_key(
        finite_key_cfg=cfg,
        sifting=sifting,
        privacy_term_asymptotic=privacy_term_asymptotic,
    )
