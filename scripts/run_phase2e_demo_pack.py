"""Build a deterministic 10-minute PhotonTrust demo pack.

This script runs one canonical QKD scenario end-to-end and emits a compact
artifact pack suitable for customer/pilot walkthroughs.
"""

from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from photonstrust.config import build_scenarios, load_config
from photonstrust.sweep import run_scenarios


DEFAULT_CONFIG = Path("configs/demo1_default.yml")
DEFAULT_OUTPUT_ROOT = Path("results/demo_pack")
DEFAULT_CANONICAL_BAND = "c_1550"
DEFAULT_DEMO_SEED = 20260216


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic Phase 2E demo pack")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Input config YAML")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Root directory for generated demo packs",
    )
    parser.add_argument(
        "--band",
        type=str,
        default=DEFAULT_CANONICAL_BAND,
        help="Canonical band to run (default: c_1550)",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_DEMO_SEED, help="Deterministic seed")
    parser.add_argument(
        "--preview-uncertainty-samples",
        type=int,
        default=60,
        help="Uncertainty samples used in preview execution mode",
    )
    parser.add_argument(
        "--label",
        type=str,
        default=None,
        help="Optional run label. Default: UTC timestamp",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    config_path = (repo_root / args.config).resolve() if not args.config.is_absolute() else args.config
    output_root = (repo_root / args.output_root).resolve() if not args.output_root.is_absolute() else args.output_root

    config = load_config(config_path)
    scenarios = build_scenarios(config)
    if not scenarios:
        raise ValueError(f"No scenarios expanded from config: {config_path}")

    scenario = _pick_canonical_scenario(scenarios, preferred_band=args.band)
    scenario = _prepare_demo_scenario(
        scenario,
        seed=int(args.seed),
        preview_uncertainty_samples=int(args.preview_uncertainty_samples),
    )

    run_label = args.label or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    pack_dir = output_root / run_label
    run_dir = pack_dir / "run"
    evidence_dir = pack_dir / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    result = run_scenarios([scenario], run_dir)
    card = result["cards"][0]

    scenario_dir = run_dir / scenario["scenario_id"] / scenario["band"]
    card_path = scenario_dir / "reliability_card.json"
    uncertainty_path = scenario_dir / "uncertainty.json"
    results_path = scenario_dir / "results.json"

    evidence_manifest = _build_file_manifest(
        [
            card_path,
            uncertainty_path,
            results_path,
            scenario_dir / "report.html",
            scenario_dir / "report.pdf",
            run_dir / "run_registry.json",
        ]
    )
    (evidence_dir / "artifact_manifest.json").write_text(
        json.dumps(evidence_manifest, indent=2),
        encoding="utf-8",
    )

    uncertainty_payload = _read_json_if_exists(uncertainty_path)
    uncertainty_summary = _build_uncertainty_summary(uncertainty_payload)
    (evidence_dir / "uncertainty_summary.json").write_text(
        json.dumps(uncertainty_summary, indent=2),
        encoding="utf-8",
    )

    reliability_summary = {
        "schema_version": card.get("schema_version"),
        "scenario_id": card.get("scenario_id"),
        "band": card.get("band"),
        "safe_use_label": (card.get("safe_use_label") or {}).get("label"),
        "key_rate_bps": (card.get("outputs") or {}).get("key_rate_bps"),
        "qber_total": (card.get("derived") or {}).get("qber_total"),
        "critical_distance_km": (card.get("outputs") or {}).get("critical_distance_km"),
        "uncertainty": (card.get("outputs") or {}).get("uncertainty"),
    }
    (evidence_dir / "reliability_card_summary.json").write_text(
        json.dumps(reliability_summary, indent=2),
        encoding="utf-8",
    )

    deterministic_fingerprint = _fingerprint_for_determinism(
        scenario=scenario,
        card=card,
        uncertainty=uncertainty_payload,
        results_payload=_read_json_if_exists(results_path),
    )

    demo_pack = {
        "schema_version": "0.1",
        "kind": "photonstrust.phase2e_demo_pack",
        "run_label": run_label,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "determinism": {
            "seed": int(args.seed),
            "preview_uncertainty_samples": int(args.preview_uncertainty_samples),
            "fingerprint_sha256": deterministic_fingerprint,
        },
        "inputs": {
            "config_path": str(config_path),
            "scenario_id": scenario["scenario_id"],
            "band": scenario["band"],
            "execution_mode": scenario.get("execution_mode"),
        },
        "outputs": {
            "pack_dir": str(pack_dir),
            "scenario_dir": str(scenario_dir),
            "reliability_card": str(card_path),
            "uncertainty": str(uncertainty_path),
            "results": str(results_path),
            "evidence_manifest": str(evidence_dir / "artifact_manifest.json"),
            "reliability_summary": str(evidence_dir / "reliability_card_summary.json"),
            "uncertainty_summary": str(evidence_dir / "uncertainty_summary.json"),
        },
    }
    (pack_dir / "demo_pack.json").write_text(json.dumps(demo_pack, indent=2), encoding="utf-8")

    print(json.dumps(demo_pack, indent=2))
    return 0


def _pick_canonical_scenario(scenarios: list[dict[str, Any]], preferred_band: str) -> dict[str, Any]:
    for sc in scenarios:
        if str(sc.get("band")) == preferred_band:
            return copy.deepcopy(sc)
    return copy.deepcopy(scenarios[0])


def _prepare_demo_scenario(scenario: dict[str, Any], *, seed: int, preview_uncertainty_samples: int) -> dict[str, Any]:
    sc = copy.deepcopy(scenario)
    sc["seed"] = int(seed)
    sc["execution_mode"] = "preview"
    sc["preview_uncertainty_samples"] = max(10, int(preview_uncertainty_samples))
    sc["certification_uncertainty_samples"] = max(sc["preview_uncertainty_samples"], int(sc.get("certification_uncertainty_samples", 400)))
    sc["scenario_id"] = f"{sc['scenario_id']}_phase2e_demo"
    return sc


def _build_file_manifest(paths: list[Path]) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for p in paths:
        if not p.exists():
            continue
        entries.append(
            {
                "path": str(p),
                "size_bytes": int(p.stat().st_size),
                "sha256": _sha256_file(p),
            }
        )
    return {
        "schema_version": "0.1",
        "kind": "photonstrust.phase2e_demo_pack.artifact_manifest",
        "files": entries,
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _read_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _build_uncertainty_summary(uncertainty: dict[str, Any] | None) -> dict[str, Any]:
    if not uncertainty:
        return {
            "present": False,
            "distance_points": 0,
            "sample": None,
        }

    keys = sorted(uncertainty.keys(), key=lambda x: float(x))
    sample_key = keys[0] if keys else None
    sample_value = uncertainty.get(sample_key) if sample_key is not None else None
    return {
        "present": True,
        "distance_points": len(keys),
        "first_distance_km": float(sample_key) if sample_key is not None else None,
        "sample": sample_value,
    }


def _fingerprint_for_determinism(
    *, scenario: dict[str, Any], card: dict[str, Any], uncertainty: dict[str, Any] | None, results_payload: dict[str, Any] | None
) -> str:
    payload = {
        "scenario": {
            "id": scenario.get("scenario_id"),
            "band": scenario.get("band"),
            "seed": scenario.get("seed"),
            "execution_mode": scenario.get("execution_mode"),
            "preview_uncertainty_samples": scenario.get("preview_uncertainty_samples"),
        },
        "outputs": {
            "key_rate_bps": (card.get("outputs") or {}).get("key_rate_bps"),
            "qber_total": (card.get("derived") or {}).get("qber_total"),
            "critical_distance_km": (card.get("outputs") or {}).get("critical_distance_km"),
            "uncertainty_primary": (card.get("outputs") or {}).get("uncertainty"),
            "results": (results_payload or {}).get("results", []),
            "uncertainty": uncertainty,
        },
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
