"""Protocol step log + optional QASM artifact helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from photonstrust.protocols.circuits import entanglement_swapping_circuit, purification_circuit, teleportation_circuit
from photonstrust.qkd_protocols.common import normalize_protocol_name


def write_protocol_steps_artifacts(
    *,
    scenario: dict[str, Any],
    output_dir: Path,
    protocol_selected: str | None,
    include_qasm: bool = True,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    protocol_norm = normalize_protocol_name(protocol_selected or ((scenario or {}).get("protocol") or {}).get("name"))
    protocol_norm = str(protocol_norm or "bbm92")

    steps_payload = {
        "schema_version": "0.1",
        "kind": "photonstrust.protocol_steps",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "protocol": protocol_norm,
        "steps": _build_protocol_steps(scenario, protocol_norm),
    }
    steps_path = output_dir / "protocol_steps.json"
    steps_path.write_text(json.dumps(steps_payload, indent=2), encoding="utf-8")

    qasm_artifacts: dict[str, str] = {}
    if include_qasm:
        qasm_artifacts = _write_qasm_artifacts(output_dir, protocol_norm)

    return {
        "protocol_steps_json": str(steps_path),
        "protocol_steps": {
            "protocol": protocol_norm,
            "step_count": len(steps_payload["steps"]),
            "qasm_artifacts": dict(qasm_artifacts),
        },
    }


def _build_protocol_steps(scenario: dict[str, Any], protocol_norm: str) -> list[dict[str, Any]]:
    distances = list(((scenario or {}).get("distances_km") or []))
    out: list[dict[str, Any]] = []
    for idx, distance in enumerate(distances):
        out.append(
            {
                "step_id": f"step-{idx + 1:04d}",
                "t_ns": float(idx),
                "operation": "evaluate_point",
                "resources": {"distance_km": float(distance), "protocol": protocol_norm},
                "measurements": {},
                "classical_messages": [],
            }
        )
    if not out:
        out.append(
            {
                "step_id": "step-0001",
                "t_ns": 0.0,
                "operation": "evaluate_point",
                "resources": {"distance_km": 0.0, "protocol": protocol_norm},
                "measurements": {},
                "classical_messages": [],
            }
        )
    return out


def _write_qasm_artifacts(output_dir: Path, protocol_norm: str) -> dict[str, str]:
    artifacts: dict[str, str] = {}
    circuit_builders = {
        "swap": entanglement_swapping_circuit,
        "purify": purification_circuit,
        "teleport": teleportation_circuit,
    }
    for circuit_id, build in circuit_builders.items():
        try:
            circuit = build()
            qasm_text = _export_qasm(circuit)
        except Exception:
            continue
        path = output_dir / f"circuit_{circuit_id}.qasm"
        path.write_text(qasm_text, encoding="utf-8")
        artifacts[f"circuit_{circuit_id}_qasm"] = str(path)
    return artifacts


def _export_qasm(circuit: Any) -> str:
    # qiskit compatibility: qasm2.dumps is preferred; fallback to qc.qasm().
    try:
        from qiskit import qasm2

        return str(qasm2.dumps(circuit))
    except Exception:
        pass
    if hasattr(circuit, "qasm"):
        return str(circuit.qasm())
    raise RuntimeError("OpenQASM export is unavailable for this qiskit version")
