"""Calibration helpers for PIC crosstalk primitives (v0.1).

This is intentionally small and deterministic: the goal is to create an
evidence-producing calibration loop suitable for CI drift gates and for
academic inspection.
"""

from __future__ import annotations

import json
import math
import platform
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from photonstrust.components.pic.crosstalk import predict_parallel_waveguide_xt_db
from photonstrust.measurements._paths import schemas_dir
from photonstrust.measurements.schema import validate_instance
from photonstrust.utils import hash_dict


@dataclass(frozen=True)
class PicCrosstalkSweep:
    parallel_length_um: float
    lambda_ref_nm: float
    wavelengths_nm: list[float]
    gaps_um: list[float]
    xt_db: list[list[float]]  # shape: [len(gaps)][len(wavelengths)]
    notes: str | None = None
    provenance: dict[str, Any] | None = None


def pic_crosstalk_sweep_schema_path() -> Path:
    return schemas_dir() / "photonstrust.pic_crosstalk_sweep.v0.schema.json"


def load_pic_crosstalk_sweep(path: str | Path, *, require_jsonschema: bool = True) -> PicCrosstalkSweep:
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("pic crosstalk sweep must be a JSON object")
    validate_instance(data, pic_crosstalk_sweep_schema_path(), require_jsonschema=require_jsonschema)

    L = float(data["parallel_length_um"])
    lam_ref = float(data["lambda_ref_nm"])
    wls = [float(x) for x in (data.get("wavelengths_nm") or [])]
    gaps = [float(x) for x in (data.get("gaps_um") or [])]
    xt = data.get("xt_db") or []
    if not isinstance(xt, list):
        raise ValueError("xt_db must be a 2D array")
    if len(xt) != len(gaps):
        raise ValueError("xt_db row count must match gaps_um length")
    for row in xt:
        if not isinstance(row, list):
            raise ValueError("xt_db must be a 2D array")
        if len(row) != len(wls):
            raise ValueError("xt_db column count must match wavelengths_nm length")

    xt_f = [[float(v) for v in row] for row in xt]
    return PicCrosstalkSweep(
        parallel_length_um=L,
        lambda_ref_nm=lam_ref,
        wavelengths_nm=wls,
        gaps_um=gaps,
        xt_db=xt_f,
        notes=(str(data.get("notes")) if data.get("notes") is not None else None),
        provenance=(data.get("provenance") if isinstance(data.get("provenance"), dict) else None),
    )


def fit_parallel_waveguide_crosstalk_model(
    sweep: PicCrosstalkSweep,
    *,
    corner_scale: float = 1.0,
    require_quadratic_region: bool = True,
    max_xt_db_for_fit: float = -3.0,
) -> dict[str, Any]:
    """Fit the v0 crosstalk model parameters from a sweep.

    We fit a linearized form of the quadratic approximation region:
      XT_dB = 20*log10(kappa0) - (20/ln(10))*(gap/gd) + 20*lambda_exp*log10(lambda/lambda_ref) + 20*log10(L*corner_scale)

    The fit is deterministic and uses numpy least squares.
    """

    L = float(sweep.parallel_length_um)
    if L <= 0.0:
        raise ValueError("parallel_length_um must be > 0")
    lam_ref = float(sweep.lambda_ref_nm)
    if lam_ref <= 1.0:
        raise ValueError("lambda_ref_nm must be > 1")
    corner_scale = float(corner_scale)
    if not math.isfinite(corner_scale) or corner_scale <= 0.0:
        raise ValueError("corner_scale must be finite and > 0")

    # Build observation table.
    obs = []
    for gi, gap in enumerate(sweep.gaps_um):
        for wi, wl in enumerate(sweep.wavelengths_nm):
            xt = float(sweep.xt_db[gi][wi])
            if require_quadratic_region and xt > float(max_xt_db_for_fit):
                # Too close to saturation; provides weak/biased info for the linearized fit.
                continue
            obs.append((float(gap), float(wl), float(xt)))
    if len(obs) < 6:
        raise ValueError("insufficient observations for fit (need >= 6 after filtering)")

    gaps = np.array([o[0] for o in obs], dtype=float)
    wls = np.array([o[1] for o in obs], dtype=float)
    xts = np.array([o[2] for o in obs], dtype=float)

    # Response adjusted to isolate kappa:
    # xt_db = 20*log10(kappa) + 20*log10(L) + 20*log10(corner_scale)
    # => y = xt_db - 20*log10(L*corner_scale) = 20*log10(kappa)
    y = xts - 20.0 * np.log10(L * corner_scale)
    x_lambda = np.log10(wls / lam_ref)

    # Linear model: y = A + B*gap + C*log10(wl/lam_ref)
    X = np.column_stack([np.ones_like(gaps), gaps, x_lambda])
    beta, residuals, rank, s = np.linalg.lstsq(X, y, rcond=None)
    A = float(beta[0])
    B = float(beta[1])
    C = float(beta[2])

    if not math.isfinite(A) or not math.isfinite(B) or not math.isfinite(C):
        raise ValueError("fit produced non-finite parameters")
    if B >= 0.0:
        raise ValueError("fit invalid: expected negative slope vs gap (B < 0)")

    kappa0_per_um = float(10 ** (A / 20.0))
    gap_decay_um = float(-20.0 / (B * math.log(10.0)))
    lambda_exp = float(C / 20.0)

    fitted = {
        "kappa0_per_um": kappa0_per_um,
        "gap_decay_um": gap_decay_um,
        "lambda_ref_nm": lam_ref,
        "lambda_exp": lambda_exp,
    }

    # Evaluate metrics on the full grid (including filtered points).
    errs = []
    for gi, gap in enumerate(sweep.gaps_um):
        for wi, wl in enumerate(sweep.wavelengths_nm):
            pred = float(
                predict_parallel_waveguide_xt_db(
                    gap_um=float(gap),
                    parallel_length_um=float(L),
                    wavelength_nm=float(wl),
                    model=fitted,
                    corner={"kappa_scale": corner_scale},
                )
            )
            err = pred - float(sweep.xt_db[gi][wi])
            if math.isfinite(err):
                errs.append(float(err))

    rmse = float(math.sqrt(sum(e * e for e in errs) / max(1, len(errs)))) if errs else None
    max_abs = float(max(abs(e) for e in errs)) if errs else None

    sweep_hash = hash_dict(
        {
            "parallel_length_um": L,
            "lambda_ref_nm": lam_ref,
            "wavelengths_nm": sweep.wavelengths_nm,
            "gaps_um": sweep.gaps_um,
            "xt_db": sweep.xt_db,
        }
    )

    return {
        "schema_version": "0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "kind": "pic_crosstalk_calibration_report",
        "fit_method": "least_squares_linearized_quadratic.v0",
        "sweep": {
            "parallel_length_um": L,
            "lambda_ref_nm": lam_ref,
            "wavelengths_nm": sweep.wavelengths_nm,
            "gaps_um": sweep.gaps_um,
            "notes": sweep.notes,
        },
        "fit": {
            "params": fitted,
            "corner_scale": corner_scale,
            "points_used": int(len(obs)),
            "filters": {
                "require_quadratic_region": bool(require_quadratic_region),
                "max_xt_db_for_fit": float(max_xt_db_for_fit),
            },
        },
        "metrics": {
            "rmse_db": rmse,
            "max_abs_error_db": max_abs,
        },
        "provenance": {
            "input_hash": sweep_hash,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
    }
