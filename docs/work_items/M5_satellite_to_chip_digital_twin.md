# Research Brief: M5 — Satellite-to-Ground-PIC Digital Twin

## Metadata
- Work item ID: M5
- Title: Integrated Satellite-to-Ground-PIC QKD Digital Twin
- Date: 2026-03-01
- Priority: P1 — EU Quantum Flagship, ESA, DOE unlock; second arxiv preprint
- Related modules: `photonstrust/orbit/`, `photonstrust/channels/free_space.py`,
  `photonstrust/qkd_protocols/`, `photonstrust/pic/`, `photonstrust/pipeline/`

---

## 1. Problem and Motivation

Satellite QKD programs — ESA EAGLE-1 (2024–2028), CSA QEYSSat (2024),
China Micius (operational since 2016), EU EuroQCI (2023–2027) — require
end-to-end link analysis that connects orbital geometry, atmospheric physics,
ground station photonic hardware, and QKD key accumulation over a pass window.

Currently, PhotonTrust has two independent subsystems:
- **OrbitVerify**: simulates a free-space pass envelope (elevation vs. time,
  atmospheric channel, per-sample key rate) — implemented in `orbit/`
- **ChipVerify**: simulates a PIC-based QKD terminal (S-parameters, key rate
  from compiled netlist) — implemented in `pic/` and `pipeline/`

These subsystems do not communicate. OrbitVerify uses a default source
efficiency parameter; it does not know about the ground station PIC design.
ChipVerify computes a static QKD key rate at a fixed link distance; it does not
model the time-varying distance and channel of a satellite pass.

**The gap:** No open-source tool can answer the question: "Given this specific
ground station PIC design (with its DRC-verified losses) and this orbital pass
geometry, how many secure key bits will accumulate over a single pass?"

**Why this is undeniable for EU/ESA/DOE funders:**
- EAGLE-1 (ESA): Europe's first satellite QKD system requires ground station
  hardware specification. The team needs to evaluate PIC vs. bulk-optic ground
  terminals for cost and performance.
- EuroQCI (EU): Requires end-to-end link analysis tools for network planning
  across terrestrial + satellite segments.
- QEYSSat (CSA): Published requirement for independent link simulation tools
  for experiment planning.
- DOE Quantum Network Infrastructure: Fund development of US satellite QKD
  ground station capabilities.

**Who benefits:**
- ESA EAGLE-1 engineering team (direct simulation of their mission parameters)
- EU EuroQCI national operators planning ground segment locations
- CSA QEYSSat science team (experiment planning, scheduling)
- Academic satellite QKD groups at DLR, INRIM, NICT, IQOQI

---

## 2. Research Questions and Hypotheses

**RQ1:** For a LEO satellite QKD downlink at 400–600 km altitude, what is
the dominant loss mechanism limiting the accumulated key per pass: geometric
beam spreading loss, atmospheric extinction, pointing jitter, or ground PIC
insertion loss? How does this change with elevation angle?

**RQ2:** What is the minimum ground station PIC insertion loss budget that
maintains a positive key rate at low elevation (15°–30°), and how does it
compare to the equivalent bulk-optic ground terminal?

**RQ3:** For the EAGLE-1 orbit and latitude of ground station candidate sites
(e.g., London 51°N, Berlin 52°N, Madrid 40°N), what is the expected annual
key accumulation as a function of ground PIC design quality?

**Hypothesis H1 (falsifiable):** Geometric beam spreading loss dominates the
link budget at all elevations above 30°, with atmospheric extinction becoming
the second-largest contribution only below 20° elevation. Pointing jitter
contributes less than 3 dB of effective loss for a ground aperture of 0.4 m
and pointing accuracy of 2 μrad. This is verifiable by computing each loss
component separately from `total_free_space_efficiency()` and comparing.

**Hypothesis H2 (falsifiable):** For a LEO downlink at 500 km altitude using
a 1 W average downlink power, a 0.5 m ground aperture, and a standard InGaAs
APD ground terminal (η_d = 0.25), a positive BB84 key rate requires ground
station PIC insertion loss ≤ 5 dB at elevations above 30°. Below 30°, no
positive key rate is achievable with InGaAs APDs regardless of PIC quality;
SNSPDs (η_d > 0.80) are required below 20°.

---

## 3. Related Work

### 3.1 Satellite QKD Link Budget References

