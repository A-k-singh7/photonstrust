"""Generate baseline fixtures for Phase 41 canonical fiber realism presets."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from photonstrust.config import build_scenarios, load_config
from photonstrust.qkd import compute_sweep


def _deterministic_generated_at() -> str:
    """Return a deterministic timestamp for fixture metadata.

    Uses SOURCE_DATE_EPOCH when provided (reproducible-build convention),
    otherwise falls back to a fixed epoch string so regenerated fixtures are
    byte-stable across runs.
    """

    source_date_epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if source_date_epoch is None:
        return "1970-01-01T00:00:00+00:00"
    try:
        epoch = int(source_date_epoch)
    except ValueError as exc:
        raise SystemExit("SOURCE_DATE_EPOCH must be an integer Unix timestamp") from exc
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    canonical_dir = root / "configs" / "canonical"
    output_path = root / "tests" / "fixtures" / "canonical_phase41_baselines.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    config_paths = sorted(canonical_dir.glob("phase41_*.yml"), key=lambda p: p.name.lower())
    if not config_paths:
        raise SystemExit(f"No canonical Phase 41 configs found under {canonical_dir}")

    out_configs = []
    for config_path in config_paths:
        cfg = load_config(config_path)
        scenarios = build_scenarios(cfg)
        baselines = []
        for scenario in scenarios:
            sweep = compute_sweep(scenario, include_uncertainty=False)
            results = sweep["results"]
            baselines.append(
                {
                    "scenario_id": scenario["scenario_id"],
                    "band": scenario["band"],
                    "distances_km": [float(r.distance_km) for r in results],
                    "key_rate_bps": [float(r.key_rate_bps) for r in results],
                    "qber": [float(r.qber_total) for r in results],
                    "raman_counts_cps": [float(r.raman_counts_cps) for r in results],
                    "background_counts_cps": [float(r.background_counts_cps) for r in results],
                    "finite_key_enabled": bool(results[0].finite_key_enabled) if results else False,
                }
            )

        out_configs.append(
            {
                "config_relpath": str(config_path.relative_to(root)).replace("\\", "/"),
                "baselines": baselines,
            }
        )

    payload = {
        "schema_version": "0.1",
        "generated_at": _deterministic_generated_at(),
        "kind": "photonstrust.canonical_baselines.phase41",
        "configs": out_configs,
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
