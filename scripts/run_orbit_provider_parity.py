#!/usr/bin/env python3
"""Run orbit-provider parity checks for satellite-chain configs."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from photonstrust.config import load_config


def _default_run_provider_parity(
    *,
    config: dict[str, Any],
    providers: list[str],
    reference_provider: str | None,
) -> dict[str, Any]:
    try:
        from photonstrust.orbit.providers.api import run_provider_parity as parity_api
    except Exception as exc:
        raise RuntimeError("orbit provider parity API unavailable") from exc

    call_attempts: list[tuple[tuple[Any, ...], dict[str, Any]]] = [
        (
            tuple(),
            {
                "config": config,
                "provider_a": providers[0],
                "provider_b": providers[1],
                "reference_provider": reference_provider,
            },
        ),
        (
            tuple(),
            {
                "config": config,
                "providers": providers,
                "reference_provider": reference_provider,
            },
        ),
        ((config, providers[0], providers[1]), {"reference_provider": reference_provider}),
        ((config, providers), {"reference_provider": reference_provider}),
    ]

    for args, kwargs in call_attempts:
        try:
            return parity_api(*args, **kwargs)
        except TypeError:
            continue

    return parity_api(config=config, providers=providers)


run_provider_parity = _default_run_provider_parity


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run orbit-provider parity checks")
    parser.add_argument("configs", nargs="+", help="One or more satellite config files")
    parser.add_argument(
        "--output-dir",
        default="results/orbit_provider_parity",
        help="Directory for parity report artifacts",
    )
    parser.add_argument(
        "--include-orekit",
        action="store_true",
        help="Force-enable orekit reference provider lane",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail when parity threshold violations are found",
    )
    return parser.parse_args()


def _config_execution_mode(config: dict[str, Any]) -> str:
    chain = config.get("satellite_qkd_chain") if isinstance(config, dict) else None
    if isinstance(chain, dict):
        runtime = chain.get("runtime")
        if isinstance(runtime, dict):
            mode = str(runtime.get("execution_mode") or "").strip().lower()
            if mode:
                return mode
    mode = str((config or {}).get("execution_mode") or "preview").strip().lower()
    return mode or "preview"


def _orekit_requested(config: dict[str, Any], *, cli_force: bool) -> bool:
    if cli_force:
        return True

    chain = config.get("satellite_qkd_chain") if isinstance(config, dict) else None
    if not isinstance(chain, dict):
        return False

    candidate_blocks: list[dict[str, Any]] = []
    for key in ("orbit_provider", "orbit", "parity"):
        block = chain.get(key)
        if isinstance(block, dict):
            candidate_blocks.append(block)
    for block in list(candidate_blocks):
        nested = block.get("parity")
        if isinstance(nested, dict):
            candidate_blocks.append(nested)

    for block in candidate_blocks:
        if bool(block.get("include_orekit")):
            return True
        if bool(block.get("orekit_reference")):
            return True
        if str(block.get("reference_provider") or "").strip().lower() == "orekit":
            return True
    return False


def _is_missing_provider_error(exc: Exception) -> bool:
    if isinstance(exc, (ImportError, ModuleNotFoundError)):
        return True
    text = str(exc).lower()
    tokens = (
        "not installed",
        "missing provider",
        "provider api unavailable",
        "unavailable",
    )
    return any(token in text for token in tokens)


def _collect_threshold_violations(parity_result: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("threshold_violations", "violations", "parity_violations", "breaches"):
        rows = parity_result.get(key)
        if isinstance(rows, list):
            return [dict(row) for row in rows if isinstance(row, dict)]

    comparisons = parity_result.get("comparisons")
    if not isinstance(comparisons, list):
        return []

    violations: list[dict[str, Any]] = []
    for row in comparisons:
        if not isinstance(row, dict):
            continue
        metric = str(row.get("metric") or "unknown")
        delta_abs = row.get("delta_abs")
        delta_rel = row.get("delta_rel")
        threshold_abs = row.get("threshold_abs")
        threshold_rel = row.get("threshold_rel")
        if threshold_abs is not None and delta_abs is not None and float(delta_abs) > float(threshold_abs):
            violations.append(
                {
                    "metric": metric,
                    "delta_kind": "abs",
                    "observed": float(delta_abs),
                    "limit": float(threshold_abs),
                }
            )
        if threshold_rel is not None and delta_rel is not None and float(delta_rel) > float(threshold_rel):
            violations.append(
                {
                    "metric": metric,
                    "delta_kind": "rel",
                    "observed": float(delta_rel),
                    "limit": float(threshold_rel),
                }
            )
    return violations


def _config_id(config: dict[str, Any], config_path: Path) -> str:
    chain = config.get("satellite_qkd_chain") if isinstance(config, dict) else None
    if isinstance(chain, dict):
        value = str(chain.get("id") or "").strip()
        if value:
            return value
    return config_path.stem


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []

    for raw_path in args.configs:
        cfg_path = Path(raw_path).expanduser().resolve()
        row: dict[str, Any] = {
            "config_path": str(cfg_path),
            "config_id": cfg_path.stem,
            "providers": ["skyfield", "poliastro"],
            "reference_provider": None,
            "execution_mode": "preview",
            "status": "ok",
            "threshold_violations": [],
        }

        try:
            config = load_config(cfg_path)
            row["config_id"] = _config_id(config, cfg_path)
            row["execution_mode"] = _config_execution_mode(config)
            include_orekit = _orekit_requested(config, cli_force=bool(args.include_orekit))
            row["reference_provider"] = "orekit" if include_orekit else None

            parity_result = run_provider_parity(
                config=config,
                providers=["skyfield", "poliastro"],
                reference_provider=row["reference_provider"],
            )
            parity_payload = dict(parity_result) if isinstance(parity_result, dict) else {"result": parity_result}
            row["parity"] = parity_payload
            row["threshold_violations"] = _collect_threshold_violations(parity_payload)
            if row["threshold_violations"]:
                row["status"] = "violations"
        except Exception as exc:
            row["error"] = str(exc)
            if _is_missing_provider_error(exc) and row["execution_mode"] == "preview":
                row["status"] = "skipped_missing_provider"
            else:
                row["status"] = "error"
        records.append(row)

    threshold_violations_total = sum(len(row.get("threshold_violations", [])) for row in records)
    status_counts: dict[str, int] = {}
    for row in records:
        status = str(row.get("status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

    hard_errors = status_counts.get("error", 0)
    strict_block = bool(args.strict) and threshold_violations_total > 0
    ok = hard_errors == 0 and not strict_block

    report = {
        "kind": "orbit_provider_parity_report",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "strict_mode": bool(args.strict),
        "status": "ok" if ok else "failed",
        "summary": {
            "configs_total": len(records),
            "status_counts": status_counts,
            "threshold_violations_total": int(threshold_violations_total),
            "providers_checked": ["skyfield", "poliastro"],
            "orekit_reference_enabled": any(bool(row.get("reference_provider")) for row in records),
        },
        "records": records,
    }

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = output_dir / f"orbit_provider_parity_report_{stamp}.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    summary = {
        "ok": bool(ok),
        "strict_mode": bool(args.strict),
        "configs_total": len(records),
        "status_counts": status_counts,
        "threshold_violations_total": int(threshold_violations_total),
        "report_path": str(report_path),
    }
    print(json.dumps(summary, separators=(",", ":"), sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
