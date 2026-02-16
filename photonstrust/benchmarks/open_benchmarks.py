"""Open benchmark drift checking.

Open benchmark bundles are stored under `datasets/benchmarks/open/<id>/`.
The check compares engine outputs against the expected curves in each bundle.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from photonstrust.benchmarks._paths import open_benchmarks_dir
from photonstrust.benchmarks.schema import benchmark_bundle_schema_path, validate_instance
from photonstrust.config import build_scenarios
from photonstrust.qkd import compute_sweep


def check_open_benchmarks(open_root: str | Path | None = None) -> tuple[bool, list[str]]:
    open_root_path = Path(open_root) if open_root is not None else open_benchmarks_dir()
    if not open_root_path.exists():
        return True, []

    bundle_paths = sorted(open_root_path.glob("*/benchmark_bundle.json"))
    if not bundle_paths:
        return True, []

    failures: list[str] = []
    for bundle_path in bundle_paths:
        ok, bundle_failures = check_bundle_file(bundle_path)
        if not ok:
            failures.extend(bundle_failures)

    return len(failures) == 0, failures


def check_bundle_file(
    bundle_path: str | Path,
    *,
    require_jsonschema: bool = True,
) -> tuple[bool, list[str]]:
    bundle_path = Path(bundle_path)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    try:
        validate_instance(
            bundle,
            benchmark_bundle_schema_path(),
            require_jsonschema=require_jsonschema,
        )
    except Exception as exc:
        return False, [f"{bundle_path}: schema validation failed: {exc}"]

    kind = str(bundle.get("kind", "")).strip().lower()
    if kind != "qkd_sweep":
        return False, [f"{bundle_path}: unsupported kind={kind!r} (v0 supports qkd_sweep only)"]

    return _check_qkd_sweep_bundle(bundle_path, bundle)


def _check_qkd_sweep_bundle(bundle_path: Path, bundle: dict) -> tuple[bool, list[str]]:
    cfg = bundle["config"]
    expected = bundle["expected"]["qkd_sweeps"]
    defaults = bundle.get("defaults", {})
    default_rel = float(defaults.get("rel_tol", 1e-6))
    default_abs = float(defaults.get("abs_tol", 1e-12))

    expected_by_key = {
        (str(entry["scenario_id"]).strip().lower(), str(entry["band"]).strip().lower()): entry
        for entry in expected
    }

    scenarios = build_scenarios(cfg)
    failures: list[str] = []

    for scenario in scenarios:
        key = (str(scenario["scenario_id"]).strip().lower(), str(scenario["band"]).strip().lower())
        if key not in expected_by_key:
            failures.append(f"{bundle_path}: missing expected entry for scenario_id={key[0]} band={key[1]}")
            continue

        entry = expected_by_key[key]
        sweep = compute_sweep(scenario, include_uncertainty=False)
        observed = sweep["results"]

        observed_distances = [res.distance_km for res in observed]
        observed_key_rates = [res.key_rate_bps for res in observed]

        expected_distances = list(entry["distances_km"])
        expected_key_rates = list(entry["key_rate_bps"])

        if len(observed_distances) != len(expected_distances):
            failures.append(
                f"{bundle_path}: {scenario['scenario_id']} {scenario['band']} length mismatch: "
                f"observed={len(observed_distances)} expected={len(expected_distances)}"
            )
            continue

        for idx, (obs_d, exp_d) in enumerate(zip(observed_distances, expected_distances)):
            if abs(float(obs_d) - float(exp_d)) > 1e-12:
                failures.append(
                    f"{bundle_path}: {scenario['scenario_id']} {scenario['band']} distance[{idx}] mismatch: "
                    f"observed={obs_d} expected={exp_d}"
                )
                break

        rel_tol = float(entry.get("rel_tol", default_rel))
        abs_tol = float(entry.get("abs_tol", default_abs))

        for idx, (obs, exp) in enumerate(zip(observed_key_rates, expected_key_rates)):
            obs = float(obs)
            exp = float(exp)
            tol = max(abs_tol, rel_tol * max(abs(exp), abs(obs)))
            if abs(obs - exp) > tol:
                failures.append(
                    f"{bundle_path}: {scenario['scenario_id']} {scenario['band']} key_rate_bps[{idx}] drift: "
                    f"observed={obs:.12g} expected={exp:.12g} tol={tol:.3g}"
                )

    # Ensure bundle doesn't contain extra expected entries not produced by config.
    produced_keys = {(str(s["scenario_id"]).strip().lower(), str(s["band"]).strip().lower()) for s in scenarios}
    for key in expected_by_key:
        if key not in produced_keys:
            failures.append(f"{bundle_path}: expected entry not produced by config: scenario_id={key[0]} band={key[1]}")

    return len(failures) == 0, failures


def bundle_from_results(
    *,
    benchmark_id: str,
    title: str | None,
    config: dict,
    scenarios: list[dict],
    sweeps: list[dict],
    created_at: str,
    photonstrust_version: str | None = None,
    requires: list[str] | None = None,
    default_rel_tol: float = 1e-6,
    default_abs_tol: float = 1e-12,
) -> dict:
    """Construct a qkd_sweep benchmark bundle from computed sweeps.

    `sweeps` is a list of dicts returned by `compute_sweep`.
    """

    expected = []
    for scenario, sweep in zip(scenarios, sweeps):
        results = sweep["results"]
        if results and not isinstance(results[0], dict):
            results_payload = [asdict(r) for r in results]
        else:
            results_payload = list(results)

        expected.append(
            {
                "scenario_id": scenario["scenario_id"],
                "band": scenario["band"],
                "distances_km": [float(row["distance_km"]) for row in results_payload],
                "key_rate_bps": [float(row["key_rate_bps"]) for row in results_payload],
            }
        )

    engine = {}
    if photonstrust_version:
        engine["photonstrust_version"] = photonstrust_version
    if requires:
        engine["requires"] = list(requires)

    bundle = {
        "schema_version": "0",
        "benchmark_id": benchmark_id,
        "kind": "qkd_sweep",
        "title": title,
        "created_at": created_at,
        "engine": engine or None,
        "config": config,
        "defaults": {"rel_tol": float(default_rel_tol), "abs_tol": float(default_abs_tol)},
        "expected": {"qkd_sweeps": expected},
    }

    # Remove null engine for a cleaner artifact.
    if bundle["engine"] is None:
        bundle.pop("engine", None)

    return bundle
