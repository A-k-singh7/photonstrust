"""Tests for protocol reliability cards."""
import pytest
from photonstrust.protocols.reliability_card import (
    build_reliability_card, compare_protocols, PROTOCOL_CARDS, ReliabilityCard,
)

def test_bb84_trl_9():
    card = build_reliability_card("bb84")
    assert card.trl == 9
    assert card.maturity == "deployed"

def test_trl_ordering():
    """BB84 > TF-QKD > DI-QKD in TRL."""
    bb84 = build_reliability_card("bb84")
    tf = build_reliability_card("tf_qkd")
    di = build_reliability_card("di_qkd")
    assert bb84.trl > tf.trl > di.trl

def test_all_protocols_build():
    for pid in PROTOCOL_CARDS:
        card = build_reliability_card(pid)
        assert isinstance(card, ReliabilityCard)
        assert 1 <= card.trl <= 9
        assert card.max_distance_km > 0

def test_unknown_protocol_raises():
    with pytest.raises(ValueError, match="Unknown protocol"):
        build_reliability_card("quantum_teleportation_v99")

def test_compare_produces_ranking():
    result = compare_protocols(["bb84", "tf_qkd", "di_qkd"])
    assert "ranking" in result
    assert len(result["ranking"]) == 3
    assert "figure_of_merit" in result

def test_compare_fom_bb84_high():
    result = compare_protocols(["bb84", "di_qkd"])
    assert result["figure_of_merit"]["bb84"] > result["figure_of_merit"]["di_qkd"]

def test_card_fields_complete():
    card = build_reliability_card("cv_qkd")
    assert card.detector_requirement == "homodyne"
    assert card.security_model == "prepare_and_measure"
    assert len(card.key_assumptions) > 0
