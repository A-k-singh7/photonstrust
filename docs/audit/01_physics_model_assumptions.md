# 01 - Physics Model Assumptions & Corrections

This document is intentionally "engineering-forward": it records assumptions in the current
models and links them to primary sources so future improvements can be made without
guesswork.

## Primary Sources Used (Quick Index)

- PLOB bound / repeaterless capacity benchmark: Pirandola et al. (2017) Nature Communications, DOI: 10.1038/ncomms15043
- Airmass at low elevation: Kasten & Young (1989) Applied Optics, DOI: 10.1364/AO.28.004735
- Detector efficiency spectral dependence (example SNSPD results): Marsili et al. (2012) Nature Photonics, DOI: 10.1038/nphoton.2012.35; Hu et al. (2020) Nature Photonics, DOI: 10.1038/s41566-020-0677-4
- Afterpulsing measurement context (InGaAs SPAD): Restelli et al. (2012) J. Mod. Opt., DOI: 10.1080/09500340.2012.668831

## Finding 1: QBER error sources assumed independent

**Location (historical):** `photonstrust/qkd.py` (pre-Phase 46)

```python
q_total = clamp(q_multi + q_dark + q_timing + q_mis + q_source, 0.0, 0.5)
```

**Issue (historical):** Five QBER contributions were added linearly, implicitly
assuming independence. This can overcount total QBER.

**Risk:** Medium. Overestimating QBER is conservative but reduces usefulness for
performance-grade predictions.

**Correction:**

Option A (document-only): Add a comment block in `qkd.py` above line 180:

```python
# ASSUMPTION: QBER contributions are combined additively under the assumption
# of statistical independence. This is conservative (may overestimate QBER)
# when noise sources are correlated (e.g., dark + Raman in coexistence
# channels). See docs/audit/01_physics_model_assumptions.md for details.
```

Option B (model improvement): Introduce a correlation matrix between noise
terms. This requires experimental data or literature values for cross-term
magnitudes. Suggested approach:

```python
# Future: replace additive QBER with matrix formulation
# Q = sum_i q_i + sum_{i<j} rho_ij * sqrt(q_i * q_j)
# where rho_ij are pairwise correlation coefficients (default 0 = independent)
```

**Implemented (Phase 46 / 2026-02-15):**

- Direct-link BBM92/E91 moved to a coincidence-based model in `photonstrust/qkd_protocols/bbm92.py`.
- QBER is computed as a true/accidental mixture:
  - `E = (e_vis*Q_true + 0.5*Q_acc) / Q`
  - with explicit multi-pair vs noise-involved accidental decomposition.
- The Reliability Card error-budget fractions are derived from these coincidence components (they sum to total QBER by construction for the direct-link BBM92 surface).

**Research anchors:**
- Raman noise / coexistence channels: Branca et al., "Raman Scattering Noise in Fiber Optic Quantum Key Distribution Systems" (2024), DOI: 10.1109/JLT.2024.3360756

---

## Finding 2: Emitter dephasing rate units ambiguous

**Location:** `photonstrust/physics/emitter.py:51,76`

```python
dephasing = max(0.0, float(source.get("dephasing_rate_per_ns", 0.5)))
...
linewidth_mhz = max(0.0, ((gamma_eff + dephasing) * 1e3) / (2.0 * math.pi))
```

**Issue:** `dephasing_rate_per_ns` is treated as a decay rate (units: 1/ns) and
added directly to `gamma_eff` (also 1/ns). However, the variable name is
ambiguous -- it could mean the pure dephasing rate `gamma_phi` or the total
dephasing rate `gamma_2 = gamma_1/2 + gamma_phi`.

In cavity-QED literature:
- `T2* = 1 / (gamma_1/2 + gamma_phi)` (total dephasing time)
- Linewidth (FWHM) = `(gamma_1 + 2*gamma_phi) / (2*pi)` in frequency units

The current formula `(gamma_eff + dephasing) / (2*pi)` implies `dephasing` is
the full `2*gamma_phi`, which should be documented.

