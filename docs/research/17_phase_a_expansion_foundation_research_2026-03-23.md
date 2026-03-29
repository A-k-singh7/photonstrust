# Phase A Scientific Research Document: Expansion Foundation

**Date:** 2026-03-23
**Scope:** Month 0-3 (Weeks 1-12)
**Status:** Research Complete — Ready for Implementation

---

## 1. Introduction and Scope

PhotonTrust Phase A transforms the platform from a fiber-QKD digital twin into a
dual-surface verification engine serving both photonic chip design teams
(ChipVerify) and satellite/space quantum link teams (OrbitVerify). This research
document establishes the scientific foundations, identifies implementation gaps,
and specifies the physics, mathematics, and engineering required to achieve Phase
A acceptance gates.

### 1.1 Phase A Deliverables (from Roadmap)

1. Free-space channel MVP integrated with existing fiber path
2. Detector gating/saturation model in physics engine
3. Fiber QKD deployment realism pack (coexistence noise, misalignment floor,
   finite-key mode)
4. Graph schema v0.1 and compiler service (graph JSON -> ScenarioConfig)
5. Initial ChipVerify alpha reports

### 1.2 Phase A Acceptance Gates

- 3 benchmark scenarios pass deterministic replay and diagnostics checks
- At least 1 QKD coexistence/finite-key scenario passes monotonicity + reporting
  gates
- Preview mode p95 runtime under 5 seconds for target scenarios

### 1.3 Current State Summary

After Phase 3+4 completion (15 features, 965 tests), the platform already
implements substantial Phase A foundations:

| Component | Status | Completeness |
|-----------|--------|-------------|
| Free-space channel | Implemented | ~75% |
| Stateful detector | Implemented | ~90% |
| Fiber Raman coexistence | Implemented | ~85% |
| Misalignment/visibility | Implemented | ~80% |
| Finite-key (v1 + v2 composable) | Implemented | ~95% |
| Graph schema v0.1 + compiler | Implemented | ~90% |
| PIC component library v1 | Implemented | ~95% |
| Web UI (React Flow) | Implemented | ~85% |
| ChipVerify orchestrator | Not started | 0% |
| Satellite realism hardening | Partial | ~40% |
| Fiber deployment hardening | Partial | ~60% |

This document identifies and specifies the remaining ~25 features/extensions
needed to close Phase A.

---

## 2. Free-Space and Satellite Channel Physics

### 2.1 Theoretical Framework

Free-space quantum channels differ fundamentally from fiber in their dominant
loss mechanisms. The total channel transmittance decomposes as:

$$\eta_{total} = \eta_{geom} \cdot \eta_{atm} \cdot \eta_{point} \cdot \eta_{turb} \cdot \eta_{optics}$$

where each factor represents an independent physical process.

### 2.2 Geometric Efficiency (Implemented)

The far-field beam spreading follows diffraction-limited divergence:

$$\theta_{div} = 1.22 \frac{\lambda}{D_{tx}}$$

where $\lambda$ is the wavelength and $D_{tx}$ is the transmitter aperture
diameter. The geometric collection efficiency at range $R$ is:

$$\eta_{geom} = \min\left(1, \left(\frac{D_{rx}}{2R \cdot \tan(\theta_{div})}\right)^2\right)$$

**Current implementation:** `channels/free_space.py::geometric_efficiency()`
supports diffraction-limited and custom beam divergence.

### 2.3 Atmospheric Transmission (Implemented, Needs Hardening)

#### 2.3.1 Effective Thickness Model

The atmosphere is modeled as a slab of effective thickness $h_{eff}$ (default
20 km). The atmospheric path length depends on elevation angle $\epsilon$:

$$L_{atm} = h_{eff} \cdot \sec(\epsilon)$$

with airmass $AM = \sec(\epsilon)$ for $\epsilon > 10°$. For low elevations,
the Kasten-Young approximation prevents divergence:

$$AM = \frac{1}{\sin(\epsilon) + 0.50572 \cdot (6.07995 + \epsilon)^{-1.6364}}$$

The atmospheric transmission is:

$$\eta_{atm} = 10^{-\alpha_{ext} \cdot L_{atm} / 10}$$

where $\alpha_{ext}$ is the extinction coefficient in dB/km.

**Current implementation:** `channels/free_space.py::atmospheric_transmission()`
with both `effective_thickness` and `slant_range` path models.

#### 2.3.2 Gap: Wavelength-Dependent Extinction Profile

Current model uses a single scalar extinction coefficient. Real atmospheric
extinction varies strongly with wavelength due to Rayleigh scattering
($\propto \lambda^{-4}$), Mie scattering (aerosols), and molecular absorption
bands (H2O, O2, O3).

**Proposed extension:** Add `extinction_model` parameter:
- `scalar` (current default): user-specified $\alpha_{ext}$
- `standard_atmosphere`: lookup table for standard visibility conditions at
  common QKD wavelengths (785, 810, 850, 1310, 1550 nm)

Standard atmosphere extinction values (clear, visibility 23 km):

| Wavelength (nm) | Extinction (dB/km) | Dominant Mechanism |
|-----------------|--------------------|--------------------|
| 785 | 0.07 | Rayleigh + Mie |
| 810 | 0.06 | Rayleigh + Mie |
| 850 | 0.05 | Mie |
| 1310 | 0.02 | Mie |
| 1550 | 0.015 | Mie |

