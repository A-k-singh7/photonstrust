"""Protocol compiler helpers."""

from __future__ import annotations

from photonstrust.protocols.circuits import (
    entanglement_swapping_circuit,
    purification_circuit,
    repeater_bsm_success_probability,
    teleportation_circuit,
)


def compile_protocol(cfg: dict) -> dict:
    """Compile protocol config into an execution graph descriptor."""
    name = str(cfg.get("name", "BBM92")).lower()
    purification_method = cfg.get("purification_method", "DEJMPS")

    if name in {"bbm92", "repeater_chain"}:
        return {
            "name": name,
            "steps": [
                {"op": "swap", "circuit": entanglement_swapping_circuit()},
                {
                    "op": "purify",
                    "method": purification_method,
                    "circuit": purification_circuit(method=purification_method),
                },
            ],
        }

    if name in {"teleportation", "teleport"}:
        return {
            "name": name,
            "steps": [
                {"op": "teleport", "circuit": teleportation_circuit()},
            ],
        }

    if name in {"repeater_primitive", "qiskit_repeater_primitive"}:
        return {
            "name": name,
            "steps": [
                {
                    "op": "swap_bsm_crosscheck",
                    "circuit": entanglement_swapping_circuit(),
                    "comparison": repeater_bsm_success_probability(),
                }
            ],
        }

    raise ValueError(f"Unsupported protocol name: {cfg.get('name')}")
