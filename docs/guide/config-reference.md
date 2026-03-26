# Configuration Reference

This document is the complete parameter reference for PhotonsTrust simulation
configurations. Parameters can be set via the Python API (`simulate_qkd_link`
keyword arguments and `**overrides`), YAML config files, or the scenario
gallery.

---

## Quick Example

```python
from photonstrust.easy import simulate_qkd_link

result = simulate_qkd_link(
    protocol="bb84",
    distance_km={"start": 0, "stop": 100, "step": 5},
    band="c_1550",
    detector="snspd",
    source_type="emitter_cavity",
    channel_model="fiber",
    include_uncertainty=True,
)
```

All parameters below can also be passed as nested `**overrides`:

```python
result = simulate_qkd_link(
    protocol="bb84",
    distance_km=50,
    source={"rep_rate_mhz": 200, "g2_0": 0.01},
    detector={"pde": 0.90, "dark_counts_cps": 10},
)
```

---

## Source Parameters

| Parameter              | Type  | Default | Range   | Unit | Description                                         |
|------------------------|-------|---------|---------|------|-----------------------------------------------------|
| `type`                 | str   | `emitter_cavity` | `emitter_cavity`, `spdc` | - | Photon source type |
| `rep_rate_mhz`         | float | 100     | 1-1000  | MHz  | Source repetition rate                               |
| `collection_efficiency`| float | 0.35    | 0-1     | -    | Photon collection efficiency                         |
| `coupling_efficiency`  | float | 0.60    | 0-1     | -    | Fiber coupling efficiency                            |
| `physics_backend`      | str   | `analytic` | `analytic`, `qutip` | - | Physics simulation backend |
| `emission_mode`        | str   | `steady_state` | `steady_state`, `pulsed` | - | Emission mode |

### Emitter-cavity source (`type: emitter_cavity`)

| Parameter              | Type  | Default | Range   | Unit | Description                                         |
|------------------------|-------|---------|---------|------|-----------------------------------------------------|
| `g2_0`                 | float | 0.02    | 0-1     | -    | Second-order autocorrelation at zero delay            |
| `purcell_factor`       | float | 5       | 1-100   | -    | Cavity Purcell enhancement factor                    |
| `radiative_lifetime_ns`| float | 1.0     | 0.1-100 | ns   | Emitter radiative lifetime                           |
| `dephasing_rate_per_ns`| float | 0.5     | 0-10    | 1/ns | Pure dephasing rate                                  |
| `drive_strength`       | float | 0.05    | 0-1     | -    | Resonant drive strength (Rabi frequency / cavity decay) |
| `pulse_window_ns`      | float | 5.0     | 1-100   | ns   | Pulsed excitation window (default: 5x radiative lifetime) |
| `transient_steps`      | int   | 64      | 16-1024 | -    | Number of time steps for transient simulation        |

### SPDC source (`type: spdc`)

| Parameter | Type  | Default | Range   | Unit | Description                             |
|-----------|-------|---------|---------|------|-----------------------------------------|
| `mu`      | float | 0.05    | 0-1     | -    | Mean photon-pair number per pulse        |

---

## Channel Parameters

| Parameter              | Type  | Default   | Range   | Unit  | Description                                  |
|------------------------|-------|-----------|---------|-------|----------------------------------------------|
| `model`                | str   | `fiber`   | `fiber`, `free_space`, `satellite` | - | Channel model |
| `connector_loss_db`    | float | 1.5 (fiber) / 1.0 (free-space) | 0-10 | dB | Fixed connector/coupling loss |

### Fiber channel (`model: fiber`)

| Parameter              | Type  | Default           | Range   | Unit    | Description                         |
|------------------------|-------|-------------------|---------|---------|-------------------------------------|
| `fiber_loss_db_per_km` | float | from band preset  | 0-10    | dB/km   | Fiber attenuation                   |
| `dispersion_ps_per_km` | float | from band preset  | 0-100   | ps/km   | Chromatic dispersion                |

### Free-space / satellite channel (`model: free_space` or `satellite`)

