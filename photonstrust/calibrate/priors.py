"""Default priors for calibration."""

DEFAULT_EMITTER_PRIORS = {
    "radiative_lifetime_ns": (0.2, 5.0),
    "purcell_factor": (1.0, 20.0),
    "dephasing_rate_per_ns": (0.0, 2.0),
    "g2_0": (0.001, 0.2),
}

DEFAULT_DETECTOR_PRIORS = {
    "pde": (0.1, 0.9),
    "dark_counts_cps": (10.0, 2000.0),
    "jitter_ps_fwhm": (10.0, 200.0),
}

DEFAULT_MEMORY_PRIORS = {
    "t1_ms": (1.0, 200.0),
    "t2_ms": (0.5, 50.0),
    "retrieval_efficiency": (0.3, 0.95),
}