**Micius satellite (CGTN/PAN group, Science 2017):**
- Orbit: Sun-synchronous, 500 km altitude
- Wavelength: 850 nm (near-IR)
- Beam divergence: 10 μrad (diffraction-limited)
- Tx aperture: 300 mm
- Rx aperture: 1.2 m (ground telescope)
- Total channel efficiency at zenith: ≈ 20 dB loss
- Sifted key at zenith pass: 10⁸ bits per 273-second pass window
- Protocol: BBM92 (entanglement-based)

**EAGLE-1 (ESA, 2024 specification, public):**
- Orbit: LEO, ~600 km altitude, inclination 70°
- Wavelength: 800 nm (provisional)
- Protocol: BB84 or BBM92 (TBC)
- Ground stations: 2 initially (EU member states), 6+ planned

**QEYSSat (CSA, 2024):**
- Orbit: polar LEO, ~600 km
- Protocol: BBM92 and BB84 variants
- Wavelength: 785 nm and 1550 nm (dual band)
- Planned passes: 5–10 minutes at elevation > 15°

### 3.2 Existing PhotonTrust Infrastructure

| Module | What it does | Used in M5 |
|--------|-------------|------------|
| `orbit/pass_envelope.py` | Time-series of distance, elevation, background | Core |
| `channels/free_space.py` | `total_free_space_efficiency(distance, wavelength, cfg)` | Core |
| `qkd_protocols/bb84_decoy.py` | Key rate at given efficiency | Per-sample |
| `qkd_protocols/bbm92.py` | BBM92 (entanglement) key rate | Per-sample |
| `pic/simulate.py` | S-parameter simulation → η_chip | Ground terminal |
| `pipeline/certify.py` (M1) | Compile + DRC + sign → η_chip | Ground terminal |
| `evidence/signing.py` | Ed25519 signing | Certificate |

### 3.3 The Missing Integration

What does not yet exist:
- A `satellite_chain` config schema that joins orbit + ground PIC + protocol
- The time-integration loop: accumulate key bits over N pass samples
- The pass-level certificate: signed record of key accumulation per pass
- The annual yield estimator: sum over passes for a given ground station location

---

## 4. Mathematical Formulation

### 4.1 Free-Space Channel Efficiency (Existing, Reference)

The existing `total_free_space_efficiency()` implements:

**Geometric efficiency (far-field Gaussian beam approximation):**
```
η_geom = (D_R / (2 θ_div z))²

where:
  D_R     = receiver aperture diameter (m)
  θ_div   = beam half-angle divergence (rad) = 1.22 λ / D_T (diffraction-limited)
  D_T     = transmitter aperture diameter (m)
  z       = slant range distance (km × 10³ m)
```

More precisely, for a Gaussian beam with 1/e² half-angle θ₀ = λ/(π w₀)
and transmit waist w₀ = D_T/2:
```
P_received / P_sent = (D_R / (2 z θ₀))² × [1 − exp(−D_R²/(2w_z²))]

w_z = z θ₀  (far-field beam radius at range z)
```

For D_R ≪ 2 z θ₀ (receiver much smaller than beam): η_geom ≈ (D_R / (2zθ₀))²

**Atmospheric extinction (Beer-Lambert through slant path):**
```
η_atm = 10^{−κ L_path / 10}

L_path = h_atm / sin(el)   for el > 10° (plane-parallel atmosphere)
         h_atm / (sin²(el) + 2 h_atm / R_Earth)^{1/2}  (for low elevation, spherical correction)

h_atm ≈ 20 km (effective atmosphere scale height for extinction)
κ_clear = 0.02 dB/km at 1550 nm, 0.05 dB/km at 800 nm (clear sky, sea level)
κ_hazy  = 0.2–2.0 dB/km (haze, altitude-dependent)
```

**Pointing jitter loss (Gaussian pointing error model):**
```
For pointing jitter σ_θ (rad, 1σ), beam divergence θ_div:
η_point = exp(−2 (σ_θ / θ_div)²)   (Gaussian intensity profile, deterministic)

For statistical Monte Carlo model (N_samples):
η_point = mean(exp(−2 (θ_i / θ_div)²))  where θ_i ~ Rayleigh(σ_θ)
```

