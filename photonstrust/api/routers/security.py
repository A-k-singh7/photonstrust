"""Security assessment API routes."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/v1/security", tags=["security"])


@router.post("/assess")
def assess_threat(payload: dict) -> dict:
    """Run a full threat assessment for the given scenario."""
    from photonstrust.security.assessment import run_threat_assessment

    try:
        result = run_threat_assessment(payload)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return result.as_dict()


@router.get("/attacks")
def list_attacks() -> dict:
    """Return the attack catalog."""
    catalog_path = (
        Path(__file__).parent.parent.parent
        / "security"
        / "data"
        / "attack_catalog.json"
    )
    if not catalog_path.exists():
        raise HTTPException(status_code=404, detail="Attack catalog not found")
    return json.loads(catalog_path.read_text(encoding="utf-8"))


@router.post("/attacks/{attack_id}/evaluate")
def evaluate_single_attack(attack_id: str, payload: dict) -> dict:
    """Evaluate a single attack by its identifier."""
    if attack_id == "pns":
        from photonstrust.security.attacks.pns import evaluate_pns_attack

        result = evaluate_pns_attack(
            mu=float(payload.get("mu", 0.5)),
            eta_channel=float(payload.get("eta_channel", 0.1)),
            protocol_name=str(payload.get("protocol_name", "BB84")),
            decoy_enabled=bool(payload.get("decoy_enabled", False)),
            nu=float(payload.get("nu", 0.0)),
            omega=float(payload.get("omega", 0.0)),
        )
    elif attack_id == "blinding":
        from photonstrust.security.attacks.blinding import evaluate_blinding_attack

        result = evaluate_blinding_attack(
            detector_class=str(payload.get("detector_class", "snspd")),
            detector_cfg=payload.get("detector_cfg", {}),
        )
    elif attack_id == "trojan_horse":
        from photonstrust.security.attacks.trojan_horse import (
            evaluate_trojan_horse_attack,
        )

        result = evaluate_trojan_horse_attack(
            isolator_attenuation_db=float(payload.get("isolator_attenuation_db", 40.0)),
            filter_bandwidth_nm=float(payload.get("filter_bandwidth_nm", 1.0)),
            modulator_extinction_ratio_db=float(
                payload.get("modulator_extinction_ratio_db", 30.0)
            ),
            rep_rate_hz=float(payload.get("rep_rate_hz", 1e9)),
        )
    elif attack_id == "time_shift":
        from photonstrust.security.attacks.time_shift import (
            evaluate_time_shift_attack,
        )

        result = evaluate_time_shift_attack(
            detector_cfg=payload.get("detector_cfg", {}),
            efficiency_mismatch_factor=payload.get("efficiency_mismatch_factor"),
        )
    elif attack_id == "dead_time":
        from photonstrust.security.attacks.dead_time import (
            evaluate_dead_time_attack,
        )

        result = evaluate_dead_time_attack(
            dead_time_ns=float(payload.get("dead_time_ns", 50.0)),
            rep_rate_hz=float(payload.get("rep_rate_hz", 1e9)),
            detector_count=int(payload.get("detector_count", 2)),
        )
    else:
        raise HTTPException(
            status_code=404, detail=f"Unknown attack_id: {attack_id}"
        )

    return result.as_dict()