References:
- Kim & Korevaar (2001) "Availability of free space optics (FSO) and hybrid
  FSO/RF systems" Proc. SPIE 4530
- Kaushal & Kaddoum (2017) "Optical Communication in Space" IEEE Commun.
  Surveys & Tutorials 19(1)

### 2.4 Turbulence and Scintillation (Partial, Needs Distribution Models)

#### 2.4.1 Current State

The platform implements a deterministic scintillation penalty:

$$\eta_{turb} = \exp(-\sigma_I^2)$$

where $\sigma_I^2$ is the scintillation index. This yields a single expected
efficiency but does not capture the stochastic fading that dominates satellite
link performance.

#### 2.4.2 Required: Fading Distribution Models

In the weak-turbulence regime ($\sigma_I^2 < 1$), the irradiance follows a
**lognormal distribution**:

$$f_I(I) = \frac{1}{I \sigma_{\ln I} \sqrt{2\pi}} \exp\left(-\frac{(\ln I - \mu_{\ln I})^2}{2\sigma_{\ln I}^2}\right)$$

where $\mu_{\ln I} = -\sigma_{\ln I}^2 / 2$ (normalized mean) and
$\sigma_{\ln I}^2 = \ln(1 + \sigma_I^2)$.

For moderate-to-strong turbulence, the **gamma-gamma distribution** provides
better accuracy:

$$f_I(I) = \frac{2(\alpha\beta)^{(\alpha+\beta)/2}}{\Gamma(\alpha)\Gamma(\beta)} I^{(\alpha+\beta)/2 - 1} K_{\alpha-\beta}\left(2\sqrt{\alpha\beta I}\right)$$

where $\alpha$ and $\beta$ are the large-scale and small-scale scintillation
parameters related to the Rytov variance $\sigma_R^2$:

$$\alpha = \left[\exp\left(\frac{0.49 \sigma_R^2}{(1 + 1.11\sigma_R^{12/5})^{7/6}}\right) - 1\right]^{-1}$$

$$\beta = \left[\exp\left(\frac{0.51 \sigma_R^2}{(1 + 0.69\sigma_R^{12/5})^{5/6}}\right) - 1\right]^{-1}$$

The **outage probability** is the key operational metric:

$$P_{outage} = P(\eta_{turb} < \eta_{threshold}) = F_I(\eta_{threshold})$$

where $F_I$ is the CDF of the irradiance distribution.

**Expected key rate under fading:**

$$\langle R_{key} \rangle = \int_0^\infty R_{key}(\eta_{turb} = I) \cdot f_I(I) \, dI$$

In practice, this integral is evaluated via Monte Carlo sampling from the
fading distribution.

References:
- Andrews & Phillips (2005) "Laser Beam Propagation through Random Media" 2nd
  ed. SPIE Press
- Al-Habash et al. (2001) "Mathematical model for the irradiance PDF of a laser
  beam propagating through turbulent media" Opt. Eng. 40(8)
- Vasylyev et al. (2016) "Toward global quantum communication: beam wandering
  preserves nonclassicality" PRL 117, 090501

#### 2.4.3 Scintillation Index Estimation

For a satellite downlink through the atmosphere, the Rytov variance is:

$$\sigma_R^2 = 2.25 k^{7/6} \sec^{11/6}(\zeta) \int_0^{h_{atm}} C_n^2(h) \left(\frac{h}{H}\right)^{5/6} dh$$

where $k = 2\pi/\lambda$, $\zeta$ is the zenith angle, $C_n^2(h)$ is the
refractive-index structure parameter profile, and $H$ is the propagation path
length. For standard Hufnagel-Valley profiles:

$$C_n^2(h) = 0.00594 (v/27)^2 (10^{-5}h)^{10} \exp(-h/1000) + 2.7 \times 10^{-16} \exp(-h/1500) + A \exp(-h/100)$$

where $v$ is the RMS wind speed (m/s) and $A$ is the ground-level turbulence
strength (typical: $1.7 \times 10^{-14}$ m$^{-2/3}$).

### 2.5 Pointing and Tracking (Partial, Needs Distribution Model)

#### 2.5.1 Current State

The platform implements both deterministic and stochastic pointing models.
The deterministic model:

$$\eta_{point} = \exp\left(-\frac{\sigma_{point}^2}{\theta_{div}^2}\right)$$

The stochastic model samples pointing errors from a Rayleigh distribution and
computes outage statistics.

#### 2.5.2 Required: Bias + Jitter Decomposition

Real pointing systems have both a systematic bias (boresight error) and
random jitter component:

$$\vec{r}_{point} = \vec{r}_{bias} + \vec{r}_{jitter}$$

where $|\vec{r}_{bias}|$ is deterministic and $\vec{r}_{jitter}$ follows a
Rayleigh distribution with scale $\sigma_{jitter}$. The combined pointing
loss distribution is a Rice distribution (non-central Rayleigh):

$$f_r(r) = \frac{r}{\sigma^2} \exp\left(-\frac{r^2 + r_0^2}{2\sigma^2}\right) I_0\left(\frac{r \cdot r_0}{\sigma^2}\right)$$

where $r_0 = |\vec{r}_{bias}|$, $\sigma = \sigma_{jitter}$, and $I_0$ is the
modified Bessel function of the first kind.

The joint pointing-turbulence outage probability requires convolution of both
distributions, which in practice is evaluated by joint Monte Carlo sampling.

