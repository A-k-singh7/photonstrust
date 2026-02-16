"""QuTiP-based emitter-cavity modeling."""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class SourceProfile:
    """Structured source model with explicit fidelity tier semantics."""

    tier: int
    source_type: str
    emission_prob: float
    p_multi: float
    g2_0: float
    diagnostics: Dict[str, Any]


def build_source_profile(source: dict) -> SourceProfile:
    tier = int(source.get("model_tier", source.get("tier", 0)) or 0)
    tier = max(0, min(1, tier))

    source_type = str(source.get("type", "emitter_cavity"))
    if source_type == "spdc":
        mu = max(0.0, float(source.get("mu", 0.0) or 0.0))
        # Poisson pair model: P(n>=1)=1-exp(-mu), P(n>=2|n>=1)
        p_emit = 1.0 - math.exp(-mu)
        p_multi = 0.0 if p_emit <= 0.0 else max(0.0, 1.0 - (mu * math.exp(-mu)) / max(1e-12, p_emit))
        g2_0 = min(1.0, mu / (1.0 + mu))
        return SourceProfile(
            tier=tier,
            source_type=source_type,
            emission_prob=_clamp_zero_one(p_emit, "spdc_emission_prob"),
            p_multi=_clamp_zero_one(p_multi, "spdc_p_multi"),
            g2_0=_clamp_zero_one(g2_0, "spdc_g2_0"),
            diagnostics={"mu": mu, "model": "spdc_poisson"},
        )

    stats = get_emitter_stats(source)
    emission_prob = _clamp_zero_one(float(stats.get("emission_prob", 0.0) or 0.0), "emission_prob")
    p_multi = _clamp_zero_one(float(stats.get("p_multi", 0.0) or 0.0), "p_multi")
    g2_0 = _clamp_zero_one(float(stats.get("g2_0", 0.0) or 0.0), "g2_0")

    if tier >= 1:
        # Tier 1 source model: explicitly honor configured pulse quality knobs.
        pulse_shape_factor = _clamp_zero_one(float(source.get("pulse_shape_factor", 1.0) or 1.0), "pulse_shape_factor")
        emission_prob = _clamp_zero_one(emission_prob * pulse_shape_factor, "emission_prob")
        p_multi = _clamp_zero_one(p_multi * (2.0 - pulse_shape_factor), "p_multi")

    return SourceProfile(
        tier=tier,
        source_type=source_type,
        emission_prob=emission_prob,
        p_multi=p_multi,
        g2_0=g2_0,
        diagnostics=dict(stats.get("diagnostics", {})),
    )


def get_emitter_stats(source: dict) -> Dict[str, Any]:
    requested_backend = source.get("physics_backend", "analytic")
    seed = int(source.get("seed", 0))
    emission_mode = _resolve_emission_mode(source.get("emission_mode", "steady_state"))
    if requested_backend != "qutip":
        stats = _analytic_emitter(source, emission_mode=emission_mode)
        stats["backend_requested"] = requested_backend
        stats["seed"] = seed
        return stats

    try:
        stats = _qutip_emitter(source, emission_mode=emission_mode)
        stats["backend_requested"] = requested_backend
        stats["seed"] = seed
        return stats
    except Exception as exc:
        warnings.warn(f"QuTiP backend unavailable, using analytic model: {exc}")
        stats = _analytic_emitter(source, emission_mode=emission_mode)
        stats["backend_requested"] = requested_backend
        stats["seed"] = seed
        stats["fallback_reason"] = str(exc)
        return stats