| Parameter                         | Type  | Default | Range    | Unit   | Description                                  |
|-----------------------------------|-------|---------|----------|--------|----------------------------------------------|
| `elevation_deg`                   | float | 45.0    | 5-90     | deg    | Link elevation angle                         |
| `tx_aperture_m`                   | float | 0.12    | 0.01-2   | m      | Transmitter aperture diameter                |
| `rx_aperture_m`                   | float | 0.30    | 0.05-5   | m      | Receiver aperture diameter                   |
| `beam_divergence_urad`            | float | None    | 0.1-100  | urad   | Beam divergence (auto-computed if None)      |
| `pointing_jitter_urad`            | float | 1.5     | 0-50     | urad   | Pointing jitter standard deviation           |
| `pointing_model`                  | str   | `deterministic` | `deterministic`, `stochastic` | - | Pointing error model |
| `pointing_bias_urad`              | float | 0.0     | 0-50     | urad   | Systematic pointing bias                     |
| `pointing_sample_count`           | int   | 256     | 1-10000  | -      | Monte Carlo samples for stochastic pointing  |
| `atmospheric_extinction_db_per_km`| float | 0.02    | 0-1      | dB/km  | Atmospheric extinction coefficient           |
| `turbulence_scintillation_index`  | float | 0.15    | 0-1      | -      | Scintillation index (Rytov variance proxy)   |
| `turbulence_model`                | str   | `deterministic` | `deterministic`, `stochastic` | - | Turbulence model |
| `turbulence_sample_count`         | int   | 256     | 1-10000  | -      | Monte Carlo samples for turbulence           |
| `atmosphere_effective_thickness_km`| float| 20.0    | 5-50     | km     | Effective atmosphere thickness               |
| `background_counts_cps`           | float | 0.0     | 0-1e6   | cps    | Background count rate                        |
| `background_model`                | str   | `fixed` | `fixed`, `computed` | - | Background noise model              |
| `background_day_night`            | str   | `night` | `night`, `day` | -   | Day/night selection for background model     |

### Satellite-specific parameters (`model: satellite`)

| Parameter                  | Type  | Default | Range | Unit | Description                          |
|----------------------------|-------|---------|-------|------|--------------------------------------|
| `satellite_uplink_fraction`| float | 0.5     | 0-1   | -    | Fraction of link that is uplink      |
| `uplink_elevation_deg`     | float | 45.0    | 5-90  | deg  | Uplink elevation angle               |
| `downlink_elevation_deg`   | float | 45.0    | 5-90  | deg  | Downlink elevation angle             |

---

## Detector Parameters

| Parameter           | Type  | Default          | Range     | Unit  | Description                                     |
|---------------------|-------|------------------|-----------|-------|-------------------------------------------------|
| `class`             | str   | `snspd`          | `si_apd`, `ingaas`, `snspd` | - | Detector technology class |
| `pde`               | float | from preset      | 0-1       | -     | Photon detection efficiency                      |
| `dark_counts_cps`   | float | from preset      | 0-1e6     | cps   | Dark count rate                                  |
| `jitter_ps_fwhm`    | float | from preset      | 1-1000    | ps    | Timing jitter (FWHM)                            |
| `dead_time_ns`      | float | from preset      | 1-100000  | ns    | Detector dead time                               |
| `afterpulsing_prob` | float | from preset      | 0-0.1     | -     | Afterpulsing probability                         |
| `physics_backend`   | str   | `analytic`       | `analytic`, `qutip` | - | Physics simulation backend           |
| `sample_count`      | int   | 500              | 10-10000  | -     | Monte Carlo sample count (stochastic mode)       |
| `time_bin_ps`       | float | 10.0             | 1-1000    | ps    | Time bin width for histogram                     |
| `afterpulse_delay_ns`| float| 50.0             | 1-10000   | ns    | Afterpulse characteristic delay                  |

### Detector presets

| Class    | PDE  | Dark counts (cps) | Jitter (ps) | Dead time (ns) | Afterpulsing |
|----------|------|--------------------|-------------|-----------------|--------------|
| `si_apd` | 0.70 | 100                | 50          | 50              | 0.005        |
| `ingaas` | 0.20 | 500                | 80          | 10 000          | 0.02         |
| `snspd`  | 0.30 | 100                | 30          | 100             | 0.001        |

> Preset values are adjusted per band. For example, SNSPD PDE increases by 0.05
> at C-band; Si-APD PDE increases by 0.05 at NIR bands.

---