References:
- Toyoshima et al. (2006) "Mutual alignment errors due to pointing, acquisition,
  and tracking in intersatellite laser communications" Applied Optics 45(30)
- Liao et al. (2017) "Satellite-to-ground quantum key distribution" Nature 549,
  43-47

### 2.6 Background Noise (Needs Physics-Based Estimator)

#### 2.6.1 Current State

Background counts are a user-specified scalar (`background_counts_cps`). This
is adequate for fiber but inadequate for satellite links where background varies
by orders of magnitude between day and night.

#### 2.6.2 Required: Radiance-Proxy Background Model

The background count rate at the detector depends on:

$$n_{bg} = \frac{H_\lambda \cdot \Omega_{FOV} \cdot A_{rx} \cdot \Delta\lambda \cdot \eta_{det} \cdot \eta_{filter}}{h\nu}$$

where:
- $H_\lambda$ is the spectral radiance (W/m^2/sr/nm) — depends on day/night,
  wavelength, site conditions
- $\Omega_{FOV}$ is the receiver field of view (sr)
- $A_{rx} = \pi(D_{rx}/2)^2$ is the receiver aperture area
- $\Delta\lambda$ is the spectral filter bandwidth (nm)
- $\eta_{det}$ is detector quantum efficiency
- $\eta_{filter}$ is the filter transmission
- $h\nu$ is the photon energy

Typical spectral radiance values:

| Condition | $H_\lambda$ at 810 nm (W/m^2/sr/nm) |
|-----------|--------------------------------------|
| Nighttime (new moon) | $\sim 10^{-8}$ |
| Nighttime (full moon) | $\sim 10^{-6}$ |
| Twilight | $\sim 10^{-4}$ |
| Daytime (direct sun avoidance) | $\sim 10^{-2}$ |

**Implementation approach:** `background_model` parameter with values:
- `fixed` (current): user-specified counts
- `radiance_proxy`: compute from radiance table + optics parameters
- `measured`: time-series from orbit pass envelope

References:
- Er-long et al. (2005) "Background noise of satellite-to-ground quantum key
  distribution" New J. Phys. 7, 215
- Liao et al. (2017) "Satellite-to-ground quantum key distribution" Nature 549

### 2.7 Finite-Key Enforcement for Satellite Passes

Satellite passes have finite duration (typically 3-10 minutes for LEO). The
total number of signals exchanged is bounded:

$$N_{signals} = f_{rep} \cdot T_{pass} \cdot \delta_{duty} \cdot P_{detect}$$

where $f_{rep}$ is the source repetition rate, $T_{pass}$ is the pass duration,
$\delta_{duty}$ is the duty cycle (accounting for tracking acquisition), and
$P_{detect}$ is the detection probability.

For typical LEO parameters ($f_{rep} = 100$ MHz, $T_{pass} = 300$ s,
$\delta_{duty} = 0.8$, $P_{detect} \sim 10^{-4}$), $N_{signals} \sim 2.4
\times 10^6$, which is 3-4 orders of magnitude smaller than typical fiber
blocks ($\sim 10^{10}$). This makes finite-key penalties **dominant** in
satellite scenarios.

**Enforcement rule:** When `scenario.kind = orbit_pass` OR pass duration <
configurable threshold (default 600 s), the composable v2 finite-key analysis
MUST be enabled. The engine should refuse to produce asymptotic-only results
for satellite passes.

---

## 3. Fiber QKD Deployment Realism

### 3.1 Raman Noise in WDM Coexistence (Implemented)

When quantum and classical channels share the same fiber (wavelength-division
multiplexing), spontaneous Raman scattering from classical signals produces
broadband noise that contaminates the quantum channel.

The Raman noise count rate uses an effective interaction length integral:

**Co-propagation:**

$$L_{eff,co} = \frac{e^{-\alpha_s L}(1 - e^{-(\alpha_p - \alpha_s)L})}{\alpha_p - \alpha_s}$$

**Counter-propagation:**

$$L_{eff,counter} = \frac{1 - e^{-(\alpha_p + \alpha_s)L}}{\alpha_p + \alpha_s}$$

where $\alpha_p$ and $\alpha_s$ are the attenuation coefficients at pump
(classical) and signal (quantum) wavelengths respectively, and $L$ is the
fiber length.

The total Raman count rate:

$$R_{Raman} = P_{cl} \cdot N_{ch} \cdot C_{Raman} \cdot L_{eff} \cdot \Delta\lambda_f \cdot \eta_{det}$$

where $P_{cl}$ is the classical launch power per channel, $N_{ch}$ is the
number of classical channels, $C_{Raman}$ is the Raman scattering coefficient
(cps/km/mW/nm), $\Delta\lambda_f$ is the quantum channel filter bandwidth,
and $\eta_{det}$ is the detector efficiency.

**Current implementation:** `channels/coexistence.py::compute_raman_counts_cps()`
with both legacy and effective-length models.

References:
- Patel et al. (2012) PRL 2, 041010
- da Silva et al. (2014) arXiv:1410.0656
- Eraerds et al. (2009) arXiv:0912.1798

### 3.2 Gap: Four-Wave Mixing (FWM) Noise

In dense WDM systems, four-wave mixing generates new photons at frequencies
$\omega_{ijk} = \omega_i + \omega_j - \omega_k$ that can fall in the quantum
channel band. The FWM power is:

