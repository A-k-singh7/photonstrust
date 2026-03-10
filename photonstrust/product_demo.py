"""Shared product-demo fixtures and payload builders."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any


@dataclass(frozen=True)
class PilotCase:
    case_id: str
    protocol_name: str
    distance_km: float
    rep_rate_mhz: float
    pde: float
    dark_counts_cps: float
    coincidence_window_ps: float
    mu: float
    relay_fraction: float = 0.5
    nu: float = 0.05
    omega: float = 0.0
    phase_slices: int = 32
    detector_class: str = "snspd"
    source_type: str = "emitter_cavity"
    collection_efficiency: float = 0.35
    coupling_efficiency: float = 0.6


PILOT_CASES: tuple[PilotCase, ...] = (
    PilotCase(
        case_id="bbm92_metro_50km",
        protocol_name="BBM92",
        distance_km=50.0,
        rep_rate_mhz=100.0,
        pde=0.30,
        dark_counts_cps=100.0,
        coincidence_window_ps=200.0,
        mu=0.5,
    ),
    PilotCase(
        case_id="mdi_intercity_150km",
        protocol_name="MDI_QKD",
        distance_km=150.0,
        rep_rate_mhz=100.0,
        pde=0.75,
        dark_counts_cps=1.0,
        coincidence_window_ps=200.0,
        mu=0.2,
        nu=0.05,
        omega=0.0,
        relay_fraction=0.5,
        collection_efficiency=0.45,
        coupling_efficiency=0.65,
    ),
    PilotCase(
        case_id="tf_backbone_300km",
        protocol_name="TF_QKD",
        distance_km=300.0,
        rep_rate_mhz=850.0,
        pde=0.80,
        dark_counts_cps=0.1,
        coincidence_window_ps=100.0,
        mu=0.2,
        phase_slices=64,
        relay_fraction=0.5,
        collection_efficiency=0.50,
        coupling_efficiency=0.75,
    ),
)


def safe_demo_id(value: str, *, max_len: int = 64, fallback: str = "run") -> str:
    text = re.sub(r"[^a-z0-9_-]+", "_", str(value or "").strip().lower())
    text = text.strip("_-")
    if not text:
        text = fallback
    if len(text) > max_len:
        text = text[:max_len]
    if not text[0].isalnum():
        text = f"x{text}"
    while len(text) < 3:
        text += "x"
    return text


def build_pilot_graph(case: PilotCase, *, run_token: str, execution_mode: str) -> dict[str, Any]:
    protocol = str(case.protocol_name).strip().upper()
    protocol_params: dict[str, Any] = {
        "name": protocol,
        "sifting_factor": 0.5,
        "ec_efficiency": 1.16,
        "misalignment_prob": 0.01,
    }
    if protocol in {"MDI_QKD", "AMDI_QKD", "PM_QKD", "TF_QKD"}:
        protocol_params["relay_fraction"] = float(case.relay_fraction)
        protocol_params["mu"] = float(case.mu)
    if protocol in {"MDI_QKD", "AMDI_QKD"}:
        protocol_params["nu"] = float(case.nu)
        protocol_params["omega"] = float(case.omega)
    if protocol in {"PM_QKD", "TF_QKD"}:
        protocol_params["phase_slices"] = int(case.phase_slices)

    case_token = safe_demo_id(case.case_id, max_len=32, fallback="case")
    scenario_id = safe_demo_id(f"s_{case_token}_{run_token}", max_len=64, fallback="scenario")
    graph_id = safe_demo_id(f"g_{case_token}_{run_token}", max_len=64, fallback="graph")
    return {
        "schema_version": "0.1",
        "graph_id": graph_id,
        "profile": "qkd_link",
        "metadata": {
            "title": f"Pilot demo: {case.case_id}",
            "description": "Generated from shared PhotonTrust product demo fixtures.",
            "created_at": datetime.now(timezone.utc).date().isoformat(),
        },
        "scenario": {
            "id": scenario_id,
            "distance_km": {"start": float(case.distance_km), "stop": float(case.distance_km), "step": 1.0},
            "band": "c_1550",
            "wavelength_nm": 1550.0,
            "execution_mode": str(execution_mode).strip().lower(),
        },
        "uncertainty": {},
        "nodes": [
            {
                "id": "source_1",
                "kind": "qkd.source",
                "label": "Emitter",
                "params": {
                    "type": str(case.source_type),
                    "physics_backend": "analytic",
                    "rep_rate_mhz": float(case.rep_rate_mhz),
                    "collection_efficiency": float(case.collection_efficiency),
                    "coupling_efficiency": float(case.coupling_efficiency),
                    "g2_0": 0.02,
                },
            },
            {
                "id": "channel_1",
                "kind": "qkd.channel",
                "label": "Fiber",
                "params": {
                    "model": "fiber",
                    "fiber_loss_db_per_km": 0.2,
                    "connector_loss_db": 1.5,
                    "background_counts_cps": 0.0,
                },
            },
            {
                "id": "detector_1",
                "kind": "qkd.detector",
                "label": "Detector",
                "params": {
                    "class": str(case.detector_class),
                    "pde": float(case.pde),
                    "dark_counts_cps": float(case.dark_counts_cps),
                    "background_counts_cps": 0.0,
                    "jitter_ps_fwhm": 30.0,
                    "dead_time_ns": 100.0,
                    "afterpulsing_prob": 0.001,
                },
            },
            {
                "id": "timing_1",
                "kind": "qkd.timing",
                "label": "Timing",
                "params": {
                    "sync_drift_ps_rms": 10.0,
                    "coincidence_window_ps": float(case.coincidence_window_ps),
                },
            },
            {
                "id": "protocol_1",
                "kind": "qkd.protocol",
                "label": "Protocol",
                "params": protocol_params,
            },
        ],
        "edges": [
            {"from": "source_1", "to": "channel_1", "kind": "control", "label": "emits into"},
            {"from": "channel_1", "to": "detector_1", "kind": "optical", "label": "propagates"},
        ],
    }


def extract_first_card(payload: dict[str, Any]) -> dict[str, Any] | None:
    results = payload.get("results") if isinstance(payload.get("results"), dict) else {}
    cards = results.get("cards") if isinstance(results.get("cards"), list) else []
    if cards and isinstance(cards[0], dict):
        return cards[0]
    return None