**Turbulence scintillation (log-normal intensity fluctuation):**
```
I = I₀ × exp(X)  where X ~ N(−σ_X²/2, σ_X²)

Scintillation index: σ_X² = σ_I² = Var(I) / ⟨I⟩²

For weak turbulence (σ_I² < 1), Rytov variance (plane wave, horizontal path):
σ_I² = 1.23 C_n² k^{7/6} L^{11/6}
where C_n² = atmospheric refractive index structure parameter (typ. 10⁻¹⁷ m⁻²/³)

For satellite link (vertical path):
σ_I² ≈ 2.25 k² sec^{11/6}(ζ) ∫₀^L C_n²(h) (1 − h/L)^{5/6} dh
```

The total channel efficiency at each pass time sample t:
```
η_channel(t) = η_geom(z(t)) × η_atm(el(t)) × η_point(t) × η_turb(t)
```

### 4.2 Key Rate Integration Over a Pass

The QKD key rate at sample time t is:
```
R(t) = f_QKD(η_total(t))

η_total(t) = η_sat(t) × η_ground_terminal

where:
  η_sat(t)          = satellite transmitter efficiency (constant over pass)
  η_channel(t)      = time-varying free-space channel (above)
  η_ground_terminal = η_chip × η_coupler × η_detector
                    = from PIC certify (M1) × PDK coupler IL × detector PDE
```

For each pass with N time samples spaced Δt_s seconds apart:

**Total accumulated key bits per pass:**
```
K_pass = Σ_{t=0}^{T_pass} R(t) × Δt_s  [bits]
```

where T_pass = pass duration (typically 200–600 s for LEO at el > 15°).

Note: R(t) = 0 when η_total(t) is below the minimum detection threshold.
The effective pass duration is thus the subset of the window where R(t) > 0.

**Time-averaged key rate:**
```
R̄_pass = K_pass / T_pass  [bps]
```

**Key rate at zenith (el = 90°, maximum):**
```
R_zenith = f_QKD(η_total at el=90°)
```
Used as a figure of merit for comparison between ground station designs.

### 4.3 BB84 Key Rate for Free-Space Link

For satellite-to-ground BB84 with WCP + decoy:

**Total transmittance at sample time t:**
```
η_total(t) = η_source × η_channel(t) × η_coupler × η_chip × η_detector

η_source   = satellite source emission × polarisation purity
η_channel  = η_geom × η_atm × η_point × η_turb  (computed above)
η_chip     = from PIC simulation (M1 output)
η_coupler  = grating/fibre coupler at ground station
η_detector = PDE × window efficiency
```

**Background counts in free-space:**
Daytime background is dominated by solar radiance:
```
b_solar_cps = L_sun(λ) × Δλ_filter × Ω_FOV × A_rx × η_det

L_sun(1550 nm) ≈ 1.8 × 10⁻³ W/(m² sr nm)  (solar spectral radiance)
Δλ_filter ≈ 0.5 nm (narrow bandpass filter)
Ω_FOV = π (θ_FOV/2)² sr  (field-of-view solid angle)
```

Night-time background is dominated by moonlight and star background:
```
b_night_cps ≈ 10–100 cps for 30 cm aperture, narrow filter, dark sky
```

### 4.4 BBM92 (Entanglement-Based) Key Rate

For BBM92 (used by Micius, planned for EAGLE-1 and QEYSSat):

**Reference:** Bennett, Brassard, Mermin (1992); Jennewein et al. review (2011)

Coincidence rate at ground station (for pair source on satellite):
```
Q_coincidence = R_pair × η_A × η_B

where:
  R_pair   = SPDC pair generation rate (pairs/s)
  η_A      = efficiency of channel A (downlink 1: satellite → ground station A)
  η_B      = efficiency of channel B (downlink 2: satellite → ground station B)
```

For single ground station + local Bob:
```
η_A = η_channel(t) × η_ground_terminal (downlink)
η_B = η_local (short fibre to local Bob, η ≈ 0.9)
```

**BBM92 key rate (asymptotic, perfect source):**
```
R_BBM92 = q × Q_coincidence × [1 − 2 H₂(e_1)]

where:
  q = 1/2  (sifting factor)
  e_1 = QBER from basis error + dark coincidences + detector noise
```

**Multi-pair contamination (SPDC source, μ pairs/pulse):**
For SPDC source with mean pair number μ:
```
Q_coincidence = μ η_A η_B + (μ η_A)(μ η_B) + ...
              ≈ μ η_A η_B  for μ ≪ 1

QBER contribution from multi-pair events:
  e_multi ≈ μ / 2  (Werner model, for μ ≪ 1)
```

