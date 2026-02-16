"""Qiskit protocol circuits."""

from __future__ import annotations

from typing import Any


def _require_qiskit():
    try:
        from qiskit import QuantumCircuit
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(f"Qiskit is required for protocol circuits: {exc}")
    return QuantumCircuit


def entanglement_swapping_circuit():
    QuantumCircuit = _require_qiskit()
    qc = QuantumCircuit(4, 2)
    qc.cx(1, 2)
    qc.h(1)
    qc.measure(1, 0)
    qc.measure(2, 1)
    return qc


def purification_circuit(method: str = "DEJMPS"):
    QuantumCircuit = _require_qiskit()
    qc = QuantumCircuit(4, 2)
    qc.cx(0, 2)
    qc.cx(1, 3)
    qc.h(0)
    qc.h(1)
    qc.measure(2, 0)
    qc.measure(3, 1)
    qc.name = f"purification_{method.lower()}"
    return qc


def teleportation_circuit():
    QuantumCircuit = _require_qiskit()
    qc = QuantumCircuit(3, 2)
    qc.cx(0, 1)
    qc.h(0)
    qc.measure(0, 0)
    qc.measure(1, 1)
    return qc


def repeater_bsm_success_probability(*, seed: int | None = None) -> dict[str, Any]:
    """Cross-check a simple repeater BSM primitive with closed-form expectation.

    The current primitive uses the existing swap circuit and compares the circuit
    probability to the deterministic formula for the success event
    ``m1 XOR m2 == 0`` (equal measurement bits).
    """

    if seed is not None:
        int(seed)

    qc = entanglement_swapping_circuit()
    circuit_probability = _bsm_equal_bits_probability(qc)
    formula_probability = 0.5
    return {
        "primitive": "swap_bsm_equal_bits",
        "formula_probability": float(formula_probability),
        "circuit_probability": float(circuit_probability),
        "absolute_delta": float(abs(formula_probability - circuit_probability)),
    }


def _bsm_equal_bits_probability(measured_circuit) -> float:
    QuantumCircuit = _require_qiskit()
    from qiskit.quantum_info import Statevector

    no_measure = measured_circuit.remove_final_measurements(inplace=False)
    evolved = QuantumCircuit(no_measure.num_qubits)
    evolved.compose(no_measure, inplace=True)
    state = Statevector.from_instruction(evolved)
    probs = state.probabilities_dict()

    success = 0.0
    for bitstring, probability in probs.items():
        b1 = int(bitstring[-2]) if len(bitstring) >= 2 else 0
        b2 = int(bitstring[-3]) if len(bitstring) >= 3 else 0
        if b1 == b2:
            success += float(probability)
    return float(success)
