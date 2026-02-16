"""Reliability card and report generation."""

from __future__ import annotations

import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

from photonstrust.physics import get_emitter_stats
from photonstrust.qkd import QKDResult
from photonstrust.qkd_protocols.common import normalize_protocol_name
from photonstrust.utils import hash_dict


def build_reliability_card(
    scenario: dict,
    results: list[QKDResult],
    uncertainty: dict | None,
    output_dir: Path,
) -> dict:
    version = str((scenario or {}).get("reliability_card_version") or "1.0").strip().lower()
    if version in {"1.1", "v1.1", "v1_1"}:
        return _build_reliability_card_v1_1(scenario, results, uncertainty, output_dir)
    return _build_reliability_card_v1_0(scenario, results, uncertainty, output_dir)


def build_reliability_card_from_external_result(external_result: dict) -> dict:
    ext = external_result if isinstance(external_result, dict) else {}
    metrics = ext.get("metrics") if isinstance(ext.get("metrics"), dict) else {}
    sim_name = str(ext.get("simulator_name") or "external_simulator")

    key_rate = float(metrics.get("key_rate_bps", 0.0) or 0.0)
    qber = float(metrics.get("qber_total", 0.0) or 0.0)
    fidelity = float(metrics.get("fidelity_est", 0.0) or 0.0)
    ent_rate = float(metrics.get("entanglement_rate_hz", key_rate) or key_rate)
    distance_km = float(metrics.get("distance_km", 0.0) or 0.0)

    scenario = {
        "scenario_id": str((ext.get("scenario_description") or {}).get("scenario_id") or f"external_{sim_name}"),
        "band": str((ext.get("scenario_description") or {}).get("band") or "external"),
        "wavelength_nm": float((ext.get("scenario_description") or {}).get("wavelength_nm", 1550.0) or 1550.0),
        "source": {"type": "external_import"},
        "channel": {"model": "external_import", "connector_loss_db": 0.0, "fiber_loss_db_per_km": 0.0},
        "detector": {"class": "external_import", "jitter_ps_fwhm": 0.0},
        "timing": {"coincidence_window_ps": None},
        "protocol": {
            "name": str((ext.get("scenario_description") or {}).get("protocol") or "EXTERNAL_IMPORT"),
            "parameter_source": "external",
        },
        "finite_key": {"enabled": False},
        "distances_km": [distance_km],
        "evidence_quality_tier": "simulated_only",
        "benchmark_coverage": "external_import",
        "calibration_diagnostics": {"status": "external_import", "gate_pass": False},
        "reliability_card_version": "1.1",
    }

    result = QKDResult(
        distance_km=distance_km,
        entanglement_rate_hz=ent_rate,
        key_rate_bps=key_rate,
        qber_total=qber,
        fidelity=fidelity,
        p_pair=0.0,
        p_false=0.0,
        q_multi=0.0,
        q_dark=0.0,
        q_timing=0.0,
        q_misalignment=0.0,
        q_source=0.0,
        q_dark_detector=0.0,
        q_background=0.0,
        q_raman=0.0,
        background_counts_cps=0.0,
        raman_counts_cps=0.0,
        finite_key_enabled=False,
        privacy_term_asymptotic=1.0,
        privacy_term_effective=1.0,
        finite_key_penalty=0.0,
        loss_db=0.0,
        protocol_name="external_import",
    )
    card = _build_reliability_card_v1_1(scenario, [result], None, Path("."))
    card["interop"] = {
        "source": "external_import",
        "simulator_name": sim_name,
        "simulator_version": ext.get("simulator_version"),
        "external_provenance": ext.get("provenance") if isinstance(ext.get("provenance"), dict) else {},
    }
    return card


