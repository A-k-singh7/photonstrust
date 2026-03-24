"""End-to-end threat assessment engine."""

from __future__ import annotations

import json
from pathlib import Path

from photonstrust.security.attacks.blinding import evaluate_blinding_attack
from photonstrust.security.attacks.dead_time import evaluate_dead_time_attack
from photonstrust.security.attacks.pns import evaluate_pns_attack
from photonstrust.security.attacks.time_shift import evaluate_time_shift_attack
from photonstrust.security.attacks.trojan_horse import evaluate_trojan_horse_attack
from photonstrust.security.countermeasures import (
    evaluate_countermeasure_active_dead_time,
    evaluate_countermeasure_decoy_state,
    evaluate_countermeasure_efficiency_equalization,
    evaluate_countermeasure_optical_isolator,
    evaluate_countermeasure_random_gating,
    evaluate_countermeasure_watchdog,
)
from photonstrust.security.types import (
    CountermeasureEffectiveness,
    ThreatAssessmentResult,
    VulnerabilityAssessment,
)

_CATALOG_PATH = Path(__file__).parent / "data" / "attack_catalog.json"


def _load_catalog() -> dict:
    return json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))


def run_threat_assessment(
    scenario: dict,
    *,
    qkd_result: dict | None = None,
) -> ThreatAssessmentResult:
    """Run a full threat assessment for a QKD scenario.

    Parameters
    ----------
    scenario : dict
        Scenario description with keys such as ``protocol_name``,
        ``detector_class``, ``source``, ``detector``, ``optics``, and
        ``countermeasures``.
    qkd_result : dict | None
        Optional QKD simulation result for additional context.
    """
    catalog = _load_catalog()

    protocol_name: str = scenario.get("protocol_name", "BB84_DECOY")
    detector_class: str = scenario.get("detector_class", "snspd")
    scenario_id: str = scenario.get("scenario_id", "default")

    # Source parameters
    source_cfg: dict = scenario.get("source", {})
    mu = float(source_cfg.get("mu", 0.5))
    nu = float(source_cfg.get("nu", 0.1))
    omega = float(source_cfg.get("omega", 0.001))
    eta_channel = float(source_cfg.get("eta_channel", 0.1))
    decoy_enabled = bool(source_cfg.get("decoy_enabled", "DECOY" in protocol_name))

    # Detector parameters
    detector_cfg: dict = scenario.get("detector", {})
    dead_time_ns = float(detector_cfg.get("dead_time_ns", 50.0))
    rep_rate_hz = float(detector_cfg.get("rep_rate_hz", scenario.get("rep_rate_hz", 1e9)))

    # Optics parameters
    optics_cfg: dict = scenario.get("optics", {})
    isolator_attenuation_db = float(optics_cfg.get("isolator_attenuation_db", 40.0))
    filter_bandwidth_nm = float(optics_cfg.get("filter_bandwidth_nm", 1.0))
    modulator_extinction_ratio_db = float(optics_cfg.get("modulator_extinction_ratio_db", 30.0))

    # Countermeasure flags
    cm_cfg: dict = scenario.get("countermeasures", {})

    # ---- Run all attack evaluators ----
    vulnerabilities: list[VulnerabilityAssessment] = []

    # 1. PNS attack
    attack_info = catalog["attacks"].get("pns", {})
    if protocol_name in attack_info.get("applicable_protocols", []):
        vuln = evaluate_pns_attack(
            mu=mu,
            eta_channel=eta_channel,
            protocol_name=protocol_name,
            decoy_enabled=decoy_enabled,
            nu=nu,
            omega=omega,
        )
        vulnerabilities.append(vuln)

    # 2. Blinding attack
    attack_info = catalog["attacks"].get("blinding", {})
    if protocol_name in attack_info.get("applicable_protocols", []):
        vuln = evaluate_blinding_attack(
            detector_class=detector_class,
            detector_cfg=detector_cfg,
        )
        vulnerabilities.append(vuln)

    # 3. Trojan Horse Attack
    attack_info = catalog["attacks"].get("trojan_horse", {})
    if protocol_name in attack_info.get("applicable_protocols", []):
        vuln = evaluate_trojan_horse_attack(
            isolator_attenuation_db=isolator_attenuation_db,
            filter_bandwidth_nm=filter_bandwidth_nm,
            modulator_extinction_ratio_db=modulator_extinction_ratio_db,
            rep_rate_hz=rep_rate_hz,
        )
        vulnerabilities.append(vuln)

    # 4. Time-shift attack
    attack_info = catalog["attacks"].get("time_shift", {})
    if protocol_name in attack_info.get("applicable_protocols", []):
        vuln = evaluate_time_shift_attack(
            detector_cfg=detector_cfg,
            efficiency_mismatch_factor=detector_cfg.get("efficiency_mismatch_factor"),
        )
        vulnerabilities.append(vuln)

    # 5. Dead-time attack
    attack_info = catalog["attacks"].get("dead_time", {})
    if protocol_name in attack_info.get("applicable_protocols", []):
        vuln = evaluate_dead_time_attack(
            dead_time_ns=dead_time_ns,
            rep_rate_hz=rep_rate_hz,
        )
        vulnerabilities.append(vuln)

    # ---- Evaluate countermeasures for applicable attacks ----
    countermeasures: list[CountermeasureEffectiveness] = []

    # Map attack_id -> best countermeasure detection_probability
    cm_best: dict[str, float] = {}

    # Decoy state CM (targets pns)
    if cm_cfg.get("decoy_state", decoy_enabled):
        cm = evaluate_countermeasure_decoy_state(mu=mu, nu=nu, omega=omega)
        countermeasures.append(cm)
        cm_best["pns"] = max(cm_best.get("pns", 0.0), cm.detection_probability)

    # Watchdog CM (targets blinding)
    if cm_cfg.get("watchdog_detector", detector_cfg.get("watchdog_enabled", False)):
        cm = evaluate_countermeasure_watchdog(detector_class=detector_class)
        countermeasures.append(cm)
        cm_best["blinding"] = max(cm_best.get("blinding", 0.0), cm.detection_probability)

    # Random gating CM (targets blinding)
    if cm_cfg.get("random_gating", detector_cfg.get("random_gating", False)):
        gate_width = float(detector_cfg.get("gate_width_ns", 1.0))
        gate_period = float(detector_cfg.get("gate_period_ns", 10.0))
        cm = evaluate_countermeasure_random_gating(
            gate_width_ns=gate_width,
            gate_period_ns=gate_period,
        )
        countermeasures.append(cm)
        cm_best["blinding"] = max(cm_best.get("blinding", 0.0), cm.detection_probability)

    # Optical isolator CM (targets trojan_horse)
    if cm_cfg.get("optical_isolator", isolator_attenuation_db > 0):
        cm = evaluate_countermeasure_optical_isolator(
            isolator_attenuation_db=isolator_attenuation_db,
        )
        countermeasures.append(cm)
        cm_best["trojan_horse"] = max(
            cm_best.get("trojan_horse", 0.0), cm.detection_probability
        )

    # Efficiency equalization CM (targets time_shift)
    if cm_cfg.get("efficiency_equalization", False):
        cm = evaluate_countermeasure_efficiency_equalization()
        countermeasures.append(cm)
        cm_best["time_shift"] = max(
            cm_best.get("time_shift", 0.0), cm.detection_probability
        )

    # Active dead-time CM (targets dead_time)
    if cm_cfg.get("active_dead_time", False):
        cm = evaluate_countermeasure_active_dead_time(dead_time_ns=dead_time_ns)
        countermeasures.append(cm)
        cm_best["dead_time"] = max(
            cm_best.get("dead_time", 0.0), cm.detection_probability
        )

    # ---- Compute overall risk score ----
    applicable_vulns = [v for v in vulnerabilities if v.applicable]
    if applicable_vulns:
        risk_terms = []
        for v in applicable_vulns:
            best_det = cm_best.get(v.attack_id, 0.0)
            risk_terms.append(v.exploitability_score * (1.0 - best_det))
        overall_risk_score = sum(risk_terms) / len(risk_terms)
    else:
        overall_risk_score = 0.0

    # Severity mapping
    if overall_risk_score > 0.6:
        overall_severity = "critical"
    elif overall_risk_score > 0.3:
        overall_severity = "high"
    elif overall_risk_score > 0.1:
        overall_severity = "medium"
    elif overall_risk_score > 0.01:
        overall_severity = "low"
    else:
        overall_severity = "none"

    # ---- Recommendations ----
    recommendations: list[str] = []
    for v in applicable_vulns:
        if v.severity in ("critical", "high"):
            if v.attack_id == "pns" and not decoy_enabled:
                recommendations.append(
                    "Enable decoy-state protocol to mitigate PNS attack"
                )
            elif v.attack_id == "blinding":
                if not detector_cfg.get("watchdog_enabled", False):
                    recommendations.append(
                        "Add watchdog detector to mitigate blinding attack"
                    )
            elif v.attack_id == "trojan_horse":
                recommendations.append(
                    "Increase optical isolator attenuation to mitigate THA"
                )
            elif v.attack_id == "time_shift":
                recommendations.append(
                    "Apply detector efficiency equalization to mitigate time-shift attack"
                )
            elif v.attack_id == "dead_time":
                recommendations.append(
                    "Enable active dead-time management to mitigate dead-time attack"
                )

    return ThreatAssessmentResult(
        scenario_id=scenario_id,
        protocol_name=protocol_name,
        detector_class=detector_class,
        vulnerabilities=vulnerabilities,
        countermeasures=countermeasures,
        overall_risk_score=overall_risk_score,
        overall_severity=overall_severity,
        recommendations=recommendations,
    )