$$P_{FWM} = \frac{1024\pi^6}{n^4 \lambda^2 c^2} \cdot (d_{eff})^2 \cdot \frac{P_i P_j P_k}{A_{eff}^2} \cdot L_{eff}^2 \cdot \eta_{FWM}$$

where $d_{eff}$ is the nonlinear susceptibility, $A_{eff}$ is the effective
mode area, and $\eta_{FWM}$ is the phase-matching efficiency:

$$\eta_{FWM} = \frac{\alpha^2}{\alpha^2 + \Delta k^2} \left(1 + \frac{4e^{-\alpha L} \sin^2(\Delta k L / 2)}{(1 - e^{-\alpha L})^2}\right)$$

The phase mismatch $\Delta k$ depends on the channel spacing and fiber
dispersion. For standard SMF-28 at 1550 nm with 100 GHz spacing,
$\eta_{FWM} \sim 10^{-3}$, making FWM significant only in dense WDM or DSF.

**Implementation approach:** Add optional `fwm_enabled` flag in coexistence
config. When enabled, compute FWM photon rate and add to background noise.
Default off (conservative — only matters for dense WDM deployments).

References:
- Inoue (1992) "Four-wave mixing in an optical fiber in the zero-dispersion
  wavelength region" J. Lightwave Technol. 10(11)
- Chapuran et al. (2009) "Optical networking for quantum key distribution and
  quantum communications" New J. Phys. 11, 105001

### 3.3 Gap: Visibility Floor Parameter

In deployed systems, the optical alignment drifts over time due to temperature
cycling, mechanical vibration, and fiber stress. This creates a non-zero
minimum QBER floor even in the absence of other noise sources.

The visibility floor $V_{floor}$ represents the worst-case alignment state:

$$e_{mis} = \frac{1 - V_{eff}}{2}, \quad V_{eff} = \max(V_{floor}, V_{measured})$$

Typical values from deployed systems:

| System Type | Typical $V_{floor}$ | Notes |
|-------------|---------------------|-------|
| Lab (stabilized) | 0.99 | Active feedback |
| Metro fiber (indoor) | 0.97 | Temperature-controlled |
| Long-haul fiber | 0.95 | Moderate drift |
| Field deployment | 0.92 | Harsh environment |

**Implementation:** Add `visibility_floor` parameter to protocol config
(default: 1.0 for backward compatibility). Apply as lower bound on effective
visibility in QBER computation.

### 3.4 Gap: Polarization Mode Dispersion (PMD)

Standard single-mode fiber exhibits random birefringence that causes
polarization-dependent group delay (DGD). The mean DGD scales as:

$$\langle\Delta\tau\rangle = D_{PMD} \cdot \sqrt{L}$$

where $D_{PMD}$ is the PMD coefficient (ps/$\sqrt{km}$) and $L$ is the fiber
length. Typical values:

| Fiber Type | $D_{PMD}$ (ps/$\sqrt{km}$) |
|------------|---------------------------|
| Modern G.652D | 0.04-0.1 |
| Legacy G.652 | 0.1-0.5 |
| G.655 (NZDSF) | 0.04-0.2 |

PMD contributes to timing uncertainty by broadening the effective coincidence
window:

$$\sigma_{eff} = \sqrt{\sigma_{jitter}^2 + \sigma_{drift}^2 + \sigma_{disp}^2 + \langle\Delta\tau\rangle^2}$$

This increases the false-coincidence rate and degrades the timing QBER
component. For long-haul links (>100 km) with legacy fiber, PMD can add
5-15 ps of timing uncertainty.

**Implementation:** Add `pmd_ps_per_sqrt_km` to channel config. Compute
$\Delta\tau$ and fold into effective timing jitter in the protocol layer.

References:
- Gordon & Kogelnik (2000) "PMD fundamentals: polarization mode dispersion in
  optical fibers" PNAS 97(9)

### 3.5 Gap: Temperature-Dependent Timing Drift

Fiber propagation delay is temperature-dependent:

$$\frac{d\tau}{dT} \approx 37 \text{ ps/km/}^\circ\text{C}$$

for standard G.652 fiber. A temperature swing of $\Delta T$ over fiber length
$L$ causes timing drift:

$$\Delta\tau_{temp} = 37 \cdot L \cdot \Delta T \text{ ps}$$

For a 50 km link with $\Delta T = 10°C$, this is $\sim 18.5$ ns — much larger
than typical coincidence windows. In practice, active clock synchronization
compensates most of this, leaving a residual drift:

$$\sigma_{temp} = 37 \cdot L \cdot \sigma_T \cdot (1 - \eta_{sync})$$

where $\sigma_T$ is the temperature fluctuation RMS and $\eta_{sync}$ is the
synchronization tracking efficiency (typically 0.99+).

**Implementation:** Add `temperature_drift_ps_per_km_per_degC` (default: 37)
and `temperature_fluctuation_degC` (default: 0) to channel config. When
nonzero, compute residual drift and add to timing budget.

---

## 4. Detector Physics and Stateful Modeling

### 4.1 Current Implementation Summary

The detector model in `physics/detector.py` implements a comprehensive
stochastic click model with:

- **Photon detection efficiency (PDE):** probabilistic detection per arrival
- **Timing jitter:** Gaussian-distributed click time displacement
  ($\sigma = \text{FWHM} / 2.355$)