**Risk:** High. If a user sets `dephasing_rate_per_ns` to a published `gamma_phi`
value, the linewidth will be correct. But if they use `1/T2*` the linewidth
will be wrong by a factor that depends on the Purcell factor.

**Correction:**

1. Rename the parameter for clarity:

```python
# In config defaults and documentation:
# dephasing_rate_per_ns -> pure_dephasing_rate_per_ns (gamma_phi)
# This is the pure dephasing rate, NOT 1/T2*.
# Linewidth = (gamma_1 + 2*gamma_phi) / (2*pi) MHz
```

2. Add a docstring to `_analytic_emitter()`:

```python
"""Analytic emitter-cavity model.

Parameters (from source config):
  radiative_lifetime_ns: Spontaneous emission lifetime (T1 = 1/gamma_1).
  purcell_factor: Cavity enhancement factor F_P. Effective decay rate is
      gamma_eff = gamma_1 * (1 + F_P).
  dephasing_rate_per_ns: Pure dephasing rate gamma_phi (1/ns).
      Linewidth = (gamma_eff + gamma_phi) * 1e3 / (2*pi) MHz.
      NOTE: This is gamma_phi, not 1/T2*. If you have T2*, convert via
      gamma_phi = 1/T2* - gamma_eff/2.
"""
```

**Research anchors (units + definitions):**
- Dephasing decomposition commonly written as: Gamma2 = Gamma1/2 + Gamma_phi (equivalently 1/T2 = 1/(2T1) + 1/T_phi).
  A representative reference stating this relation explicitly: Bylander et al. (2011) Nature Physics, DOI: 10.1038/nphys1994

---

## Finding 3: Afterpulse jitter ratio has no literature basis

**Location:** `photonstrust/physics/detector.py:75`

```python
ap_jitter = max(1.0, jitter_ps * 0.25)
```

**Issue:** Afterpulse timing jitter is hardcoded at 25% of signal jitter. This
ratio is plausible for InGaAs SPADs but not universal. SNSPDs have different
afterpulse timing characteristics. No citation is provided.

**Risk:** Low. Affects timing distribution shape, not key rate significantly.

**Correction:**

Add the ratio as a configurable parameter with the current value as default:

```python
afterpulse_jitter_ratio = float(
    detector_cfg.get("afterpulse_jitter_ratio", 0.25)
)
ap_jitter = max(1.0, jitter_ps * afterpulse_jitter_ratio)
```

Add a comment with the assumption source:

```python
# Default ratio must be treated as a heuristic unless tied to a specific detector
# characterization. Afterpulsing behavior depends on detector technology and
# operating conditions (e.g., gating, temperature, dead-time strategy).
```

**Research anchors (afterpulsing context):**
- Restelli et al. (2012), characterization/mitigation methods for afterpulsing in InGaAs SPADs, DOI: 10.1080/09500340.2012.668831

---

## Finding 4: Free-space airmass proxy invalid at low elevation

**Location:** `photonstrust/channels/free_space.py:95-97`

```python
elevation_deg = _clamp(float(elevation_deg), 0.0, 90.0)
airmass = max(1.0, _kasten_young_airmass(elevation_deg))
```

**Issue (pre-Phase 39):** The earlier `1/sin(h)` plane-parallel airmass proxy is
accurate above ~15 degrees elevation. Between 5-15 degrees it diverges from
the Kasten & Young (1989) approximation by up to ~10%. Below 5 degrees it is
unreliable.

**Risk:** Medium. Satellite downlink scenarios at low elevation angles (horizon
passes) will have inaccurate loss estimates.

**Correction:**

1. Add a warning for low elevation:

```python
if elevation_deg < 5.0:
    import warnings
    warnings.warn(
        f"Elevation {elevation_deg:.1f} deg is below 5 deg. The plane-parallel "
        f"airmass approximation (1/sin h) may overestimate atmospheric loss by "
        f">10%. Consider using the Kasten & Young (1989) formula for accuracy.",
        stacklevel=2,
    )
```