def _analytic_emitter(source: dict, emission_mode: str) -> Dict[str, Any]:
    lifetime_ns = _positive(
        source.get("radiative_lifetime_ns", 1.0),
        default=1.0,
        field_name="radiative_lifetime_ns",
    )
    purcell = _positive(
        source.get("purcell_factor", 1.0),
        default=1.0,
        field_name="purcell_factor",
    )
    g2_input = _clamp_zero_one(source.get("g2_0", 0.0), "g2_0", warn_on_clip=True)
    window_ns = _positive(
        source.get("pulse_window_ns", 5.0 * lifetime_ns),
        default=5.0 * lifetime_ns,
        field_name="pulse_window_ns",
    )
    dephasing = max(0.0, float(source.get("dephasing_rate_per_ns", 0.0)))
    drive = max(0.0, float(source.get("drive_strength", 0.05)))
    gamma_eff = (1.0 / lifetime_ns) * (1.0 + purcell)
    emission_prob = 1.0 - math.exp(-gamma_eff * window_ns)
    emission_prob = _clamp_zero_one(emission_prob, "emission_prob")
    spectral_purity = _clamp_zero_one(math.exp(-dephasing * window_ns * 0.2), "spectral_purity")
    transient_contrast = 0.0

    if emission_mode == "transient":
        tau = window_ns / lifetime_ns
        transient_contrast = _clamp_zero_one(
            1.0 - math.exp(-drive * max(tau, 1e-6)),
            "transient_contrast",
        )
        emission_prob = _clamp_zero_one(
            emission_prob * (0.75 + 0.25 * transient_contrast),
            "emission_prob",
        )
        g2_0 = _clamp_zero_one(
            g2_input * (1.0 + 0.30 * (1.0 - spectral_purity)) * (1.0 - 0.05 * min(tau, 10.0)),
            "g2_0",
        )
    else:
        g2_0 = g2_input

    linewidth_mhz = max(0.0, ((gamma_eff + dephasing) * 1e3) / (2.0 * math.pi))
    mode_overlap = _clamp_zero_one(
        math.exp(-1.5 * g2_0) * spectral_purity,
        "mode_overlap",
    )
    p_multi = g2_0 / (1.0 + g2_0)

    return {
        "g2_0": g2_0,
        "p_multi": p_multi,
        "emission_prob": emission_prob,
        "backend": "analytic",
        "emission_mode": emission_mode,
        "diagnostics": {
            "lifetime_ns": lifetime_ns,
            "purcell_factor": purcell,
            "pulse_window_ns": window_ns,
            "gamma_eff_per_ns": gamma_eff,
            "window_over_lifetime": window_ns / lifetime_ns,
            "dephasing_rate_per_ns": dephasing,
            "drive_strength": drive,
            "emission_mode": emission_mode,
            "transient_contrast": transient_contrast,
            "linewidth_mhz": linewidth_mhz,
            "spectral_purity": spectral_purity,
            "mode_overlap": mode_overlap,
        },
    }