- **Dark counts:** Poisson-distributed thermal events
- **Dead time:** Non-paralyzable and paralyzable models with event queue
- **Afterpulsing:** Probabilistic delayed secondary clicks
- **Gating:** Configurable gate width and period for gated detectors
- **Saturation:** Count-rate-dependent PDE reduction

### 4.2 Effective PDE Under Saturation

The saturation model reduces effective PDE at high count rates:

$$\text{PDE}_{eff} = \text{PDE} \cdot \frac{1}{1 + R_{signal} / R_{sat}}$$

where $R_{signal}$ is the incident photon rate and $R_{sat}$ is the saturation
count rate (detector-dependent).

Typical saturation rates:

| Detector | $R_{sat}$ (cps) | Recovery Mechanism |
|----------|------------------|--------------------|
| SNSPD | $10^7 - 10^8$ | Hotspot relaxation |
| InGaAs APD (gated) | $10^6 - 10^7$ | Quench + reset |
| Si APD (free-running) | $10^6$ | Passive quench |

### 4.3 Gap: Detector Class-Specific Preset Hardening

The platform defines detector presets in `presets.py` but the presets should be
validated against manufacturer specifications and literature values for each
detector class. Phase A should lock down canonical presets.

**Proposed canonical detector presets:**

| Parameter | SNSPD (WSi) | SNSPD (NbN) | InGaAs APD | Si APD |
|-----------|------------|------------|------------|--------|
| PDE | 0.93 | 0.85 | 0.25 | 0.65 |
| Dark counts (cps) | 10 | 100 | 1000 | 250 |
| Jitter FWHM (ps) | 30 | 60 | 200 | 350 |
| Dead time (ns) | 40 | 50 | 10000 | 50 |
| Afterpulse prob | 0.001 | 0.005 | 0.05 | 0.01 |
| Saturation (Mcps) | 50 | 20 | 1 | 1 |

References:
- Reddy et al. (2020) "Superconducting nanowire single-photon detectors with
  98% system detection efficiency at 1550 nm" Optica 7(12)
- Zhang et al. (2017) "NbN superconducting nanowire single photon detector with
  efficiency over 90% at 1550 nm" Science Bulletin 62(16)

### 4.4 Gap: Wavelength-Dependent PDE Curves

Current PDE is a scalar. Real detectors have wavelength-dependent response
curves. For multi-wavelength or broadband scenarios, a PDE spectrum is needed:

$$\text{PDE}(\lambda) = \text{PDE}_{peak} \cdot S(\lambda)$$

where $S(\lambda)$ is a normalized spectral response function.

**Implementation approach:** Optional `pde_spectrum` field in detector config.
When absent, use scalar PDE (backward compatible). When present, interpolate
at operating wavelength.

---

## 5. Source Physics and Emission Quality

### 5.1 Current Implementation Summary

The emitter model (`physics/emitter.py`) supports:

- **Steady-state mode:** Analytical emission probability, g2(0), spectral
  diagnostics
- **Transient mode:** Pulse-resolved dynamics with drive strength dependence
- **Source types:** Emitter-cavity (solid-state quantum emitter with Purcell
  enhancement) and SPDC (spontaneous parametric down-conversion)
- **QuTiP backend:** Optional Jaynes-Cummings master equation solver

### 5.2 Source Profile (`physics/emitter.py::SourceProfile`)

The `SourceProfile` dataclass captures all derived source parameters:
- `emission_prob`: per-pulse emission probability
- `g2_0`: second-order correlation at zero delay
- `mu`: mean photon number
- `spectral_purity`: coherence quality metric
- `collection_efficiency`, `coupling_efficiency`
- Diagnostic metadata for trust reporting

### 5.3 Gap: Spectral Indistinguishability Degradation

For entanglement-based protocols, photon indistinguishability determines Hong-
Ou-Mandel (HOM) visibility and thus the achievable QBER. In real systems,
indistinguishability degrades with:

1. **Spectral diffusion:** Random frequency jitter from local charge noise
2. **Temperature fluctuations:** Shift emission wavelength
3. **Distance-dependent chromatic dispersion:** Broadens photon wavepackets

The effective HOM visibility at distance $d$:

$$V_{HOM}(d) = V_0 \cdot \exp\left(-\frac{\pi^2 (\Delta\nu)^2 (\sigma_{disp} \cdot d)^2}{4\ln 2}\right)$$

where $V_0$ is the source HOM visibility, $\Delta\nu$ is the spectral
linewidth, and $\sigma_{disp}$ is the dispersion-induced broadening rate.

**Implementation:** Add optional `hom_visibility_decay_per_km` parameter to
source config for long-distance entanglement-based scenarios.

### 5.4 Gap: Multi-Photon Statistics for WCP Sources

For decoy-state BB84 with weak coherent pulses, the photon-number distribution
is Poisson:

$$P(n|\mu) = \frac{\mu^n e^{-\mu}}{n!}$$

The multi-photon fraction is:

$$P_{multi} = 1 - (1 + \mu)e^{-\mu}$$

For the 3-intensity decoy protocol (signal $\mu_s$, decoy $\mu_d$, vacuum
$\mu_v \approx 0$), the single-photon yield lower bound is:

$$Y_1^L \geq \frac{\mu_s}{\mu_s \mu_d - \mu_d^2} \left(Q_{\mu_d} e^{\mu_d} - Q_{\mu_v} e^{\mu_v} \frac{\mu_d^2}{\mu_s^2} - \frac{\mu_s^2 - \mu_d^2}{\mu_s^2} Q_{\mu_v}\right)$$