Total QBER:
```
E = e_optical + e_multi + e_dark
  = e_d + μ/2 + (d_A/Q_coincidence + d_B/Q_coincidence)/2
```

### 4.5 Orbital Geometry and Pass Parameters

**Slant range as function of elevation angle el and orbit altitude h:**
```
z(el) = −R_E sin(el) + √((R_E sin(el))² + h² + 2 R_E h)

where R_E = 6371 km (Earth radius), h = orbit altitude (km)
```

For h = 500 km:
```
z(el=90°) = 500 km  (zenith)
z(el=30°) ≈ 851 km
z(el=15°) ≈ 1330 km
z(el=10°) ≈ 1647 km
```

**Angular velocity of LEO satellite:**
```
ω_sat = √(μ_E / (R_E + h)³)

where μ_E = GM_E = 3.986 × 10¹⁴ m³/s²

For h = 500 km: T_orbit = 94.5 min, ω_sat = 0.00111 rad/s
```

**Elevation angle rate:**
```
del/dt ≈ ω_sat × cos(el) / (1 + (R_E / (R_E + h)) cos(el))
```

**Maximum pass duration at el_min = 15°:**
```
T_pass(el_min) ≈ 2 × arccos(R_E sin(el_min) / (R_E + h)) / ω_sat
              ≈ 400–600 s  for h=500–600 km
```

### 4.6 Ground Station PIC Integration

For a fibre-coupled ground station (telescope → fibre → PIC → detector):

```
η_ground_terminal = η_telescope × η_fibre × η_pic × η_coupler × η_detector

η_telescope  = mirror reflectivity² × obscuration factor ≈ 0.85
η_fibre      = coupling from telescope focal point to single-mode fibre
               (typically 0.3–0.6 for free-space to SMF; use turbulence-corrected AO)
η_pic        = from `certify` pipeline (M1 output)
η_coupler    = grating coupler IL from PDK
η_detector   = PDE in coincidence window
```

For the specific case of a photonic chip–based polarisation analyser (passive):
The PIC replaces the bulk polarisation beam splitter (PBS) + half-wave plate:
```
η_chip_analyser = η_input_coupler × η_PBS × η_output_coupler
```
The PIC advantage: lower insertion loss, no mechanical drift, wavelength
selectivity via integrated filters.

### 4.7 Annual Key Accumulation Estimator

For a ground station at latitude φ, a polar orbit at inclination i,
altitude h, the expected number of passes per day above el_min:

For a sun-synchronous orbit (i ≈ 97°):
```
N_passes_day ≈ (T_day / T_orbit) × visibility_fraction(φ, i, h, el_min)
```

For EAGLE-1 (h=600 km, i=70°, el_min=15°):
```
N_passes_day ≈ 3–5 passes/day for European latitudes (40°–55°N)
T_pass ≈ 400–500 s per pass (usable window at el > 15°)
```

**Annual key bits (first-order estimate):**
```
K_annual = N_passes_day × T_pass × R̄_pass × P_clear_sky × 365 [bits/year]

where P_clear_sky = site-specific clear-sky probability
  (Canary Islands: ~0.85, London: ~0.35, Berlin: ~0.40)
```

---

## 5. Method Design

### 5.1 Satellite Chain Config Schema

New config block `satellite_qkd_chain`:

```yaml
# configs/demo_eagle1_analog.yml
satellite_qkd_chain:
  id: eagle1_analog_berlin
  description: EAGLE-1 analog simulation for Berlin ground station

  satellite:
    altitude_km: 600.0
    orbit_inclination_deg: 70.0
    transmit_power_dbm: 27.0          # 500 mW
    tx_aperture_m: 0.15
    wavelength_nm: 785.0
    source_type: bb84_wcp
    mu_signal: 0.5
    mu_decoy: 0.1
    rep_rate_mhz: 100.0
    source_qber_contribution: 0.005   # 0.5% optical misalignment

  atmosphere:
    model: effective_thickness
    extinction_db_per_km: 0.05        # clear sky, 785nm
    effective_thickness_km: 20.0
    turbulence_scintillation_index: 0.15
    pointing_jitter_urad: 2.0

  ground_station:
    latitude_deg: 52.5                # Berlin
    rx_aperture_m: 0.40
    telescope_efficiency: 0.80
    fibre_coupling_efficiency: 0.45   # AO-corrected
    pic_graph_path: graphs/demo_qkd_transmitter.json
    pic_pdk: aim_photonics_300nm_sin
    detector_type: ingaas_apd
    detector_pde: 0.25
    detector_dcr_cps: 1000.0
    detector_jitter_ps_fwhm: 500.0
    coincidence_window_ps: 1000.0
    bandpass_filter_nm: 0.5

  pass_geometry:
    elevation_min_deg: 15.0
    dt_s: 5.0                         # time step for integration
    day_night: night                  # night passes only

  protocol: BB84_decoy
  target_security_epsilon: 1.0e-10

  output:
    key_per_pass: true
    annual_estimate: true
    sign_certificate: false
```

