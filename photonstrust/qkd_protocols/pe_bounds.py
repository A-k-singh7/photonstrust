"""Parameter estimation bounds for composable finite-key proofs.

Random sampling without replacement confidence intervals for QBER,
phase error rate, and single-photon yields.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class PEBound:
    """Result of a parameter estimation bound calculation."""

    estimated_value: float
    confidence_interval_half_width: float
    lower_bound: float
    upper_bound: float
    sample_size: int
    confidence_level: float


def random_sampling_bound(
    *,
    n_sample: int,
    n_total: int,
    observed_rate: float,
    epsilon_pe: float,
) -> PEBound:
    """Serfling-type bound for random sampling without replacement.

    Uses the Serfling inequality to bound the deviation between the sample
    mean and the population mean for sampling without replacement.

    Parameters
    ----------
    n_sample : int
        Number of samples used for parameter estimation.
    n_total : int
        Total population size.
    observed_rate : float
        Observed rate in the sample (e.g. QBER).
    epsilon_pe : float
        Failure probability for parameter estimation.

    Returns
    -------
    PEBound
        Confidence interval around the observed rate.
    """
    n_sample = max(1, int(n_sample))
    n_total = max(n_sample, int(n_total))
    epsilon_pe = max(1e-30, float(epsilon_pe))
    observed_rate = max(0.0, min(1.0, float(observed_rate)))

    correction = (n_total - n_sample) / n_total
    if correction <= 0:
        half_width = 0.0
    else:
        half_width = math.sqrt(
            correction * math.log(1.0 / epsilon_pe) / (2.0 * n_sample)
        )

    lower = max(0.0, observed_rate - half_width)
    upper = min(1.0, observed_rate + half_width)

    return PEBound(
        estimated_value=observed_rate,
        confidence_interval_half_width=half_width,
        lower_bound=lower,
        upper_bound=upper,
        sample_size=n_sample,
        confidence_level=1.0 - epsilon_pe,
    )


def phase_error_upper_bound(
    *,
    n_sifted: int,
    n_test: int,
    observed_qber: float,
    epsilon_pe: float,
    protocol: str = "",
) -> PEBound:
    """Protocol-aware phase error upper bound including statistical fluctuation.

    For BB84-type protocols the bit error rate in one basis bounds the phase
    error rate in the conjugate basis, up to a finite-sample fluctuation term.

    Parameters
    ----------
    n_sifted : int
        Total sifted key length.
    n_test : int
        Number of bits used for parameter estimation (test bits).
    observed_qber : float
        Observed QBER in the test bits.
    epsilon_pe : float
        Failure probability for the parameter estimation step.
    protocol : str
        Protocol identifier for protocol-aware adjustments.

    Returns
    -------
    PEBound
        Upper bound on the phase error rate.
    """
    bound = random_sampling_bound(
        n_sample=n_test,
        n_total=n_sifted,
        observed_rate=observed_qber,
        epsilon_pe=epsilon_pe,
    )

    proto_upper = protocol.upper().replace("-", "_").replace(" ", "_")
    if proto_upper in ("MDI_QKD", "AMDI_QKD"):
        adjusted_upper = min(0.5, bound.upper_bound * 1.05)
    else:
        adjusted_upper = bound.upper_bound

    return PEBound(
        estimated_value=observed_qber,
        confidence_interval_half_width=bound.confidence_interval_half_width,
        lower_bound=bound.lower_bound,
        upper_bound=adjusted_upper,
        sample_size=bound.sample_size,
        confidence_level=bound.confidence_level,
    )
