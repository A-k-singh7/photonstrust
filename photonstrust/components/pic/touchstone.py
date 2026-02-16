"""Touchstone (.sNp) utilities for PIC compact model import.

This parser intentionally supports a conservative subset of Touchstone:
- N-port networks via .sNp (Touchstone 1.x style)
- parameter type: S
- data formats: RI, MA, DB
- frequency units: HZ/KHZ/MHZ/GHZ

It is designed for deterministic, unit-tested ingestion in ChipVerify workflows.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class TouchstoneNetwork:
    n_ports: int
    freqs_hz: np.ndarray  # shape (n,)
    s: np.ndarray  # shape (n, n_ports, n_ports), complex
    z0_ohm: float | None
    data_format: str  # "RI" | "MA" | "DB"


_FREQ_UNIT = {
    "HZ": 1.0,
    "KHZ": 1e3,
    "MHZ": 1e6,
    "GHZ": 1e9,
}

_SNP_RE = re.compile(r"\.s(\d+)p$", flags=re.IGNORECASE)


def infer_touchstone_n_ports(path: str) -> int | None:
    m = _SNP_RE.search(str(path).strip())
    if not m:
        return None
    try:
        n = int(m.group(1))
    except Exception:
        return None
    if n <= 0:
        return None
    return n


def _complex_from_pair(a: float, b: float, *, fmt: str) -> complex:
    fmt = fmt.upper()
    if fmt == "RI":
        return complex(float(a), float(b))
    if fmt == "MA":
        mag = float(a)
        ang_rad = float(b) * math.pi / 180.0
        return complex(mag * math.cos(ang_rad), mag * math.sin(ang_rad))
    if fmt == "DB":
        mag = 10 ** (float(a) / 20.0)
        ang_rad = float(b) * math.pi / 180.0
        return complex(mag * math.cos(ang_rad), mag * math.sin(ang_rad))
    raise ValueError(f"Unsupported Touchstone data format: {fmt!r}")


def _parse_header(header: str) -> tuple[str, float, float | None]:
    toks = header.lstrip("#").strip().split()
    if len(toks) < 3:
        raise ValueError(f"Invalid Touchstone header: {header!r}")
    unit = toks[0].upper()
    param_type = toks[1].upper()
    fmt = toks[2].upper()

    if unit not in _FREQ_UNIT:
        raise ValueError(f"Unsupported Touchstone frequency unit: {unit!r}")
    if param_type != "S":
        raise ValueError(f"Unsupported Touchstone parameter type: {param_type!r} (expected 'S')")
    if fmt not in {"RI", "MA", "DB"}:
        raise ValueError(f"Unsupported Touchstone data format: {fmt!r}")

    z0 = None
    toks_u = [t.upper() for t in toks]
    if "R" in toks_u:
        i = toks_u.index("R")
        if i + 1 < len(toks):
            try:
                z0 = float(toks[i + 1])
            except Exception:
                z0 = None

    return fmt, float(_FREQ_UNIT[unit]), z0


def parse_touchstone_nport(text: str, *, n_ports: int) -> TouchstoneNetwork:
    if not isinstance(n_ports, int) or n_ports <= 0:
        raise ValueError("n_ports must be a positive integer")

    header = None
    data_tokens: list[float] = []
    freqs: list[float] = []
    mats: list[np.ndarray] = []
    z0: float | None = None
    fmt: str | None = None

    needed = 1 + 2 * n_ports * n_ports

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue

        # Strip inline comments.
        if "!" in line:
            line = line.split("!", 1)[0].strip()
            if not line:
                continue

        if line.startswith("#"):
            header = line
            fmt, _, z0 = _parse_header(header)
            continue

        # Touchstone 2.0 directives are not supported; ignore bracket lines.
        if line.startswith("["):
            continue

        # Data can be split across lines; accumulate tokens and parse records.
        for tok in line.split():
            t = tok.replace("D", "E").replace("d", "e")
            data_tokens.append(float(t))

        while len(data_tokens) >= needed:
            if header is None or fmt is None:
                raise ValueError("Touchstone header line is required (starts with '#').")

            freq = float(data_tokens[0])
            vals = data_tokens[1:needed]
            data_tokens = data_tokens[needed:]

            _, unit_scale, _ = _parse_header(header)
            mat = np.zeros((n_ports, n_ports), dtype=np.complex128)

            # Touchstone ordering: S11, S21, ..., SN1, S12, S22, ..., SN2, ..., SNN.
            for j in range(n_ports):
                for i in range(n_ports):
                    k = j * n_ports + i
                    a = vals[2 * k]
                    b = vals[2 * k + 1]
                    mat[i, j] = _complex_from_pair(a, b, fmt=fmt)

            freqs.append(freq * unit_scale)
            mats.append(mat)

    if header is None or fmt is None:
        raise ValueError("Touchstone header line is required (starts with '#').")
    if data_tokens:
        raise ValueError(f"Incomplete Touchstone record: leftover tokens={len(data_tokens)}")
    if not freqs:
        raise ValueError("No Touchstone data records found.")

    freqs_hz = np.array(freqs, dtype=np.float64)
    s = np.stack(mats, axis=0).astype(np.complex128)
    if freqs_hz.ndim != 1 or s.shape != (freqs_hz.shape[0], n_ports, n_ports):
        raise ValueError("Touchstone parse produced inconsistent shapes.")

    # Ensure strictly increasing frequencies for interpolation determinism.
    order = np.argsort(freqs_hz)
    freqs_hz = freqs_hz[order]
    s = s[order]
    if np.any(np.diff(freqs_hz) <= 0.0):
        raise ValueError("Touchstone frequencies must be strictly increasing.")

    return TouchstoneNetwork(n_ports=n_ports, freqs_hz=freqs_hz, s=s, z0_ohm=z0, data_format=str(fmt))


def parse_touchstone_2port(text: str) -> TouchstoneNetwork:
    """Backwards-compatible 2-port parser (expects an S2P file)."""

    return parse_touchstone_nport(text, n_ports=2)


@lru_cache(maxsize=32)
def load_touchstone_nport(path: str, *, n_ports: int) -> TouchstoneNetwork:
    p = Path(path)
    text = p.read_text(encoding="utf-8", errors="replace")
    return parse_touchstone_nport(text, n_ports=n_ports)


def load_touchstone(path: str) -> TouchstoneNetwork:
    n = infer_touchstone_n_ports(path)
    if n is None:
        raise ValueError("Could not infer port count from Touchstone filename (expected .sNp).")
    return load_touchstone_nport(path, n_ports=int(n))


def load_touchstone_2port(path: str) -> TouchstoneNetwork:
    data = load_touchstone(path)
    if int(data.n_ports) != 2:
        raise ValueError(f"Touchstone file is not 2-port (n_ports={data.n_ports}).")
    return data


def interpolate_s_matrix(data: TouchstoneNetwork, *, freq_hz: float, allow_extrapolation: bool) -> np.ndarray:
    f = data.freqs_hz
    if not math.isfinite(float(freq_hz)) or float(freq_hz) <= 0.0:
        raise ValueError("freq_hz must be finite and > 0.")

    freq_hz = float(freq_hz)
    if freq_hz < float(f[0]):
        if not allow_extrapolation:
            raise ValueError(f"freq_hz below Touchstone range: {freq_hz} < {float(f[0])}")
        return np.array(data.s[0], dtype=np.complex128)
    if freq_hz > float(f[-1]):
        if not allow_extrapolation:
            raise ValueError(f"freq_hz above Touchstone range: {freq_hz} > {float(f[-1])}")
        return np.array(data.s[-1], dtype=np.complex128)

    idx = int(np.searchsorted(f, freq_hz, side="left"))
    if idx == 0:
        return np.array(data.s[0], dtype=np.complex128)
    if idx >= len(f):
        return np.array(data.s[-1], dtype=np.complex128)

    f1 = float(f[idx - 1])
    f2 = float(f[idx])
    if f2 <= f1:
        return np.array(data.s[idx], dtype=np.complex128)
    w = (freq_hz - f1) / (f2 - f1)
    return (1.0 - w) * data.s[idx - 1] + w * data.s[idx]