2. Optionally implement the Kasten & Young formula:

```python
def _kasten_young_airmass(elevation_deg: float) -> float:
    """Kasten & Young (1989) airmass formula, valid down to horizon."""
    h = max(0.0, float(elevation_deg))
    return 1.0 / (math.sin(math.radians(h)) + 0.50572 * (h + 6.07995) ** -1.6364)
```

**Implemented (Phase 39 / 2026-02-14):**
- `atmospheric_transmission()` now uses the Kasten & Young (1989) approximation.
- A warning is emitted for elevation angles below 5 degrees.

**Research anchors:**
- Kasten & Young (1989), "Revised optical air mass tables and approximation formula", Applied Optics, DOI: 10.1364/AO.28.004735

---

## Finding 5: No wavelength-dependent PDE

**Location:** `photonstrust/physics/detector.py:26`

```python
pde = _clamp_probability(detector_cfg.get("pde", 0.0), "pde")
```

**Issue:** PDE is a single scalar value. Real detectors (SNSPDs, InGaAs SPADs)
have wavelength-dependent efficiency that varies 10-20% across a telecom band.

**Risk:** Medium for cross-band comparisons. A C-band SNSPD at 1550 nm might
have PDE=0.90 but only PDE=0.80 at 1530 nm.

**Correction:**

For v0.2, add optional wavelength-dependent PDE lookup:

```python
pde_spectrum = detector_cfg.get("pde_spectrum")  # {wavelength_nm: pde}
if pde_spectrum and wavelength_nm is not None:
    pde = _interpolate_pde(pde_spectrum, wavelength_nm)
else:
    pde = _clamp_probability(detector_cfg.get("pde", 0.0), "pde")
```

For v0.1, document the flat-PDE assumption in the config:

```yaml
detector:
  class: snspd
  pde: 0.90  # NOTE: flat across band. See docs/audit/01_physics_model_assumptions.md
```

**Research anchors (example wavelength dependence):**
- Marsili et al. (2012) high-efficiency SNSPD system results across telecom wavelengths, DOI: 10.1038/nphoton.2012.35
- Hu et al. (2020) high-efficiency SNSPD systems across ~1530-1630 nm, DOI: 10.1038/s41566-020-0677-4

---

## Finding 6: Hardcoded seed in uncertainty computation

**Location:** `photonstrust/qkd.py:259`

```python
seed_raw = uncertainty.get("seed", scenario.get("seed", 42))
rng = np.random.default_rng(seed_base + sample_idx)
```

**Issue (pre-Phase 39):** Uncertainty sampling always used seed 42. This was
good for reproducibility but not configurable, and prevented seed-sensitivity
checks.

**Risk:** Low. But prevents users from verifying that results are seed-stable
or running independent Monte Carlo ensembles.

**Correction:**

Thread the seed through the scenario config:

```python
uncertainty_seed = int(scenario.get("uncertainty", {}).get("seed", 42))
rng = np.random.default_rng(uncertainty_seed)
```

**Implemented (Phase 39 / 2026-02-14):**
- `_compute_uncertainty()` now accepts `uncertainty.seed` (fallback: `scenario.seed`, fallback: 42).
- The RNG is derived per sample (`seed_base + sample_idx`) to preserve determinism if sampling is later parallelized.

---

## Finding 7: Silent QuTiP fallback

**Location:** `photonstrust/physics/emitter.py:25-31`

```python
except Exception as exc:
    warnings.warn(f"QuTiP backend unavailable, using analytic model: {exc}")
```

**Issue:** When QuTiP is requested but unavailable, the emitter silently falls
back to the analytic model. Users may not notice the warning and assume they
are running the full quantum model.

**Correction:**

Add a `require_backend` config option:

```python
if requested_backend == "qutip":
    require = bool(source.get("require_backend", False))
    try:
        stats = _qutip_emitter(source, emission_mode=emission_mode)
    except Exception as exc:
        if require:
            raise RuntimeError(
                f"QuTiP backend required but unavailable: {exc}. "
                f"Install with: pip install 'photonstrust[qutip]'"
            ) from exc
        warnings.warn(...)
        stats = _analytic_emitter(...)
```

