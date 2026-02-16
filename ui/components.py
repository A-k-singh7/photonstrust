"""Streamlit UI components."""

from __future__ import annotations

import streamlit as st


def render_card_summary(card: dict) -> None:
    st.subheader(f"{card['scenario_id']} | {card['band']}")
    st.metric("Key rate (bps)", f"{card['outputs']['key_rate_bps']:.4g}")
    st.metric("QBER", f"{card['derived']['qber_total']:.4f}")
    st.write(f"Safe use: {card['safe_use_label']['label']}")
    if card.get("reproducibility"):
        st.caption(f"Config hash: {card['reproducibility']['config_hash']}")
