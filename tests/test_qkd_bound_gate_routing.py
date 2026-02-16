from __future__ import annotations

from photonstrust.qkd_protocols.registry import protocol_gate_policy


def test_plob_gate_routing_is_protocol_aware() -> None:
    assert protocol_gate_policy("bbm92")["plob_repeaterless_bound"] == "apply"
    assert protocol_gate_policy("bb84_decoy")["plob_repeaterless_bound"] == "apply"
    assert protocol_gate_policy("mdi_qkd")["plob_repeaterless_bound"] == "skip"
    assert protocol_gate_policy("pm_qkd")["plob_repeaterless_bound"] == "skip"
    assert protocol_gate_policy("tf_qkd")["plob_repeaterless_bound"] == "skip"
