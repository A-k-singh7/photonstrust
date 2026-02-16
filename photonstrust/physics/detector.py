"""Stochastic detector click model with optional stateful dynamics."""

from __future__ import annotations

import heapq
import math
import warnings
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Union

import numpy as np


@dataclass
class DetectionStats:
    p_click: float
    p_false: float
    click_time_hist: List[float]
    click_time_edges_ps: List[float]
    variance_p_click: float
    diagnostics: Dict[str, Union[float, str]] = field(default_factory=dict)


def simulate_detector(detector_cfg: dict, arrival_times_ps: List[float]) -> DetectionStats:
    rng = np.random.default_rng(detector_cfg.get("seed", 17))
    pde = _clamp_probability(detector_cfg.get("pde", 0.0), "pde")
    jitter_ps = _non_negative(detector_cfg.get("jitter_ps_fwhm", 0.0), "jitter_ps_fwhm") / 2.355
    dark_counts = _non_negative(detector_cfg.get("dark_counts_cps", 0.0), "dark_counts_cps")
    dead_time_ns = _non_negative(detector_cfg.get("dead_time_ns", 0.0), "dead_time_ns")
    afterpulse_prob = _clamp_probability(detector_cfg.get("afterpulsing_prob", 0.0), "afterpulsing_prob")
    afterpulse_delay_ns = _non_negative(
        detector_cfg.get("afterpulse_delay_ns", 50.0), "afterpulse_delay_ns"
    )
    force_legacy_path = bool(detector_cfg.get("force_legacy_path", False))
    time_bin_ps = max(1.0, _non_negative(detector_cfg.get("time_bin_ps", 10.0), "time_bin_ps"))
    gate_width_ns = _non_negative(detector_cfg.get("gate_width_ns", 0.0), "gate_width_ns")
    gate_period_ns = _non_negative(detector_cfg.get("gate_period_ns", 0.0), "gate_period_ns")
    saturation_count_rate_cps = _non_negative(
        detector_cfg.get("saturation_count_rate_cps", 0.0), "saturation_count_rate_cps"
    )

    arrivals = [float(v) for v in arrival_times_ps]
    gated_arrivals, duty_cycle = _apply_gate(arrivals, gate_width_ns, gate_period_ns)
    window_min, window_max, window_s = _observation_window(arrivals, time_bin_ps)
    signal_rate_cps = len(gated_arrivals) / max(window_s, 1e-12)

    pde_eff = _effective_pde(pde, signal_rate_cps, saturation_count_rate_cps)
    signal_events: List[float] = []
    for t in gated_arrivals:
        if rng.random() <= pde_eff:
            signal_events.append(t + rng.normal(0.0, jitter_ps))

    dark_mean = dark_counts * duty_cycle * max(window_s, 1e-12)
    dark_generated = int(rng.poisson(dark_mean))
    dark_events: List[float] = [rng.uniform(window_min, window_max) for _ in range(dark_generated)]

    dead_time_ps = dead_time_ns * 1e3
    afterpulse_delay_ps = afterpulse_delay_ns * 1e3
    use_fast_path = afterpulse_prob <= 0.0 and not force_legacy_path
    if use_fast_path:
        clicks, false_clicks, processed = _process_events_fast_no_afterpulse(
            signal_events,
            dark_events,
            dead_time_ps,
        )
        path = "fast_no_afterpulse"
    else:
        clicks, false_clicks, processed = _process_events_heap_legacy(
            signal_events,
            dark_events,
            dead_time_ps,
            afterpulse_prob,
            afterpulse_delay_ps,
            jitter_ps,
            rng,
        )
        path = "heap_legacy"

    total_events = len(gated_arrivals) if gated_arrivals else 1
    p_click = min(1.0, len(clicks) / max(total_events, 1))
    p_false = min(1.0, false_clicks / max(total_events, 1))

    if clicks:
        min_time = min(clicks)
        max_time = max(clicks)
    else:
        min_time = window_min
        max_time = window_max

    if max_time <= min_time:
        max_time = min_time + time_bin_ps

    bins = max(1, int((max_time - min_time) / time_bin_ps) + 1)
    hist, edges = np.histogram(clicks, bins=bins, range=(min_time, max_time))
    hist = hist / max(1, hist.sum())
    variance = float(np.var(hist)) if hist.size else 0.0

    return DetectionStats(
        p_click=p_click,
        p_false=p_false,
        click_time_hist=hist.tolist(),
        click_time_edges_ps=edges.tolist(),
        variance_p_click=variance,
        diagnostics={
            "pde_effective": pde_eff,
            "signal_rate_cps": signal_rate_cps,
            "duty_cycle": duty_cycle,
            "dark_generated": float(dark_generated),
            "events_processed": float(processed),
            "path": path,
        },
    )


def _process_events_fast_no_afterpulse(
    signal_events: List[float],
    dark_events: List[float],
    dead_time_ps: float,
) -> tuple[List[float], int, int]:
    events = [(t, "signal") for t in signal_events]
    events.extend((t, "dark") for t in dark_events)
    events.sort(key=lambda item: (item[0], item[1]))

    clicks: List[float] = []
    false_clicks = 0
    last_click = -1e18
    for t, origin in events:
        if dead_time_ps > 0 and (t - last_click) < dead_time_ps:
            continue
        clicks.append(t)
        last_click = t
        if origin != "signal":
            false_clicks += 1
    return clicks, false_clicks, len(events)