### 5.2 Satellite Chain Orchestrator

New file: `photonstrust/pipeline/satellite_chain.py`

```python
def run_satellite_chain(config: dict) -> dict:
    """Run the full satellite-to-ground-PIC QKD digital twin."""

    sat_cfg = config["satellite_qkd_chain"]

    # Step 1: Load and certify ground station PIC
    ground_cfg = sat_cfg["ground_station"]
    if "pic_graph_path" in ground_cfg:
        cert = run_certify(
            graph_path=Path(ground_cfg["pic_graph_path"]),
            pdk_name=ground_cfg.get("pic_pdk", "generic_silicon_photonics"),
            protocol=sat_cfg.get("protocol", "BB84_decoy"),
            wavelength_nm=float(sat_cfg["satellite"]["wavelength_nm"]),
            output_dir=output_dir / "pic_cert",
        )
        eta_chip = cert["pic"]["eta_chip"]
    else:
        eta_chip = float(ground_cfg.get("eta_chip", 1.0))

    # Step 2: Build pass envelope (orbit geometry + atmosphere)
    pass_config = _build_orbit_pass_config(sat_cfg, eta_chip)
    pass_result = simulate_orbit_pass(pass_config)

    # Step 3: Extract key accumulation from pass samples
    samples = pass_result["samples"]
    key_bits_per_sample = [
        max(0.0, s["key_rate_bps"]) * sat_cfg["pass_geometry"]["dt_s"]
        for s in samples
    ]
    K_pass = sum(key_bits_per_sample)
    T_pass = len(samples) * sat_cfg["pass_geometry"]["dt_s"]
    R_mean = K_pass / T_pass if T_pass > 0 else 0.0

    # Step 4: Annual yield estimate (if requested)
    annual = None
    if sat_cfg.get("output", {}).get("annual_estimate"):
        annual = _estimate_annual_yield(sat_cfg, R_mean, T_pass)

    # Step 5: Build + optionally sign satellite chain certificate
    chain_cert = _build_chain_certificate(
        sat_cfg=sat_cfg,
        pic_cert=cert if "pic_graph_path" in ground_cfg else None,
        pass_result=pass_result,
        K_pass=K_pass,
        R_mean=R_mean,
        annual=annual,
    )

    return chain_cert
```

### 5.3 Pass Config Builder (Orbit → OrbitVerify Format)

```python
def _build_orbit_pass_config(sat_cfg: dict, eta_chip: float) -> dict:
    """Convert satellite_qkd_chain config to orbit_pass config for OrbitVerify."""
    atm = sat_cfg["atmosphere"]
    ground = sat_cfg["ground_station"]
    sat = sat_cfg["satellite"]
    pass_geo = sat_cfg["pass_geometry"]

    # Generate elevation profile from orbital geometry
    h_km = float(sat["altitude_km"])
    el_min = float(pass_geo["elevation_min_deg"])
    dt_s = float(pass_geo["dt_s"])
    samples = _generate_elevation_profile(h_km, el_min, dt_s)

    # η_ground = telescope × fibre × chip × coupler × (incorporated into PDE)
    eta_ground = (float(ground.get("telescope_efficiency", 0.80)) *
                  float(ground.get("fibre_coupling_efficiency", 0.45)) *
                  eta_chip)

    return {
        "orbit_pass": {
            "id": sat_cfg["id"],
            "band": _wavelength_to_band(float(sat["wavelength_nm"])),
            "wavelength_nm": float(sat["wavelength_nm"]),
            "dt_s": dt_s,
            "samples": samples,
        },
        "source": {
            "type": "wcp",
            "rep_rate_mhz": float(sat["rep_rate_mhz"]),
            "mu": float(sat.get("mu_signal", 0.5)),
            "coupling_efficiency": eta_ground,
        },
        "channel": {
            "model": "free_space",
            "tx_aperture_m": float(sat["tx_aperture_m"]),
            "rx_aperture_m": float(ground["rx_aperture_m"]),
            "atmospheric_extinction_db_per_km": float(
                atm.get("extinction_db_per_km", 0.05)),
            "atmosphere_effective_thickness_km": float(
                atm.get("effective_thickness_km", 20.0)),
            "pointing_jitter_urad": float(atm.get("pointing_jitter_urad", 2.0)),
            "turbulence_scintillation_index": float(
                atm.get("turbulence_scintillation_index", 0.15)),
        },
        "detector": {
            "pde": float(ground["detector_pde"]),
            "dark_counts_cps": float(ground.get("detector_dcr_cps", 1000.0)),
            "jitter_ps_fwhm": float(ground.get("detector_jitter_ps_fwhm", 500.0)),
        },
        "timing": {
            "coincidence_window_ps": float(
                ground.get("coincidence_window_ps", 1000.0)),
        },
        "protocol": {"name": sat_cfg.get("protocol", "BB84_decoy"),
                     "mu_decoy": float(sat.get("mu_decoy", 0.1))},
    }
```

