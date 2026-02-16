"""PhotonTrust Streamlit dashboard."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from ui.components import render_card_summary
from ui.data import list_dataset_entries, list_runs, load_card, load_dataset_entry


def main() -> None:
    st.title("PhotonTrust Run Registry")
    results_root = Path(st.sidebar.text_input("Results directory", "results"))
    run_paths = list_runs(results_root)
    dataset_paths = list_dataset_entries(results_root)

    st.sidebar.write(f"Found {len(run_paths)} runs")
    st.sidebar.write(f"Found {len(dataset_paths)} dataset entries")
    if not run_paths:
        st.info("No reliability cards found.")
        return

    cards_all = [load_card(Path(path)) for path in run_paths]
    bands = sorted({card["band"] for card in cards_all})
    safe_labels = sorted({card["safe_use_label"]["label"] for card in cards_all})

    band_filter = st.sidebar.multiselect("Bands", bands, default=bands)
    safe_filter = st.sidebar.multiselect("Safe use", safe_labels, default=safe_labels)
    filtered = [
        card for card in cards_all if card["band"] in band_filter and card["safe_use_label"]["label"] in safe_filter
    ]

    selected = st.sidebar.multiselect("Select runs", filtered, default=filtered[:1], format_func=lambda c: f"{c['scenario_id']} | {c['band']}")
    cards = list(selected)

    if len(cards) > 1:
        table = [
            {
                "scenario": card["scenario_id"],
                "band": card["band"],
                "key_rate_bps": card["outputs"]["key_rate_bps"],
                "qber": card["derived"]["qber_total"],
                "safe_use": card["safe_use_label"]["label"],
            }
            for card in cards
        ]
        st.table(table)

    for card in cards:
        render_card_summary(card)
        plot_path = card["artifacts"]["plots"].get("key_rate_vs_distance_path")
        if plot_path:
            st.image(plot_path, caption="Key rate vs distance")

    if dataset_paths:
        st.header("Dataset entries")
        entries = [load_dataset_entry(Path(path)) for path in dataset_paths]
        table = [
            {
                "scenario_id": entry.get("scenario_id"),
                "generated_at": entry.get("metadata", {}).get("generated_at"),
                "seed": entry.get("metadata", {}).get("seed"),
                "path": str(path),
            }
            for entry, path in zip(entries, dataset_paths)
        ]
        st.table(table)


if __name__ == "__main__":
    main()
