from __future__ import annotations

import json
from pathlib import Path

from photonstrust.calibrate.pic_crosstalk import load_pic_crosstalk_sweep, fit_parallel_waveguide_crosstalk_model


def test_pic_crosstalk_calibration_recovers_synthetic_params():
    root = Path(__file__).resolve().parents[1]
    sweep_path = root / "tests" / "fixtures" / "measurement_bundle_pic_crosstalk" / "data" / "pic_crosstalk_sweep.json"
    baseline_path = root / "tests" / "fixtures" / "pic_crosstalk_calibration_baseline.json"

    sweep = load_pic_crosstalk_sweep(sweep_path)
    report = fit_parallel_waveguide_crosstalk_model(sweep)

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    expected = baseline["expected"]["params"]

    fitted = report["fit"]["params"]
    assert abs(float(fitted["kappa0_per_um"]) - float(expected["kappa0_per_um"])) / float(expected["kappa0_per_um"]) < 1e-6
    assert abs(float(fitted["gap_decay_um"]) - float(expected["gap_decay_um"])) / float(expected["gap_decay_um"]) < 1e-6
    assert abs(float(fitted["lambda_exp"]) - float(expected["lambda_exp"])) < 1e-6