def _build_reliability_card_v1_0(
    scenario: dict,
    results: list[QKDResult],
    uncertainty: dict | None,
    output_dir: Path,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    primary = results[0]

    # Multipair emission proxy (source-side, independent of detection).
    p_multi_emission = 0.0
    src = scenario.get("source", {}) or {}
    if src.get("type") == "spdc":
        try:
            mu = float(src.get("mu", 0.0) or 0.0)
        except Exception:
            mu = 0.0
        p_multi_emission = float((mu**2) / (1.0 + mu) ** 2) if mu > 0.0 else 0.0
    elif src.get("type") == "emitter_cavity":
        try:
            p_multi_emission = float(get_emitter_stats(src).get("p_multi", 0.0) or 0.0)
        except Exception:
            p_multi_emission = 0.0
    critical_distance = next(
        (res.distance_km for res in results if res.key_rate_bps <= 0.0),
        results[-1].distance_km,
    )

    loss_fraction = 1.0 - 10 ** (-primary.loss_db / 10.0)
    fractions = {
        "loss_fraction": loss_fraction,
        "detector_fraction": primary.q_dark_detector,
        "background_fraction": primary.q_background,
        "raman_fraction": primary.q_raman,
        "multiphoton_fraction": primary.q_multi,
        "timing_fraction": primary.q_timing,
        "misalignment_fraction": primary.q_misalignment,
        "source_fraction": primary.q_source,
    }
    total_fraction = sum(fractions.values())
    if total_fraction > 0:
        for key in fractions:
            fractions[key] = fractions[key] / total_fraction

    dominant_error = sorted(fractions.items(), key=lambda item: item[1], reverse=True)[0][0]
    dominant_error = dominant_error.replace("_fraction", "")

    label, rationale = _safe_use_label(primary)
    uncertainty_summary = None
    if uncertainty:
        distance_key = results[0].distance_km
        ci = uncertainty.get(distance_key)
        if ci:
            uncertainty_summary = {
                "key_rate_ci_low": ci["low"],
                "key_rate_ci_high": ci["high"],
                "outage_probability": ci.get("outage_probability"),
            }

    connector_loss_db = float(scenario["channel"].get("connector_loss_db", 0.0))
    channel_model = str(scenario["channel"].get("model", "fiber")).lower()
    if channel_model == "free_space":
        # Reuse v1 schema fields while preserving total-loss accounting.
        fiber_loss_db = max(0.0, primary.loss_db - connector_loss_db)
    else:
        fiber_loss_db = primary.distance_km * scenario["channel"]["fiber_loss_db_per_km"]
    reproducibility = {
        "config_hash": hash_dict(scenario),
        "model_hash": None,
        "seed": scenario.get("seed", 0),
    }

    notes_lines: list[str] = []
    if channel_model == "fiber":
        co = (scenario.get("channel", {}) or {}).get("coexistence") or {}
        if bool(co.get("enabled", False)):
            coeff = co.get("raman_coeff_cps_per_km_per_mw_per_nm")
            notes_lines.append(
                "Fiber coexistence enabled: Raman noise is modeled via an attenuation-aware effective-length integral (calibration-friendly coefficient)."
            )
            if coeff is None:
                notes_lines.append("Raman coefficient is not provided (defaults may understate/overstate deployment noise).")
        else:
            notes_lines.append("Fiber coexistence disabled: no Raman term applied.")

    fk = scenario.get("finite_key") or {}
    if bool(fk.get("enabled", False)):
        notes_lines.append(
            "Finite-key enabled: secret fraction uses a monotonic penalty surrogate (not a protocol-complete composable proof)."
        )

    proto = scenario.get("protocol", {}) or {}
    proto_name_norm = normalize_protocol_name(proto.get("name"))

    if proto_name_norm in {"mdi_qkd", "mdi"}:
        notes_lines.append(
            "Protocol MDI_QKD: relay-based analytical model (Xu et al., arXiv:1305.6965) with two-decoy single-photon bounds; "
            "assumes two-arm stabilization and decoy intensity parameters in protocol (mu/nu/omega)."
        )
    elif proto_name_norm in {"pm_qkd", "pm", "tf_qkd", "tf", "twin_field", "twinfield"}:
        mu = proto.get("mu")
        m = proto.get("phase_slices")
        if m is None:
            m = proto.get("M")
        protocol_label = "TF_QKD" if proto_name_norm in {"tf_qkd", "tf", "twin_field", "twinfield"} else "PM_QKD"
        notes_lines.append(
            "Protocol {}: relay-based analytical model (Ma et al., arXiv:1805.05538 Appendix B.2) with phase slicing; "
            "parameters include mu={} and phase_slices(M)={}; strong sensitivity to phase noise/stabilization assumptions.".format(
                protocol_label,
                "unset" if mu is None else mu,
                "unset" if m is None else m,
            )
        )

    if proto.get("optical_visibility") is not None:
        notes_lines.append("Misalignment modeled via optical visibility: q_mis = (1 - visibility) / 2.")
    else:
        try:
            mis = float(proto.get("misalignment_prob", 0.0) or 0.0)
        except Exception:
            mis = 0.0
        if mis > 0.0:
            notes_lines.append("Misalignment modeled via misalignment_prob (non-zero QBER floor).")

    src = scenario.get("source", {}) or {}
    if src.get("hom_visibility") is not None or src.get("indistinguishability") is not None:
        notes_lines.append("Source indistinguishability proxy enabled (HOM visibility contributes to QBER/fidelity).")

    ch_bg = float((scenario.get("channel", {}) or {}).get("background_counts_cps", 0.0) or 0.0)
    det_bg = float((scenario.get("detector", {}) or {}).get("background_counts_cps", 0.0) or 0.0)
    if (ch_bg + det_bg) > 0.0:
        notes_lines.append("Background counts enabled (channel + detector additive count-rate model).")

    notes = "\n".join(notes_lines).strip()

    card = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scenario_id": scenario["scenario_id"],
        "band": scenario["band"],
        "wavelength_nm": scenario["wavelength_nm"],
        "evidence_quality_tier": scenario.get("evidence_quality_tier", "simulated_only"),
        "benchmark_coverage": scenario.get("benchmark_coverage", "internal_demo"),
        "calibration_diagnostics": scenario.get(
            "calibration_diagnostics",
            {
                "status": "not_calibrated",
                "gate_pass": False,
            },
        ),
        "reproducibility_artifact_uri": scenario.get("reproducibility_artifact_uri"),
        "notes": notes,
        "inputs": {
            "source": scenario["source"],
            "channel": {
                **scenario["channel"],
                "distance_km": primary.distance_km,
            },
            "detector": scenario["detector"],
            "timing": {
                **scenario["timing"],
                "coincidence_window_ps": scenario["timing"].get("coincidence_window_ps"),
            },
            "protocol": scenario["protocol"],
            "finite_key": scenario.get("finite_key"),
        },
        "derived": {
            "loss_budget": {
                "fiber_loss_db": fiber_loss_db,
                "connector_loss_db": connector_loss_db,
                "total_loss_db": fiber_loss_db + connector_loss_db,
            },
            "timing_budget": {
                "effective_jitter_ps": scenario["detector"]["jitter_ps_fwhm"],
                "false_herald_prob": primary.p_false,
            },
            "multiphoton": {
                "p_multi": p_multi_emission,
                "qber_contrib": primary.q_multi,
            },
            "dark_counts": {"qber_contrib": primary.q_dark_detector},
            "background_counts": {"qber_contrib": primary.q_background},
            "raman_counts": {"qber_contrib": primary.q_raman},
            "timing_errors": {"qber_contrib": primary.q_timing},
            "misalignment": {"qber_contrib": primary.q_misalignment},
            "source_visibility": {"qber_contrib": primary.q_source},
            "finite_key": {
                "enabled": primary.finite_key_enabled,
                "privacy_term_asymptotic": primary.privacy_term_asymptotic,
                "privacy_term_effective": primary.privacy_term_effective,
                "penalty": primary.finite_key_penalty,
            },
            "noise_counts_cps": {
                "background": primary.background_counts_cps,
                "raman": primary.raman_counts_cps,
            },
            "qber_total": primary.qber_total,
        },
        "outputs": {
            "entanglement_rate_hz": primary.entanglement_rate_hz,
            "key_rate_bps": primary.key_rate_bps,
            "fidelity_est": primary.fidelity,
            "critical_distance_km": critical_distance,
            "uncertainty": uncertainty_summary,
        },
        "error_budget": {
            "dominant_error": dominant_error,
            "error_budget": fractions,
        },
        "safe_use_label": {"label": label, "rationale": rationale},
        "reproducibility": reproducibility,
        "artifacts": {
            "plots": {},
            "report_html_path": None,
            "report_pdf_path": None,
        },
    }
    card.update(_build_trust_metadata(scenario=scenario, card=card))
    return card


