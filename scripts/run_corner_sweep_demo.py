#!/usr/bin/env python3
"""Run a corner-sweep demo on the PIC QKD transmitter graph."""

from __future__ import annotations

import inspect
import json
from pathlib import Path


def _invoke_corner_sweep(
    run_fn: object,
    *,
    graph_path: Path,
    output_dir: Path,
) -> dict:
    if not callable(run_fn):
        raise TypeError("run_corner_sweep is not callable")

    try:
        sig = inspect.signature(run_fn)
        params = sig.parameters
    except (TypeError, ValueError):
        params = {}

    kwargs: dict[str, object] = {}

    def _set(names: tuple[str, ...], value: object) -> None:
        for name in names:
            if name in params:
                kwargs[name] = value
                return

    _set(("pdk_name", "pdk"), "generic_sip_corners")
    _set(("protocol",), "BB84_DECOY")
    _set(("target_distance_km", "target_distance"), 50.0)
    _set(("wavelength_nm", "wavelength"), 1550.0)
    _set(("n_monte_carlo", "monte_carlo"), 50)
    _set(("mc_seed",), 42)
    _set(("key_rate_threshold_bps", "threshold_bps", "threshold"), 1000.0)
    _set(("output_dir", "output_path"), output_dir)

    try:
        result = run_fn(graph_path, **kwargs)
    except TypeError:
        result = run_fn(
            graph_path,
            pdk_name="generic_sip_corners",
            protocol="BB84_DECOY",
            target_distance_km=50.0,
            wavelength_nm=1550.0,
            corner_set=None,
            n_monte_carlo=50,
            mc_seed=42,
            key_rate_threshold_bps=1000.0,
            output_dir=output_dir,
        )

    if not isinstance(result, dict):
        raise ValueError("run_corner_sweep returned a non-dict payload")
    return result


def _summarize(result: dict, *, output_dir: Path) -> dict:
    risk = result.get("risk_assessment") if isinstance(result.get("risk_assessment"), dict) else {}
    monte_carlo = result.get("monte_carlo") if isinstance(result.get("monte_carlo"), dict) else {}

    worst_corner = risk.get("worst_corner", result.get("worst_corner"))
    worst_case_key_rate_bps = risk.get("worst_case_key_rate_bps", result.get("worst_case_key_rate_bps"))
    risk_level = risk.get("risk_level", result.get("risk_level"))
    yield_above_threshold = risk.get("yield_above_threshold")
    if yield_above_threshold is None:
        yield_above_threshold = monte_carlo.get("yield_fraction")

    output_path_raw = result.get("output_path")
    if output_path_raw is None:
        output_path_raw = result.get("output_dir")
    output_path = str(output_path_raw) if output_path_raw is not None else str(output_dir.resolve())

    return {
        "output_path": output_path,
        "risk_level": risk_level,
        "worst_case_key_rate_bps": worst_case_key_rate_bps,
        "worst_corner": worst_corner,
        "yield_above_threshold": yield_above_threshold,
    }


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    graph_path = repo_root / "graphs" / "demo_qkd_transmitter.json"
    output_dir = (repo_root / "results" / "corner_sweep" / "demo_qkd_transmitter").resolve()

    try:
        from photonstrust.pic.corner_sweep import run_corner_sweep
    except Exception as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": f"corner_sweep_api_unavailable: {exc}",
                },
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        return 2

    try:
        result = _invoke_corner_sweep(
            run_corner_sweep,
            graph_path=graph_path,
            output_dir=output_dir,
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": f"corner_sweep_run_failed: {exc}",
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