### 5.4 Elevation Profile Generator

```python
def _generate_elevation_profile(
    altitude_km: float,
    el_min_deg: float,
    dt_s: float,
) -> list[dict]:
    """Generate a realistic elevation vs. time profile for a LEO pass."""
    import math
    R_E = 6371.0  # km
    h = altitude_km
    el_min_rad = math.radians(el_min_deg)

    # Half-angle subtended at Earth's centre for el_min visibility
    cos_half_angle = (R_E / (R_E + h)) * math.cos(el_min_rad)
    half_angle_sat = math.acos(cos_half_angle) - el_min_rad

    # Orbital angular velocity
    mu_E = 3.986e5  # km³/s²
    omega = math.sqrt(mu_E / (R_E + h)**3)  # rad/s

    # Total pass time
    T_half = half_angle_sat / omega
    T_pass = 2 * T_half
    N_samples = int(T_pass / dt_s) + 1

    samples = []
    for i in range(N_samples):
        t = -T_half + i * dt_s
        # Nadir angle from satellite:
        nadir_angle = omega * abs(t)
        # Elevation angle at ground station (spherical geometry):
        cos_el = math.cos(nadir_angle) * (R_E / (R_E + h))
        el_rad = math.asin(math.cos(nadir_angle) - cos_el) - nadir_angle + \
                 math.asin(R_E * math.sin(nadir_angle + el_min_rad) / (R_E + h))
        # Simplified: use direct formula
        sin_el = ((R_E + h) * math.cos(nadir_angle) - R_E) / \
                  math.sqrt((R_E + h)**2 + R_E**2 - 2*R_E*(R_E+h)*math.cos(nadir_angle))
        el_rad = math.asin(max(-1.0, min(1.0, sin_el)))
        el_deg = math.degrees(el_rad)

        if el_deg < el_min_deg:
            continue

        # Slant range
        z_km = math.sqrt((R_E + h)**2 + R_E**2 - 2*R_E*(R_E+h)*math.cos(nadir_angle)) - R_E

        samples.append({
            "t_s": float(t + T_half),
            "distance_km": float(max(h, z_km)),
            "elevation_deg": float(max(0.0, el_deg)),
            "background_counts_cps": 200.0 if el_deg < 20.0 else 50.0,
            "day_night": "night",
        })

    return samples
```

### 5.5 Satellite Chain Certificate Schema

```json
{
  "schema_version": "0.1",
  "kind": "satellite_qkd_chain_certificate",
  "run_id": "<hex>",
  "generated_at": "<ISO-8601>",
  "mission": "eagle1_analog_berlin",
  "ground_station": {
    "latitude_deg": 52.5,
    "pic_cert_run_id": "<hex>",
    "eta_chip": 0.654,
    "eta_ground_terminal": 0.235
  },
  "pass": {
    "altitude_km": 600.0,
    "elevation_min_deg": 15.0,
    "pass_duration_s": 487.0,
    "samples_evaluated": 97,
    "samples_with_positive_key_rate": 74,
    "key_bits_accumulated": 48200,
    "mean_key_rate_bps": 98.9,
    "peak_key_rate_bps": 840.0,
    "peak_elevation_deg": 68.3
  },
  "annual_estimate": {
    "passes_per_day": 4.1,
    "clear_sky_probability": 0.40,
    "key_bits_per_year": 28700000,
    "key_mbits_per_year": 28.7,
    "notes": "Night passes only; clear sky fraction for Berlin"
  },
  "signoff": {
    "decision": "GO",
    "key_rate_positive_at_zenith": true,
    "annual_key_above_1mbit": true
  },
  "signature": { ... }
}
```