def _process_events_heap_legacy(
    signal_events: List[float],
    dark_events: List[float],
    dead_time_ps: float,
    afterpulse_prob: float,
    afterpulse_delay_ps: float,
    jitter_ps: float,
    rng: np.random.Generator,
) -> tuple[List[float], int, int]:
    events: List[Tuple[float, str]] = []
    for t in signal_events:
        heapq.heappush(events, (t, "signal"))
    for t in dark_events:
        heapq.heappush(events, (t, "dark"))

    clicks: List[float] = []
    false_clicks = 0
    last_click = -1e18
    processed = 0

    while events:
        t, origin = heapq.heappop(events)
        processed += 1
        if dead_time_ps > 0 and (t - last_click) < dead_time_ps:
            continue
        clicks.append(t)
        last_click = t
        if origin != "signal":
            false_clicks += 1
        if afterpulse_prob > 0 and rng.random() <= afterpulse_prob:
            ap_jitter = max(1.0, jitter_ps * 0.25)
            heapq.heappush(
                events,
                (t + afterpulse_delay_ps + rng.normal(0.0, ap_jitter), "afterpulse"),
            )

    return clicks, false_clicks, processed


def _apply_gate(
    arrivals: List[float],
    gate_width_ns: float,
    gate_period_ns: float,
) -> tuple[List[float], float]:
    if gate_width_ns <= 0 or gate_period_ns <= 0:
        return arrivals, 1.0
    width_ps = gate_width_ns * 1e3
    period_ps = max(gate_period_ns * 1e3, 1.0)
    in_gate = [t for t in arrivals if (t % period_ps) <= width_ps]
    duty = max(0.0, min(1.0, width_ps / period_ps))
    return in_gate, duty


def _observation_window(arrivals: List[float], time_bin_ps: float) -> tuple[float, float, float]:
    if not arrivals:
        min_time = 0.0
        max_time = max(1.0, time_bin_ps)
    else:
        min_time = float(min(arrivals))
        max_time = float(max(arrivals))
        if max_time <= min_time:
            max_time = min_time + max(1.0, time_bin_ps)
    span_ps = max(1.0, max_time - min_time)
    return min_time, max_time, span_ps * 1e-12


def _effective_pde(pde: float, signal_rate_cps: float, saturation_rate_cps: float) -> float:
    if saturation_rate_cps <= 0:
        return pde
    return _clamp_probability(pde / (1.0 + signal_rate_cps / saturation_rate_cps), "pde_effective")


def _non_negative(value: float, field_name: str) -> float:
    out = float(value)
    if not math.isfinite(out):
        warnings.warn(f"{field_name} non-finite; using 0.0", stacklevel=3)
        return 0.0
    if out < 0.0:
        warnings.warn(f"{field_name}={out} below 0.0; clamped", stacklevel=3)
        return 0.0
    return out


def _clamp_probability(value: float, field_name: str) -> float:
    out = float(value)
    if not math.isfinite(out):
        warnings.warn(f"{field_name} non-finite; using 0.0", stacklevel=3)
        return 0.0
    if out < 0.0:
        warnings.warn(f"{field_name}={out} below 0.0; clamped", stacklevel=3)
        return 0.0
    if out > 1.0:
        warnings.warn(f"{field_name}={out} above 1.0; clamped", stacklevel=3)
        return 1.0
    return out


@dataclass(frozen=True)
class DetectorProfile:
    """Structured detector model used by analytical QKD paths.

    Tiering is intentionally lightweight to preserve existing APIs:
    - Tier 0: legacy behavior (no extra corrections).
    - Tier 1: apply jitter-capture and afterpulse noise inflation.
    """

    tier: int
    pde: float
    dark_counts_cps: float
    background_counts_cps: float
    jitter_ps_fwhm: float
    dead_time_ns: float
    afterpulsing_prob: float

    @property
    def jitter_sigma_ps(self) -> float:
        return self.jitter_ps_fwhm / 2.355 if self.jitter_ps_fwhm > 0 else 0.0

    def pde_in_window(self, window_ps: float) -> float:
        """Effective PDE with optional timing-window capture factor."""

        base = _clamp_probability(self.pde, "pde")
        if self.tier <= 0:
            return base
        sigma = self.jitter_sigma_ps
        if sigma <= 0.0:
            return base
        window_ps = max(0.0, float(window_ps))
        if window_ps <= 0.0:
            return 0.0
        capture = math.erf(window_ps / (2.0 * math.sqrt(2.0) * sigma))
        capture = _clamp_probability(capture, "jitter_capture")
        return _clamp_probability(base * capture, "pde_effective_window")

    def effective_noise_cps(self, extra_channel_noise_cps: float = 0.0) -> float:
        """Effective detector+channel noise in cps for analytical models."""

        base = max(0.0, float(self.dark_counts_cps + self.background_counts_cps + extra_channel_noise_cps))
        if self.tier <= 0:
            return base
        # Geometric-branch approximation: observed rate = base / (1 - p_ap).
        return base / max(1e-9, 1.0 - self.afterpulsing_prob)


def build_detector_profile(detector_cfg: dict) -> DetectorProfile:
    tier = int(detector_cfg.get("model_tier", detector_cfg.get("tier", 0)) or 0)
    tier = max(0, min(1, tier))
    return DetectorProfile(
        tier=tier,
        pde=_clamp_probability(detector_cfg.get("pde", 0.0), "pde"),
        dark_counts_cps=_non_negative(detector_cfg.get("dark_counts_cps", 0.0), "dark_counts_cps"),
        background_counts_cps=_non_negative(detector_cfg.get("background_counts_cps", 0.0), "background_counts_cps"),
        jitter_ps_fwhm=_non_negative(detector_cfg.get("jitter_ps_fwhm", 0.0), "jitter_ps_fwhm"),
        dead_time_ns=_non_negative(detector_cfg.get("dead_time_ns", 0.0), "dead_time_ns"),
        afterpulsing_prob=_clamp_probability(detector_cfg.get("afterpulsing_prob", 0.0), "afterpulsing_prob"),
    )
