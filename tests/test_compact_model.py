"""Tests for compact S-parameter model loading and cascading."""
import numpy as np
import pytest

from photonstrust.components.pic.compact_model import (
    CompactModel,
    cascade_2port_models,
    evaluate_at_wavelength,
    load_compact_model_from_dict,
    s_to_t,
    t_to_s,
)


def _make_test_model(name="test", n_ports=2, n_freq=5):
    """Create a simple test compact model (identity-like)."""
    freqs = np.linspace(190e12, 195e12, n_freq)  # ~1535-1578 nm
    s = np.zeros((n_freq, n_ports, n_ports), dtype=complex)
    for i in range(n_freq):
        # Near-unity transmission through port
        s[i, 0, 1] = 0.95 * np.exp(1j * 0.1 * i)
        s[i, 1, 0] = 0.95 * np.exp(1j * 0.1 * i)
        s[i, 0, 0] = 0.05
        s[i, 1, 1] = 0.05
    return CompactModel(
        name=name, n_ports=n_ports, frequencies_hz=freqs, s_params=s
    )


def test_load_from_dict():
    data = {
        "name": "test",
        "n_ports": 2,
        "frequencies_hz": [190e12, 195e12],
        "s_params_real": [[[0, 0.9], [0.9, 0]], [[0, 0.85], [0.85, 0]]],
        "s_params_imag": [[[0, 0.1], [0.1, 0]], [[0, 0.15], [0.15, 0]]],
    }
    m = load_compact_model_from_dict(data)
    assert m.n_ports == 2
    assert len(m.frequencies_hz) == 2


def test_evaluate_interpolates():
    m = _make_test_model(n_freq=10)
    s = evaluate_at_wavelength(m, 1550.0)
    assert s.shape == (2, 2)
    assert abs(s[1, 0]) > 0.5  # should have transmission


def test_s_to_t_roundtrip():
    s = np.array([[0.1 + 0.01j, 0.9 + 0.1j], [0.9 + 0.1j, 0.1 - 0.01j]])
    t = s_to_t(s)
    s2 = t_to_s(t)
    np.testing.assert_allclose(s2, s, atol=1e-12)


def test_cascade_identity():
    """Cascading with identity-like models preserves transmission."""
    m = _make_test_model()
    s_single = evaluate_at_wavelength(m, 1550.0)
    s_cascade = cascade_2port_models([m], 1550.0)
    np.testing.assert_allclose(s_cascade, s_single, atol=1e-10)


def test_cascade_two_models_reduces_transmission():
    m = _make_test_model()
    s1 = evaluate_at_wavelength(m, 1550.0)
    s2 = cascade_2port_models([m, m], 1550.0)
    # Two lossy elements: transmission should be less
    assert abs(s2[1, 0]) <= abs(s1[1, 0]) + 0.01


def test_empty_cascade():
    s = cascade_2port_models([], 1550.0)
    np.testing.assert_allclose(s, np.eye(2), atol=1e-12)
