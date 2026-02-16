"""Utility helpers."""

from __future__ import annotations

import hashlib
import json
import math


def binary_entropy(x: float) -> float:
    if x <= 0.0 or x >= 1.0:
        return 0.0
    return -x * math.log2(x) - (1.0 - x) * math.log2(1.0 - x)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def hash_dict(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
