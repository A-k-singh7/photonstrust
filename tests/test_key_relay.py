"""Tests for photonstrust.network.key_relay -- trusted-node key relay."""

from __future__ import annotations

import pytest

from photonstrust.network.key_relay import (
    compute_relay_rate,
    relay_key_through_trusted_nodes,
)


# ---------------------------------------------------------------------------
# relay_key_through_trusted_nodes
# ---------------------------------------------------------------------------


def test_xor_relay_two_nodes():
    """Direct Alice->Bob link: key_bits > 0, no trusted intermediaries."""
    link_keys = {"Alice->Bob": b"\xaa\xbb\xcc\xdd" * 8}  # 32 bytes
    result = relay_key_through_trusted_nodes(["Alice", "Bob"], link_keys)
    assert result.n_trusted_nodes == 0
    assert result.key_bits > 0
    # 32 bytes = 256 bits minus 128 auth bits for 1 link = 128
    assert result.key_bits == 256 - 128


def test_xor_relay_three_nodes():
    """Alice->T->Bob: n_trusted_nodes=1, key passes through trusted node."""
    link_keys = {
        "Alice->T": b"\xff" * 64,  # 64 bytes
        "T->Bob": b"\x00" * 64,
    }
    result = relay_key_through_trusted_nodes(["Alice", "T", "Bob"], link_keys)
    assert result.n_trusted_nodes == 1
    # 64 bytes = 512 bits, minus 128*2 = 256 auth bits => 256 key bits
    assert result.key_bits == 512 - 256
    assert result.key_bits > 0


def test_auth_overhead_reduces_key():
    """auth_consumed_bits > 0 for multi-hop relay."""
    link_keys = {
        "A->T1": b"\x01" * 128,
        "T1->T2": b"\x02" * 128,
        "T2->B": b"\x03" * 128,
    }
    result = relay_key_through_trusted_nodes(["A", "T1", "T2", "B"], link_keys)
    assert result.auth_consumed_bits == 128 * 3  # 3 links
    assert result.auth_consumed_bits > 0
    # 128 bytes = 1024 bits, minus 384 auth bits = 640 key bits
    assert result.key_bits == 1024 - 384


def test_bottleneck_link_identified():
    """The shortest key link is reported as the bottleneck."""
    link_keys = {
        "A->T": b"\xab" * 64,   # 64 bytes = 512 bits
        "T->B": b"\xcd" * 32,   # 32 bytes = 256 bits  (bottleneck)
    }
    result = relay_key_through_trusted_nodes(["A", "T", "B"], link_keys)
    assert "T->B" in result.bottleneck_link
    # Truncated to 32 bytes; 256 - 256 auth = 0
    assert result.key_bits == max(0, 256 - 256)


def test_insufficient_keys_raises():
    """Missing link key raises ValueError."""
    with pytest.raises(ValueError, match="No link key"):
        relay_key_through_trusted_nodes(["A", "B"], {})


# ---------------------------------------------------------------------------
# compute_relay_rate
# ---------------------------------------------------------------------------


def test_relay_rate_bottleneck():
    """compute_relay_rate returns min_rate * useful_fraction."""
    rates = [1000.0, 2000.0, 500.0]
    result = compute_relay_rate(rates)
    # useful_fraction = (1024 - 128) / 1024 = 0.875
    expected = 500.0 * (1024 - 128) / 1024
    assert result == pytest.approx(expected)


def test_empty_link_rates():
    """compute_relay_rate([]) returns 0."""
    assert compute_relay_rate([]) == pytest.approx(0.0)