def _qutip_emitter(source: dict, emission_mode: str) -> Dict[str, Any]:
    import numpy as np
    from qutip import basis, destroy, expect, mesolve, qeye, steadystate, tensor

    lifetime_ns = _positive(
        source.get("radiative_lifetime_ns", 1.0),
        default=1.0,
        field_name="radiative_lifetime_ns",
    )
    gamma = 1.0 / lifetime_ns
    purcell = _positive(
        source.get("purcell_factor", 1.0),
        default=1.0,
        field_name="purcell_factor",
    )
    dephasing = max(0.0, float(source.get("dephasing_rate_per_ns", 0.0)))
    drive = max(0.0, float(source.get("drive_strength", 0.05)))

    g = 1.0
    kappa = 4.0 * g**2 / (purcell * gamma)

    n_cavity = 3
    a = tensor(destroy(n_cavity), qeye(2))
    sm = tensor(qeye(n_cavity), destroy(2))

    hamiltonian = g * (a.dag() * sm + a * sm.dag()) + drive * (a + a.dag())
    collapse_ops = [math.sqrt(kappa) * a, math.sqrt(gamma) * sm]
    if dephasing > 0:
        collapse_ops.append(math.sqrt(dephasing) * sm.dag() * sm)

    rho_ss = steadystate(hamiltonian, collapse_ops)
    n_photon = expect(a.dag() * a, rho_ss)
    if n_photon <= 0:
        g2_0 = 0.0
    else:
        g2_0 = expect(a.dag() * a.dag() * a * a, rho_ss) / (n_photon**2)

    g2_0 = _clamp_zero_one(g2_0, "g2_0")
    p_multi = g2_0 / (1.0 + g2_0)

    window_ns = _positive(
        source.get("pulse_window_ns", 5.0 * lifetime_ns),
        default=5.0 * lifetime_ns,
        field_name="pulse_window_ns",
    )
    gamma_eff = gamma * (1.0 + purcell)
    emission_prob = 1.0 - math.exp(-gamma_eff * window_ns)
    emission_prob = _clamp_zero_one(emission_prob, "emission_prob")
    spectral_purity = _clamp_zero_one(math.exp(-dephasing * window_ns * 0.2), "spectral_purity")
    transient_contrast = 0.0

    if emission_mode == "transient":
        transient_steps = int(source.get("transient_steps", 64))
        transient_steps = max(8, min(4096, transient_steps))
        rho0 = tensor(basis(n_cavity, 0), basis(2, 1))
        rho0 = rho0 * rho0.dag()
        times = np.linspace(0.0, window_ns, transient_steps)
        trajectory = mesolve(
            hamiltonian,
            rho0,
            times,
            collapse_ops,
            [sm.dag() * sm],
        )
        excited_final = float(trajectory.expect[0][-1])
        transient_contrast = _clamp_zero_one(1.0 - excited_final, "transient_contrast")
        emission_prob = _clamp_zero_one(
            emission_prob * (0.75 + 0.25 * transient_contrast),
            "emission_prob",
        )
        g2_0 = _clamp_zero_one(g2_0 * (1.0 + 0.25 * (1.0 - spectral_purity)), "g2_0")
    else:
        excited_final = None

    linewidth_mhz = max(0.0, ((gamma_eff + dephasing) * 1e3) / (2.0 * math.pi))
    mode_overlap = _clamp_zero_one(
        math.exp(-1.5 * g2_0) * spectral_purity,
        "mode_overlap",
    )
    p_multi = g2_0 / (1.0 + g2_0)

    return {
        "g2_0": g2_0,
        "p_multi": p_multi,
        "emission_prob": emission_prob,
        "backend": "qutip",
        "emission_mode": emission_mode,
        "diagnostics": {
            "lifetime_ns": lifetime_ns,
            "purcell_factor": purcell,
            "pulse_window_ns": window_ns,
            "gamma_per_ns": gamma,
            "kappa_per_ns": kappa,
            "gamma_eff_per_ns": gamma_eff,
            "window_over_lifetime": window_ns / lifetime_ns,
            "dephasing_rate_per_ns": dephasing,
            "drive_strength": drive,
            "n_photon_ss": float(n_photon),
            "emission_mode": emission_mode,
            "transient_contrast": transient_contrast,
            "linewidth_mhz": linewidth_mhz,
            "spectral_purity": spectral_purity,
            "mode_overlap": mode_overlap,
            "excited_population_final": excited_final,
        },
    }


def _resolve_emission_mode(value: str) -> str:
    mode = str(value).strip().lower()
    if mode in {"steady_state", "transient"}:
        return mode
    warnings.warn(f"Unsupported emission_mode={value}; using steady_state", stacklevel=3)
    return "steady_state"


def _positive(value: float, default: float, field_name: str) -> float:
    out = float(value)
    if not math.isfinite(out) or out <= 0.0:
        warnings.warn(
            f"{field_name}={value} is invalid; using default {default}",
            stacklevel=3,
        )
        return float(default)
    return out


def _clamp_zero_one(value: float, field_name: str, warn_on_clip: bool = False) -> float:
    out = float(value)
    if not math.isfinite(out):
        warnings.warn(f"{field_name} is non-finite; using 0.0", stacklevel=3)
        return 0.0
    if out < 0.0:
        if warn_on_clip:
            warnings.warn(f"{field_name}={out} below 0.0; clamped", stacklevel=3)
        return 0.0
    if out > 1.0:
        if warn_on_clip:
            warnings.warn(f"{field_name}={out} above 1.0; clamped", stacklevel=3)
        return 1.0
    return out