## Protocol Parameters

| Parameter       | Type  | Default | Description                                     |
|-----------------|-------|---------|-------------------------------------------------|
| `name`          | str   | `bb84`  | Protocol identifier (see [protocol-guide.md](protocol-guide.md)) |

### Protocol-specific parameters

| Protocol        | Parameter       | Default | Description                              |
|-----------------|-----------------|---------|------------------------------------------|
| `pm_qkd`        | `mu`            | 0.1     | Signal state mean photon number          |
| `pm_qkd`        | `phase_slices`  | 16      | Phase-matching slice count               |
| `tf_qkd`        | `mu`            | 0.1     | Signal state mean photon number          |
| `tf_qkd`        | `phase_slices`  | 16      | Phase-matching slice count               |
| `mdi_qkd`       | `mu`            | 0.3     | Signal state intensity                   |
| `mdi_qkd`       | `nu`            | 0.05    | Decoy state intensity                    |
| `amdi_qkd`      | `mu`            | 0.3     | Signal state intensity                   |
| `amdi_qkd`      | `nu`            | 0.05    | Decoy state intensity                    |
| `sns_tf_qkd`    | `mu_z`          | 0.3     | Z-basis signal intensity                 |
| `sns_tf_qkd`    | `mu_1`          | 0.1     | Decoy intensity 1                        |
| `sns_tf_qkd`    | `mu_2`          | 0.02    | Decoy intensity 2                        |

### Available protocols and aliases

| Protocol ID   | Aliases                         |
|---------------|---------------------------------|
| `bb84_decoy`  | `bb84`                          |
| `bbm92`       | `e91`                           |
| `mdi_qkd`     | `mdi`                           |
| `amdi_qkd`    | -                               |
| `pm_qkd`      | -                               |
| `tf_qkd`      | `tf`, `twin_field`, `twinfield` |
| `cv_qkd`      | `gg02`                          |
| `sns_tf_qkd`  | `sns`                           |
| `di_qkd`      | -                               |

---

## Band Presets

| Band       | Wavelength (nm) | Fiber loss (dB/km) | Dispersion (ps/km) | Typical use case        |
|------------|-----------------|--------------------|--------------------|-------------------------|
| `nir_795`  | 795             | 2.5                | 2.0                | Quantum-dot NIR sources |
| `nir_850`  | 850             | 2.2                | 2.0                | Short-range / free-space|
| `o_1310`   | 1310            | 0.33               | 3.0                | O-band telecom          |
| `c_1550`   | 1550            | 0.20               | 5.0                | C-band telecom (default)|

> **Tip:** C-band (1550 nm) has the lowest fiber loss and is the best choice
> for most fiber-based QKD links. NIR bands have significantly higher loss and
> are mainly useful for short-range or free-space scenarios.

---

## Distance Specification

The `distance_km` parameter accepts three formats:

### Single float

```python
# Auto-sweep from 0 to 50 km in ~20 steps
result = simulate_qkd_link(protocol="bb84", distance_km=50.0)
```

### List of distances

```python
# Evaluate at specific distances
result = simulate_qkd_link(protocol="bb84", distance_km=[10, 25, 50, 75, 100])
```

### Dictionary range

```python
# Sweep from 0 to 200 km in 10 km steps
result = simulate_qkd_link(
    protocol="bb84",
    distance_km={"start": 0, "stop": 200, "step": 10},
)
```

---

## Timing Parameters

| Parameter            | Type  | Default | Range  | Unit | Description                     |
|----------------------|-------|---------|--------|------|---------------------------------|
| `sync_drift_ps_rms`  | float | 10      | 0-1000 | ps   | Clock synchronization drift RMS |

---

## Uncertainty Parameters

| Parameter | Type | Default | Description                              |
|-----------|------|---------|------------------------------------------|
| `seed`    | int  | 42      | Random seed for Monte Carlo uncertainty  |

Set `include_uncertainty=False` in `simulate_qkd_link` to disable uncertainty
analysis entirely (faster runs).

---

## Schema Version

All configuration files (YAML) must include:

```yaml
schema_version: "0.1"
```

Legacy configs without a version are auto-migrated, but explicit versioning is
recommended. See [troubleshooting.md](troubleshooting.md) for
`ConfigSchemaVersionError` fixes.
