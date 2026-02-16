from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from photonstrust.calibrate.pic_crosstalk import load_pic_crosstalk_sweep, fit_parallel_waveguide_crosstalk_model


def _rel_err(obs: float, exp: float) -> float:
    if exp == 0:
        return float("inf") if obs != 0 else 0.0
    return abs(obs - exp) / abs(exp)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check drift for PIC crosstalk calibration (deterministic gate).")
    parser.add_argument(
        "--sweep",
        type=Path,
        default=Path("tests/fixtures/measurement_bundle_pic_crosstalk/data/pic_crosstalk_sweep.json"),
        help="Path to pic_crosstalk_sweep.json",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=Path("tests/fixtures/pic_crosstalk_calibration_baseline.json"),
        help="Path to baseline calibration expectations JSON.",
    )
    args = parser.parse_args()

    sweep = load_pic_crosstalk_sweep(args.sweep)
    report = fit_parallel_waveguide_crosstalk_model(sweep)

    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    exp = (baseline.get("expected") or {}).get("params") or {}
    tol = baseline.get("tolerances") or {}

    fitted = (((report.get("fit") or {}).get("params") or {}) if isinstance(report, dict) else {}) or {}

    failures = []

    def get(name: str) -> float:
        return float(fitted.get(name))

    kappa0 = get("kappa0_per_um")
    gd = get("gap_decay_um")
    lam_exp = get("lambda_exp")

    exp_kappa0 = float(exp.get("kappa0_per_um"))
    exp_gd = float(exp.get("gap_decay_um"))
    exp_lam_exp = float(exp.get("lambda_exp"))

    kappa0_rel_tol = float(tol.get("kappa0_rel_tol", 1e-6))
    gd_rel_tol = float(tol.get("gap_decay_rel_tol", 1e-6))
    lam_exp_abs_tol = float(tol.get("lambda_exp_abs_tol", 1e-6))

    if not math.isfinite(kappa0) or not math.isfinite(gd) or not math.isfinite(lam_exp):
        failures.append("non-finite fitted parameters")
    if _rel_err(kappa0, exp_kappa0) > kappa0_rel_tol:
        failures.append(f"kappa0_per_um drift: observed={kappa0} expected={exp_kappa0} rel_tol={kappa0_rel_tol}")
    if _rel_err(gd, exp_gd) > gd_rel_tol:
        failures.append(f"gap_decay_um drift: observed={gd} expected={exp_gd} rel_tol={gd_rel_tol}")
    if abs(lam_exp - exp_lam_exp) > lam_exp_abs_tol:
        failures.append(f"lambda_exp drift: observed={lam_exp} expected={exp_lam_exp} abs_tol={lam_exp_abs_tol}")

    rmse_db = float(((report.get("metrics") or {}).get("rmse_db") or 0.0))
    rmse_max = float((baseline.get("expected") or {}).get("rmse_db_max", 1e-6))
    if rmse_db > rmse_max:
        failures.append(f"rmse_db drift: observed={rmse_db} max={rmse_max}")

    if failures:
        print("PIC crosstalk calibration drift check: FAIL")
        for f in failures:
            print(f" - {f}")
        return 1

    print("PIC crosstalk calibration drift check: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

