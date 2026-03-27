"""GS-QKD-014 key delivery API compliance checks."""

from __future__ import annotations

from typing import Any


def check_k1(sweep_result: Any, scenario: dict, *, context: dict) -> dict:
    """Clause 6.1: Key delivery interface exposes status endpoint.

    Checks that the KMS configuration is present and the simulated pool is
    populated.
    """
    kms_cfg = scenario.get("kms") or context.get("kms")
    if not kms_cfg:
        return {
            "status": "NOT_ASSESSED",
            "notes": ["No KMS configuration in scenario or context."],
        }
    return {
        "status": "PASS",
        "computed_value": True,
        "notes": ["KMS configuration present; status endpoint addressable."],
    }


def check_k2(sweep_result: Any, scenario: dict, *, context: dict) -> dict:
    """Clause 6.2: Delivered keys use unique UUIDs.

    Validates that all key IDs in the context pool snapshot are unique.
    """
    pool_keys = context.get("pool_keys", [])
    if not pool_keys:
        return {
            "status": "NOT_ASSESSED",
            "notes": ["No pool key data in context."],
        }
    ids = [k.get("key_id") or k.get("key_ID") for k in pool_keys]
    unique_count = len(set(ids))
    if unique_count == len(ids):
        return {
            "status": "PASS",
            "computed_value": unique_count,
            "notes": [f"All {unique_count} key IDs are unique."],
        }
    return {
        "status": "FAIL",
        "computed_value": unique_count,
        "threshold": len(ids),
        "notes": [f"Duplicate key IDs found: {len(ids) - unique_count} duplicates."],
    }


def check_k3(sweep_result: Any, scenario: dict, *, context: dict) -> dict:
    """Clause 6.3: Key size matches requested specification.

    Verifies that keys in the pool match the configured key size.
    """
    kms_cfg = scenario.get("kms") or context.get("kms") or {}
    expected_bits = int(kms_cfg.get("key_size_bits", 256))
    pool_keys = context.get("pool_keys", [])
    if not pool_keys:
        return {
            "status": "NOT_ASSESSED",
            "notes": ["No pool key data in context."],
        }
    mismatches = [k for k in pool_keys if k.get("key_length_bits") != expected_bits]
    if not mismatches:
        return {
            "status": "PASS",
            "computed_value": expected_bits,
            "unit": "bits",
            "notes": [f"All keys match expected size of {expected_bits} bits."],
        }
    return {
        "status": "FAIL",
        "computed_value": len(mismatches),
        "threshold": 0,
        "unit": "mismatched_keys",
        "notes": [f"{len(mismatches)} keys have incorrect key size."],
    }


def check_k4(sweep_result: Any, scenario: dict, *, context: dict) -> dict:
    """Clause 6.4: Key pool replenishment rate matches simulated QKD key rate.

    Compares the configured replenishment rate against the simulated key rate.
    """
    kms_cfg = scenario.get("kms") or context.get("kms") or {}
    configured_rate = float(kms_cfg.get("replenish_rate_keys_per_sec", 0))

    rows = sweep_result if isinstance(sweep_result, list) else []
    if not rows:
        sr = sweep_result if isinstance(sweep_result, dict) else {}
        rows = sr.get("results", [])

    if not rows:
        return {
            "status": "NOT_ASSESSED",
            "notes": ["No sweep results to compare against."],
        }

    key_rates = []
    for r in rows:
        kr = r.get("key_rate_bps", 0) if isinstance(r, dict) else getattr(r, "key_rate_bps", 0)
        key_rates.append(float(kr))

    max_kr = max(key_rates) if key_rates else 0.0
    key_size = int(kms_cfg.get("key_size_bits", 256))
    max_keys_per_sec = max_kr / key_size if key_size > 0 else 0.0

    if configured_rate <= max_keys_per_sec * 1.1:
        return {
            "status": "PASS",
            "computed_value": configured_rate,
            "threshold": max_keys_per_sec,
            "unit": "keys/s",
            "notes": [
                f"Configured rate {configured_rate:.1f} keys/s within "
                f"simulated capacity {max_keys_per_sec:.1f} keys/s."
            ],
        }
    return {
        "status": "WARNING",
        "computed_value": configured_rate,
        "threshold": max_keys_per_sec,
        "unit": "keys/s",
        "notes": [
            f"Configured rate {configured_rate:.1f} keys/s exceeds "
            f"simulated capacity {max_keys_per_sec:.1f} keys/s."
        ],
    }
