"""Tests for KMS key lifecycle state machine."""

from __future__ import annotations

import pytest

from photonstrust.kms.lifecycle import (
    InvalidTransitionError,
    KeyLifecycleManager,
    KeyState,
)


def test_register_key():
    mgr = KeyLifecycleManager()
    key = mgr.register_key("k1", key_length_bits=256)
    assert key.state == KeyState.GENERATED
    assert key.key_id == "k1"
    assert key.key_length_bits == 256


def test_full_lifecycle():
    """Key goes through GENERATED -> STORED -> DELIVERED -> CONSUMED -> EXPIRED."""
    mgr = KeyLifecycleManager()
    mgr.register_key("k1")
    mgr.store("k1")
    assert mgr.keys["k1"].state == KeyState.STORED
    mgr.deliver("k1", "alice")
    assert mgr.keys["k1"].state == KeyState.DELIVERED
    mgr.consume("k1", "encryption")
    assert mgr.keys["k1"].state == KeyState.CONSUMED
    mgr.expire("k1")
    assert mgr.keys["k1"].state == KeyState.EXPIRED


def test_invalid_transition():
    """Cannot go from GENERATED directly to CONSUMED."""
    mgr = KeyLifecycleManager()
    mgr.register_key("k1")
    with pytest.raises(InvalidTransitionError):
        mgr.consume("k1")


def test_revoke_from_any_state():
    """Revocation should work from non-terminal states."""
    mgr = KeyLifecycleManager()
    mgr.register_key("k1")
    mgr.store("k1")
    mgr.revoke("k1", "compromise detected")
    assert mgr.keys["k1"].state == KeyState.REVOKED


def test_cannot_transition_from_terminal():
    mgr = KeyLifecycleManager()
    mgr.register_key("k1")
    mgr.store("k1")
    mgr.deliver("k1")
    mgr.consume("k1")
    mgr.expire("k1")
    with pytest.raises(InvalidTransitionError):
        mgr.revoke("k1")


def test_transition_log():
    mgr = KeyLifecycleManager()
    mgr.register_key("k1")
    mgr.store("k1")
    mgr.deliver("k1")
    log = mgr.get_transition_log()
    assert len(log) == 2
    assert log[0].from_state == KeyState.GENERATED
    assert log[0].to_state == KeyState.STORED


def test_count_by_state():
    mgr = KeyLifecycleManager()
    mgr.register_key("k1")
    mgr.register_key("k2")
    mgr.store("k1")
    mgr.store("k2")
    mgr.deliver("k1")
    counts = mgr.count_by_state()
    assert counts["delivered"] == 1
    assert counts["stored"] == 1
    assert counts["generated"] == 0


def test_is_terminal():
    mgr = KeyLifecycleManager()
    mgr.register_key("k1")
    assert not mgr.keys["k1"].is_terminal
    mgr.store("k1")
    mgr.deliver("k1")
    mgr.consume("k1")
    mgr.expire("k1")
    assert mgr.keys["k1"].is_terminal


def test_key_not_found():
    mgr = KeyLifecycleManager()
    with pytest.raises(KeyError):
        mgr.store("nonexistent")