---

## Finding 8: Missing PLOB bound sanity check

**Issue (pre-Phase 39):** There was no test that verifies computed key rates
respect the repeaterless (PLOB) bound: `R <= -log2(1 - eta)` where `eta` is
total channel transmittance. Exceeding this bound indicates a physics model
error.

**Correction:**

Add a test that enforces the PLOB repeaterless bound as a hard sanity check:

- File: `tests/test_qkd_plob_bound.py`
- Check: `compute_point(...).key_rate_bps <= (-log2(1 - eta) * rep_rate_hz) * (1 + tol)`
  where `eta = 10 ** (-loss_db / 10.0)` is the modeled channel transmittance.

**Implemented (Phase 39 / 2026-02-14):**
- Added `tests/test_qkd_plob_bound.py` which checks that `compute_point()` does not exceed the PLOB bound
  (converted to bps via `rep_rate_mhz`).

**Research anchors:**
- Pirandola et al. (2017), "Fundamental limits of repeaterless quantum communications" (PLOB bound / rate-loss tradeoff benchmark), DOI: 10.1038/ncomms15043

---

## Summary Table

| # | Finding | Severity | Fix Effort | Location |
|---|---------|----------|------------|----------|
| 1 | QBER independence assumption | Medium | Low (doc) | qkd.py:180 |
| 2 | Dephasing rate units ambiguous | High | Low (rename+doc) | emitter.py:51,76 |
| 3 | Afterpulse jitter ratio unjustified | Low | Low (make configurable) | detector.py:75 |
| 4 | Airmass proxy invalid at low elev | Medium | Medium (warning+formula) | free_space.py:95-97 |
| 5 | No wavelength-dependent PDE | Medium | Medium (interpolation) | detector.py:26 |
| 6 | Hardcoded uncertainty seed | Low | Low (config thread) | qkd.py:259 |
| 7 | Silent QuTiP fallback | Medium | Low (require_backend flag) | emitter.py:25-31 |
| 8 | Missing PLOB bound check | High | Low (add test) | tests/ (new) |

---

## Roadmap: Research-Backed Model Extensions (v0.2+)

These are high-leverage additions that materially increase "decision-grade"
accuracy and credibility, and are well supported by literature.

1. **Finite-key analysis (composable security)**
   - Add an explicit finite-key module (`finite_key.*`) and surface it in cards
     as an evidence requirement for Tier 2+.
   - Anchors: Tomamichel et al. (2012) Nature Communications, DOI: 10.1038/ncomms1631; Curty et al. (2019) Nature Communications, DOI: 10.1038/s41467-019-12670-5

2. **MDI-QKD and TF/PM-QKD protocol families**
   - Implement rate models and operating envelopes; publish canonical configs.
   - Anchors: Lo, Curty, Qi (2012) PRL (MDI-QKD), DOI: 10.1103/PhysRevLett.108.130503;
     Lucamarini et al. (2018) Nature (TF-QKD), DOI: 10.1038/s41586-018-0066-6;
     Ma et al. (2018) PRX (PM-QKD), DOI: 10.1103/PhysRevX.8.031043

3. **Satellite/free-space realism pack**
   - Expand background noise + filtering models, pointing/turbulence options, and
     validate against published satellite-to-ground system results.
   - Anchors: Liao et al. (2017) Nature, DOI: 10.1038/nature23655; Bedington et al. (2017) Nature, DOI: 10.1038/nature23675;
     Ko et al. (2018) Scientific Reports (daylight filtering considerations), DOI: 10.1038/s41598-018-34980-9

4. **Published-system calibration targets**
   - Add "literature benchmark configs" and hold them as golden/qualification tests.
   - Anchor example: Boaron et al. (2018) PRL, DOI: 10.1103/PhysRevLett.121.190502
