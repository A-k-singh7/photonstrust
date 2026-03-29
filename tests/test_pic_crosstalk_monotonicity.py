from __future__ import annotations

from photonstrust.components.pic.crosstalk import (
    predict_parallel_waveguide_xt_db,
    recommended_min_gap_um,
)


def test_crosstalk_monotonic_in_gap_and_length():
    xt_tight = predict_parallel_waveguide_xt_db(
        gap_um=0.4,
        parallel_length_um=1000.0,
        wavelength_nm=1550.0,
    )
    xt_loose = predict_parallel_waveguide_xt_db(
        gap_um=1.0,
        parallel_length_um=1000.0,
        wavelength_nm=1550.0,
    )
    assert xt_tight >= xt_loose

    xt_short = predict_parallel_waveguide_xt_db(
        gap_um=0.6,
        parallel_length_um=200.0,
        wavelength_nm=1550.0,
    )
    xt_long = predict_parallel_waveguide_xt_db(
        gap_um=0.6,
        parallel_length_um=2000.0,
        wavelength_nm=1550.0,
    )
    assert xt_long >= xt_short


def test_recommended_gap_meets_target_spec():
    model = {"kappa0_per_um": 1.0e-3, "gap_decay_um": 0.2}
    target = -40.0
    gap = recommended_min_gap_um(
        target_xt_db=target,
        parallel_length_um=1000.0,
        wavelength_nm=1550.0,
        model=model,
    )
    achieved = predict_parallel_waveguide_xt_db(
        gap_um=gap,
        parallel_length_um=1000.0,
        wavelength_nm=1550.0,
        model=model,
    )
    # Allow small numerical slack due to log/float rounding.
    assert achieved <= target + 1e-6