---

## 6. Experimental Design

### 6.1 Reference Scenarios

Three scenarios committed to `configs/satellite/`:

**Scenario 1: Eagle1 analog — Berlin, night, InGaAs APD**
```
h=600 km, λ=785 nm, D_T=0.15 m, D_R=0.40 m
η_d=0.25, DCR=1000 cps, el_min=15°
Expected: K_pass ≈ 30–80 kbits, R_peak ≈ 0.5–2 kbps at zenith
```

**Scenario 2: Eagle1 analog — Berlin, night, SNSPD**
```
Same geometry; η_d=0.85, DCR=10 cps
Expected: K_pass ≈ 200–500 kbits (5–10× improvement over InGaAs)
```

**Scenario 3: Micius analog — zenith pass, near-IR**
```
h=500 km, λ=850 nm, D_T=0.30 m, D_R=1.2 m (matching Micius ground telescope)
η_d=0.70 (SNSPD at 850 nm), DCR=100 cps, BBM92 protocol, el_min=20°
Expected: K_pass ≈ 1–5 Mbits (comparison to Micius reported 10⁸ bits/pass
shows asymptotic vs. finite-key distinction; factor ~100 from finite-key)
```

### 6.2 Validation Tests

| Test | What it verifies |
|------|-----------------|
| `test_slant_range_zenith` | z(el=90°) = h_km (altitude) |
| `test_slant_range_low_elevation` | z(el=15°) > z(el=90°) by correct factor |
| `test_eta_geom_decreases_with_distance` | η_geom monotone decreasing with z |
| `test_eta_atm_decreases_with_el` | Lower el → longer path → lower η_atm |
| `test_k_pass_positive_for_eagle1` | Eagle1 analog: K_pass > 0 |
| `test_snspd_better_than_ingaas` | Scenario 2 K_pass > Scenario 1 |
| `test_micius_analog_within_order_mag` | Micius K_pass within 100× of reported |
| `test_pass_duration_correct` | Duration matches orbital geometry formula |
| `test_chain_cert_schema_valid` | Output JSON schema-validates |
| `test_annual_estimate_sanity` | Annual bits > 0 and < 10¹² (physical bounds) |

### 6.3 Micius Analog Calibration

The Micius experiment is the only published satellite QKD result with fully
documented parameters. Use it as a calibration point:

Published: 10⁸ sifted bits per 273-second pass (Science 2017, Liao et al.)
That is sifted, not secure key. Secure key ≈ sifted × (1 − H₂(QBER) − f_EC H₂(QBER))
≈ sifted × 0.4 ≈ 4 × 10⁷ bits per pass.

PhotonTrust target: reproduce the sifted count rate (not the secure key) for the
Micius parameters. Discrepancy within factor 10 is acceptable given:
- Micius used a novel optical ground station (not modelled in detail)
- Turbulence conditions at that specific night are not published
- Point ahead mechanism losses are not modelled

---

## 7. Risk and Failure Analysis

**Risk R1: Atmospheric model accuracy at low elevation**
The plane-parallel atmosphere approximation breaks down below 10° elevation.
The existing code has a spherical correction flag. Mitigation: document that
el_min = 15° is the minimum supported by the current model; warn if el_min < 15°.

**Risk R2: Turbulence fading causes all-zero key rate**
At high turbulence (C_n² > 10⁻¹⁵ m⁻²/³) and low elevation, the channel can
undergo deep fades where η_channel → 0. The QKD key rate model must correctly
return R = 0 (not negative) in these conditions.
Mitigation: clamp all efficiency values at 0 in `total_free_space_efficiency`;
existing code already does this.

**Risk R3: PIC certify not available (M1 dependency)**
M5 depends on M1 (certify pipeline) for the ground station PIC η_chip.
Mitigation: satellite chain also accepts a scalar `eta_chip` parameter directly,
bypassing the PIC certify step. M5 can be developed without M1 complete.