def _build_reliability_card_v1_1(
    scenario: dict,
    results: list[QKDResult],
    uncertainty: dict | None,
    output_dir: Path,
) -> dict:
    card = _build_reliability_card_v1_0(scenario, results, uncertainty, output_dir)
    card["schema_version"] = "1.1"

    # Evidence tier mapping: deterministic and conservative.
    tier_raw = str((scenario or {}).get("evidence_quality_tier") or "simulated_only").strip().lower()
    tier = 0
    if tier_raw == "calibrated_lab":
        tier = 1
    elif tier_raw == "field_validated":
        tier = 2

    cal_diag = (scenario or {}).get("calibration_diagnostics")
    if isinstance(cal_diag, dict) and bool(cal_diag.get("gate_pass")):
        tier = max(tier, 1)

    label = ["Simulation-only", "Calibrated", "Validated", "Qualified"][min(3, max(0, int(tier)))]

    # Operating envelope: minimal but explicit.
    distances = [float(r.distance_km) for r in results]
    dmin = min(distances) if distances else 0.0
    dmax = max(distances) if distances else 0.0
    channel = (scenario or {}).get("channel", {}) or {}
    detector = (scenario or {}).get("detector", {}) or {}
    source = (scenario or {}).get("source", {}) or {}
    channel_model = str(channel.get("model", "fiber")).lower()

    # Canonical preset hint.
    canonical_presets: list[str] = []
    sid = str((scenario or {}).get("scenario_id") or "")
    if sid.startswith("canonical_phase41"):
        canonical_presets.append(sid)

    # Version/provenance.
    photonstrust_version = None
    try:
        from importlib.metadata import version as _pkg_version

        photonstrust_version = _pkg_version("photonstrust")
    except Exception:
        photonstrust_version = None

    dep_versions: dict[str, str | None] = {"numpy": None, "qutip": None, "qiskit": None}
    for dep in list(dep_versions.keys()):
        try:
            from importlib.metadata import version as _pkg_version

            dep_versions[dep] = _pkg_version(dep)
        except Exception:
            dep_versions[dep] = None

    repro = card.get("reproducibility")
    repro_hash = None
    if isinstance(repro, dict):
        repro_hash = repro.get("config_hash")
    config_hash = str(repro_hash or hash_dict(scenario))

    protocol = (scenario or {}).get("protocol", {}) or {}

    card["evidence_quality"] = {
        "tier": int(tier),
        "label": str(label),
        "calibration_diagnostics": cal_diag if isinstance(cal_diag, dict) else None,
        "notes": "Evidence tier is conservative and derived from scenario metadata (not a certification claim).",
    }

    card["operating_envelope"] = {
        "channel_model": channel_model,
        "distance_range_km": [float(dmin), float(dmax)],
        "wavelength_nm": float(card.get("wavelength_nm", scenario.get("wavelength_nm", 0.0)) or 0.0),
        "fiber_type": channel.get("fiber_type"),
        "detector_technology": detector.get("class"),
        "source_technology": source.get("type"),
        "notes": "Envelope fields are minimal v0.1; extend in future releases for temperature/wavelength ranges and equipment variants.",
    }

    card["benchmark_coverage_v1_1"] = {
        "canonical_presets": canonical_presets,
        "plob_bound_check": "not_assessed",
        "regression_baseline_match": None,
        "golden_report_hash_match": None,
        "notes": "Benchmark coverage is currently declarative; canonical presets indicate which fixed configs were used.",
    }

    card["standards_alignment"] = {
        "etsi_gs_qkd_016": "informational",
        "iso_iec_23837_1": "informational",
        "itu_t_y_3800": "informational",
        "nist_sp_800_57": "not_assessed",
        "notes": "Standards fields are anchors only and do not imply certification.",
    }

    card.update(_build_trust_metadata(scenario=scenario, card=card))

    card["provenance_v1_1"] = {
        "photonstrust_version": photonstrust_version,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "config_hash": config_hash,
        "dependencies": dep_versions,
    }
    return card