**Current state:** BB84 decoy protocol implements vacuum + weak decoy bounds.
Phase A should validate these bounds against published experimental results.

---

## 6. Composable Finite-Key Security Framework

### 6.1 Framework Summary (Implemented)

The v2 composable finite-key analysis decomposes the security parameter as:

$$\varepsilon_{total} = \varepsilon_{sec} + \varepsilon_{cor} + \varepsilon_{pa} + \varepsilon_{pe} + \varepsilon_{ec}$$

### 6.2 Smooth Min-Entropy Bound

$$H_{min}^{\varepsilon_{sec}}(X|E) \geq n_{sifted} \left[Y_1(1 - h_2(e_1^U)) - \sqrt{\frac{2\ln(1/\varepsilon_{sec})}{n_{sifted}}}\right]$$

### 6.3 Parameter Estimation (Serfling Bound)

$$\Delta_{PE} = \sqrt{\frac{(N - n_{sample})}{N} \cdot \frac{\ln(1/\varepsilon_{pe})}{2n_{sample}}}$$

### 6.4 Privacy Amplification (Leftover Hash Lemma)

$$\ell = H_{min} - \text{leak}_{EC} - 2\log_2(1/\varepsilon_{pa})$$

where $\text{leak}_{EC} = n \cdot f_{EC} \cdot h_2(\text{QBER}) + \log_2(1/\varepsilon_{cor})$.

### 6.5 Gap: Cross-Protocol v2 Validation

The v2 framework is fully implemented but needs systematic validation across
all 6 protocols with canonical test vectors. Currently v2 is opt-in; Phase A
should make it the default for new scenarios while maintaining v1 fallback.

### 6.6 Gap: Epsilon Budget Optimization

The current budget split strategies (balanced, pa_heavy, custom) are static.
An adaptive optimizer could find the split that maximizes key rate for given
block size and QBER:

$$\text{maximize}_{\varepsilon_i} \quad \ell(\varepsilon_{sec}, \varepsilon_{cor}, \varepsilon_{pa}, \varepsilon_{pe}, \varepsilon_{ec})$$
$$\text{subject to} \quad \sum_i \varepsilon_i = \varepsilon_{total}, \quad \varepsilon_i > 0$$

This is a low-dimensional convex optimization solvable by scipy or grid search.

---

## 7. Multi-Fidelity Physics Architecture

### 7.1 Design Philosophy

> "You do not claim one model is truth; you show consistent conclusions across
> models."

The multi-fidelity architecture uses three tiers:

| Tier | Name | Use Case | Runtime |
|------|------|----------|---------|
| 0 | Analytic | UI preview, sliders | <1 s |
| 1 | Stochastic/MC | Uncertainty estimation | 1-30 s |
| 2 | High-Fidelity | Cross-check, certification | 30 s - 5 min |

### 7.2 Backend Interface Contract

```python
class PhysicsBackend(Protocol):
    def simulate(self, component, inputs, *, seed, mode) -> dict: ...
    def applicability(self, inputs) -> dict: ...
    def provenance(self) -> dict: ...
```

**Current state:** The platform uses `physics_backend` field in source config
to select between `analytic` and `qutip` paths. Phase A should formalize this
into a proper backend interface with:

1. Registration/discovery of available backends
2. Automatic fallback (Tier 2 unavailable -> Tier 1 -> Tier 0)
3. Cross-fidelity comparison reports
4. Provenance tracking per backend

### 7.3 QuTiP Integration Points (High-ROI)

1. **Emitter dynamics:** Jaynes-Cummings master equation for Purcell-enhanced
   emission with dephasing — validates analytic g2(0) and emission probability
2. **Memory decoherence:** Amplitude damping + dephasing channels for quantum
   repeater fidelity decay curves
3. **Detector afterpulsing:** Markov chain model for state-dependent click
   correlations

### 7.4 Qiskit Integration Points (Focused)

1. **Repeater primitives:** Entanglement swapping + purification circuits
2. **Protocol verification:** Small-instance circuit simulation for BB84/BBM92
   steps
3. **Education artifacts:** QASM circuit export alongside reliability cards

---

## 8. Graph Schema and Compilation Pipeline

### 8.1 Current State (Production-Ready)

The graph schema v0.1 is fully operational:

- **JSON Schema:** Draft 2020-12 with two profiles (`qkd_link`, `pic_circuit`)
- **13 component kinds** registered with typed ports and parameter schemas
- **Compiler pipeline:** Graph JSON -> validation -> compilation -> YAML config
  (QKD) or normalized netlist (PIC)
- **Caching:** SHA256-based compile cache with provenance metadata
- **Web UI:** React Flow editor with kind registry integration

### 8.2 Gap: Graph Schema Extensions for Phase A

#### 8.2.1 Free-Space Channel Kind

Add `qkd.channel_free_space` kind with parameters:
- `tx_aperture_m`, `rx_aperture_m`, `beam_divergence_urad`
- `elevation_deg`, `pointing_jitter_urad`, `pointing_bias_urad`
- `turbulence_scintillation_index`, `turbulence_model`
- `atmospheric_extinction_db_per_km`, `atmosphere_effective_thickness_km`
- `background_model`, `background_counts_cps`

The compiler should route to the free-space channel engine when this kind is
present.

#### 8.2.2 Satellite Pass Kind

