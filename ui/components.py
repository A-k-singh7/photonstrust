"""Streamlit UI components."""

from __future__ import annotations

from typing import Any

import streamlit as st


def render_card_summary(card: dict) -> None:
    scenario = str(card.get("scenario_id", "unknown"))
    band = str(card.get("band", "unknown"))
    outputs = card.get("outputs") if isinstance(card.get("outputs"), dict) else {}
    derived = card.get("derived") if isinstance(card.get("derived"), dict) else {}
    safe = card.get("safe_use_label") if isinstance(card.get("safe_use_label"), dict) else {}
    repro = card.get("reproducibility") if isinstance(card.get("reproducibility"), dict) else {}

    st.subheader(f"{scenario} | {band}")
    st.metric("Key rate (bps)", f"{_to_float(outputs.get('key_rate_bps'), 0.0):.4g}")
    st.metric("QBER", f"{_to_float(derived.get('qber_total'), 0.5):.4f}")
    st.write(f"Safe use: {str(safe.get('label', 'unknown'))}")
    if repro:
        cfg_hash = str(repro.get("config_hash", "")).strip()
        if cfg_hash:
            st.caption(f"Config hash: {cfg_hash}")


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def render_decision_summary(card: dict) -> None:
    outputs = card.get("outputs") if isinstance(card.get("outputs"), dict) else {}
    derived = card.get("derived") if isinstance(card.get("derived"), dict) else {}
    safe = card.get("safe_use_label") if isinstance(card.get("safe_use_label"), dict) else {}

    key_rate = _to_float(outputs.get("key_rate_bps"), 0.0)
    qber = _to_float(derived.get("qber_total"), 0.5)
    safe_label = str(safe.get("label", "")).strip().lower()

    checks = [
        ("Positive key rate", key_rate > 0.0),
        ("QBER below 11%", qber < 0.11),
        ("Safe-use label above qualitative", safe_label not in {"", "qualitative"}),
    ]
    passed = sum(1 for _, ok in checks if ok)

    st.markdown("**Decision Summary**")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Checks passed", f"{passed}/{len(checks)}")
    with c2:
        st.metric("Key rate > 0", "yes" if key_rate > 0.0 else "no")
    with c3:
        st.metric("QBER < 11%", "yes" if qber < 0.11 else "no")

    if passed == len(checks):
        st.success("Run meets default product-quality gates.")
    elif passed >= 2:
        st.warning("Run is partially viable. Check failing gate(s) before signoff.")
    else:
        st.error("Run fails core viability gates for practical use.")


def render_card_delta(baseline: dict, candidate: dict) -> None:
    b_out = baseline.get("outputs") if isinstance(baseline.get("outputs"), dict) else {}
    b_der = baseline.get("derived") if isinstance(baseline.get("derived"), dict) else {}
    b_safe = baseline.get("safe_use_label") if isinstance(baseline.get("safe_use_label"), dict) else {}

    c_out = candidate.get("outputs") if isinstance(candidate.get("outputs"), dict) else {}
    c_der = candidate.get("derived") if isinstance(candidate.get("derived"), dict) else {}
    c_safe = candidate.get("safe_use_label") if isinstance(candidate.get("safe_use_label"), dict) else {}

    key_base = _to_float(b_out.get("key_rate_bps"), 0.0)
    key_cand = _to_float(c_out.get("key_rate_bps"), 0.0)
    qber_base = _to_float(b_der.get("qber_total"), 0.5)
    qber_cand = _to_float(c_der.get("qber_total"), 0.5)

    key_delta = key_cand - key_base
    key_delta_pct = 0.0 if key_base == 0.0 else (key_delta / key_base) * 100.0
    qber_delta = qber_cand - qber_base

    st.markdown("**Run Delta (Candidate vs Baseline)**")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(
            "Key rate delta (bps)",
            f"{key_delta:.4g}",
            delta=f"{key_delta_pct:.2f}%" if key_base != 0.0 else "n/a",
        )
    with c2:
        st.metric("QBER delta", f"{qber_delta:+.6f}")
    with c3:
        safe_base = str(b_safe.get("label", "unknown"))
        safe_cand = str(c_safe.get("label", "unknown"))
        safe_delta = "changed" if safe_cand != safe_base else "unchanged"
        st.metric(
            "Safe-use label",
            safe_cand,
            delta=safe_delta,
        )