def _build_trust_metadata(*, scenario: dict, card: dict) -> dict:
    scenario = scenario or {}
    finite_key = scenario.get("finite_key", {}) or {}
    protocol = scenario.get("protocol", {}) or {}
    channel = scenario.get("channel", {}) or {}
    detector = scenario.get("detector", {}) or {}
    source = scenario.get("source", {}) or {}

    epsilon_total = finite_key.get("security_epsilon")
    epsilon_correctness = finite_key.get("epsilon_correctness")
    epsilon_secrecy = finite_key.get("epsilon_secrecy")
    epsilon_pe = finite_key.get("epsilon_parameter_estimation")
    epsilon_ec = finite_key.get("epsilon_error_correction")
    epsilon_pa = finite_key.get("epsilon_privacy_amplification")

    if epsilon_total is None and (epsilon_correctness is not None or epsilon_secrecy is not None):
        try:
            epsilon_total = float(epsilon_correctness or 0.0) + float(epsilon_secrecy or 0.0)
        except Exception:
            epsilon_total = None

    ci = (card.get("outputs", {}) or {}).get("uncertainty")
    channel_model = str(channel.get("model", "fiber")).lower()
    proto_norm = normalize_protocol_name(protocol.get("name"))
    decoy_assumption_default = proto_norm in {"bb84_decoy", "mdi_qkd"}

    return {
        "security_assumptions_metadata": {
            "security_model": "asymptotic_with_optional_finite_key_surrogate",
            "trusted_device_model": "trusted_source_and_detector",
            "assume_iid": bool(finite_key.get("assume_iid", True)),
            "assume_phase_randomization": bool(protocol.get("assume_phase_randomization", True)),
            "decoy_state_assumption": bool(protocol.get("decoy_states_enabled", decoy_assumption_default)),
            "notes": "Security assumptions are scenario-declared metadata and must be reviewed against deployment conditions.",
        },
        "finite_key_epsilon_ledger": {
            "enabled": bool(finite_key.get("enabled", False)),
            "signals_per_block": finite_key.get("signals_per_block"),
            "epsilon_total": epsilon_total,
            "epsilon_correctness": epsilon_correctness,
            "epsilon_secrecy": epsilon_secrecy,
            "epsilon_parameter_estimation": epsilon_pe,
            "epsilon_error_correction": epsilon_ec,
            "epsilon_privacy_amplification": epsilon_pa,
            "notes": "Unset fields indicate the scenario did not provide a full composable epsilon decomposition.",
        },
        "confidence_intervals": {
            "key_rate_bps": {
                "low": ci.get("key_rate_ci_low") if isinstance(ci, dict) else None,
                "high": ci.get("key_rate_ci_high") if isinstance(ci, dict) else None,
                "confidence_level": float((scenario.get("uncertainty", {}) or {}).get("confidence_level", 0.95) or 0.95),
                "method": str((scenario.get("uncertainty", {}) or {}).get("method", "bootstrap") or "bootstrap"),
            },
            "fidelity_est": None,
            "qber_total": None,
        },
        "model_provenance": {
            "protocol_family": str(protocol.get("name", "BBM92") or "BBM92"),
            "protocol_normalized": normalize_protocol_name(protocol.get("name")),
            "channel_model": channel_model,
            "source_model": str(source.get("type", "unknown") or "unknown"),
            "detector_model": str(detector.get("class", "unknown") or "unknown"),
            "finite_key_model": "surrogate_monotonic_penalty" if bool(finite_key.get("enabled", False)) else "asymptotic",
            "parameter_sources": {
                "source": str(source.get("parameter_source", "scenario") or "scenario"),
                "channel": str(channel.get("parameter_source", "scenario") or "scenario"),
                "detector": str(detector.get("parameter_source", "scenario") or "scenario"),
                "protocol": str(protocol.get("parameter_source", "scenario") or "scenario"),
            },
        },
    }


