#!/usr/bin/env python3
"""Run the M5 satellite-chain demo with Berlin reference config."""

from __future__ import annotations

import json
from pathlib import Path

from photonstrust.config import load_config
from photonstrust.pipeline.satellite_chain import run_satellite_chain


def _summarize(result: object, *, output_dir: Path) -> dict[str, object]:
    payload = result if isinstance(result, dict) else {}
    cert = payload.get("certificate") if isinstance(payload.get("certificate"), dict) else {}
    signoff = cert.get("signoff") if isinstance(cert.get("signoff"), dict) else {}
    pass_section = cert.get("pass") if isinstance(cert.get("pass"), dict) else {}

    decision = signoff.get("decision")
    if decision is None:
        decision = payload.get("decision")
    if decision is None:
        decision = "HOLD"

    output_path_raw = payload.get("output_path")
    output_path = str(output_path_raw) if output_path_raw is not None else str(output_dir.resolve())

    return {
        "decision": str(decision).strip().upper(),
        "key_bits_accumulated": pass_section.get("key_bits_accumulated"),
        "mean_key_rate_bps": pass_section.get("mean_key_rate_bps"),
        "output_path": output_path,
    }


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    config_path = repo_root / "configs" / "satellite" / "eagle1_analog_berlin.yml"
    output_dir = (repo_root / "results" / "satellite_chain_demo").resolve()

    try:
        config = load_config(config_path)
        result = run_satellite_chain(config, output_dir=output_dir)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": f"satellite_chain_run_failed: {exc}",
                },
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        return 2

    print(json.dumps(_summarize(result, output_dir=output_dir), separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
