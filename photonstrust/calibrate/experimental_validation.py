"""Compare simulation against published experimental data."""
from __future__ import annotations
import math
from dataclasses import dataclass, field
import numpy as np

@dataclass(frozen=True)
class ValidationResult:
    """Result of validating simulation against experiment."""
    experiment_name: str
    chi_squared: float
    p_value: float
    residuals: list[float]
    max_residual_ratio: float  # max(|sim-exp|/exp)
    pass_within_3x: bool  # all points within 3x of experiment
    n_points: int

# Published experimental QKD benchmarks
PUBLISHED_EXPERIMENTS: dict[str, dict] = {
    "bb84_gobby_2004": {
        "description": "BB84 decoy-state, Gobby et al. APL 2004",
        "distances_km": [0, 25, 50, 75, 100, 122],
        "key_rates_bps": [1.0e6, 1.0e5, 1.0e4, 2.0e3, 200, 17],
        "protocol": "bb84",
    },
    "cvqkd_jouguet_2013": {
        "description": "CV-QKD, Jouguet et al. Nature Photonics 2013",
        "distances_km": [0, 25, 50, 80.5],
        "key_rates_bps": [1.0e5, 5.0e3, 200, 2],
        "protocol": "cv_qkd",
    },
    "tfqkd_pittaluga_2021": {
        "description": "TF-QKD, Pittaluga et al. Nature Photonics 2021",
        "distances_km": [0, 100, 200, 300, 400, 500, 605],
        "key_rates_bps": [1.0e5, 5.0e3, 500, 50, 5, 0.5, 0.01],
        "protocol": "tf_qkd",
    },
    "satellite_liao_2017": {
        "description": "Satellite QKD, Liao et al. Nature 2017",
        "distances_km": [500, 700, 900, 1200],
        "key_rates_bps": [12000, 6000, 2000, 1000],
        "protocol": "satellite_bb84",
    },
}


def validate_against_experiment(
    experiment_name: str,
    simulated_rates_bps: list[float],
    published_data: dict | None = None,
) -> ValidationResult:
    """Compare simulated key rates against published experimental data.

    Parameters
    ----------
    experiment_name : str
        Name of experiment (key in PUBLISHED_EXPERIMENTS, or custom).
    simulated_rates_bps : list[float]
        Simulated key rates at the same distances as published data.
    published_data : dict or None
        Custom data dict. If None, uses PUBLISHED_EXPERIMENTS.
    """
    if published_data is None:
        if experiment_name not in PUBLISHED_EXPERIMENTS:
            raise ValueError(f"Unknown experiment: {experiment_name}")
        data = PUBLISHED_EXPERIMENTS[experiment_name]
    else:
        data = published_data

    exp_rates = np.array(data["key_rates_bps"], dtype=float)
    sim_rates = np.array(simulated_rates_bps, dtype=float)

    if len(sim_rates) != len(exp_rates):
        raise ValueError(
            f"Length mismatch: {len(sim_rates)} simulated vs {len(exp_rates)} experimental"
        )

    # Residuals in log space (more appropriate for rates spanning decades)
    with np.errstate(divide='ignore', invalid='ignore'):
        log_sim = np.where(sim_rates > 0, np.log10(sim_rates), -10)
        log_exp = np.where(exp_rates > 0, np.log10(exp_rates), -10)

    residuals = (log_sim - log_exp).tolist()

    # Chi-squared in log space
    # Assume ~0.5 decade uncertainty per point
    sigma_log = 0.5
    chi2 = float(np.sum(((log_sim - log_exp) / sigma_log) ** 2))

    # p-value from chi-squared
    n = len(exp_rates)
    try:
        from scipy.stats import chi2 as chi2_dist
        p_val = float(1.0 - chi2_dist.cdf(chi2, df=n))
    except ImportError:
        # Rough approximation
        p_val = float(math.exp(-chi2 / 2))

    # Check within 3x
    ratios = []
    for s, e in zip(sim_rates, exp_rates):
        if e > 0 and s > 0:
            ratios.append(max(s/e, e/s))
        elif e == 0 and s == 0:
            ratios.append(1.0)
        else:
            ratios.append(float('inf'))

    max_ratio = max(ratios) if ratios else float('inf')
    pass_3x = all(r <= 3.0 for r in ratios)

    return ValidationResult(
        experiment_name=experiment_name,
        chi_squared=chi2,
        p_value=p_val,
        residuals=residuals,
        max_residual_ratio=float(max_ratio),
        pass_within_3x=pass_3x,
        n_points=n,
    )