def write_reliability_card(card: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(card, indent=2), encoding="utf-8")


def write_html_report(card: dict, output_path: Path, plot_paths: dict | None = None) -> None:
    plot_paths = plot_paths or {}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    html = _render_html(card, plot_paths)
    output_path.write_text(html, encoding="utf-8")


def write_pdf_report(card: dict, output_path: Path) -> None:
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(f"reportlab is required for PDF export: {exc}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(output_path), pagesize=letter)
    width, height = letter
    y = height - 72

    def draw_line(text: str) -> None:
        nonlocal y
        c.drawString(72, y, text)
        y -= 16

    draw_line("PhotonTrust Reliability Card")
    draw_line(f"Scenario: {card['scenario_id']}")
    draw_line(f"Band: {card['band']} ({card['wavelength_nm']} nm)")
    draw_line(f"Key rate: {card['outputs']['key_rate_bps']:.4g} bps")
    draw_line(f"QBER: {card['derived']['qber_total']:.4f}")
    draw_line(f"Fidelity: {card['outputs']['fidelity_est']:.4f}")
    draw_line(f"Safe use: {card['safe_use_label']['label']}")
    draw_line(f"Config hash: {card['reproducibility']['config_hash']}")
    draw_line("Error budget:")
    draw_line(
        "  loss {:.3f} | detector {:.3f} | multiphoton {:.3f} | timing {:.3f}".format(
            card["error_budget"]["error_budget"]["loss_fraction"],
            card["error_budget"]["error_budget"]["detector_fraction"],
            card["error_budget"]["error_budget"]["multiphoton_fraction"],
            card["error_budget"]["error_budget"]["timing_fraction"],
        )
    )

    c.showPage()
    c.save()


def _safe_use_label(primary: QKDResult) -> tuple[str, str]:
    if primary.qber_total > 0.11 or primary.key_rate_bps <= 0:
        return "qualitative", "QBER or key rate exceeds security threshold."
    if primary.qber_total <= 0.08 and primary.key_rate_bps >= 1.0:
        return "engineering_grade", "Low QBER with stable key rate."
    return "security_target_ready", "Within typical QKD thresholds but needs validation."


def _render_html(card: dict, plot_paths: dict) -> str:
    plot_path = card["artifacts"].get("plots", {}).get("key_rate_vs_distance_path")
    plot_block = (
        f"<img src=\"{plot_path}\" alt=\"Key rate plot\" />" if plot_path else ""
    )

    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <title>PhotonTrust Reliability Card</title>
  <style>
    :root {{
      --ink: #1b1b1b;
      --muted: #5e6a75;
      --panel: #ffffff;
      --line: #d8dee4;
      --accent: #0b4f6c;
      --accent-soft: #e5f3f9;
    }}
    body {{
      font-family: "IBM Plex Sans", "Segoe UI", Tahoma, sans-serif;
      margin: 32px;
      color: var(--ink);
      background: linear-gradient(140deg, #f5f7fb 0%, #eef3f7 60%, #f9fafc 100%);
    }}
    h1 {{ margin-bottom: 6px; font-size: 28px; }}
    .subtle {{ color: var(--muted); margin-top: 0; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 20px; }}
    .card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 16px; box-shadow: 0 6px 16px rgba(15, 23, 42, 0.06); }}
    .label {{ font-weight: 600; color: var(--accent); margin-bottom: 8px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    td {{ padding: 6px 4px; vertical-align: top; }}
    td:first-child {{ color: var(--muted); width: 52%; }}
    .tag {{ display: inline-block; padding: 4px 10px; border-radius: 999px; background: var(--accent-soft); color: var(--accent); font-weight: 600; }}
    .plot {{ margin-top: 20px; text-align: center; }}
    .plot img {{ max-width: 100%; border-radius: 12px; border: 1px solid var(--line); }}
  </style>
</head>
<body>
  <h1>PhotonTrust Reliability Card</h1>
  <p class=\"subtle\">Scenario: {card["scenario_id"]} | Band: {card["band"]} | {card["wavelength_nm"]} nm</p>

  <div class=\"grid\">
    <div class=\"card\">
      <div class=\"label\">Outputs</div>
      <table>
        <tr><td>Key rate (bps)</td><td>{card["outputs"]["key_rate_bps"]:.4g}</td></tr>
        <tr><td>Entanglement rate (Hz)</td><td>{card["outputs"]["entanglement_rate_hz"]:.4g}</td></tr>
        <tr><td>QBER</td><td>{card["derived"]["qber_total"]:.4f}</td></tr>
        <tr><td>Fidelity</td><td>{card["outputs"]["fidelity_est"]:.4f}</td></tr>
        <tr><td>Critical distance (km)</td><td>{card["outputs"]["critical_distance_km"]:.1f}</td></tr>
      </table>
    </div>
    <div class=\"card\">
      <div class=\"label\">Safe Use</div>
      <span class=\"tag\">{card["safe_use_label"]["label"]}</span>
      <p>{card["safe_use_label"]["rationale"]}</p>
    </div>
    <div class=\"card\">
      <div class=\"label\">Error Budget</div>
      <table>
        <tr><td>Dominant</td><td>{card["error_budget"]["dominant_error"]}</td></tr>
        <tr><td>Loss fraction</td><td>{card["error_budget"]["error_budget"]["loss_fraction"]:.3f}</td></tr>
        <tr><td>Detector fraction</td><td>{card["error_budget"]["error_budget"]["detector_fraction"]:.3f}</td></tr>
        <tr><td>Multiphoton fraction</td><td>{card["error_budget"]["error_budget"]["multiphoton_fraction"]:.3f}</td></tr>
        <tr><td>Timing fraction</td><td>{card["error_budget"]["error_budget"]["timing_fraction"]:.3f}</td></tr>
      </table>
    </div>
    <div class=\"card\">
      <div class=\"label\">Reproducibility</div>
      <table>
        <tr><td>Config hash</td><td>{card["reproducibility"]["config_hash"]}</td></tr>
        <tr><td>Seed</td><td>{card["reproducibility"]["seed"]}</td></tr>
      </table>
    </div>
  </div>

  <div class=\"plot\">{plot_block}</div>
</body>
</html>"""