Add `orbit.pass_envelope` kind with parameters:
- `orbit_altitude_km`, `pass_duration_s`, `max_elevation_deg`
- `ground_station_lat`, `ground_station_lon`
- `time_step_s`, `day_night`
- `availability_clear_fraction`

This extends the graph schema to support OrbitVerify scenarios.

#### 8.2.3 Coexistence Configuration

Add `qkd.coexistence` optional node kind:
- `classical_launch_power_dbm`, `classical_channel_count`
- `direction` (co/counter), `filter_bandwidth_nm`
- `raman_coeff_cps_per_km_per_mw_per_nm`

---

## 9. ChipVerify Alpha Framework

### 9.1 Architecture Overview

ChipVerify alpha provides a unified photonic chip verification workflow:

```
Graph (PIC topology) -> Compile (netlist) -> Simulate (chain/DAG/scattering)
-> DRC Checks -> LVS-lite -> Performance Report -> Signoff Bundle
```

### 9.2 Current PIC Component Library (v1)

| Component | Model | Ports |
|-----------|-------|-------|
| Waveguide | Loss + phase | 2-port |
| Phase Shifter | Phase modulation | 2-port |
| Coupler | 2x2 coupling matrix | 4-port |
| Ring Resonator | FSR/finesse/resonance | 2-4 port |
| Isolator | Non-reciprocal | 2-port |
| Grating/Edge Coupler | Loss + reflection | 2-port |
| Touchstone (2/N-port) | S-parameter import | Variable |

### 9.3 Gap: ChipVerify Orchestrator

**Required new module:** `photonstrust/chipverify/orchestrator.py`

The orchestrator coordinates the full verification pipeline:

1. **Input:** Compiled PIC netlist + design rules + PDK reference
2. **Step 1:** Run PIC simulation (chain/DAG/scattering solver)
3. **Step 2:** Execute DRC checks against rule database
4. **Step 3:** Run LVS-lite (netlist vs layout comparison)
5. **Step 4:** Generate performance metrics (insertion loss, crosstalk, etc.)
6. **Step 5:** Compile signoff report with pass/fail gates
7. **Output:** ChipVerify report + evidence bundle

**API surface:** `POST /v1/chipverify/run`, `GET /v1/chipverify/report/{id}`

### 9.4 Gap: Unified ChipVerify Report Schema

```python
@dataclass(frozen=True)
class ChipVerifyReport:
    report_id: str
    netlist_hash: str
    timestamp: str
    simulation_results: dict        # S-parameters, loss budgets
    drc_results: list[dict]         # Rule violations
    lvs_results: dict               # Netlist vs layout comparison
    performance_metrics: dict       # IL, crosstalk, bandwidth
    pass_fail_gates: list[dict]     # Gate name, status, threshold
    overall_status: str             # "pass" | "fail" | "conditional"
    evidence_bundle_path: str | None
```

### 9.5 Performance Metrics for PIC Circuits

The ChipVerify report should include:

1. **Total insertion loss (dB):** Sum of component losses along critical path
2. **3-dB bandwidth (nm):** For resonant structures (rings, filters)
3. **Crosstalk isolation (dB):** Between adjacent waveguides
4. **Phase error sensitivity (rad/nm):** Wavelength-dependent phase response
5. **Group delay variation (ps):** For wideband components
6. **Process yield estimate (%):** Monte Carlo variation analysis

---

## 10. Benchmark Scenarios for Phase A Acceptance

### 10.1 Scenario 1: Metro Fiber BB84 with Coexistence

**Purpose:** Validate fiber deployment realism pack

```yaml
scenario:
  id: phaseA_metro_bb84_coexistence
  distance_km: {start: 0, stop: 80, step: 5}
  band: telecom_c
  wavelength_nm: 1550
source:
  type: wcp
  mu: 0.5
  decoy_mu: 0.1
channel:
  model: fiber
  fiber_loss_db_per_km: 0.20
  connector_loss_db: 2.0
  coexistence:
    enabled: true
    classical_launch_power_dbm: 0.0
    classical_channel_count: 8
    direction: counter
    filter_bandwidth_nm: 0.2
protocol:
  name: BB84_DECOY
  misalignment_prob: 0.015
  visibility_floor: 0.97
detector:
  class: ingaas
finite_key:
  enabled: true
  composable_version: v2
  signals_per_block: 1.0e9
  security_epsilon: 1.0e-10
```

**Validation gates:**
- Key rate monotonically decreasing with distance
- Key rate decreasing with increasing classical power
- QBER decomposition shows Raman + misalignment contributions
- Finite-key penalty visible at short block sizes

### 10.2 Scenario 2: Satellite Downlink BBM92

**Purpose:** Validate free-space channel + satellite realism

```yaml
scenario:
  id: phaseA_satellite_downlink
  kind: orbit_pass
  band: nir_810
  wavelength_nm: 810
orbit:
  altitude_km: 500
  max_elevation_deg: 70
  pass_duration_s: 300
  time_step_s: 10
source:
  type: spdc
  mu: 0.1
channel:
  model: satellite
  tx_aperture_m: 0.15
  rx_aperture_m: 0.80
  turbulence_model: lognormal
  turbulence_scintillation_index: 0.2
  pointing_jitter_urad: 2.0
  pointing_model: stochastic
  background_model: radiance_proxy
detector:
  class: snspd
protocol:
  name: BBM92
finite_key:
  enabled: true
  composable_version: v2
```