**Risk R4: Orbital geometry model is simplified**
The elevation profile generator uses a simple spherical Earth model with no
ground track precession. For a real satellite (EAGLE-1), the ground track and
maximum elevation vary from pass to pass. Mitigation: document as "single-pass
simulation at maximum elevation scenario"; multi-pass annual estimator uses
a statistical model (N_passes × mean K_pass × clear_sky_fraction), not a
full STK-style propagator. This is sufficient for tool-level analysis.

---

## 8. Reproducibility Package

- Config files: `configs/satellite/eagle1_analog_berlin.yml`,
  `configs/satellite/eagle1_analog_snspd.yml`,
  `configs/satellite/micius_analog.yml`
- Reference outputs: `results/satellite/eagle1_analog_berlin/` (locked)
- Script: `scripts/run_satellite_chain_demo.py`
- Tests: `tests/pipeline/test_satellite_chain.py`
- Notebook: `examples/Satellite_to_Chip_Digital_Twin.ipynb`
- Second arxiv preprint: anchored to Scenarios 1 + 2 + Micius calibration

---

## 9. Acceptance Criteria

**Scientific correctness:**
- [ ] z(el=90°) = altitude_km (geometry identity test)
- [ ] η_geom ∝ D_R² / z² (geometric scaling verified)
- [ ] η_atm decreases monotonically with decreasing elevation
- [ ] PLOB bound not violated at any pass sample
- [ ] Micius analog K_pass within factor 10 of published sifted rate

**Engineering correctness:**
- [ ] All 10 unit tests pass
- [ ] Eagle1 analog produces K_pass > 0 at night (both APD and SNSPD scenarios)
- [ ] Annual estimate in physically reasonable range (1 kbit – 1 Tbit per year)
- [ ] Chain certificate schema-validates
- [ ] Pipeline completes in < 60 seconds for a 500-second pass at dt_s=5s

**Product/reporting:**
- [ ] `scripts/run_satellite_chain_demo.py` runs end-to-end with no exceptions
- [ ] Certificate clearly shows eta_chip from PIC certify (when M1 available)
- [ ] Annual estimate includes clear-sky probability and is documented
- [ ] Notebook runs on Google Colab with no local install

---

## 10. Decision

Proceed after M1 is complete (PIC certify provides η_chip). M5 can be
partially built before M1 using scalar η_chip input. The satellite chain
orchestrator and orbital geometry are independent of M1. The full integration
(PIC certify → satellite chain) requires M1.

Estimated effort: 3 weeks (1 week orbital geometry + config schema,
1 week pass integration + annual estimator, 1 week Micius calibration +
demo scripts + notebook).

---

## Implementation Plan

### Step 1: Orbital geometry utilities
- New file: `photonstrust/orbit/geometry.py`
- Functions: `slant_range_km(el_deg, altitude_km)`,
  `generate_elevation_profile(altitude_km, el_min_deg, dt_s)`,
  `annual_pass_count(latitude_deg, inclination_deg, altitude_km, el_min_deg)`

### Step 2: Satellite chain config schema
- New file: `schemas/satellite_qkd_chain.json`
- New function in `photonstrust/workflow/schema.py`

### Step 3: Satellite chain orchestrator
- New file: `photonstrust/pipeline/satellite_chain.py`
- Functions: `run_satellite_chain(config)`,
  `_build_orbit_pass_config(sat_cfg, eta_chip)`,
  `_estimate_annual_yield(sat_cfg, R_mean, T_pass)`

### Step 4: Chain certificate schema + builder
- New file: `schemas/satellite_qkd_chain_certificate.json`
- Function: `_build_chain_certificate(...)` in satellite_chain.py

### Step 5: CLI integration
- Edit `photonstrust/cli.py` — add `satellite-chain` subcommand
  `photonstrust satellite-chain configs/satellite/eagle1_analog_berlin.yml`

### Step 6: Reference scenarios, demo, tests, notebook
- New dir: `configs/satellite/` with 3 scenario YAML files
- New file: `scripts/run_satellite_chain_demo.py`
- New file: `tests/pipeline/test_satellite_chain.py`
- New file: `examples/Satellite_to_Chip_Digital_Twin.ipynb`

### Step 7: Second arxiv preprint
- Title: "PhotonTrust OrbitVerify: Open-Source Digital Twin for Satellite-to-Ground
          Photonic QKD Links"
- Sections: Introduction, Link Budget Model, Ground Station PIC Integration,
  Results (Eagle1 analog + Micius calibration), Conclusion
- Submit to arxiv quant-ph after Scenarios 1–3 pass acceptance criteria
