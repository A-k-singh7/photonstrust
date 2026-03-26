"""Structured protocol maturity and reliability assessment."""
from __future__ import annotations
from dataclasses import dataclass, field

@dataclass(frozen=True)
class ReliabilityCard:
    """Protocol maturity assessment card."""
    protocol_id: str
    trl: int  # Technology Readiness Level 1-9
    maturity: str  # "theoretical", "lab_demo", "field_trial", "deployed"
    max_distance_km: float
    typical_rate_at_100km_bps: float
    implementation_complexity: int  # 1-5 (1=simple, 5=very complex)
    detector_requirement: str
    security_model: str
    key_assumptions: list[str] = field(default_factory=list)

# Published TRL assignments based on Xu et al. RMP 2020, Pirandola et al. 2020
PROTOCOL_CARDS: dict[str, dict] = {
    "bb84": {
        "trl": 9,
        "maturity": "deployed",
        "max_distance_km": 421,
        "typical_rate_at_100km_bps": 1000.0,
        "implementation_complexity": 2,
        "detector_requirement": "single_photon",
        "security_model": "prepare_and_measure",
        "key_assumptions": ["trusted_source", "single_photon_or_decoy"],
    },
    "bbm92": {
        "trl": 7,
        "maturity": "lab_demo",
        "max_distance_km": 144,
        "typical_rate_at_100km_bps": 100.0,
        "implementation_complexity": 3,
        "detector_requirement": "single_photon",
        "security_model": "entanglement_based",
        "key_assumptions": ["entangled_source"],
    },
    "cv_qkd": {
        "trl": 7,
        "maturity": "field_trial",
        "max_distance_km": 202,
        "typical_rate_at_100km_bps": 500.0,
        "implementation_complexity": 3,
        "detector_requirement": "homodyne",
        "security_model": "prepare_and_measure",
        "key_assumptions": ["gaussian_modulation", "reverse_reconciliation"],
    },
    "mdi_qkd": {
        "trl": 5,
        "maturity": "lab_demo",
        "max_distance_km": 404,
        "typical_rate_at_100km_bps": 50.0,
        "implementation_complexity": 4,
        "detector_requirement": "single_photon_bsm",
        "security_model": "measurement_device_independent",
        "key_assumptions": ["untrusted_relay"],
    },
    "tf_qkd": {
        "trl": 5,
        "maturity": "lab_demo",
        "max_distance_km": 605,
        "typical_rate_at_100km_bps": 500.0,
        "implementation_complexity": 4,
        "detector_requirement": "single_photon",
        "security_model": "twin_field",
        "key_assumptions": ["phase_locking", "single_photon_interference"],
    },
    "sns_tf": {
        "trl": 4,
        "maturity": "lab_demo",
        "max_distance_km": 509,
        "typical_rate_at_100km_bps": 200.0,
        "implementation_complexity": 4,
        "detector_requirement": "single_photon",
        "security_model": "twin_field_sns",
        "key_assumptions": ["sending_or_not_sending"],
    },
    "pm_qkd": {
        "trl": 4,
        "maturity": "lab_demo",
        "max_distance_km": 502,
        "typical_rate_at_100km_bps": 100.0,
        "implementation_complexity": 4,
        "detector_requirement": "single_photon",
        "security_model": "phase_matching",
        "key_assumptions": ["phase_randomization"],
    },
    "di_qkd": {
        "trl": 3,
        "maturity": "theoretical",
        "max_distance_km": 220,
        "typical_rate_at_100km_bps": 0.1,
        "implementation_complexity": 5,
        "detector_requirement": "single_photon_high_efficiency",
        "security_model": "device_independent",
        "key_assumptions": ["bell_violation", "no_communication"],
    },
}


def build_reliability_card(protocol_id: str) -> ReliabilityCard:
    """Build a ReliabilityCard from known protocol metadata."""
    pid = protocol_id.lower().replace("-", "_")
    if pid not in PROTOCOL_CARDS:
        raise ValueError(f"Unknown protocol: {protocol_id}. Known: {sorted(PROTOCOL_CARDS.keys())}")

    info = PROTOCOL_CARDS[pid]
    return ReliabilityCard(
        protocol_id=pid,
        trl=info["trl"],
        maturity=info["maturity"],
        max_distance_km=info["max_distance_km"],
        typical_rate_at_100km_bps=info["typical_rate_at_100km_bps"],
        implementation_complexity=info["implementation_complexity"],
        detector_requirement=info["detector_requirement"],
        security_model=info["security_model"],
        key_assumptions=list(info.get("key_assumptions", [])),
    )


def compare_protocols(
    protocol_ids: list[str],
    distances_km: list[float] | None = None,
) -> dict:
    """Compare multiple protocols by their reliability cards.

    Returns a summary dict with per-protocol cards and figure of merit.
    FoM = max_distance * rate_at_100km * 1/complexity
    """
    if distances_km is None:
        distances_km = [0, 25, 50, 100, 200, 300, 500]

    cards = {}
    fom = {}
    for pid in protocol_ids:
        card = build_reliability_card(pid)
        cards[pid] = card
        fom[pid] = (card.max_distance_km * card.typical_rate_at_100km_bps
                     / max(card.implementation_complexity, 1))

    # Rank by FoM
    ranked = sorted(fom.items(), key=lambda x: -x[1])

    return {
        "cards": {pid: {
            "trl": c.trl, "maturity": c.maturity,
            "max_distance_km": c.max_distance_km,
            "rate_at_100km": c.typical_rate_at_100km_bps,
            "complexity": c.implementation_complexity,
            "security_model": c.security_model,
        } for pid, c in cards.items()},
        "figure_of_merit": dict(fom),
        "ranking": [pid for pid, _ in ranked],
        "distances_km": distances_km,
    }
