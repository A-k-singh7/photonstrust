"""Orbit pass envelope execution (v0.1).

This module intentionally models a pass as an explicit envelope (samples over time),
not an orbit propagator.
"""

from __future__ import annotations

import platform
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import json

from photonstrust.channels.free_space import total_free_space_efficiency
from photonstrust.config import (
    apply_channel_defaults,
    apply_detector_defaults,
    apply_source_defaults,
    apply_timing_defaults,
    resolve_band_wavelength,
)
from photonstrust.qkd import compute_point
from photonstrust.utils import hash_dict


@dataclass(frozen=True)
class OrbitPassSample:
    t_s: float
    distance_km: float
    elevation_deg: float
    background_counts_cps: float | None
    day_night: str | None


def simulate_orbit_pass(config: dict) -> dict:
    """Simulate an orbit/free-space pass envelope described in config['orbit_pass']."""

    orbit_pass = config.get("orbit_pass")
    if not isinstance(orbit_pass, dict):
        raise ValueError("orbit_pass config block is required")

    pass_id = str(orbit_pass.get("id", "")).strip()
    if not pass_id:
        raise ValueError("orbit_pass.id is required")

    band = str(orbit_pass.get("band", "")).strip()
    if not band:
        raise ValueError("orbit_pass.band is required")

    wavelength_nm = resolve_band_wavelength(band, orbit_pass.get("wavelength_nm"))
    dt_s = float(orbit_pass.get("dt_s", 0.0))
    if dt_s <= 0.0:
        raise ValueError("orbit_pass.dt_s must be > 0")

    samples = _parse_samples(orbit_pass.get("samples"))
    if not samples:
        raise ValueError("orbit_pass.samples must be non-empty")

    execution_mode = str(orbit_pass.get("execution_mode", config.get("execution_mode", "preview")) or "preview").strip().lower()
    if execution_mode not in {"preview", "certification"}:
        execution_mode = "preview"

    clear_fraction = 1.0
    availability_cfg = orbit_pass.get("availability")
    explicit_availability = False
    if availability_cfg is not None:
        if not isinstance(availability_cfg, dict):
            raise ValueError("orbit_pass.availability must be an object when provided")
        if "clear_fraction" in availability_cfg:
            explicit_availability = True
            raw_clear_fraction = availability_cfg.get("clear_fraction")
            if raw_clear_fraction is None:
                raise ValueError("orbit_pass.availability.clear_fraction must be a number")
            try:
                clear_fraction = float(raw_clear_fraction)
            except Exception as exc:
                raise ValueError("orbit_pass.availability.clear_fraction must be a number") from exc
            if not (0.0 <= clear_fraction <= 1.0):
                raise ValueError("orbit_pass.availability.clear_fraction must be within [0, 1]")

    base_source = apply_source_defaults(config.get("source", {}))
    base_channel = apply_channel_defaults(config.get("channel", {}), band)
    if str(base_channel.get("model", "fiber")).lower() != "free_space":
        raise ValueError("orbit_pass requires channel.model=free_space")
    base_detector = apply_detector_defaults(config.get("detector", {}), band)
    base_timing = apply_timing_defaults(config.get("timing", {}))
    base_protocol = config.get("protocol", {}) or {}
    base_uncertainty = config.get("uncertainty", {}) or {}
    finite_key_plan = _build_orbit_finite_key_plan(
        config=config,
        orbit_pass=orbit_pass,
        samples=samples,
        dt_s=dt_s,
        source=base_source,
    )

    background_model = str(
        orbit_pass.get("background_model", base_channel.get("background_model", "fixed")) or "fixed"
    ).strip().lower()
    if background_model not in {"fixed", "radiance_proxy"}:
        raise ValueError("orbit_pass.background_model must be 'fixed' or 'radiance_proxy'")
    base_day_night = str(
        orbit_pass.get("background_day_night", base_channel.get("background_day_night", "night")) or "night"
    ).strip().lower()
    if base_day_night not in {"day", "night"}:
        base_day_night = "night"

    cases_cfg = orbit_pass.get("cases")
    cases = _normalize_cases(cases_cfg)

    t0 = time.perf_counter()
    case_results = []
    for case in cases:
        case_id = case["id"]
        label = case.get("label")
        channel_overrides = dict(case.get("channel_overrides", {}) or {})

        effective_channel = dict(base_channel)
        bg_scale = float(channel_overrides.pop("background_counts_cps_scale", 1.0) or 1.0)
        effective_channel["background_model"] = background_model
        effective_channel["background_day_night"] = base_day_night
        for k, v in channel_overrides.items():
            effective_channel[k] = v

        points = []
        for s in samples:
            channel_cfg = dict(effective_channel)
            channel_cfg["elevation_deg"] = float(s.elevation_deg)
            channel_cfg["background_counts_cps_scale"] = max(0.0, float(bg_scale))
            if s.day_night in {"day", "night"}:
                channel_cfg["background_day_night"] = s.day_night
            if s.background_counts_cps is not None:
                channel_cfg["background_model"] = "fixed"
                channel_cfg["background_counts_cps"] = max(0.0, float(s.background_counts_cps) * bg_scale)
            elif str(channel_cfg.get("background_model", "fixed")).strip().lower() == "fixed":
                channel_cfg["background_counts_cps"] = max(
                    0.0,
                    float(channel_cfg.get("background_counts_cps", 0.0) or 0.0) * max(0.0, float(bg_scale)),
                )

            # Compute diagnostics and point performance.
            diag = total_free_space_efficiency(
                distance_km=float(s.distance_km),
                wavelength_nm=float(wavelength_nm),
                channel_cfg=channel_cfg,
            )
            scenario = {
                "scenario_id": pass_id,
                "band": band,
                "wavelength_nm": float(wavelength_nm),
                "distances_km": [float(s.distance_km)],
                "source": base_source,
                "channel": channel_cfg,
                "detector": base_detector,
                "timing": base_timing,
                "protocol": base_protocol,
                "uncertainty": base_uncertainty,
                "finite_key": dict(finite_key_plan["scenario_finite_key"]),
            }
            r = compute_point(scenario, distance_km=float(s.distance_km))

            points.append(
                {
                    "t_s": float(s.t_s),
                    "distance_km": float(s.distance_km),
                    "elevation_deg": float(s.elevation_deg),
                    "background_counts_cps": float(diag.get("background_counts_cps", 0.0) or 0.0),
                    "background_model": str(diag.get("background_model", "fixed") or "fixed"),
                    "background_day_night": str(diag.get("background_day_night", "night") or "night"),
                    "background_uncertainty_cps": dict(diag.get("background_uncertainty_cps", {}) or {}),
                    "qkd": {
                        "key_rate_bps": float(r.key_rate_bps),
                        "entanglement_rate_hz": float(r.entanglement_rate_hz),
                        "qber_total": float(r.qber_total),
                        "fidelity": float(r.fidelity),
                        "loss_db": float(r.loss_db),
                        "finite_key_enabled": bool(r.finite_key_enabled),
                        "finite_key_penalty": float(r.finite_key_penalty),
                        "finite_key_epsilon": float(r.finite_key_epsilon),
                        "privacy_term_effective": float(r.privacy_term_effective),
                    },
                    "channel_diag": diag,
                }
            )

        summary = _summarize(
            points,
            dt_s=dt_s,
            clear_fraction=clear_fraction,
            finite_key_summary=finite_key_plan["summary"],
        )
        case_results.append(
            {
                "case_id": case_id,
                "label": label,
                "effective_channel": effective_channel,
                "points": points,
                "summary": summary,
            }
        )

    elapsed_s = time.perf_counter() - t0

    standards_anchors = [
        {
            "id": "itu_r_p1814",
            "title": "ITU-R P.1814 (terrestrial FSO attenuation prediction methods)",
            "url": "https://www.itu.int/rec/R-REC-P.1814/en",
        },
        {
            "id": "itu_r_p1817",
            "title": "ITU-R P.1817 (terrestrial FSO availability prediction methods)",
            "url": "https://www.itu.int/rec/R-REC-P.1817/en",
        },
        {
            "id": "ccsds_141_11_o_1",
            "title": "CCSDS 141.11-O-1 (Optical High Data Rate Communication - 1064 nm)",
            "url": "https://public.ccsds.org/Pubs/141x11o1.pdf",
        },
    ]

    availability_note = (
        f"Availability assumption: clear_fraction={clear_fraction} "
        + ("(explicit) used to compute expected_total_keys_bits." if explicit_availability else "(default).")
    )

    trust_label = _build_satellite_trust_label(
        mode=execution_mode,
        config=config,
        samples=samples,
        finite_key_summary=finite_key_plan["summary"],
    )

    pass_duration_s = _pass_duration_s(samples, dt_s)

    return {
        "schema_version": "0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pass_id": pass_id,
        "band": band,
        "wavelength_nm": float(wavelength_nm),
        "dt_s": float(dt_s),
        "availability": {
            "model": "clear_fraction",
            "clear_fraction": float(clear_fraction),
            "explicit": bool(explicit_availability),
        },
        "standards_anchors": standards_anchors,
        "pass_metadata": {
            "n_samples": len(samples),
            "sample_time_span_s": float(max(s.t_s for s in samples) - min(s.t_s for s in samples)) if samples else 0.0,
            "pass_duration_s": float(pass_duration_s),
            "cases": [c["id"] for c in cases],
            "elapsed_s": float(elapsed_s),
        },
        "provenance": {
            "config_hash": hash_dict(config),
            "photonstrust_version": _photonstrust_version(),
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
        "assumptions": {
            "model": "pass_envelope_samples",
            "notes": [
                "This v0.1 OrbitVerify layer treats a pass as explicit samples (dt_s) rather than orbit propagation.",
                "Free-space channel model uses airmass proxy and simple pointing/turbulence proxies (see channels/free_space.py).",
                f"Background model: {background_model} (default day/night: {base_day_night}).",
                "Finite-key pass budgeting is enforced for orbit-pass runs; claims are pass-duration constrained.",
                f"Trust mode: {trust_label['mode']} ({trust_label['label']}).",
                availability_note,
                "Standards anchors are provided for conceptual mapping only (not a compliance claim).",
            ],
        },
        "trust_label": trust_label,
        "finite_key": dict(finite_key_plan["summary"]),
        "cases": case_results,
    }


def run_orbit_pass_from_config(config: dict, output_root: Path) -> dict:
    """Run orbit pass simulation and write artifacts under output_root."""

    results = simulate_orbit_pass(config)
    pass_id = results["pass_id"]
    band = results["band"]
    out_dir = Path(output_root) / pass_id / band
    out_dir.mkdir(parents=True, exist_ok=True)

    results_path = out_dir / "orbit_pass_results.json"
    results_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    html_path = out_dir / "orbit_pass_report.html"
    html_path.write_text(_render_orbit_pass_html(results), encoding="utf-8")

    return {"output_dir": str(out_dir), "results_path": str(results_path), "report_html_path": str(html_path)}


def _render_orbit_pass_html(results: dict) -> str:
    pass_id = results.get("pass_id", "")
    band = results.get("band", "")
    dt_s = results.get("dt_s", "")
    wl = results.get("wavelength_nm", "")
    cases = results.get("cases", []) or []
    availability = results.get("availability", {}) or {}
    clear_fraction = availability.get("clear_fraction")
    trust_label = results.get("trust_label", {}) or {}
    anchors = results.get("standards_anchors", []) or []

    rows = []
    for case in cases:
        s = case.get("summary", {}) or {}
        rows.append(
            "<tr>"
            f"<td>{case.get('case_id','')}</td>"
            f"<td>{case.get('label') or ''}</td>"
            f"<td>{s.get('total_keys_bits','')}</td>"
            f"<td>{s.get('expected_total_keys_bits','')}</td>"
            f"<td>{s.get('avg_key_rate_bps','')}</td>"
            f"<td>{s.get('min_key_rate_bps','')}</td>"
            f"<td>{s.get('max_key_rate_bps','')}</td>"
            f"<td>{s.get('min_loss_db','')}</td>"
            f"<td>{s.get('max_loss_db','')}</td>"
            f"<td>{s.get('avg_channel_outage_probability','')}</td>"
            f"<td>{s.get('max_channel_outage_probability','')}</td>"
            "</tr>"
        )

    case_table = "\n".join(rows) if rows else "<tr><td colspan=\"11\">No cases</td></tr>"
    assumptions = results.get("assumptions", {}) or {}
    prov = results.get("provenance", {}) or {}
    notes = assumptions.get("notes", []) or []
    notes_html = "".join([f"<li>{_escape(str(n))}</li>" for n in notes])

    anchor_rows = []
    for a in anchors:
        if not isinstance(a, dict):
            continue
        title = str(a.get("title", "")).strip() or str(a.get("id", "")).strip()
        url = str(a.get("url", "")).strip()
        if url:
            anchor_rows.append(f"<li><a href=\"{_escape(url)}\">{_escape(title)}</a></li>")
        elif title:
            anchor_rows.append(f"<li>{_escape(title)}</li>")
    anchors_html = "\n".join(anchor_rows) if anchor_rows else "<li>No anchors</li>"

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>PhotonTrust Orbit Pass Report</title>
  <style>
    body {{
      font-family: "IBM Plex Sans", "Segoe UI", Tahoma, sans-serif;
      margin: 32px;
      color: #1b1b1b;
      background: linear-gradient(140deg, #f5f7fb 0%, #eef3f7 60%, #f9fafc 100%);
    }}
    h1 {{ margin: 0 0 8px 0; }}
    .subtle {{ color: #5e6a75; margin: 0 0 18px 0; }}
    .panel {{
      background: #ffffff;
      border: 1px solid #d8dee4;
      border-radius: 12px;
      padding: 16px;
      box-shadow: 0 6px 16px rgba(15, 23, 42, 0.06);
      margin-bottom: 16px;
    }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ text-align: left; padding: 8px; border-bottom: 1px solid #e7ecf1; }}
    th {{ color: #0b4f6c; font-weight: 700; }}
    code {{ background: #f3f5f7; padding: 2px 6px; border-radius: 6px; }}
  </style>
</head>
  <body>
  <h1>PhotonTrust Orbit Pass Report</h1>
  <p class="subtle">pass_id: <code>{_escape(str(pass_id))}</code> | band: <code>{_escape(str(band))}</code> | wavelength_nm: <code>{_escape(str(wl))}</code> | dt_s: <code>{_escape(str(dt_s))}</code> | clear_fraction: <code>{_escape(str(clear_fraction))}</code></p>

  <div class="panel">
    <h2>Case Summary</h2>
    <table>
      <thead>
        <tr>
          <th>case_id</th>
          <th>label</th>
          <th>total_keys_bits</th>
          <th>expected_total_keys_bits</th>
          <th>avg_key_rate_bps</th>
          <th>min_key_rate_bps</th>
          <th>max_key_rate_bps</th>
          <th>min_loss_db</th>
          <th>max_loss_db</th>
          <th>avg_channel_outage_probability</th>
          <th>max_channel_outage_probability</th>
        </tr>
      </thead>
      <tbody>
        {case_table}
      </tbody>
    </table>
  </div>

  <div class="panel">
    <h2>Trust Label</h2>
    <p>mode: <code>{_escape(str(trust_label.get("mode", "")))}</code></p>
    <p>label: <code>{_escape(str(trust_label.get("label", "")))}</code></p>
    <p>regime: <code>{_escape(str(trust_label.get("regime", "")))}</code></p>
    <p>caveats:</p>
    <ul>
      {"".join([f"<li>{_escape(str(c))}</li>" for c in (trust_label.get("caveats") or [])])}
    </ul>
  </div>

  <div class="panel">
    <h2>Assumptions</h2>
    <ul>
      {notes_html}
    </ul>
  </div>

  <div class="panel">
    <h2>Anchors (references)</h2>
    <p class="subtle">These references are provided as conceptual anchors, not as a standards compliance claim.</p>
    <ul>
      {anchors_html}
    </ul>
  </div>

  <div class="panel">
    <h2>Provenance</h2>
    <p>config_hash: <code>{_escape(str(prov.get("config_hash","")))}</code></p>
    <p>photonstrust_version: <code>{_escape(str(prov.get("photonstrust_version","")))}</code></p>
    <p>python: <code>{_escape(str(prov.get("python","")))}</code></p>
    <p>platform: <code>{_escape(str(prov.get("platform","")))}</code></p>
  </div>
</body>
</html>
"""


def _escape(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _parse_samples(samples_cfg) -> list[OrbitPassSample]:
    if not isinstance(samples_cfg, list):
        return []
    out: list[OrbitPassSample] = []
    for item in samples_cfg:
        if not isinstance(item, dict):
            continue
        raw_bg = item.get("background_counts_cps")
        bg = None if raw_bg is None else float(raw_bg)
        day_night = str(item.get("day_night", "")).strip().lower() or None
        if day_night not in {"day", "night"}:
            day_night = None
        out.append(
            OrbitPassSample(
                t_s=float(item.get("t_s", 0.0)),
                distance_km=float(item.get("distance_km", 0.0)),
                elevation_deg=float(item.get("elevation_deg", 45.0)),
                background_counts_cps=bg,
                day_night=day_night,
            )
        )
    out.sort(key=lambda s: float(s.t_s))
    return out


def _normalize_cases(cases_cfg) -> list[dict]:
    if isinstance(cases_cfg, list) and cases_cfg:
        out = []
        for item in cases_cfg:
            if not isinstance(item, dict):
                continue
            cid = str(item.get("id", "")).strip()
            if not cid:
                raise ValueError("orbit_pass.cases[].id is required")
            out.append(
                {
                    "id": cid,
                    "label": item.get("label"),
                    "channel_overrides": dict(item.get("channel_overrides", {}) or {}),
                }
            )
        return out

    return [{"id": "median", "label": "Median", "channel_overrides": {}}]


def _summarize(
    points: list[dict],
    *,
    dt_s: float,
    clear_fraction: float = 1.0,
    finite_key_summary: dict | None = None,
) -> dict:
    key_rates = [float(p["qkd"]["key_rate_bps"]) for p in points]
    losses = [float(p["qkd"]["loss_db"]) for p in points]
    outages = [float((p.get("channel_diag", {}) or {}).get("outage_probability", 0.0) or 0.0) for p in points]
    backgrounds = [float(p.get("background_counts_cps", 0.0) or 0.0) for p in points]
    background_sigmas = [
        float(((p.get("background_uncertainty_cps", {}) or {}).get("sigma", 0.0) or 0.0))
        for p in points
    ]
    total_keys = float(sum(key_rates) * float(dt_s))
    if key_rates:
        avg = float(sum(key_rates) / len(key_rates))
        min_k = float(min(key_rates))
        max_k = float(max(key_rates))
    else:
        avg = min_k = max_k = 0.0
    if losses:
        min_l = float(min(losses))
        max_l = float(max(losses))
    else:
        min_l = max_l = 0.0

    if outages:
        avg_out = float(sum(outages) / len(outages))
        max_out = float(max(outages))
    else:
        avg_out = 0.0
        max_out = 0.0

    if backgrounds:
        avg_bg = float(sum(backgrounds) / len(backgrounds))
        min_bg = float(min(backgrounds))
        max_bg = float(max(backgrounds))
    else:
        avg_bg = min_bg = max_bg = 0.0

    if background_sigmas:
        avg_bg_sigma = float(sum(background_sigmas) / len(background_sigmas))
        max_bg_sigma = float(max(background_sigmas))
    else:
        avg_bg_sigma = 0.0
        max_bg_sigma = 0.0

    if points:
        first = points[0]
        background_model = str(first.get("background_model", "fixed") or "fixed")
        background_day_night = str(first.get("background_day_night", "night") or "night")
    else:
        background_model = "fixed"
        background_day_night = "night"

    cf = float(clear_fraction)
    expected_total_keys = float(total_keys) * cf

    return {
        "total_keys_bits": total_keys,
        "expected_total_keys_bits": expected_total_keys,
        "clear_fraction": cf,
        "avg_key_rate_bps": avg,
        "min_key_rate_bps": min_k,
        "max_key_rate_bps": max_k,
        "min_loss_db": min_l,
        "max_loss_db": max_l,
        "avg_channel_outage_probability": avg_out,
        "max_channel_outage_probability": max_out,
        "background_model": background_model,
        "background_day_night": background_day_night,
        "avg_background_counts_cps": avg_bg,
        "min_background_counts_cps": min_bg,
        "max_background_counts_cps": max_bg,
        "avg_background_uncertainty_sigma_cps": avg_bg_sigma,
        "max_background_uncertainty_sigma_cps": max_bg_sigma,
        "finite_key": dict(finite_key_summary or {}),
    }


def _build_satellite_trust_label(
    *,
    mode: str,
    config: dict,
    samples: list[OrbitPassSample],
    finite_key_summary: dict | None = None,
) -> dict:
    channel = (config or {}).get("channel", {}) or {}
    elevations = [float(s.elevation_deg) for s in samples]
    distances = [float(s.distance_km) for s in samples]
    elevation_range = [float(min(elevations)) if elevations else 0.0, float(max(elevations)) if elevations else 0.0]
    distance_range = [float(min(distances)) if distances else 0.0, float(max(distances)) if distances else 0.0]

    turbulence_model = str(channel.get("turbulence_model", "deterministic") or "deterministic")
    pointing_model = str(channel.get("pointing_model", "deterministic") or "deterministic")
    path_model = str(channel.get("atmosphere_path_model", "effective_thickness") or "effective_thickness")
    thickness_km = float(channel.get("atmosphere_effective_thickness_km", 20.0) or 20.0)
    background_model = str(channel.get("background_model", "fixed") or "fixed")

    caveats: list[str] = []
    if mode == "preview":
        caveats.append("Preview mode is non-certification and intended for rapid tradeoff exploration.")
    if turbulence_model in {"deterministic", "none"}:
        caveats.append("Turbulence is deterministic; outage realism may be understated.")
    if pointing_model in {"deterministic", "none"}:
        caveats.append("Pointing is deterministic; tracking outage behavior is approximated.")
    if path_model in {"slant_range", "legacy_slant_range"}:
        caveats.append("Legacy slant-range atmospheric path model is active.")
    if background_model == "fixed":
        caveats.append("Background is fixed-input unless sample overrides are used.")
    if finite_key_summary and not bool(finite_key_summary.get("requested_enabled", True)):
        caveats.append("Finite-key was requested disabled but enforced for orbit-pass budgeting semantics.")

    regime = "preview"
    if mode == "certification" and turbulence_model not in {"deterministic", "none"} and pointing_model not in {"deterministic", "none"}:
        regime = "certification_candidate"

    return {
        "mode": str(mode),
        "label": "preview" if mode == "preview" else "certification",
        "regime": regime,
        "applicability_bounds": {
            "distance_km_range": distance_range,
            "elevation_deg_range": elevation_range,
            "atmosphere_path_model": path_model,
            "atmosphere_effective_thickness_km": float(thickness_km),
            "turbulence_model": turbulence_model,
            "pointing_model": pointing_model,
            "background_model": background_model,
            "finite_key_enforced": bool((finite_key_summary or {}).get("enforced_for_orbit_pass", True)),
        },
        "caveats": caveats,
    }


def _build_orbit_finite_key_plan(
    *,
    config: dict,
    orbit_pass: dict,
    samples: list[OrbitPassSample],
    dt_s: float,
    source: dict,
) -> dict:
    cfg: dict = {}
    if isinstance(config.get("finite_key"), dict):
        cfg.update(config.get("finite_key") or {})
    if isinstance(orbit_pass.get("finite_key"), dict):
        cfg.update(orbit_pass.get("finite_key") or {})

    requested_enabled = bool(cfg.get("enabled", True))
    pe_fraction = _clamp(float(cfg.get("parameter_estimation_fraction", 0.1) or 0.1), 0.0, 0.9)

    security_epsilon = _safe_positive(cfg.get("security_epsilon"), default=1.0e-10)
    epsilon_correctness = _safe_positive(cfg.get("epsilon_correctness"), default=0.20 * security_epsilon)
    epsilon_secrecy = _safe_positive(cfg.get("epsilon_secrecy"), default=0.40 * security_epsilon)
    epsilon_parameter_estimation = _safe_positive(
        cfg.get("epsilon_parameter_estimation"),
        default=0.15 * security_epsilon,
    )
    epsilon_error_correction = _safe_positive(cfg.get("epsilon_error_correction"), default=0.15 * security_epsilon)
    epsilon_privacy_amplification = _safe_positive(
        cfg.get("epsilon_privacy_amplification"),
        default=0.10 * security_epsilon,
    )
    epsilon_total = float(
        epsilon_correctness
        + epsilon_secrecy
        + epsilon_parameter_estimation
        + epsilon_error_correction
        + epsilon_privacy_amplification
    )
    security_epsilon_effective = max(security_epsilon, epsilon_total)

    rep_rate_hz = max(1.0, float(source.get("rep_rate_mhz", 100.0) or 100.0) * 1e6)
    pass_duration_s = _pass_duration_s(samples, dt_s)
    pass_duty_cycle = _clamp(float(cfg.get("pass_duty_cycle", 1.0) or 1.0), 1e-6, 1.0)
    detection_probability = _clamp(float(cfg.get("detection_probability", 1.0e-3) or 1.0e-3), 1e-12, 1.0)
    signals_per_pass_budget = max(1.0, rep_rate_hz * pass_duration_s * pass_duty_cycle * detection_probability)

    configured_signals_per_block = None
    if cfg.get("signals_per_block") is not None:
        configured_signals_per_block = max(1.0, float(cfg.get("signals_per_block") or 1.0))
    max_signals_per_block = None
    if cfg.get("max_signals_per_block") is not None:
        max_signals_per_block = max(1.0, float(cfg.get("max_signals_per_block") or 1.0))

    effective_signals_per_block = (
        configured_signals_per_block if configured_signals_per_block is not None else signals_per_pass_budget
    )
    effective_signals_per_block = min(effective_signals_per_block, signals_per_pass_budget)
    if max_signals_per_block is not None:
        effective_signals_per_block = min(effective_signals_per_block, max_signals_per_block)
    effective_signals_per_block = max(1.0, float(effective_signals_per_block))

    scenario_finite_key = {
        "enabled": True,
        "signals_per_block": float(effective_signals_per_block),
        "security_epsilon": float(security_epsilon_effective),
        "parameter_estimation_fraction": float(pe_fraction),
    }

    return {
        "scenario_finite_key": scenario_finite_key,
        "summary": {
            "enabled": True,
            "requested_enabled": bool(requested_enabled),
            "enforced_for_orbit_pass": True,
            "rep_rate_hz": float(rep_rate_hz),
            "pass_duration_s": float(pass_duration_s),
            "pass_duty_cycle": float(pass_duty_cycle),
            "detection_probability": float(detection_probability),
            "signals_per_pass_budget": float(signals_per_pass_budget),
            "configured_signals_per_block": (
                None if configured_signals_per_block is None else float(configured_signals_per_block)
            ),
            "max_signals_per_block": None if max_signals_per_block is None else float(max_signals_per_block),
            "effective_signals_per_block": float(effective_signals_per_block),
            "security_epsilon": float(security_epsilon_effective),
            "parameter_estimation_fraction": float(pe_fraction),
            "epsilon_correctness": float(epsilon_correctness),
            "epsilon_secrecy": float(epsilon_secrecy),
            "epsilon_parameter_estimation": float(epsilon_parameter_estimation),
            "epsilon_error_correction": float(epsilon_error_correction),
            "epsilon_privacy_amplification": float(epsilon_privacy_amplification),
            "epsilon_total": float(epsilon_total),
        },
    }


def _pass_duration_s(samples: list[OrbitPassSample], dt_s: float) -> float:
    if not samples:
        return float(max(0.0, dt_s))
    t_span = float(max(s.t_s for s in samples) - min(s.t_s for s in samples))
    return float(max(0.0, t_span + max(0.0, float(dt_s))))


def _safe_positive(value, *, default: float) -> float:
    try:
        out = float(value)
    except Exception:
        out = float(default)
    if out <= 0.0:
        out = float(default)
    return float(out)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(float(value), hi))


def _photonstrust_version() -> str | None:
    try:
        from importlib.metadata import version

        return version("photonstrust")
    except Exception:
        try:
            root = Path(__file__).resolve().parents[2]
            pyproject = root / "pyproject.toml"
            if not pyproject.exists():
                return None
            for line in pyproject.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("version"):
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        return parts[1].strip().strip("\"'")
        except Exception:
            return None
    return None
