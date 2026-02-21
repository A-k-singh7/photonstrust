"""WDM multi-channel analysis for PhotonTrust PIC netlists."""
from __future__ import annotations
import math
from typing import Any, Optional

_C_M_S = 299_792_458.0


def itu_channel_grid(center_wl_nm: float = 1550.0, channel_spacing_ghz: float = 100.0, n_channels: int = 8) -> list[dict]:
    f_center = _C_M_S / (center_wl_nm * 1e-9)
    df = channel_spacing_ghz * 1e9
    half = (n_channels - 1) / 2.0
    channels = []
    for i in range(n_channels):
        f = f_center + (i - half) * df
        wl = _C_M_S / f * 1e9
        channels.append({"channel": i + 1, "frequency_thz": round(f * 1e-12, 6), "wavelength_nm": round(wl, 4)})
    return channels


def analyze_wdm_channels(
    netlist: dict[str, Any],
    *,
    channel_spacing_ghz: float = 100.0,
    n_channels: int = 8,
    center_wl_nm: float = 1550.0,
    points_per_channel: int = 20,
) -> dict[str, Any]:
    """Run WDM multi-channel analysis on a PIC netlist.

    Returns per-channel peak transmission, 3-dB passband, in-band ripple,
    N×N isolation matrix, and an OSNR estimate.
    """
    from photonstrust.pic import simulate_pic_netlist_sweep

    grid = itu_channel_grid(center_wl_nm, channel_spacing_ghz, n_channels)

    # Half-span per channel (nm), derived from channel spacing
    f0 = grid[0]["frequency_thz"] * 1e12
    f0_lo = f0 - channel_spacing_ghz * 0.5e9
    half_span_nm = abs(_C_M_S / f0_lo * 1e9 - _C_M_S / f0 * 1e9)

    all_wls: list[float] = []
    ch_ranges: list[tuple[float, float]] = []
    for ch in grid:
        wc = ch["wavelength_nm"]
        lo, hi = wc - half_span_nm, wc + half_span_nm
        ch_wls = [lo + (hi - lo) * j / max(1, points_per_channel - 1) for j in range(points_per_channel)]
        all_wls.extend(ch_wls)
        ch_ranges.append((lo, hi))

    all_wls = sorted(set(round(w, 4) for w in all_wls))

    try:
        sweep = simulate_pic_netlist_sweep(netlist, wavelengths_nm=all_wls)
    except Exception as exc:
        return {"error": str(exc), "channels": [], "grid": grid}

    wl_power: dict[float, float] = {}
    for res in sweep:
        wl = round(float(res.get("wavelength_nm", 0)), 4)
        outs = res.get("outputs", [])
        if outs:
            pdb = outs[0].get("power_dB")
            if pdb is not None:
                wl_power[wl] = float(pdb)

    channel_results, peaks = [], []
    for ch, (lo, hi) in zip(grid, ch_ranges):
        band_wls = [w for w in all_wls if lo <= w <= hi]
        band_pows = [wl_power.get(w, -100.0) for w in band_wls]
        peak = max(band_pows) if band_pows else -100.0
        thr = peak - 3.0
        in_band = [w for w, p in zip(band_wls, band_pows) if p >= thr]
        passband = round(max(in_band) - min(in_band), 4) if len(in_band) >= 2 else 0.0
        in_band_p = [p for p in band_pows if p >= thr]
        ripple = round(max(in_band_p) - min(in_band_p), 4) if len(in_band_p) >= 2 else 0.0
        peaks.append(peak)
        channel_results.append({
            "channel": ch["channel"],
            "center_wavelength_nm": ch["wavelength_nm"],
            "frequency_thz": ch["frequency_thz"],
            "peak_transmission_db": round(peak, 2),
            "passband_3db_nm": passband,
            "inband_ripple_db": ripple,
        })

    isolation_matrix: list[list[float]] = []
    for i, ch_i in enumerate(grid):
        row = []
        for j, ch_j in enumerate(grid):
            if i == j:
                row.append(0.0)
            else:
                nearest = min(all_wls, key=lambda w: abs(w - ch_j["wavelength_nm"]))
                p_at_j = wl_power.get(round(nearest, 4), -100.0)
                row.append(round(peaks[i] - p_at_j, 2))
        isolation_matrix.append(row)

    adj_xt = [isolation_matrix[i][j] for i in range(len(grid)) for j in [i - 1, i + 1] if 0 <= j < len(grid)]
    avg_peak = sum(peaks) / max(1, len(peaks))

    return {
        "ok": True,
        "channel_spacing_ghz": channel_spacing_ghz,
        "n_channels": n_channels,
        "center_wl_nm": center_wl_nm,
        "channels": channel_results,
        "grid": grid,
        "isolation_matrix_db": isolation_matrix,
        "worst_adjacent_crosstalk_db": round(min(adj_xt), 2) if adj_xt else None,
        "avg_peak_transmission_db": round(avg_peak, 2),
        "osnr_estimate_db": round(avg_peak - (-40.0), 2),
        "wavelengths_simulated": len(all_wls),
    }