**Validation gates:**
- Key rate peaks near highest elevation
- Outage probability > 0 with turbulence enabled
- Day/night background difference >10x
- Finite-key enforced (no asymptotic fallback)

### 10.3 Scenario 3: PIC Ring Resonator Verification

**Purpose:** Validate ChipVerify alpha pipeline

```json
{
  "profile": "pic_circuit",
  "circuit": {
    "id": "phaseA_ring_filter_verify",
    "nodes": [
      {"id": "gc_in", "kind": "pic.grating_coupler", "params": {"insertion_loss_db": 3.5}},
      {"id": "wg1", "kind": "pic.waveguide", "params": {"length_um": 500, "loss_db_per_cm": 2.0}},
      {"id": "ring1", "kind": "pic.ring", "params": {"radius_um": 10, "coupling_ratio": 0.15}},
      {"id": "wg2", "kind": "pic.waveguide", "params": {"length_um": 200, "loss_db_per_cm": 2.0}},
      {"id": "gc_out", "kind": "pic.grating_coupler", "params": {"insertion_loss_db": 3.5}}
    ],
    "edges": [
      {"from": "gc_in", "to": "wg1"},
      {"from": "wg1", "to": "ring1"},
      {"from": "ring1", "to": "wg2"},
      {"from": "wg2", "to": "gc_out"}
    ]
  }
}
```

**Validation gates:**
- Compilation produces valid netlist
- Simulation produces S-parameter data
- Total insertion loss > 0 dB
- Ring shows resonance behavior (wavelength-dependent response)

---

## 11. Performance Targets

| Scenario Class | Target p95 Runtime | Current Estimate |
|----------------|-------------------|------------------|
| Fiber QKD preview (single distance) | <1 s | ~0.2 s |
| Fiber QKD sweep (20 distances) | <5 s | ~3 s |
| Satellite pass (30 time steps) | <10 s | ~8 s (with MC) |
| PIC simulation (5-node circuit) | <2 s | ~0.5 s |
| ChipVerify full pipeline | <15 s | N/A (not built) |

---

## 12. References

### Free-Space / Satellite QKD

1. Liao et al. (2017) "Satellite-to-ground quantum key distribution" Nature 549, 43-47
2. Bedington et al. (2017) "Progress in satellite quantum key distribution" npj Quantum Information 3, 30
3. Andrews & Phillips (2005) "Laser Beam Propagation through Random Media" 2nd ed. SPIE Press
4. Al-Habash et al. (2001) "Mathematical model for the irradiance PDF" Opt. Eng. 40(8)
5. Vasylyev et al. (2016) PRL 117, 090501
6. Toyoshima et al. (2006) "Mutual alignment errors" Applied Optics 45(30)
7. Er-long et al. (2005) "Background noise of satellite-to-ground QKD" NJP 7, 215
8. Kim & Korevaar (2001) "Availability of FSO" Proc. SPIE 4530
9. Kaushal & Kaddoum (2017) IEEE Commun. Surveys & Tutorials 19(1)
10. Nature (2025) microsatellite real-time QKD: DOI 10.1038/s41586-025-08739-z

### Fiber QKD Deployment

11. Patel et al. (2012) PRL 2, 041010
12. da Silva et al. (2014) arXiv:1410.0656
13. Eraerds et al. (2009) arXiv:0912.1798
14. Chapuran et al. (2009) "Optical networking for QKD" NJP 11, 105001
15. Inoue (1992) "Four-wave mixing" J. Lightwave Technol. 10(11)
16. Gordon & Kogelnik (2000) "PMD fundamentals" PNAS 97(9)

### Finite-Key Security

17. Tomamichel et al. (2012) Nature Communications 3, 634
18. Serfling (1974) Ann. Statist. 2, 39-48
19. Renner (2005) "Security of QKD" PhD thesis, ETH Zurich
20. Tomamichel et al. (2017) "Largely Self-Testing QKD" Quantum 1, 14

### QKD Protocols

21. Lo, Ma, Chen (2005) PRL 94, 230504 (decoy state BB84)
22. Lo, Curty, Qi (2012) PRL 108, 130503 (MDI-QKD)
23. Lucamarini et al. (2018) Nature 557, 400-403 (TF-QKD)
24. Ma, Zeng, Zhou (2018) PRX 8, 031043 (PM-QKD)
25. Wang et al. (2018) PRL 121, 190502 (SNS)
26. Bennett & Brassard (1984) "Quantum cryptography" Proc. IEEE ICCSSP

### Detector Physics

27. Reddy et al. (2020) "SNSPD with 98% SDE" Optica 7(12)
28. Zhang et al. (2017) "NbN SNSPD >90%" Science Bulletin 62(16)
29. Restelli et al. (2012) "Detector afterpulsing" J. Mod. Opt.

### Photonic Integrated Circuits

30. Bogaerts et al. (2012) "Silicon microring resonators" Laser Photonics Rev. 6(1)
31. Chrostowski & Hochberg (2015) "Silicon Photonics Design" Cambridge UP

### Standards

32. ETSI GS QKD 004 V2.1.1 (2020) "Application Interface"
33. ETSI GS QKD 005 V1.1.1 (2010) "Security Proofs"
34. ETSI GS QKD 008 V1.1.1 (2010) "QKD Module Security Specification"
35. ETSI GS QKD 011 V1.1.1 (2016) "Component characterization"
36. ETSI GS QKD 014 V1.1.1 (2019) "Protocol and data format"
