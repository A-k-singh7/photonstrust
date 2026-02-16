from __future__ import annotations

import pytest

from photonstrust.protocols import compiler


def test_compile_protocol_repeater_chain(monkeypatch):
    monkeypatch.setattr(compiler, "entanglement_swapping_circuit", lambda: "swap_qc")
    monkeypatch.setattr(compiler, "purification_circuit", lambda method="DEJMPS": f"purify_{method}")

    graph = compiler.compile_protocol({"name": "BBM92", "purification_method": "BBPSSW"})

    assert graph["name"] == "bbm92"
    assert [step["op"] for step in graph["steps"]] == ["swap", "purify"]
    assert graph["steps"][0]["circuit"] == "swap_qc"
    assert graph["steps"][1]["circuit"] == "purify_BBPSSW"


def test_compile_protocol_teleportation(monkeypatch):
    monkeypatch.setattr(compiler, "teleportation_circuit", lambda: "teleport_qc")

    graph = compiler.compile_protocol({"name": "teleportation"})
    assert graph["name"] == "teleportation"
    assert graph["steps"][0]["op"] == "teleport"
    assert graph["steps"][0]["circuit"] == "teleport_qc"


def test_compile_protocol_qiskit_repeater_primitive(monkeypatch):
    monkeypatch.setattr(compiler, "entanglement_swapping_circuit", lambda: "swap_qc")
    monkeypatch.setattr(
        compiler,
        "repeater_bsm_success_probability",
        lambda: {
            "primitive": "swap_bsm_equal_bits",
            "formula_probability": 0.5,
            "circuit_probability": 0.5,
            "absolute_delta": 0.0,
        },
    )

    graph = compiler.compile_protocol({"name": "qiskit_repeater_primitive"})

    assert graph["name"] == "qiskit_repeater_primitive"
    assert graph["steps"][0]["op"] == "swap_bsm_crosscheck"
    assert graph["steps"][0]["circuit"] == "swap_qc"
    assert graph["steps"][0]["comparison"]["formula_probability"] == 0.5


def test_compile_protocol_rejects_unknown_protocol():
    with pytest.raises(ValueError):
        compiler.compile_protocol({"name": "unknown_protocol"})
