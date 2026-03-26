"""Compact S-parameter model loading and evaluation."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class CompactModel:
    """Frequency-dependent S-parameter model."""

    name: str
    n_ports: int
    frequencies_hz: np.ndarray  # shape (N_freq,)
    s_params: np.ndarray  # shape (N_freq, n_ports, n_ports) complex

    def __eq__(self, other):
        if not isinstance(other, CompactModel):
            return NotImplemented
        return (
            self.name == other.name
            and self.n_ports == other.n_ports
            and np.array_equal(self.frequencies_hz, other.frequencies_hz)
            and np.array_equal(self.s_params, other.s_params)
        )

    def __hash__(self):
        return hash((self.name, self.n_ports))


def load_compact_model_from_dict(data: dict) -> CompactModel:
    """Load compact model from a dictionary (JSON-like format).

    Expected format:
    {"name": "ring_filter", "n_ports": 2,
     "frequencies_hz": [...], "s_params_real": [...], "s_params_imag": [...]}
    """
    freqs = np.array(data["frequencies_hz"], dtype=float)
    s_real = np.array(data["s_params_real"], dtype=float)
    s_imag = np.array(data["s_params_imag"], dtype=float)
    s = s_real + 1j * s_imag
    return CompactModel(
        name=data["name"],
        n_ports=int(data["n_ports"]),
        frequencies_hz=freqs,
        s_params=s,
    )


def evaluate_at_wavelength(model: CompactModel, wavelength_nm: float) -> np.ndarray:
    """Interpolate S-params at a given wavelength.

    Converts wavelength to frequency: f = c/lambda
    Returns interpolated S-matrix (n_ports x n_ports) complex.
    """
    c = 299792458.0  # m/s
    freq = c / (wavelength_nm * 1e-9)

    freqs = model.frequencies_hz
    if freq <= freqs[0]:
        return model.s_params[0]
    if freq >= freqs[-1]:
        return model.s_params[-1]

    # Linear interpolation
    idx = np.searchsorted(freqs, freq) - 1
    idx = max(0, min(idx, len(freqs) - 2))
    t = (freq - freqs[idx]) / (freqs[idx + 1] - freqs[idx])

    return (1 - t) * model.s_params[idx] + t * model.s_params[idx + 1]


def s_to_t(s: np.ndarray) -> np.ndarray:
    """Convert 2-port S-matrix to T (transfer) matrix.

    T = [[1/S21, -S22/S21], [S11/S21, S12 - S11*S22/S21]]
    Based on scikit-rf conventions.
    """
    if s.shape != (2, 2):
        raise ValueError("S->T conversion requires 2x2 S-matrix")
    s21 = s[1, 0]
    if abs(s21) < 1e-15:
        raise ValueError("S21 ~ 0; T-matrix undefined")
    return np.array(
        [
            [1.0 / s21, -s[1, 1] / s21],
            [s[0, 0] / s21, s[0, 1] - s[0, 0] * s[1, 1] / s21],
        ]
    )


def t_to_s(t: np.ndarray) -> np.ndarray:
    """Convert 2-port T (transfer) matrix back to S-matrix."""
    if t.shape != (2, 2):
        raise ValueError("T->S conversion requires 2x2 T-matrix")
    t11 = t[0, 0]
    if abs(t11) < 1e-15:
        raise ValueError("T11 ~ 0; S-matrix undefined")
    return np.array(
        [
            [t[1, 0] / t11, t[1, 1] - t[1, 0] * t[0, 1] / t11],
            [1.0 / t11, -t[0, 1] / t11],
        ]
    )


def cascade_2port_models(
    models: list[CompactModel], wavelength_nm: float
) -> np.ndarray:
    """Cascade multiple 2-port compact models via T-matrix multiplication.

    T_total = T_N * ... * T_2 * T_1
    Returns resulting S-matrix (2x2 complex).
    """
    if not models:
        return np.eye(2, dtype=complex)

    t_total = np.eye(2, dtype=complex)
    for m in models:
        s = evaluate_at_wavelength(m, wavelength_nm)
        t = s_to_t(s)
        t_total = t @ t_total

    return t_to_s(t_total)
