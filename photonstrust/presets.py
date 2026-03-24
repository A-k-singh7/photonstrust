"""Preset tables for bands and detectors."""

BAND_PRESETS = {
    "nir_795": {
        "wavelength_nm": 795,
        "fiber_loss_db_per_km": 2.5,
        "dispersion_ps_per_km": 2.0,
    },
    "nir_850": {
        "wavelength_nm": 850,
        "fiber_loss_db_per_km": 2.2,
        "dispersion_ps_per_km": 2.0,
    },
    "o_1310": {
        "wavelength_nm": 1310,
        "fiber_loss_db_per_km": 0.33,
        "dispersion_ps_per_km": 3.0,
    },
    "c_1550": {
        "wavelength_nm": 1550,
        "fiber_loss_db_per_km": 0.20,
        "dispersion_ps_per_km": 5.0,
    },
}

DETECTOR_PRESETS = {
    "si_apd": {
        "pde": 0.70,
        "dark_counts_cps": 100,
        "jitter_ps_fwhm": 50,
        "dead_time_ns": 50,
        "afterpulsing_prob": 0.005,
    },
    "ingaas": {
        "pde": 0.20,
        "dark_counts_cps": 500,
        "jitter_ps_fwhm": 80,
        "dead_time_ns": 10000,
        "afterpulsing_prob": 0.02,
    },
    "snspd": {
        "pde": 0.30,
        "dark_counts_cps": 100,
        "jitter_ps_fwhm": 30,
        "dead_time_ns": 100,
        "afterpulsing_prob": 0.001,
    },
}

DETECTOR_ADJUSTMENTS = {
    "nir_795": {"si_apd": {"pde_delta": 0.05, "dark_scale": 0.8}},
    "nir_850": {"si_apd": {"pde_delta": 0.05, "dark_scale": 0.8}},
    "o_1310": {"ingaas": {"pde_delta": 0.02, "dark_scale": 1.2}},
    "c_1550": {"snspd": {"pde_delta": 0.05, "dark_scale": 1.0}},
}


def get_band_preset(band):
    if band not in BAND_PRESETS:
        raise ValueError(f"Unknown band '{band}'")
    return dict(BAND_PRESETS[band])


def get_detector_preset(detector_class, band=None):
    if detector_class not in DETECTOR_PRESETS:
        raise ValueError(f"Unknown detector class '{detector_class}'")
    preset = dict(DETECTOR_PRESETS[detector_class])
    if band:
        band_adjustments = DETECTOR_ADJUSTMENTS.get(band, {})
        adj = band_adjustments.get(detector_class)
        if adj:
            preset["pde"] = max(0.0, min(1.0, preset["pde"] + adj.get("pde_delta", 0.0)))
            preset["dark_counts_cps"] *= adj.get("dark_scale", 1.0)
    return preset


def get_catalog():
    """Return the global :class:`ComponentCatalog` instance (lazy-loaded)."""
    from photonstrust.catalog.store import ComponentCatalog
    return ComponentCatalog()
