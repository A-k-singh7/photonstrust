"""Orbit pass envelope simulator for satellite QKD link budgets.

Generates the elevation vs. time profile for a LEO satellite pass and
computes the time-varying link budget (slant range, channel efficiency,
background counts, key rate) at each time step.

References:
    Liao et al. (2017) Nature 549, 43-47
    Bedington et al. (2017) npj Quantum Information 3, 30
"""

from __future__ import annotations

import math

from photonstrust.satellite.types import OrbitPassEnvelope


_EARTH_RADIUS_KM = 6371.0


def elevation_profile(
    *,
    pass_duration_s: float,
    max_elevation_deg: float,
    time_step_s: float = 10.0,
    min_elevation_deg: float = 10.0,
) -> list[tuple[float, float]]:
    """Generate a symmetric elevation profile for a LEO pass.

    Returns list of (time_s, elevation_deg) tuples.  The profile is a
    sinusoidal approximation peaking at max_elevation at pass midpoint.
    """
    dur = max(1.0, float(pass_duration_s))
    dt = max(0.1, float(time_step_s))
    el_max = max(10.0, min(90.0, float(max_elevation_deg)))
    el_min = max(0.0, min(el_max, float(min_elevation_deg)))

    steps: list[tuple[float, float]] = []
    t = 0.0
    while t <= dur + 1e-9:
        # Sinusoidal elevation: peaks at midpoint
        phase = math.pi * t / dur
        el = el_min + (el_max - el_min) * math.sin(phase)
        steps.append((t, el))
        t += dt

    return steps


def slant_range_km(
    *,
    orbit_altitude_km: float,
    elevation_deg: float,
) -> float:
    """Compute slant range from ground station to satellite.

    Uses the geometric relation:
        R = -Re*sin(el) + sqrt((Re*sin(el))^2 + 2*Re*h + h^2)

    where Re is Earth radius, h is orbit altitude, el is elevation angle.
    """
    re = _EARTH_RADIUS_KM
    h = max(1.0, float(orbit_altitude_km))
    el_rad = math.radians(max(0.01, float(elevation_deg)))
    sin_el = math.sin(el_rad)

    discriminant = (re * sin_el) ** 2 + 2.0 * re * h + h ** 2
    return -re * sin_el + math.sqrt(max(0.0, discriminant))


def compute_orbit_pass_envelope(
    *,
    orbit_altitude_km: float = 500.0,
    max_elevation_deg: float = 70.0,
    pass_duration_s: float = 300.0,
    time_step_s: float = 10.0,
    min_elevation_deg: float = 10.0,
    channel_efficiency_fn=None,
    background_counts_fn=None,
    key_rate_fn=None,
) -> OrbitPassEnvelope:
    """Simulate a full orbit pass and build the link budget envelope.

    Parameters
    ----------
    channel_efficiency_fn : callable, optional
        ``f(elevation_deg, slant_range_km) -> float`` returning eta_channel.
        Defaults to a simple geometric+atmospheric proxy.
    background_counts_fn : callable, optional
        ``f(elevation_deg) -> float`` returning background_counts_cps.
        Defaults to a fixed 500 cps.
    key_rate_fn : callable, optional
        ``f(eta_channel, background_counts_cps) -> float`` returning key_rate_bps.
        Defaults to a simplified analytic proxy.
    """
    profile = elevation_profile(
        pass_duration_s=pass_duration_s,
        max_elevation_deg=max_elevation_deg,
        time_step_s=time_step_s,
        min_elevation_deg=min_elevation_deg,
    )

    time_steps: list[float] = []
    elevations: list[float] = []
    slant_ranges: list[float] = []
    eta_channels: list[float] = []
    bg_counts: list[float] = []
    key_rates: list[float] = []
    cumulative: list[float] = []

    dt = max(0.1, float(time_step_s))
    running_bits = 0.0
    outage_count = 0

    for t, el in profile:
        sr = slant_range_km(orbit_altitude_km=orbit_altitude_km, elevation_deg=el)

        if channel_efficiency_fn is not None:
            eta = float(channel_efficiency_fn(el, sr))
        else:
            eta = _default_channel_efficiency(el, sr, orbit_altitude_km)

        if background_counts_fn is not None:
            bg = float(background_counts_fn(el))
        else:
            bg = 500.0

        if key_rate_fn is not None:
            kr = float(key_rate_fn(eta, bg))
        else:
            kr = _default_key_rate(eta, bg)

        if eta < 1e-10:
            outage_count += 1

        running_bits += kr * dt
        time_steps.append(t)
        elevations.append(el)
        slant_ranges.append(sr)
        eta_channels.append(eta)
        bg_counts.append(bg)
        key_rates.append(kr)
        cumulative.append(running_bits)

    n_steps = len(time_steps)
    outage_frac = outage_count / max(1, n_steps)

    return OrbitPassEnvelope(
        time_steps_s=time_steps,
        elevation_deg=elevations,
        slant_range_km=slant_ranges,
        eta_channel=eta_channels,
        background_counts_cps=bg_counts,
        key_rate_bps=key_rates,
        cumulative_key_bits=cumulative,
        total_key_bits=running_bits,
        outage_fraction=outage_frac,
        pass_duration_s=float(pass_duration_s),
        max_elevation_deg=float(max_elevation_deg),
        orbit_altitude_km=float(orbit_altitude_km),
    )


def _default_channel_efficiency(el_deg: float, sr_km: float, alt_km: float) -> float:
    """Simple analytic proxy for channel efficiency."""
    # Geometric loss: (D_rx / (2 * theta_div * R))^2
    theta_div_rad = 1.22 * 810e-9 / 0.15  # 810nm, 15cm aperture
    beam_radius_m = theta_div_rad * sr_km * 1000.0
    rx_area = math.pi * (0.40) ** 2  # 80cm aperture
    beam_area = max(1e-9, math.pi * beam_radius_m ** 2)
    eta_geom = min(1.0, rx_area / beam_area)

    # Atmospheric: extinction through effective thickness / sin(el)
    el_rad = math.radians(max(5.0, el_deg))
    airmass = 1.0 / max(0.01, math.sin(el_rad))
    atm_path_km = 20.0 * airmass
    eta_atm = 10.0 ** (-0.05 * atm_path_km / 10.0)

    # Pointing jitter: exp(-(jitter/divergence)^2)
    jitter_urad = 2.0
    theta_div_urad = theta_div_rad * 1e6
    eta_point = math.exp(-((jitter_urad / max(1e-6, theta_div_urad)) ** 2))

    return max(0.0, min(1.0, eta_geom * eta_atm * eta_point))


def _default_key_rate(eta: float, bg_cps: float) -> float:
    """Simplified key rate proxy (analytic, not a full protocol)."""
    if eta < 1e-12:
        return 0.0
    rep_rate = 1e8  # 100 MHz
    mu = 0.5
    p_det = mu * eta
    dark_rate = 100.0
    total_noise = bg_cps + dark_rate
    noise_per_pulse = total_noise / rep_rate
    qber = 0.5 * noise_per_pulse / max(1e-15, p_det + noise_per_pulse)
    if qber >= 0.11:
        return 0.0
    h_qber = _binary_entropy(qber)
    sifted_rate = rep_rate * p_det * 0.5
    key_rate = max(0.0, sifted_rate * (1.0 - 2.0 * h_qber))
    return key_rate


def _binary_entropy(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -p * math.log2(p) - (1.0 - p) * math.log2(1.0 - p)
