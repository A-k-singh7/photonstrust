"""Core PIC layout verification checks.

The checks here are deterministic and lightweight so they can run inside CI or
interactive design workflows with clear pass/fail criteria.
"""

from __future__ import annotations

import math
import random
from typing import Any

from photonstrust.components.pic.crosstalk import predict_parallel_waveguide_xt_db
from photonstrust.pdk import get_pdk


def _normal_cdf(x: float) -> float:
    """Numerically stable normal CDF helper."""

    return 0.5 * (1.0 + math.erf(float(x) / math.sqrt(2.0)))


def verify_crosstalk_budget(
    *,
    parallel_runs: list[dict[str, Any]],
    wavelength_nm: float,
    target_xt_db: float,
    model: dict[str, Any] | None = None,
    corner: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Verify parallel-run crosstalk against a target budget.

    Pass criteria:
    - every run has finite positive gap/length inputs
    - predicted XT for every run is <= target_xt_db
    """

    if not isinstance(parallel_runs, list) or not parallel_runs:
        raise ValueError("parallel_runs must be a non-empty list")

    wavelength_nm = float(wavelength_nm)
    target_xt_db = float(target_xt_db)

    points: list[dict[str, Any]] = []
    violations: list[str] = []
    worst_xt_db = -200.0

    for i, run in enumerate(parallel_runs):
        if not isinstance(run, dict):
            violations.append(f"run[{i}] invalid: expected object")
            continue

        gap_um = float(run.get("gap_um", 0.0) or 0.0)
        parallel_length_um = float(run.get("parallel_length_um", 0.0) or 0.0)
        run_id = str(run.get("id") or f"run_{i}")

        if not math.isfinite(gap_um) or not math.isfinite(parallel_length_um) or gap_um <= 0.0 or parallel_length_um < 0.0:
            violations.append(f"{run_id}: invalid geometry")
            continue

        xt_db = float(
            predict_parallel_waveguide_xt_db(
                gap_um=gap_um,
                parallel_length_um=parallel_length_um,
                wavelength_nm=wavelength_nm,
                model=model,
                corner=corner,
            )
        )
        worst_xt_db = max(worst_xt_db, xt_db)
        passed = bool(xt_db <= target_xt_db)
        if not passed:
            violations.append(f"{run_id}: xt_db={xt_db:.3f} exceeds target={target_xt_db:.3f}")

        points.append(
            {
                "run_id": run_id,
                "gap_um": gap_um,
                "parallel_length_um": parallel_length_um,
                "xt_db": xt_db,
                "target_xt_db": target_xt_db,
                "pass": passed,
            }
        )

    return {
        "check": "pic.layout.verification.crosstalk_budget",
        "pass": len(violations) == 0,
        "criteria": "all predicted xt_db <= target_xt_db",
        "wavelength_nm": wavelength_nm,
        "target_xt_db": target_xt_db,
        "worst_xt_db": worst_xt_db,
        "points": points,
        "violations": violations,
    }


def verify_thermal_drift(
    *,
    segments: list[dict[str, Any]],
    delta_temperature_c: float,
    max_phase_drift_rad: float,
    max_wavelength_shift_pm: float,
) -> dict[str, Any]:
    """Verify thermal drift envelope from thermo-optic variation.

    Pass criteria (per segment):
    - |phase_drift_rad| <= max_phase_drift_rad
    - |wavelength_shift_pm| <= max_wavelength_shift_pm
    """

    if not isinstance(segments, list) or not segments:
        raise ValueError("segments must be a non-empty list")

    dt = float(delta_temperature_c)
    max_phase = abs(float(max_phase_drift_rad))
    max_shift_pm = abs(float(max_wavelength_shift_pm))

    points: list[dict[str, Any]] = []
    violations: list[str] = []

    for i, seg in enumerate(segments):
        if not isinstance(seg, dict):
            violations.append(f"segment[{i}] invalid: expected object")
            continue

        seg_id = str(seg.get("id") or f"segment_{i}")
        length_um = float(seg.get("length_um", 0.0) or 0.0)
        wavelength_nm = float(seg.get("wavelength_nm", 1550.0) or 1550.0)
        thermo_optic_coeff_per_c = float(seg.get("thermo_optic_coeff_per_c", 1.86e-4) or 1.86e-4)
        group_index = float(seg.get("group_index", 4.2) or 4.2)

        wavelength_um = max(1e-9, wavelength_nm * 1e-3)
        delta_n = thermo_optic_coeff_per_c * dt
        phase_drift_rad = (2.0 * math.pi / wavelength_um) * delta_n * length_um
        wavelength_shift_pm = wavelength_nm * (delta_n / max(1e-9, group_index)) * 1.0e3

        passed = abs(phase_drift_rad) <= max_phase and abs(wavelength_shift_pm) <= max_shift_pm
        if not passed:
            violations.append(
                f"{seg_id}: phase={phase_drift_rad:.3f}rad, shift={wavelength_shift_pm:.3f}pm exceeds limits"
            )

        points.append(
            {
                "segment_id": seg_id,
                "length_um": length_um,
                "delta_temperature_c": dt,
                "phase_drift_rad": phase_drift_rad,
                "wavelength_shift_pm": wavelength_shift_pm,
                "limits": {
                    "max_phase_drift_rad": max_phase,
                    "max_wavelength_shift_pm": max_shift_pm,
                },
                "pass": passed,
            }
        )

    worst_phase = max((abs(float(p["phase_drift_rad"])) for p in points), default=0.0)
    worst_shift = max((abs(float(p["wavelength_shift_pm"])) for p in points), default=0.0)

    return {
        "check": "pic.layout.verification.thermal_drift",
        "pass": len(violations) == 0,
        "criteria": "per segment phase and wavelength drift remain below limits",
        "delta_temperature_c": dt,
        "worst_phase_drift_rad": worst_phase,
        "worst_wavelength_shift_pm": worst_shift,
        "points": points,
        "violations": violations,
    }


def verify_bend_and_routing_loss(
    *,
    routes: list[dict[str, Any]],
    max_route_loss_db: float,
    pdk_name: str | None = None,
    bend_loss_model: dict[str, float] | None = None,
    waveguide_loss_db_per_cm: float = 2.0,
) -> dict[str, Any]:
    """Verify bend-radius DRC and route-level insertion-loss budget.

    Pass criteria (per route):
    - every bend radius >= pdk.min_bend_radius_um
    - predicted route_loss_db <= max_route_loss_db
    """

    if not isinstance(routes, list) or not routes:
        raise ValueError("routes must be a non-empty list")

    pdk = get_pdk(pdk_name)
    min_bend_radius_um = float(pdk.design_rules.get("min_bend_radius_um", 0.0) or 0.0)

    model = dict(bend_loss_model or {})
    ref_radius_um = float(model.get("ref_radius_um", 10.0) or 10.0)
    coeff_90deg_db = float(model.get("coeff_90deg_db", 0.005) or 0.005)
    radius_exponent = float(model.get("radius_exponent", 3.0) or 3.0)

    points: list[dict[str, Any]] = []
    violations: list[str] = []
    worst_route_loss_db = 0.0

    for i, route in enumerate(routes):
        if not isinstance(route, dict):
            violations.append(f"route[{i}] invalid: expected object")
            continue

        route_id = str(route.get("id") or f"route_{i}")
        length_um = float(route.get("length_um", 0.0) or 0.0)
        bends = route.get("bends") or []
        if not isinstance(bends, list):
            bends = []

        propagation_loss_db = float(waveguide_loss_db_per_cm) * (length_um / 1.0e4)

        bend_loss_db = 0.0
        radius_violations = 0
        for j, bend in enumerate(bends):
            if not isinstance(bend, dict):
                continue
            radius_um = float(bend.get("radius_um", 0.0) or 0.0)
            angle_deg = float(bend.get("angle_deg", 90.0) or 90.0)
            if radius_um < min_bend_radius_um:
                radius_violations += 1
                violations.append(
                    f"{route_id}.bend[{j}]: radius {radius_um:.3f} < min {min_bend_radius_um:.3f} um"
                )
            eff_r = max(1e-9, radius_um)
            bend_loss_db += coeff_90deg_db * (ref_radius_um / eff_r) ** radius_exponent * (angle_deg / 90.0)

        route_loss_db = propagation_loss_db + bend_loss_db
        worst_route_loss_db = max(worst_route_loss_db, route_loss_db)
        pass_loss = route_loss_db <= float(max_route_loss_db)
        if not pass_loss:
            violations.append(
                f"{route_id}: route_loss_db={route_loss_db:.3f} exceeds max_route_loss_db={float(max_route_loss_db):.3f}"
            )

        points.append(
            {
                "route_id": route_id,
                "length_um": length_um,
                "propagation_loss_db": propagation_loss_db,
                "bend_loss_db": bend_loss_db,
                "route_loss_db": route_loss_db,
                "radius_violations": radius_violations,
                "max_route_loss_db": float(max_route_loss_db),
                "pass": pass_loss and radius_violations == 0,
            }
        )

    return {
        "check": "pic.layout.verification.bend_and_routing_loss",
        "pass": len(violations) == 0,
        "criteria": "all bend radii satisfy PDK minimum and all route losses meet budget",
        "pdk": {"name": pdk.name, "version": pdk.version, "min_bend_radius_um": min_bend_radius_um},
        "worst_route_loss_db": worst_route_loss_db,
        "points": points,
        "violations": violations,
    }


def verify_process_variation(
    *,
    metrics: list[dict[str, Any]],
    sigma_multiplier: float = 3.0,
) -> dict[str, Any]:
    """Check if process-variation envelopes remain within metric limits.

    Each metric requires:
    - name
    - nominal
    - sigma (1σ process variation in native units)
    - sensitivity (scale factor from sigma to metric variation)
    - min_allowed / max_allowed limits

    Pass criteria:
    - [nominal - N*sigma*sensitivity, nominal + N*sigma*sensitivity]
      is inside [min_allowed, max_allowed]
    """

    if not isinstance(metrics, list) or not metrics:
        raise ValueError("metrics must be a non-empty list")

    n_sigma = abs(float(sigma_multiplier))
    points: list[dict[str, Any]] = []
    violations: list[str] = []

    for i, m in enumerate(metrics):
        if not isinstance(m, dict):
            violations.append(f"metric[{i}] invalid: expected object")
            continue

        name = str(m.get("name") or f"metric_{i}")
        nominal = float(m.get("nominal"))
        sigma = abs(float(m.get("sigma", 0.0) or 0.0))
        sensitivity = abs(float(m.get("sensitivity", 1.0) or 1.0))
        min_allowed = float(m.get("min_allowed", -math.inf))
        max_allowed = float(m.get("max_allowed", math.inf))

        envelope_delta = n_sigma * sigma * sensitivity
        low = nominal - envelope_delta
        high = nominal + envelope_delta
        passed = low >= min_allowed and high <= max_allowed
        if not passed:
            violations.append(
                f"{name}: envelope=[{low:.6g}, {high:.6g}] outside limits=[{min_allowed:.6g}, {max_allowed:.6g}]"
            )

        points.append(
            {
                "name": name,
                "nominal": nominal,
                "sigma": sigma,
                "sensitivity": sensitivity,
                "sigma_multiplier": n_sigma,
                "envelope": {"low": low, "high": high},
                "limits": {"min_allowed": min_allowed, "max_allowed": max_allowed},
                "pass": passed,
            }
        )

    return {
        "check": "pic.layout.verification.process_variation",
        "pass": len(violations) == 0,
        "criteria": "variation envelope stays inside metric limits",
        "sigma_multiplier": n_sigma,
        "points": points,
        "violations": violations,
    }


def verify_design_rule_envelope(
    *,
    pdk_name: str | None = None,
    waveguides: list[dict[str, Any]] | None = None,
    couplers: list[dict[str, Any]] | None = None,
    bends: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run geometry-level DRC envelope checks against PDK minimum rules.

    Pass criteria:
    - every waveguide width >= pdk.min_waveguide_width_um
    - every coupler gap >= pdk.min_waveguide_gap_um
    - every bend radius >= pdk.min_bend_radius_um
    """

    waveguides = list(waveguides or [])
    couplers = list(couplers or [])
    bends = list(bends or [])
    if not (waveguides or couplers or bends):
        raise ValueError("at least one of waveguides/couplers/bends must be provided")

    pdk = get_pdk(pdk_name)
    min_width_um = float(pdk.design_rules.get("min_waveguide_width_um", 0.0) or 0.0)
    min_gap_um = float(pdk.design_rules.get("min_waveguide_gap_um", 0.0) or 0.0)
    min_bend_radius_um = float(pdk.design_rules.get("min_bend_radius_um", 0.0) or 0.0)

    points: list[dict[str, Any]] = []
    violations: list[str] = []

    for i, wg in enumerate(waveguides):
        if not isinstance(wg, dict):
            violations.append(f"waveguide[{i}] invalid: expected object")
            continue
        wg_id = str(wg.get("id") or f"waveguide_{i}")
        width_um = float(wg.get("width_um", 0.0) or 0.0)
        passed = math.isfinite(width_um) and width_um >= min_width_um
        if not passed:
            violations.append(
                f"{wg_id}: width_um={width_um:.6g} < min_waveguide_width_um={min_width_um:.6g}"
            )
        points.append(
            {
                "entity_type": "waveguide",
                "entity_id": wg_id,
                "measured": {"width_um": width_um},
                "limits": {"min_waveguide_width_um": min_width_um},
                "pass": passed,
            }
        )

    for i, cp in enumerate(couplers):
        if not isinstance(cp, dict):
            violations.append(f"coupler[{i}] invalid: expected object")
            continue
        cp_id = str(cp.get("id") or f"coupler_{i}")
        gap_um = float(cp.get("gap_um", 0.0) or 0.0)
        passed = math.isfinite(gap_um) and gap_um >= min_gap_um
        if not passed:
            violations.append(
                f"{cp_id}: gap_um={gap_um:.6g} < min_waveguide_gap_um={min_gap_um:.6g}"
            )
        points.append(
            {
                "entity_type": "coupler",
                "entity_id": cp_id,
                "measured": {"gap_um": gap_um},
                "limits": {"min_waveguide_gap_um": min_gap_um},
                "pass": passed,
            }
        )

    for i, bend in enumerate(bends):
        if not isinstance(bend, dict):
            violations.append(f"bend[{i}] invalid: expected object")
            continue
        bend_id = str(bend.get("id") or f"bend_{i}")
        radius_um = float(bend.get("radius_um", 0.0) or 0.0)
        passed = math.isfinite(radius_um) and radius_um >= min_bend_radius_um
        if not passed:
            violations.append(
                f"{bend_id}: radius_um={radius_um:.6g} < min_bend_radius_um={min_bend_radius_um:.6g}"
            )
        points.append(
            {
                "entity_type": "bend",
                "entity_id": bend_id,
                "measured": {"radius_um": radius_um},
                "limits": {"min_bend_radius_um": min_bend_radius_um},
                "pass": passed,
            }
        )

    return {
        "check": "pic.layout.verification.design_rule_envelope",
        "pass": len(violations) == 0,
        "criteria": "all geometry values satisfy PDK minimum design rules",
        "pdk": {
            "name": pdk.name,
            "version": pdk.version,
            "min_waveguide_width_um": min_width_um,
            "min_waveguide_gap_um": min_gap_um,
            "min_bend_radius_um": min_bend_radius_um,
        },
        "points": points,
        "violations": violations,
    }


def verify_thermal_crosstalk_matrix(
    *,
    heaters: list[dict[str, Any]],
    victims: list[dict[str, Any]],
    coupling_matrix_c_per_mw: list[list[float]],
    max_victim_delta_temperature_c: float,
    max_victim_phase_drift_rad: float,
) -> dict[str, Any]:
    """Verify heater-to-victim thermal crosstalk envelope.

    For each victim j:
      delta_t_j = sum_i(heater_power_i_mW * coupling_matrix_c_per_mw[i][j])
      phase_j from thermo-optic shift on victim path length.

    Pass criteria (per victim):
    - |delta_t_j| <= max_victim_delta_temperature_c
    - |phase_drift_rad_j| <= max_victim_phase_drift_rad
    """

    if not isinstance(heaters, list) or not heaters:
        raise ValueError("heaters must be a non-empty list")
    if not isinstance(victims, list) or not victims:
        raise ValueError("victims must be a non-empty list")
    if not isinstance(coupling_matrix_c_per_mw, list) or not coupling_matrix_c_per_mw:
        raise ValueError("coupling_matrix_c_per_mw must be a non-empty matrix")

    n_h = len(heaters)
    n_v = len(victims)
    if len(coupling_matrix_c_per_mw) != n_h:
        raise ValueError("coupling_matrix_c_per_mw row count must match number of heaters")
    for row in coupling_matrix_c_per_mw:
        if not isinstance(row, list) or len(row) != n_v:
            raise ValueError("every coupling_matrix_c_per_mw row must match number of victims")

    max_dt = abs(float(max_victim_delta_temperature_c))
    max_phase = abs(float(max_victim_phase_drift_rad))

    heater_ids: list[str] = []
    heater_powers_mw: list[float] = []
    for i, h in enumerate(heaters):
        if not isinstance(h, dict):
            raise ValueError(f"heaters[{i}] must be an object")
        heater_ids.append(str(h.get("id") or f"heater_{i}"))
        heater_powers_mw.append(float(h.get("power_mw", 0.0) or 0.0))

    points: list[dict[str, Any]] = []
    violations: list[str] = []

    for j, victim in enumerate(victims):
        if not isinstance(victim, dict):
            violations.append(f"victim[{j}] invalid: expected object")
            continue

        victim_id = str(victim.get("id") or f"victim_{j}")
        length_um = float(victim.get("length_um", 0.0) or 0.0)
        wavelength_nm = float(victim.get("wavelength_nm", 1550.0) or 1550.0)
        thermo_optic_coeff_per_c = float(victim.get("thermo_optic_coeff_per_c", 1.86e-4) or 1.86e-4)

        contributions = []
        delta_t_c = 0.0
        for i in range(n_h):
            c_per_mw = float(coupling_matrix_c_per_mw[i][j] or 0.0)
            delta_t_ij = heater_powers_mw[i] * c_per_mw
            delta_t_c += delta_t_ij
            contributions.append(
                {
                    "heater_id": heater_ids[i],
                    "power_mw": heater_powers_mw[i],
                    "coupling_c_per_mw": c_per_mw,
                    "delta_t_c": delta_t_ij,
                }
            )

        wavelength_um = max(1e-9, wavelength_nm * 1e-3)
        delta_n = thermo_optic_coeff_per_c * delta_t_c
        phase_drift_rad = (2.0 * math.pi / wavelength_um) * delta_n * length_um

        passed = abs(delta_t_c) <= max_dt and abs(phase_drift_rad) <= max_phase
        if not passed:
            violations.append(
                f"{victim_id}: delta_t={delta_t_c:.6g}C, phase={phase_drift_rad:.6g}rad exceeds limits"
            )

        points.append(
            {
                "victim_id": victim_id,
                "length_um": length_um,
                "wavelength_nm": wavelength_nm,
                "thermo_optic_coeff_per_c": thermo_optic_coeff_per_c,
                "delta_temperature_c": delta_t_c,
                "phase_drift_rad": phase_drift_rad,
                "limits": {
                    "max_victim_delta_temperature_c": max_dt,
                    "max_victim_phase_drift_rad": max_phase,
                },
                "heater_contributions": contributions,
                "pass": passed,
            }
        )

    worst_dt = max((abs(float(p["delta_temperature_c"])) for p in points), default=0.0)
    worst_phase = max((abs(float(p["phase_drift_rad"])) for p in points), default=0.0)

    return {
        "check": "pic.layout.verification.thermal_crosstalk_matrix",
        "pass": len(violations) == 0,
        "criteria": "all victims satisfy thermal crosstalk temperature and phase limits",
        "heater_count": n_h,
        "victim_count": n_v,
        "worst_victim_delta_temperature_c": worst_dt,
        "worst_victim_phase_drift_rad": worst_phase,
        "points": points,
        "violations": violations,
    }


def verify_resonance_alignment(
    *,
    channels: list[dict[str, Any]],
    max_detune_pm: float,
    min_linewidth_pm: float | None = None,
    max_linewidth_pm: float | None = None,
) -> dict[str, Any]:
    """Verify ring/filter resonance alignment against target wavelengths.

    Per channel pass criteria:
    - |observed_wavelength_nm - target_wavelength_nm| * 1000 <= max_detune_pm
    - optional linewidth bounds (when provided)
    """

    if not isinstance(channels, list) or not channels:
        raise ValueError("channels must be a non-empty list")

    max_detune_pm = abs(float(max_detune_pm))
    min_lw = None if min_linewidth_pm is None else max(0.0, float(min_linewidth_pm))
    max_lw = None if max_linewidth_pm is None else max(0.0, float(max_linewidth_pm))

    points: list[dict[str, Any]] = []
    violations: list[str] = []

    for i, ch in enumerate(channels):
        if not isinstance(ch, dict):
            violations.append(f"channel[{i}] invalid: expected object")
            continue

        ch_id = str(ch.get("id") or f"channel_{i}")
        target_nm = float(ch.get("target_wavelength_nm"))
        observed_nm = float(ch.get("observed_wavelength_nm", ch.get("current_wavelength_nm", target_nm)))
        linewidth_pm = ch.get("linewidth_pm")
        linewidth_pm_f = None if linewidth_pm is None else max(0.0, float(linewidth_pm))

        detune_pm = (observed_nm - target_nm) * 1.0e3
        pass_detune = abs(detune_pm) <= max_detune_pm

        pass_linewidth = True
        if min_lw is not None and linewidth_pm_f is not None and linewidth_pm_f < min_lw:
            pass_linewidth = False
        if max_lw is not None and linewidth_pm_f is not None and linewidth_pm_f > max_lw:
            pass_linewidth = False
        if (min_lw is not None or max_lw is not None) and linewidth_pm_f is None:
            pass_linewidth = False

        passed = pass_detune and pass_linewidth
        if not pass_detune:
            violations.append(
                f"{ch_id}: detune_pm={detune_pm:.6g} exceeds max_detune_pm={max_detune_pm:.6g}"
            )
        if not pass_linewidth:
            violations.append(
                f"{ch_id}: linewidth_pm={linewidth_pm_f} outside bounds [{min_lw}, {max_lw}]"
            )

        points.append(
            {
                "channel_id": ch_id,
                "target_wavelength_nm": target_nm,
                "observed_wavelength_nm": observed_nm,
                "detune_pm": detune_pm,
                "linewidth_pm": linewidth_pm_f,
                "limits": {
                    "max_detune_pm": max_detune_pm,
                    "min_linewidth_pm": min_lw,
                    "max_linewidth_pm": max_lw,
                },
                "pass": passed,
            }
        )

    worst_detune_pm = max((abs(float(p["detune_pm"])) for p in points), default=0.0)

    return {
        "check": "pic.layout.verification.resonance_alignment",
        "pass": len(violations) == 0,
        "criteria": "all resonance channels satisfy detune and linewidth limits",
        "max_detune_pm": max_detune_pm,
        "worst_detune_pm": worst_detune_pm,
        "points": points,
        "violations": violations,
    }


def verify_phase_shifter_range(
    *,
    shifters: list[dict[str, Any]],
    default_required_phase_span_rad: float = math.pi,
    max_total_power_mw: float | None = None,
) -> dict[str, Any]:
    """Verify phase shifters can provide required phase span within power budgets.

    Per shifter pass criteria:
    - achievable_phase_span_rad = tuning_efficiency_rad_per_mw * max_power_mw
    - achievable_phase_span_rad >= required_phase_span_rad

    Optional global criterion:
    - sum(max_power_mw) <= max_total_power_mw
    """

    if not isinstance(shifters, list) or not shifters:
        raise ValueError("shifters must be a non-empty list")

    default_required = max(0.0, float(default_required_phase_span_rad))
    max_total_power = None if max_total_power_mw is None else max(0.0, float(max_total_power_mw))

    points: list[dict[str, Any]] = []
    violations: list[str] = []

    total_power_mw = 0.0
    for i, sh in enumerate(shifters):
        if not isinstance(sh, dict):
            violations.append(f"shifter[{i}] invalid: expected object")
            continue

        sh_id = str(sh.get("id") or f"shifter_{i}")
        tuning_eff = max(0.0, float(sh.get("tuning_efficiency_rad_per_mw", 0.0) or 0.0))
        max_power = max(0.0, float(sh.get("max_power_mw", 0.0) or 0.0))
        required = max(0.0, float(sh.get("required_phase_span_rad", default_required) or default_required))

        achievable = tuning_eff * max_power
        margin = achievable - required
        passed = margin >= 0.0
        if not passed:
            violations.append(
                f"{sh_id}: achievable_phase_span_rad={achievable:.6g} < required={required:.6g}"
            )

        total_power_mw += max_power

        points.append(
            {
                "shifter_id": sh_id,
                "tuning_efficiency_rad_per_mw": tuning_eff,
                "max_power_mw": max_power,
                "required_phase_span_rad": required,
                "achievable_phase_span_rad": achievable,
                "margin_rad": margin,
                "pass": passed,
            }
        )

    if max_total_power is not None and total_power_mw > max_total_power:
        violations.append(
            f"total_max_power_mw={total_power_mw:.6g} exceeds max_total_power_mw={max_total_power:.6g}"
        )

    return {
        "check": "pic.layout.verification.phase_shifter_range",
        "pass": len(violations) == 0,
        "criteria": "all shifters satisfy phase-span requirement and optional total-power budget",
        "default_required_phase_span_rad": default_required,
        "max_total_power_mw": max_total_power,
        "total_max_power_mw": total_power_mw,
        "points": points,
        "violations": violations,
    }


def verify_wavelength_sweep_signoff(
    *,
    channels: list[dict[str, Any]],
    min_channel_spacing_pm: float,
    max_insertion_loss_db: float,
    min_extinction_ratio_db: float,
    min_linewidth_pm: float | None = None,
    max_linewidth_pm: float | None = None,
) -> dict[str, Any]:
    """Verify wavelength-domain channel quality and spacing constraints.

    Each channel requires:
    - id
    - center_wavelength_nm
    - insertion_loss_db
    - extinction_ratio_db
    - optional linewidth_pm

    Pass criteria:
    - insertion_loss_db <= max_insertion_loss_db
    - extinction_ratio_db >= min_extinction_ratio_db
    - optional linewidth bounds if provided
    - pairwise channel spacing >= min_channel_spacing_pm
    """

    if not isinstance(channels, list) or not channels:
        raise ValueError("channels must be a non-empty list")

    min_spacing_pm = abs(float(min_channel_spacing_pm))
    max_il_db = float(max_insertion_loss_db)
    min_er_db = float(min_extinction_ratio_db)
    min_lw = None if min_linewidth_pm is None else max(0.0, float(min_linewidth_pm))
    max_lw = None if max_linewidth_pm is None else max(0.0, float(max_linewidth_pm))

    points: list[dict[str, Any]] = []
    violations: list[str] = []

    parsed_channels: list[dict[str, Any]] = []
    for i, ch in enumerate(channels):
        if not isinstance(ch, dict):
            violations.append(f"channel[{i}] invalid: expected object")
            continue

        ch_id = str(ch.get("id") or f"channel_{i}")
        center_nm = float(ch.get("center_wavelength_nm"))
        il_db = float(ch.get("insertion_loss_db", math.inf))
        er_db = float(ch.get("extinction_ratio_db", -math.inf))
        linewidth_pm = ch.get("linewidth_pm")
        linewidth_pm_f = None if linewidth_pm is None else max(0.0, float(linewidth_pm))

        pass_il = il_db <= max_il_db
        pass_er = er_db >= min_er_db
        pass_lw = True
        if min_lw is not None and linewidth_pm_f is not None and linewidth_pm_f < min_lw:
            pass_lw = False
        if max_lw is not None and linewidth_pm_f is not None and linewidth_pm_f > max_lw:
            pass_lw = False
        if (min_lw is not None or max_lw is not None) and linewidth_pm_f is None:
            pass_lw = False

        if not pass_il:
            violations.append(f"{ch_id}: insertion_loss_db={il_db:.6g} exceeds max={max_il_db:.6g}")
        if not pass_er:
            violations.append(f"{ch_id}: extinction_ratio_db={er_db:.6g} below min={min_er_db:.6g}")
        if not pass_lw:
            violations.append(f"{ch_id}: linewidth_pm={linewidth_pm_f} outside bounds [{min_lw}, {max_lw}]")

        parsed_channels.append(
            {
                "channel_id": ch_id,
                "center_wavelength_nm": center_nm,
                "insertion_loss_db": il_db,
                "extinction_ratio_db": er_db,
                "linewidth_pm": linewidth_pm_f,
                "pass": pass_il and pass_er and pass_lw,
            }
        )

    parsed_channels.sort(key=lambda row: float(row["center_wavelength_nm"]))
    spacing_rows: list[dict[str, Any]] = []
    for left, right in zip(parsed_channels, parsed_channels[1:]):
        spacing_pm = (float(right["center_wavelength_nm"]) - float(left["center_wavelength_nm"])) * 1.0e3
        pass_spacing = spacing_pm >= min_spacing_pm
        if not pass_spacing:
            violations.append(
                f"spacing {left['channel_id']}->{right['channel_id']} = {spacing_pm:.6g}pm below min={min_spacing_pm:.6g}pm"
            )
        spacing_rows.append(
            {
                "left_channel_id": left["channel_id"],
                "right_channel_id": right["channel_id"],
                "spacing_pm": spacing_pm,
                "min_channel_spacing_pm": min_spacing_pm,
                "pass": pass_spacing,
            }
        )

    worst_il = max((float(p["insertion_loss_db"]) for p in parsed_channels), default=0.0)
    worst_er = min((float(p["extinction_ratio_db"]) for p in parsed_channels), default=math.inf)
    worst_spacing = min((float(p["spacing_pm"]) for p in spacing_rows), default=math.inf)

    points.extend(parsed_channels)

    return {
        "check": "pic.layout.verification.wavelength_sweep_signoff",
        "pass": len(violations) == 0,
        "criteria": "all channels satisfy IL/ER/linewidth limits and spacing constraints",
        "min_channel_spacing_pm": min_spacing_pm,
        "max_insertion_loss_db": max_il_db,
        "min_extinction_ratio_db": min_er_db,
        "worst_insertion_loss_db": worst_il,
        "worst_extinction_ratio_db": worst_er,
        "worst_channel_spacing_pm": worst_spacing,
        "points": points,
        "spacing": spacing_rows,
        "violations": violations,
    }


def _estimate_linewidth_pm(
    *,
    wavelengths_nm: list[float],
    trace_db: list[float],
    peak_idx: int,
    level_db: float,
) -> float | None:
    """Estimate linewidth (pm) at a target level below peak using linear interpolation."""

    if peak_idx < 0 or peak_idx >= len(wavelengths_nm):
        return None

    # left crossing
    left_nm = None
    for i in range(peak_idx, 0, -1):
        y0 = float(trace_db[i])
        y1 = float(trace_db[i - 1])
        if (y0 >= level_db and y1 <= level_db) or (y0 <= level_db and y1 >= level_db):
            x0 = float(wavelengths_nm[i])
            x1 = float(wavelengths_nm[i - 1])
            if abs(y1 - y0) <= 1e-15:
                left_nm = x0
            else:
                t = (level_db - y0) / (y1 - y0)
                left_nm = x0 + t * (x1 - x0)
            break

    # right crossing
    right_nm = None
    for i in range(peak_idx, len(wavelengths_nm) - 1):
        y0 = float(trace_db[i])
        y1 = float(trace_db[i + 1])
        if (y0 >= level_db and y1 <= level_db) or (y0 <= level_db and y1 >= level_db):
            x0 = float(wavelengths_nm[i])
            x1 = float(wavelengths_nm[i + 1])
            if abs(y1 - y0) <= 1e-15:
                right_nm = x1
            else:
                t = (level_db - y0) / (y1 - y0)
                right_nm = x0 + t * (x1 - x0)
            break

    if left_nm is None or right_nm is None:
        return None
    return max(0.0, (right_nm - left_nm) * 1.0e3)


def verify_wavelength_sweep_signoff_from_trace(
    *,
    wavelengths_nm: list[float],
    transmission_db: list[float],
    channel_windows: list[dict[str, Any]],
    min_channel_spacing_pm: float,
    max_insertion_loss_db: float,
    min_extinction_ratio_db: float,
    min_linewidth_pm: float | None = None,
    max_linewidth_pm: float | None = None,
    reference_peak_db: float = 0.0,
    linewidth_drop_db: float = 3.0,
) -> dict[str, Any]:
    """Auto-extract channel metrics from wavelength trace, then run sweep signoff.

    This is a one-click bridge from spectral traces to signoff checks.

    Each channel window requires:
    - id
    - start_wavelength_nm
    - stop_wavelength_nm
    """

    if not isinstance(wavelengths_nm, list) or not isinstance(transmission_db, list):
        raise ValueError("wavelengths_nm and transmission_db must be lists")
    if len(wavelengths_nm) != len(transmission_db) or len(wavelengths_nm) < 3:
        raise ValueError("wavelengths_nm and transmission_db must have same length >= 3")
    if not isinstance(channel_windows, list) or not channel_windows:
        raise ValueError("channel_windows must be a non-empty list")

    pairs = sorted(
        [(float(w), float(t)) for w, t in zip(wavelengths_nm, transmission_db)],
        key=lambda x: x[0],
    )
    ws = [p[0] for p in pairs]
    ts = [p[1] for p in pairs]

    extracted_channels: list[dict[str, Any]] = []
    extraction_violations: list[str] = []

    for i, window in enumerate(channel_windows):
        if not isinstance(window, dict):
            extraction_violations.append(f"channel_window[{i}] invalid: expected object")
            continue

        ch_id = str(window.get("id") or f"channel_{i}")
        start_nm = float(window.get("start_wavelength_nm"))
        stop_nm = float(window.get("stop_wavelength_nm"))
        lo = min(start_nm, stop_nm)
        hi = max(start_nm, stop_nm)

        idxs = [k for k, w in enumerate(ws) if lo <= w <= hi]
        if len(idxs) < 3:
            extraction_violations.append(
                f"{ch_id}: insufficient points in window [{lo:.6g}, {hi:.6g}]"
            )
            continue

        # peak-based extraction (higher transmission_db is better)
        peak_idx = max(idxs, key=lambda k: ts[k])
        valley_idx = min(idxs, key=lambda k: ts[k])

        center_nm = float(ws[peak_idx])
        peak_db = float(ts[peak_idx])
        valley_db = float(ts[valley_idx])

        insertion_loss_db = max(0.0, float(reference_peak_db) - peak_db)
        extinction_ratio_db = max(0.0, peak_db - valley_db)
        linewidth_pm = _estimate_linewidth_pm(
            wavelengths_nm=ws,
            trace_db=ts,
            peak_idx=peak_idx,
            level_db=peak_db - abs(float(linewidth_drop_db)),
        )

        extracted_channels.append(
            {
                "id": ch_id,
                "center_wavelength_nm": center_nm,
                "insertion_loss_db": insertion_loss_db,
                "extinction_ratio_db": extinction_ratio_db,
                "linewidth_pm": linewidth_pm,
                "window": {
                    "start_wavelength_nm": lo,
                    "stop_wavelength_nm": hi,
                },
            }
        )

    if not extracted_channels:
        return {
            "check": "pic.layout.verification.wavelength_sweep_signoff_from_trace",
            "pass": False,
            "criteria": "trace extraction + wavelength_sweep_signoff must pass",
            "extracted_channels": [],
            "trace_summary": {
                "point_count": len(ws),
                "wavelength_min_nm": min(ws),
                "wavelength_max_nm": max(ws),
            },
            "signoff": None,
            "violations": extraction_violations or ["no channels extracted"],
        }

    signoff = verify_wavelength_sweep_signoff(
        channels=extracted_channels,
        min_channel_spacing_pm=min_channel_spacing_pm,
        max_insertion_loss_db=max_insertion_loss_db,
        min_extinction_ratio_db=min_extinction_ratio_db,
        min_linewidth_pm=min_linewidth_pm,
        max_linewidth_pm=max_linewidth_pm,
    )

    merged_violations = list(extraction_violations)
    merged_violations.extend(signoff.get("violations", []))

    return {
        "check": "pic.layout.verification.wavelength_sweep_signoff_from_trace",
        "pass": bool(signoff.get("pass")) and len(extraction_violations) == 0,
        "criteria": "trace extraction + wavelength_sweep_signoff must pass",
        "extracted_channels": extracted_channels,
        "trace_summary": {
            "point_count": len(ws),
            "wavelength_min_nm": min(ws),
            "wavelength_max_nm": max(ws),
        },
        "signoff": signoff,
        "violations": merged_violations,
    }


def _cholesky_lower(matrix: list[list[float]]) -> list[list[float]]:
    """Compute lower-triangular Cholesky factor for a symmetric positive matrix."""

    n = len(matrix)
    l = [[0.0 for _ in range(n)] for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            s = sum(l[i][k] * l[j][k] for k in range(j))
            if i == j:
                v = float(matrix[i][i]) - s
                if v <= 0.0 or not math.isfinite(v):
                    raise ValueError("correlation/covariance matrix is not positive definite")
                l[i][j] = math.sqrt(v)
            else:
                d = l[j][j]
                if abs(d) <= 1e-15:
                    raise ValueError("correlation/covariance matrix is singular")
                l[i][j] = (float(matrix[i][j]) - s) / d
    return l


def estimate_process_yield(
    *,
    metrics: list[dict[str, Any]],
    min_required_yield: float = 0.90,
    monte_carlo_samples: int = 0,
    seed: int = 7,
    correlation_matrix: list[list[float]] | None = None,
) -> dict[str, Any]:
    """Estimate process yield from metric distributions.

    Metric fields match `verify_process_variation`:
    - name, nominal, sigma, sensitivity, min_allowed, max_allowed

    Analytic estimate assumes independent normal variables:
      X ~ N(nominal, (sigma*sensitivity)^2)
    Yield_independent = product_i P(min_i <= X_i <= max_i)

    Monte Carlo estimate supports:
    - independent sampling (default), or
    - correlated sampling when `correlation_matrix` is provided.
    """

    if not isinstance(metrics, list) or not metrics:
        raise ValueError("metrics must be a non-empty list")

    min_required = min(1.0, max(0.0, float(min_required_yield)))
    samples_requested = max(0, int(monte_carlo_samples))
    use_correlation = correlation_matrix is not None
    samples = samples_requested
    if use_correlation and samples == 0:
        # Enable correlated-yield mode even when caller omitted explicit samples.
        samples = 5000

    points: list[dict[str, Any]] = []
    violations: list[str] = []
    analytic_yield = 1.0

    parsed: list[dict[str, Any]] = []
    for i, m in enumerate(metrics):
        if not isinstance(m, dict):
            raise ValueError(f"metrics[{i}] must be an object")

        name = str(m.get("name") or f"metric_{i}")
        nominal = float(m.get("nominal"))
        sigma = abs(float(m.get("sigma", 0.0) or 0.0))
        sensitivity = abs(float(m.get("sensitivity", 1.0) or 1.0))
        sigma_eff = sigma * sensitivity
        min_allowed = float(m.get("min_allowed", -math.inf))
        max_allowed = float(m.get("max_allowed", math.inf))

        if sigma_eff <= 0.0:
            p_pass = 1.0 if (nominal >= min_allowed and nominal <= max_allowed) else 0.0
            z_low = -math.inf
            z_high = math.inf
        else:
            z_low = (min_allowed - nominal) / sigma_eff
            z_high = (max_allowed - nominal) / sigma_eff
            p_pass = max(0.0, min(1.0, _normal_cdf(z_high) - _normal_cdf(z_low)))

        analytic_yield *= p_pass
        parsed.append(
            {
                "name": name,
                "nominal": nominal,
                "sigma": sigma,
                "sensitivity": sensitivity,
                "sigma_effective": sigma_eff,
                "limits": {"min_allowed": min_allowed, "max_allowed": max_allowed},
                "z_window": {"low": z_low, "high": z_high},
                "analytic_pass_probability": p_pass,
            }
        )

    corr_matrix_clean: list[list[float]] | None = None
    corr_active_idx: list[int] = []
    cov_cholesky: list[list[float]] | None = None

    if use_correlation:
        n = len(parsed)
        if not isinstance(correlation_matrix, list) or len(correlation_matrix) != n:
            raise ValueError("correlation_matrix must be an NxN list matching metric count")

        corr_matrix_clean = []
        for i, row in enumerate(correlation_matrix):
            if not isinstance(row, list) or len(row) != n:
                raise ValueError("correlation_matrix must be an NxN list matching metric count")
            clean_row = []
            for j, v in enumerate(row):
                f = float(v)
                if not math.isfinite(f) or f < -1.0 or f > 1.0:
                    raise ValueError("correlation_matrix entries must be finite and within [-1, 1]")
                if i == j and abs(f - 1.0) > 1e-6:
                    raise ValueError("correlation_matrix diagonal entries must be 1.0")
                clean_row.append(f)
            corr_matrix_clean.append(clean_row)

        for i in range(n):
            for j in range(i + 1, n):
                if abs(corr_matrix_clean[i][j] - corr_matrix_clean[j][i]) > 1e-6:
                    raise ValueError("correlation_matrix must be symmetric")

        corr_active_idx = [i for i, row in enumerate(parsed) if float(row["sigma_effective"]) > 0.0]
        if corr_active_idx:
            cov_sub: list[list[float]] = []
            for i in corr_active_idx:
                sigma_i = float(parsed[i]["sigma_effective"])
                cov_row: list[float] = []
                for j in corr_active_idx:
                    sigma_j = float(parsed[j]["sigma_effective"])
                    cov_row.append(corr_matrix_clean[i][j] * sigma_i * sigma_j)
                cov_sub.append(cov_row)
            cov_cholesky = _cholesky_lower(cov_sub)

    mc_yield = None
    mc_mode = "independent"
    if samples > 0:
        rng = random.Random(int(seed))
        pass_count = 0

        if use_correlation:
            mc_mode = "correlated"
            nominals = [float(row["nominal"]) for row in parsed]
            limits = [row["limits"] for row in parsed]
            active = corr_active_idx

            for _ in range(samples):
                x = list(nominals)
                if active and cov_cholesky is not None:
                    z = [rng.gauss(0.0, 1.0) for _ in active]
                    for i_sub, idx in enumerate(active):
                        delta = 0.0
                        for k in range(i_sub + 1):
                            delta += cov_cholesky[i_sub][k] * z[k]
                        x[idx] = nominals[idx] + delta

                sample_pass = True
                for i, xv in enumerate(x):
                    lo = float(limits[i]["min_allowed"])
                    hi = float(limits[i]["max_allowed"])
                    if xv < lo or xv > hi:
                        sample_pass = False
                        break
                if sample_pass:
                    pass_count += 1
        else:
            for _ in range(samples):
                sample_pass = True
                for row in parsed:
                    sigma_eff = float(row["sigma_effective"])
                    x = float(row["nominal"])
                    if sigma_eff > 0.0:
                        x = rng.gauss(float(row["nominal"]), sigma_eff)
                    limits = row["limits"]
                    if x < float(limits["min_allowed"]) or x > float(limits["max_allowed"]):
                        sample_pass = False
                        break
                if sample_pass:
                    pass_count += 1

        mc_yield = float(pass_count / max(1, samples))

    estimated_yield = mc_yield if mc_yield is not None else analytic_yield
    if estimated_yield < min_required:
        violations.append(
            f"estimated_yield={estimated_yield:.6g} below min_required_yield={min_required:.6g}"
        )

    points.extend(parsed)

    return {
        "check": "pic.layout.verification.process_yield",
        "pass": len(violations) == 0,
        "criteria": "estimated process yield exceeds min_required_yield",
        "min_required_yield": min_required,
        "analytic_yield": analytic_yield,
        "correlation": {
            "used": use_correlation,
            "matrix": corr_matrix_clean,
            "active_metric_indices": corr_active_idx,
        },
        "monte_carlo": {
            "mode": mc_mode,
            "samples": samples,
            "samples_requested": samples_requested,
            "samples_used": samples,
            "seed": int(seed),
            "estimated_yield": mc_yield,
        },
        "estimated_yield": estimated_yield,
        "points": points,
        "violations": violations,
    }


def verify_layout_signoff_bundle(
    *,
    crosstalk_budget: dict[str, Any] | None = None,
    thermal_drift: dict[str, Any] | None = None,
    bend_and_routing_loss: dict[str, Any] | None = None,
    process_variation: dict[str, Any] | None = None,
    design_rule_envelope: dict[str, Any] | None = None,
    thermal_crosstalk_matrix: dict[str, Any] | None = None,
    resonance_alignment: dict[str, Any] | None = None,
    phase_shifter_range: dict[str, Any] | None = None,
    wavelength_sweep_signoff: dict[str, Any] | None = None,
    wavelength_sweep_trace_signoff: dict[str, Any] | None = None,
    process_yield: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run a signoff bundle from any subset of core PIC verification checks.

    The bundle is backward-compatible and optional: only provided checks are
    executed. Pass criteria is strict (all included checks must pass).
    """

    requested = [
        ("crosstalk_budget", verify_crosstalk_budget, crosstalk_budget),
        ("thermal_drift", verify_thermal_drift, thermal_drift),
        ("bend_and_routing_loss", verify_bend_and_routing_loss, bend_and_routing_loss),
        ("process_variation", verify_process_variation, process_variation),
        ("design_rule_envelope", verify_design_rule_envelope, design_rule_envelope),
        ("thermal_crosstalk_matrix", verify_thermal_crosstalk_matrix, thermal_crosstalk_matrix),
        ("resonance_alignment", verify_resonance_alignment, resonance_alignment),
        ("phase_shifter_range", verify_phase_shifter_range, phase_shifter_range),
        ("wavelength_sweep_signoff", verify_wavelength_sweep_signoff, wavelength_sweep_signoff),
        (
            "wavelength_sweep_trace_signoff",
            verify_wavelength_sweep_signoff_from_trace,
            wavelength_sweep_trace_signoff,
        ),
        ("process_yield", estimate_process_yield, process_yield),
    ]

    if not any(cfg is not None for _, _, cfg in requested):
        raise ValueError("at least one check request must be provided")

    checks: list[dict[str, Any]] = []
    violations: list[str] = []

    for label, fn, cfg in requested:
        if cfg is None:
            continue
        if not isinstance(cfg, dict):
            checks.append(
                {
                    "check": f"pic.layout.verification.{label}",
                    "pass": False,
                    "violations": [f"invalid request for {label}: expected object"],
                    "points": [],
                }
            )
            violations.append(f"{label}: invalid request object")
            continue

        try:
            result = fn(**cfg)
        except Exception as exc:  # defensive: preserve a complete signoff output
            result = {
                "check": f"pic.layout.verification.{label}",
                "pass": False,
                "violations": [f"internal error: {exc}"],
                "points": [],
            }
        checks.append(result)
        for v in result.get("violations", []):
            violations.append(f"{label}: {v}")

    total = len(checks)
    pass_count = sum(1 for c in checks if bool(c.get("pass")))

    return {
        "check": "pic.layout.verification.signoff_bundle",
        "pass": pass_count == total,
        "criteria": "all included checks must pass",
        "summary": {
            "total_checks": total,
            "passed_checks": pass_count,
            "failed_checks": total - pass_count,
            "score": float(pass_count / max(1, total)),
        },
        "checks": checks,
        "violations": violations,
    }
