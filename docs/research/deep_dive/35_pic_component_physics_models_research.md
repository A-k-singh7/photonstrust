# PIC Component Physics Models: Deep Research Report

**Date:** 2026-03-25
**Scope:** Physics equations, published parameters, and implementation specifications for eight photonic integrated circuit component models targeted at 220 nm SOI platforms operating at C-band (1550 nm).

---

## Table of Contents

1. [MMI Coupler (Multimode Interference)](#1-mmi-coupler)
2. [Y-Branch Splitter](#2-y-branch-splitter)
3. [Mach-Zehnder Modulator (MZM)](#3-mach-zehnder-modulator)
4. [Ge-on-Si Photodetector](#4-ge-on-si-photodetector)
5. [Arrayed Waveguide Grating (AWG)](#5-arrayed-waveguide-grating)
6. [Thermo-Optic Heater](#6-thermo-optic-heater)
7. [Spot-Size Converter / Edge Coupler](#7-spot-size-converter--edge-coupler)
8. [Waveguide Crossing](#8-waveguide-crossing)

---

## 1. MMI Coupler

### 1.1 Physical Basis

The MMI coupler operates on the **self-imaging principle**: when a single-mode waveguide feeds into a wide multimode section, the input field reproduces itself (or mirror images) at predictable longitudinal positions due to constructive interference among the excited modes of the multimode region.

**Key reference:** Soldano, L. B. & Pennings, E. C. M., "Optical multi-mode interference devices based on self-imaging: principles and applications," *Journal of Lightwave Technology*, vol. 13, no. 4, pp. 615-627, April 1995.

### 1.2 Core Equations

#### Beat length

The fundamental beat length between the two lowest-order modes in a multimode waveguide of effective width `W_eff` is:

```
L_pi = (4 * n_eff * W_eff^2) / (3 * lambda)
```

where:
- `n_eff` = effective index of the fundamental mode in the multimode section
- `W_eff` = effective width of the multimode section (accounts for lateral penetration into the cladding)
- `lambda` = free-space wavelength

The effective width includes the Goos-Hanchen shift:

```
W_eff = W_MMI + (lambda / pi) * (n_clad / n_core)^(2*sigma) * (n_core^2 - n_clad^2)^(-1/2)
```

where `sigma = 0` for TE polarization and `sigma = 1` for TM.

#### General Interference (GI) mechanism

In GI-MMI, all modes are excited. Self-images form at:

```
L_MMI = (3 * p * L_pi) / N       (single images at specific p, N)
```

For a 1xN GI-MMI splitter:
- 1x2: `L_MMI = (3/2) * L_pi`  (first single image pair)
- 1x3: `L_MMI = L_pi`

#### Restricted Interference (RI) mechanism

RI uses symmetric excitation (input at the center or edges) to suppress certain mode families, producing images at shorter lengths:

- Paired interference: `L_MMI = L_pi / N` (for symmetric 2xN)
- 2x2 RI coupler (3 dB): `L_MMI = L_pi / 2`

#### Transfer matrix for NxM MMI

For a 2x2 MMI acting as a 3 dB coupler, the forward transfer matrix is:

```
M = sqrt(eta) * (1/sqrt(2)) * [[1,  j],
                                 [j,  1]]
```

where `eta = 10^(-IL_dB / 10)` is the power transmission efficiency accounting for excess loss.

For a 1x2 MMI:

```
out1 = sqrt(eta/2) * exp(j*phi_1) * in
out2 = sqrt(eta/2) * exp(j*phi_2) * in
```

where `phi_1` and `phi_2` are the accumulated phases to each output, and the power splitting ratio is ideally 50:50.

#### Excess loss model

Excess loss arises from imperfect self-imaging (higher-order mode content that does not re-image at the output):

```
IL_excess = -10 * log10(sum_m |c_m|^2 * T_m)
```

where `c_m` is the excitation coefficient of mode m, and `T_m` is its power transmission to the output. In practice, excess loss is dominated by the number of excited modes that fail to reconstruct the image.

For a well-designed 2x2 MMI, the excess loss from non-imaged modes scales approximately as:

```
IL_excess ~ (pi^2 / 48) * (W_out / W_MMI)^2   [in amplitude]
```

This is typically 0.1-0.3 dB for optimized designs.

#### Imbalance

The splitting imbalance (deviation from ideal 50:50) of a 2x2 MMI is:

```
Imbalance_dB = 10 * log10(P_bar / P_cross)
```

Typical values: < 0.1 dB for foundry-optimized designs.

### 1.3 Wavelength Dependence

The MMI length is optimized for a center wavelength. The deviation from ideal splitting at wavelength `lambda` when designed for `lambda_0`:

```
delta_L / L_MMI ~ (lambda - lambda_0) / lambda_0  *  [1 + (lambda / n_eff) * (dn_eff/dlambda)]
```

The 1 dB bandwidth is typically > 100 nm for a 2x2 MMI coupler on SOI.

### 1.4 Published Parameters for 220 nm SOI

| Parameter | 1x2 MMI | 2x2 MMI | Source |
|-----------|---------|---------|--------|
| MMI width | 2.5-6 um | 2.5-6 um | IMEC, AMF PDKs |
| MMI length | 10-30 um | 15-50 um | Soldano & Pennings 1995; Halir et al. OE 2006 |
| Insertion loss | 0.1-0.3 dB | 0.1-0.5 dB | IMEC iSiPP50G PDK |
| Imbalance | < 0.15 dB | < 0.15 dB | AIM Photonics PDK |
| Bandwidth (1 dB) | > 100 nm | > 100 nm | Halir et al. 2006 |
| Access waveguide width | 0.45-0.5 um | 0.45-0.5 um | Standard 220 nm SOI |
| Taper length (access) | 5-15 um | 5-15 um | Process-dependent |
| n_eff (TE0, 1550 nm) | ~2.85 | ~2.85 | 220 nm x 500 nm SOI wire |

**Additional references:**
- Halir, R. et al., "Colorless directional coupler with dispersion engineered sub-wavelength structure," *Optics Express*, vol. 20, pp. 13470, 2012.
- Besse, P. A. et al., "New 2x2 and 1x3 multimode interference couplers with free selection of power splitting ratios," *Journal of Lightwave Technology*, vol. 14, no. 10, pp. 2286-2293, 1996.
- Bachmann, M. et al., "General self-imaging properties in NxN multimode interference couplers including phase relations," *Applied Optics*, vol. 33, pp. 3905-3911, 1994.

### 1.5 Simulation Model I/O

**Inputs:**
- `W_mmi` (um): multimode section width
- `L_mmi` (um): multimode section length
- `n_eff`: effective index of MMI section (or computed from geometry)
- `n_ports_in`, `n_ports_out`: 1x2, 2x2, 1xN, etc.
- `insertion_loss_db`: total excess insertion loss
- `imbalance_db`: splitting ratio deviation from ideal
- `wavelength_nm`: operating wavelength
- `mechanism`: "GI" or "RI"

**Outputs:**
- Forward transfer matrix `M` (n_out x n_in), complex
- Scattering matrix `S` (N x N), complex, with optional reflections
- Power splitting ratios per output port
- Excess loss per port

---

## 2. Y-Branch Splitter

### 2.1 Physical Basis

A Y-branch (Y-junction) splits a single waveguide into two diverging branches. The structure is inherently a 3 dB (1:1) power splitter for the fundamental mode. The physics is governed by **adiabatic mode evolution**: if the taper is sufficiently gradual, the fundamental mode of the input waveguide evolves into the symmetric supermode of the two-waveguide system, which then decomposes into the fundamental modes of the two output waveguides.

### 2.2 Core Equations

#### Adiabatic criterion

For adiabatic (lossless) operation, the taper angle `theta` must satisfy:

```
theta << lambda / (2 * n_eff * W)
```

where `W` is the local waveguide width. Equivalently, the taper length `L_taper` must satisfy:

```
L_taper >> W / theta_max
```

Typical adiabatic Y-branches on SOI require `L_taper > 10-20 um` for < 0.2 dB excess loss.

#### Splitting ratio

For an ideal symmetric Y-branch:

```
P_out1 / P_in = P_out2 / P_in = (1 - IL) / 2
```

where `IL` is the fractional insertion loss. The splitting ratio deviation from 50:50 arises from fabrication asymmetry:

```
Split_ratio = (0.5 + delta, 0.5 - delta)
```

#### Excess loss model

The dominant loss mechanism is radiation at the junction point where the two waveguides separate. This loss depends on the gap at the junction tip and the taper angle:

```
IL_excess ~ (pi * gap / lambda)^2 * f(n_eff, geometry)
```

For sharp (non-adiabatic) junctions:

```
IL_sharp ~ -10 * log10(|<E_in | E_out1 + E_out2>|^2)
```

Computed from the overlap integral between the input mode and the sum of the two output modes.

A more practical semi-empirical model for excess loss vs. taper half-angle `alpha`:

```
IL_dB ~ A * exp(-B * L_taper / lambda) + C
```

where A, B, C are geometry-dependent fitting coefficients. For SOI 220 nm: A ~ 2 dB, B ~ 0.1 um^-1, C ~ 0.05 dB.

#### Forward transfer matrix (1x2)

```
M = sqrt(eta) * [[sqrt(r)],
                  [sqrt(1-r)]]
```

where `r` is the splitting ratio (ideally 0.5) and `eta = 10^(-IL_dB/10)`.

For the reverse (2x1 combiner), only the symmetric supermode couples to the output. The anti-symmetric component is radiated:

```
M_reverse = sqrt(eta) * [sqrt(r), sqrt(1-r)]
```

This inherently discards the antisymmetric portion, giving a maximum 3 dB theoretical loss when combining two independent signals.

#### Bandwidth

Y-branches are inherently broadband because the splitting mechanism depends on mode evolution, not interference. The 1 dB bandwidth is typically > 300 nm for adiabatic designs on SOI.

### 2.3 Published Parameters for 220 nm SOI

| Parameter | Value | Source |
|-----------|-------|--------|
| Taper length | 10-50 um | IMEC iSiPP50G; GlobalFoundries 45CLO |
| Junction gap (tip) | 100-200 nm (litho-limited) | Process design rule |
| Excess insertion loss | 0.1-0.3 dB | Zhang et al., OL 2013 |
| Imbalance | < 0.1 dB | Foundry PDK specs |
| 1 dB bandwidth | > 300 nm | Inherent broadband |
| Input waveguide width | 0.45-0.5 um | Standard SOI wire |
| Output waveguide width | 0.45-0.5 um (each arm) | Standard SOI wire |
| Branch angle | 1-3 degrees | Design-dependent |

**Key references:**
- Zhang, Y. et al., "A compact and low loss Y-junction for submicron silicon waveguide," *Optics Express*, vol. 21, no. 1, pp. 1310-1316, 2013.
- Sakai, A. et al., "Low-loss ultra-small branches in a silicon photonic wire waveguide," *IEICE Transactions*, vol. E85-C, no. 4, pp. 1033-1038, 2002.
- Bogaerts, W. et al., "Silicon microring resonators," *Laser & Photonics Reviews*, vol. 6, no. 1, pp. 47-73, 2012 (contains Y-branch data in context of ring circuits).

### 2.4 Simulation Model I/O

**Inputs:**
- `taper_length_um`: length of the Y-junction taper
- `branch_angle_deg`: half-angle of the Y-branch
- `gap_nm`: gap at the junction tip
- `insertion_loss_db`: excess loss
- `splitting_ratio`: fraction of power to output 1 (default 0.5)
- `wavelength_nm`: operating wavelength

**Outputs:**
- Forward transfer matrix `M` (2x1), complex
- Splitting ratio (power) per output
- Excess loss (dB)

---

## 3. Mach-Zehnder Modulator (MZM)

### 3.1 Physical Basis

Silicon MZMs exploit the **free-carrier plasma dispersion effect** (Soref & Bennett, 1987) to modulate the refractive index of silicon through carrier injection, depletion, or accumulation in a PN or PIN junction embedded in the waveguide.

**Foundational reference:** Soref, R. A. & Bennett, B. R., "Electrooptical effects in silicon," *IEEE Journal of Quantum Electronics*, vol. QE-23, no. 1, pp. 123-129, January 1987.

### 3.2 Core Equations

#### Plasma dispersion effect (Soref & Bennett)

At 1550 nm, the empirical change in refractive index and absorption coefficient due to free carriers:

```
delta_n = delta_n_e + delta_n_h
        = -[8.8e-22 * delta_N_e + 8.5e-18 * (delta_N_h)^0.8]

delta_alpha = delta_alpha_e + delta_alpha_h
            = 8.5e-18 * delta_N_e + 6.0e-18 * delta_N_h    [cm^-1]
```

where:
- `delta_N_e` = change in free electron concentration (cm^-3)
- `delta_N_h` = change in free hole concentration (cm^-3)
- `delta_n` = change in real refractive index (dimensionless)
- `delta_alpha` = change in absorption coefficient (cm^-1)

Updated coefficients (Nedeljkovic et al., IEEE Phot. J. 2011):

```
delta_n_e = -5.4e-22 * (delta_N_e)^1.011
delta_n_h = -1.53e-18 * (delta_N_h)^0.838

delta_alpha_e = 8.88e-21 * delta_N_e^1.167    [cm^-1]
delta_alpha_h = 5.84e-20 * delta_N_h^1.109    [cm^-1]
```

#### PN junction depletion-mode phase shifter

In reverse bias, the depletion width `W_dep` changes with voltage:

```
W_dep(V) = sqrt(2 * epsilon_Si * (V_bi - V) * (N_A + N_D) / (q * N_A * N_D))
```

where:
- `epsilon_Si` = 11.7 * epsilon_0 = 1.04e-12 F/cm (permittivity of silicon)
- `V_bi` = (kT/q) * ln(N_A * N_D / n_i^2) (built-in voltage, typically 0.7-0.9 V)
- `V` = applied voltage (negative for reverse bias)
- `N_A`, `N_D` = acceptor and donor concentrations (cm^-3)
- `q` = 1.602e-19 C
- `n_i` = 1.08e10 cm^-3 (intrinsic carrier concentration in Si at 300K)

The change in carrier concentration within the waveguide mode region:

```
delta_N_e ~ N_D * delta_W_dep / W_wg
delta_N_h ~ N_A * delta_W_dep / W_wg
```

#### PIN junction carrier-injection mode

Under forward bias, injected carriers change the index:

```
delta_n(I) = -[8.8e-22 * n_e(I) + 8.5e-18 * n_h(I)^0.8]
```

where carrier concentration depends on injection current:

```
n = I * tau / (q * V_active)
```

- `tau` = carrier lifetime (~1-10 ns in SOI)
- `V_active` = active volume of the waveguide junction region

PIN injection gives larger `delta_n` per unit length but is speed-limited by carrier recombination.

#### Phase shift

```
delta_phi = (2 * pi / lambda) * delta_n_eff * L
```

where `delta_n_eff = Gamma * delta_n` and `Gamma` is the optical confinement factor (overlap of the mode with the doped region), typically 0.7-0.9 for SOI rib waveguides.

#### V_pi * L_pi product

The voltage-length product for a pi phase shift:

```
V_pi * L_pi = lambda / (2 * |dn_eff/dV|)
```

Typical values for SOI PN depletion-mode:
- `V_pi * L_pi ~ 1.5-2.5 V*cm` at -2V bias
- `V_pi * L_pi ~ 0.8-1.5 V*cm` at -4V bias

#### MZM transfer function

For a push-pull MZM with splitting ratio `r` (power fraction to arm 1):

```
E_out = E_in * sqrt(eta) * [sqrt(r) * exp(j*phi_1) + sqrt(1-r) * exp(j*phi_2)]
```

Power transfer:

```
T = eta * [r + (1-r) + 2*sqrt(r*(1-r)) * cos(delta_phi)]
  = eta * [1 + 2*sqrt(r*(1-r)) * cos(delta_phi)]    (for r + (1-r) = 1)
```

where `delta_phi = phi_1 - phi_2`.

For ideal 50:50 splitting (r = 0.5):

```
T = eta * cos^2(delta_phi / 2)
```

#### Extinction ratio

```
ER = 10 * log10((P_max / P_min))
   = 10 * log10(((sqrt(r) + sqrt(1-r))^2) / ((sqrt(r) - sqrt(1-r))^2))
   = 10 * log10(((1 + 2*sqrt(r*(1-r))) / (1 - 2*sqrt(r*(1-r)))))
```

For small imbalance `delta_r = r - 0.5`:

```
ER ~ 10 * log10(1 / (4 * delta_r^2))
```

Alternatively, defining `gamma = |sqrt(r) - sqrt(1-r)| / |sqrt(r) + sqrt(1-r)|` (the amplitude imbalance ratio):

```
ER = -20 * log10(gamma)    [in dB, with gamma < 1]
```

#### Bandwidth limitations

**RC-limited bandwidth:**

```
f_RC = 1 / (2 * pi * R_total * C_junction)
```

where:
- `R_total = R_series + R_driver` (series resistance of junction + driver impedance, typically 50 ohm)
- `C_junction = epsilon_Si * A_junction / W_dep` (junction capacitance per unit length times length)

For traveling-wave electrode (TWE) MZMs:

```
f_3dB_TW ~ 1.4 * c / (pi * L * |n_RF - n_opt|)     (velocity mismatch limited)
```

and also limited by RF loss:

```
f_3dB_TW ~ (6.4 / (alpha_RF * L))^2               (RF attenuation limited, alpha in Np/m)
```

**Transit-time limited bandwidth** (for lumped-element):

```
f_transit = 0.45 * v_sat / W_dep
```

where `v_sat ~ 1e7 cm/s` for silicon.

**Combined:**

```
1/f_3dB^2 = 1/f_RC^2 + 1/f_transit^2
```

### 3.3 Published Parameters for 220 nm SOI

| Parameter | PN depletion | PIN injection | Source |
|-----------|-------------|---------------|--------|
| V_pi * L_pi | 1.5-2.5 V*cm | 0.02-0.05 V*cm | Reed et al., Nature Photonics 2010 |
| Phase shifter length | 1-4 mm | 0.2-1 mm | IMEC iSiPP50G |
| V_pi (for L=2mm) | 5-8 V | N/A (current driven) | Thomson et al., JLT 2012 |
| Insertion loss (phase shifter) | 3-8 dB (length-dep.) | 1-3 dB | Process-dependent |
| Propagation loss in doped WG | 5-15 dB/cm | 2-5 dB/cm | Doping-dependent |
| 3 dB EO bandwidth | 25-60 GHz (TWE) | 0.5-2 GHz | Xu et al., Nature 2005 (PIN); Thomson et al. 2012 (PN) |
| Extinction ratio | 20-35 dB | 20-40 dB | Design-dependent |
| Modulation format | NRZ, PAM4, QPSK | OOK | Application-dependent |
| Operating voltage swing | 1-4 V_pp | 1-5 mA | Typical driver specs |
| PN doping levels | N_D ~ 5e17, N_A ~ 3e17 cm^-3 | N/A | IMEC standard |
| Rib waveguide dimensions | 500 nm x 220 nm, 90 nm slab | Similar | Standard SOI rib |

**Key references:**
- Reed, G. T. et al., "Silicon optical modulators," *Nature Photonics*, vol. 4, pp. 518-526, 2010.
- Thomson, D. J. et al., "50-Gb/s silicon optical modulator," *IEEE Photonics Technology Letters*, vol. 24, no. 4, pp. 234-236, 2012.
- Xu, Q. et al., "Micrometre-scale silicon electro-optic modulator," *Nature*, vol. 435, pp. 325-327, 2005.
- Nedeljkovic, M. et al., "Free-carrier electrorefraction and electroabsorption modulation predictions for silicon over the 1-14 um infrared wavelength range," *IEEE Photonics Journal*, vol. 3, no. 6, pp. 1171-1180, 2011.
- Dong, P. et al., "Low Vpp, ultralow-energy, compact, high-speed silicon electro-optic modulator," *Optics Express*, vol. 17, no. 25, pp. 22484-22490, 2009.

### 3.4 Simulation Model I/O

**Inputs:**
- `modulator_type`: "PN_depletion" | "PIN_injection"
- `phase_shifter_length_mm`: length of the active region
- `V_pi_L_pi`: voltage-length product (V*cm)
- `voltage_bias_V`: DC bias voltage
- `voltage_signal_V`: RF signal amplitude (peak-to-peak)
- `splitting_ratio`: splitter imbalance (default 0.5)
- `insertion_loss_db`: total passive insertion loss (splitter + combiner + waveguide)
- `alpha_dB_per_cm`: propagation loss in doped waveguide
- `wavelength_nm`: operating wavelength
- `bandwidth_GHz`: 3 dB EO bandwidth (for frequency response)
- `N_A`, `N_D`: doping concentrations (cm^-3) [for physics-based mode]

**Outputs:**
- `T(V)`: optical transmission vs. voltage (transfer curve)
- `delta_phi(V)`: phase shift vs. voltage
- `ER_dB`: extinction ratio
- `IL_dB`: total insertion loss at quadrature point
- `bandwidth_3dB_GHz`: electro-optic bandwidth
- `chirp_alpha`: chirp parameter (alpha_H)
- S-matrix (2x2 with optional MZI arms exposed as internal ports)

---

## 4. Ge-on-Si Photodetector

### 4.1 Physical Basis

Germanium-on-silicon (Ge-on-Si) photodetectors exploit the direct-bandgap absorption of Ge (E_g_direct ~ 0.80 eV at 300K, corresponding to ~1550 nm) grown epitaxially on Si. The tensile strain from the Si/Ge lattice mismatch and thermal expansion difference red-shifts the absorption edge, enabling detection across the full C+L telecom bands (1530-1620 nm).

### 4.2 Core Equations

#### Responsivity

```
R = eta_ext * q * lambda / (h * c)    [A/W]
```

where:
- `eta_ext` = external quantum efficiency (dimensionless)
- `q` = 1.602e-19 C (electron charge)
- `h` = 6.626e-34 J*s (Planck constant)
- `c` = 2.998e8 m/s (speed of light)
- `lambda` = wavelength (m)

At 1550 nm: `q*lambda/(h*c) = 1.25 A/W`, so `R = 1.25 * eta_ext`.

#### Quantum efficiency

The external quantum efficiency is composed of:

```
eta_ext = eta_coupling * eta_abs * eta_collection
```

where:
- `eta_coupling` = fraction of waveguide light coupled into the Ge absorber (butt-coupling efficiency, typically 0.8-0.95)
- `eta_abs = 1 - exp(-alpha * L_Ge)` = fraction of light absorbed in Ge of length `L_Ge`
- `eta_collection` = fraction of photogenerated carriers collected before recombination (typically 0.9-0.99 for well-designed PIN)

The absorption coefficient of Ge at 1550 nm:

```
alpha_Ge ~ 4000-7000 cm^-1    (strain-dependent, at 1550 nm)
```

For an evanescently-coupled waveguide photodetector, replace `alpha * L` with an effective absorption:

```
eta_abs = 1 - exp(-Gamma_Ge * alpha_Ge * L_Ge)
```

where `Gamma_Ge` is the confinement factor of the optical mode in the Ge region.

#### Dark current

```
I_dark = J_dark * A_Ge + J_surface * P_Ge
```

where:
- `J_dark` = bulk dark current density (A/cm^2), typically 1-100 mA/cm^2 for Ge-on-Si
- `A_Ge` = cross-sectional area of the Ge absorber (cm^2)
- `J_surface` = surface leakage current density
- `P_Ge` = perimeter of the Ge absorber

For a well-passivated Ge-on-Si PIN with area `A`:

```
I_dark = J_dark * A
```

Typical values: `J_dark ~ 1-50 mA/cm^2`, giving `I_dark ~ 1-100 nA` for typical detector areas (5-50 um^2).

The dark current temperature dependence:

```
I_dark(T) = I_dark(T_0) * (T/T_0)^2 * exp(-E_g/(2*k_B) * (1/T - 1/T_0))
```

#### 3 dB Bandwidth

**Transit-time limited:**

```
f_tr = 0.45 * v_sat / w_i
```

where:
- `v_sat` = saturation velocity of carriers in Ge (~6e6 cm/s for electrons, ~5e6 cm/s for holes)
- `w_i` = intrinsic (depletion) region width

The factor 0.45 comes from the Fourier analysis of a uniform photocurrent impulse response:

```
H(f) = sin(pi*f*t_tr) / (pi*f*t_tr)    where t_tr = w_i / v_sat
```

giving `f_tr = 0.443 / t_tr`.

**RC-limited:**

```
f_RC = 1 / (2 * pi * R_total * C_total)
```

where:
- `C_total = epsilon_Ge * A / w_i + C_parasitic` (junction capacitance + parasitics)
- `epsilon_Ge = 16.0 * epsilon_0 = 1.42e-12 F/cm`
- `R_total = R_series + R_load` (series resistance + load impedance, typically 50 ohm)

**Combined bandwidth:**

```
1 / f_3dB^2 = 1 / f_tr^2 + 1 / f_RC^2
```

This is the standard approximation assuming the two bandwidth limits contribute independently.

#### Noise

**Shot noise current:**

```
i_shot = sqrt(2 * q * (I_photo + I_dark) * B)
```

**Thermal noise:**

```
i_thermal = sqrt(4 * k_B * T * B / R_load)
```

**Signal-to-noise ratio:**

```
SNR = I_photo^2 / (i_shot^2 + i_thermal^2)
```

**Noise-equivalent power (NEP):**

```
NEP = sqrt(2 * q * I_dark) / R    [W/sqrt(Hz)]
```

### 4.3 Published Parameters for Ge-on-Si

| Parameter | Value | Source |
|-----------|-------|--------|
| Responsivity at 1550 nm | 0.8-1.1 A/W | Vivien et al., OE 2012; Michel et al., Nature Phot. 2010 |
| Responsivity at 1310 nm | 0.9-1.15 A/W | Higher alpha at 1310 nm |
| Dark current | 1-100 nA (at -1V) | Loh et al., IEEE PTL 2018; IMEC PDK |
| Dark current density | 1-50 mA/cm^2 | Process-dependent |
| 3 dB bandwidth | 30-70 GHz | Vivien et al. 2012; Loh et al. 2018 |
| Ge thickness | 0.5-1.0 um | Standard epitaxial growth |
| Ge length | 10-40 um | Design parameter |
| Ge width | 5-10 um | Design parameter |
| Depletion width (w_i) | 0.3-1.0 um | Vertical PIN |
| Reverse bias voltage | -1 to -3 V | Typical operating range |
| Saturation photocurrent | 1-10 mA | Linearity limit |
| alpha_Ge (1550 nm, strained) | 4000-7000 cm^-1 | Strain-enhanced |
| alpha_Ge (1310 nm) | ~10000 cm^-1 | Well above bandgap |

**Key references:**
- Michel, J. et al., "High-performance Ge-on-Si photodetectors," *Nature Photonics*, vol. 4, pp. 527-534, 2010.
- Vivien, L. et al., "Zero bias 40Gbit/s germanium waveguide photodetector on silicon," *Optics Express*, vol. 20, no. 2, pp. 1096-1101, 2012.
- Ahn, D. et al., "High performance, waveguide integrated Ge photodetectors," *Optics Express*, vol. 15, no. 7, pp. 3916-3921, 2007.
- Loh, T. H. et al., "Ultrathin low-temperature SiGe buffer for the growth of high quality Ge epilayer on Si(100) by ultrahigh vacuum chemical vapor deposition," *Applied Physics Letters*, 2007.
- Assefa, S. et al., "Reinventing germanium avalanche photodetector for nanophotonic on-chip optical interconnects," *Nature*, vol. 464, pp. 80-84, 2010.

### 4.4 Simulation Model I/O

**Inputs:**
- `Ge_length_um`: length of Ge absorber
- `Ge_width_um`: width of Ge absorber
- `Ge_thickness_um`: thickness of Ge layer
- `depletion_width_um`: intrinsic region width (or computed from bias)
- `bias_voltage_V`: reverse bias
- `alpha_Ge_per_cm`: absorption coefficient at operating wavelength (or computed from wavelength)
- `J_dark_mA_per_cm2`: dark current density
- `R_series_ohm`: series resistance
- `R_load_ohm`: load resistance (typically 50)
- `C_parasitic_fF`: parasitic capacitance
- `eta_coupling`: waveguide-to-Ge coupling efficiency
- `wavelength_nm`: operating wavelength
- `temperature_K`: operating temperature

**Outputs:**
- `responsivity_A_per_W`: responsivity at operating wavelength
- `I_dark_nA`: dark current
- `f_3dB_GHz`: 3 dB bandwidth
- `NEP_W_per_rtHz`: noise-equivalent power
- `I_photo(P_in)`: photocurrent vs. input optical power

---

## 5. Arrayed Waveguide Grating (AWG)

### 5.1 Physical Basis

The AWG is a planar dispersive wavelength demultiplexer consisting of:
1. An input star coupler (free propagation region, FPR)
2. An array of waveguides with constant path length increment `delta_L`
3. An output star coupler (FPR)
4. Output waveguides positioned along the focal curve

The principle: light from the input waveguide diffracts in the first FPR, couples into the waveguide array, accumulates wavelength-dependent phase differences `delta_phi = (2*pi/lambda) * n_eff * delta_L`, and then recombines in the second FPR. Different wavelengths focus at different positions along the output focal curve.

### 5.2 Core Equations

#### Grating equation

The constructive interference condition (in the slab FPR region):

```
n_s * d * sin(theta_in) + n_eff * delta_L + n_s * d * sin(theta_out) = m * lambda
```

where:
- `n_s` = effective index of the slab (FPR) mode
- `d` = pitch (spacing) of the arrayed waveguides at the FPR interface
- `theta_in`, `theta_out` = angles of incidence/diffraction from the array center
- `n_eff` = effective index of the arrayed waveguides
- `delta_L` = constant path length increment between adjacent waveguides
- `m` = diffraction order (integer)

At the center wavelength `lambda_c` with center input/output (`theta_in = theta_out = 0`):

```
n_eff * delta_L = m * lambda_c
```

Therefore:

```
m = n_eff * delta_L / lambda_c
```

#### Free spectral range (FSR)

```
FSR = lambda_c^2 / (n_g * delta_L)
```

where `n_g` is the group index of the arrayed waveguides:

```
n_g = n_eff - lambda * (dn_eff / dlambda)
```

Typical SOI values: `n_g ~ 4.2-4.4` for 220 nm SOI strip waveguides.

#### Channel spacing

```
delta_lambda = FSR / N_ch
```

where `N_ch` is the number of output channels. Alternatively, from the angular dispersion:

```
delta_lambda = n_s * d * delta_x / (m * R_f)
```

where `delta_x` is the spacing between output waveguides at the focal curve and `R_f` is the focal length of the FPR (Rowland circle radius).

#### Number of arrayed waveguides

The minimum number of arrayed waveguides `N_a` determines the angular resolution:

```
N_a >= m * N_ch
```

In practice, `N_a` is chosen as:

```
N_a ~ 2 * m * N_ch / FSR * delta_lambda
```

or simply `N_a ~ 2*N_ch` to `4*N_ch` for adequate sidelobe suppression.

#### Rowland circle geometry

The input and output waveguides are placed on a Rowland circle of radius `R_f/2`, while the arrayed waveguides are positioned on a circle of radius `R_f` (the grating circle):

```
R_f = N_a * d / (2 * n_s) * (lambda_c / delta_lambda) / N_ch
```

More precisely:

```
R_f = n_s * N_a * d^2 / (m * lambda_c)
```

#### Passband shape

**Gaussian passband** (standard):

The transmission of channel `k` as a function of wavelength:

```
T_k(lambda) = T_0 * exp(-4 * ln(2) * ((lambda - lambda_k) / delta_lambda_3dB)^2)
```

where `delta_lambda_3dB` is the 3 dB passband width.

**Flat-top passband:**

Achieved by using a multimode interference (MMI) or parabolic horn at the input. The passband shape is then approximately:

```
T_k(lambda) ~ T_0 * sinc^2(pi * (lambda - lambda_k) / delta_lambda_flat)
```

or trapezoidal, depending on design. Flat-top designs have 1-2 dB higher insertion loss but < 1 dB passband ripple.

#### Crosstalk

**Adjacent channel crosstalk:**

```
X_adj = -10 * log10(T_k(lambda_{k+1}) / T_k(lambda_k))
```

For Gaussian passbands:

```
X_adj ~ 4 * ln(2) * (delta_lambda / delta_lambda_3dB)^2 * (10/ln(10))    [dB]
```

**Non-adjacent (background) crosstalk:**

Arises from phase errors in the arrayed waveguides due to fabrication non-uniformity:

```
X_bg ~ -10 * log10(N_a * (delta_phi_rms / (2*pi))^2)
```

where `delta_phi_rms` is the RMS phase error across the array. For SOI: `delta_phi_rms ~ 0.01-0.1 rad`, giving `X_bg ~ -20 to -35 dB`.

#### Insertion loss budget

```
IL_total = IL_FPR_in + IL_array + IL_FPR_out + IL_coupling + IL_truncation
```

where:
- `IL_FPR` = free propagation region diffraction loss (typically 0.5-1 dB each)
- `IL_array` = propagation loss in arrayed waveguides (`alpha * L_avg`)
- `IL_coupling` = mode mismatch at FPR-to-waveguide interfaces
- `IL_truncation` = finite aperture truncation loss (Gaussian illumination clipped by finite array)

```
IL_truncation ~ -10 * log10(erf(sqrt(2) * N_a * d / (2 * w_mode)))^2
```

### 5.3 Published Parameters for 220 nm SOI

| Parameter | Value | Source |
|-----------|-------|--------|
| Channel count | 4-64 channels | Design-dependent |
| Channel spacing | 0.8 nm (100 GHz), 1.6 nm (200 GHz), 3.2 nm (400 GHz) | ITU grid |
| Free spectral range | 12-50 nm | Design-dependent |
| Insertion loss (center) | 1.5-4 dB | Pathak et al., JLT 2014; Bogaerts et al. 2005 |
| Adjacent crosstalk | -20 to -35 dB | Phase error limited |
| Non-adjacent crosstalk | -15 to -30 dB | Fabrication-limited |
| Passband width (3 dB) | 0.3-0.8 nm (Gaussian) | Design-dependent |
| Footprint (8-ch, 200 GHz) | ~0.5 mm x 0.5 mm | SOI compact designs |
| delta_L | 10-50 um | Design-dependent |
| Arrayed waveguide count | 20-200 | Design-dependent |
| Waveguide width (array) | 0.45-0.5 um | Standard SOI |
| Waveguide pitch (d) | 1.0-2.0 um | Limited by coupling |
| Temperature sensitivity | ~80 pm/K | Due to dn/dT of Si |

**Key references:**
- Smit, M. K. & van Dam, C., "PHASAR-based WDM-devices: principles, design, and applications," *IEEE Journal of Selected Topics in Quantum Electronics*, vol. 2, no. 2, pp. 236-250, 1996.
- Bogaerts, W. et al., "Compact wavelength-selective functions in silicon-on-insulator photonic wires," *IEEE Journal of Selected Topics in Quantum Electronics*, vol. 12, no. 6, pp. 1394-1401, 2006.
- Pathak, S. et al., "Comparison of AWGs and echelle gratings for wavelength division multiplexing on silicon-on-insulator," *IEEE Photonics Journal*, vol. 6, no. 5, 2014.
- Cheben, P. et al., "A high-resolution silicon-on-insulator arrayed waveguide grating microspectrometer with sub-micrometer aperture waveguides," *Optics Express*, vol. 15, pp. 2299-2306, 2007.
- Okamoto, K., "Fundamentals of Optical Waveguides," Academic Press, 2nd edition, 2006. (Chapters 9-10 on AWGs.)

### 5.4 Simulation Model I/O

**Inputs:**
- `N_channels`: number of output channels
- `center_wavelength_nm`: center wavelength of the AWG
- `channel_spacing_nm`: wavelength spacing between channels
- `FSR_nm`: free spectral range (or computed)
- `delta_L_um`: path length increment
- `N_arrayed`: number of arrayed waveguides
- `n_eff`: effective index of arrayed waveguides
- `n_g`: group index
- `n_slab`: effective index of FPR slab mode
- `d_pitch_um`: waveguide pitch at FPR interface
- `passband_shape`: "gaussian" | "flat_top"
- `phase_error_rms_rad`: RMS phase error in the array
- `insertion_loss_db`: total insertion loss at center channel
- `propagation_loss_dB_per_cm`: waveguide loss in the array

**Outputs:**
- `T(lambda)`: transmission spectrum for each output channel (NxM matrix: N_ch x N_wavelengths)
- `IL_per_channel_dB`: insertion loss per channel
- `crosstalk_adj_dB`: adjacent channel crosstalk
- `crosstalk_bg_dB`: background crosstalk level
- `center_wavelength_per_channel`: center wavelength of each channel
- `passband_3dB_width_nm`: 3 dB bandwidth per channel
- Scattering matrix `S` (N_in x N_out x N_wavelengths)

---

## 6. Thermo-Optic Heater

### 6.1 Physical Basis

Silicon has a large thermo-optic coefficient (`dn/dT ~ 1.86e-4 /K`), enabling efficient phase tuning via local heating. A metallic (TiN, NiCr, or W) or doped-silicon resistive heater is placed above or adjacent to the waveguide. Electrical power dissipation raises the local temperature, changing the effective index of the guided mode.

### 6.2 Core Equations

#### Thermo-optic coefficients

| Material | dn/dT (K^-1) | Source |
|----------|-------------|--------|
| Si | 1.86e-4 | Cocorullo & Rendina, Elect. Lett. 1992 |
| SiN (Si3N4) | 2.45e-5 | Arbabi & Goddard, Opt. Lett. 2013 |
| SiO2 | 1.0e-5 | Handbook value |
| Ge | 4.1e-4 | Li, J. Phys. Chem. Ref. Data 1980 |

Note: Si dn/dT is ~7.5x larger than SiN, making SOI much more efficient for thermo-optic tuning.

#### Phase shift from heating

```
delta_phi = (2 * pi / lambda) * (dn/dT) * delta_T * L_heater
```

where:
- `lambda` = free-space wavelength (m)
- `dn/dT` = thermo-optic coefficient of the waveguide core
- `delta_T` = local temperature rise (K) averaged over the waveguide mode
- `L_heater` = length of the heater section (m)

For a pi phase shift:

```
delta_T_pi = lambda / (2 * (dn/dT) * L_heater)
```

At 1550 nm with Si and L_heater = 100 um:

```
delta_T_pi = 1.55e-6 / (2 * 1.86e-4 * 100e-6) = 41.7 K
```

#### Power efficiency (P_pi)

The electrical power required for a pi phase shift:

```
P_pi = delta_T_pi / R_th
```

where `R_th` is the thermal resistance (K/mW) from the heater to the heat sink (substrate).

```
R_th = t_clad / (k_SiO2 * A_eff)
```

where:
- `t_clad` = thickness of the SiO2 cladding between heater and substrate (~2-3 um)
- `k_SiO2 ~ 1.38 W/(m*K)` = thermal conductivity of SiO2
- `A_eff` = effective heated area (heater length x effective thermal spreading width)

Typical values:
- `R_th ~ 10-30 K/mW` per 100 um heater length
- `P_pi ~ 20-40 mW` for standard SOI
- Undercut/suspended waveguides: `P_pi ~ 1-5 mW` (much higher R_th due to air isolation)

#### Thermal crosstalk

The temperature perturbation at distance `r` from the heater decays approximately as:

```
delta_T(r) = delta_T_heater * K_0(r / L_th) / K_0(0)
```

where `K_0` is the modified Bessel function of the second kind. For large `r`:

```
delta_T(r) ~ delta_T_heater * exp(-r / L_th) / sqrt(r)
```

where `L_th` is the thermal decay length, typically:

```
L_th = sqrt(k_SiO2 * t_clad / h_sub)
```

With `h_sub` being the effective heat transfer coefficient to the substrate. Typical `L_th ~ 10-50 um` in SOI.

A practical model for thermal crosstalk between heater `i` and waveguide `j`:

```
delta_phi_j = sum_i (K_ij * P_i)
```

where `K_ij` is the thermal crosstalk kernel (rad/mW), approximately:

```
K_ij ~ K_ii * exp(-d_ij / L_th)
```

with `d_ij` = center-to-center distance between heater i and waveguide j.

#### Thermal time constant

The thermal response is characterized by a first-order time constant:

```
tau = R_th * C_th
```

where `C_th` is the thermal capacitance:

```
C_th = rho * c_p * V_heated
```

- `rho` = density (SiO2: 2200 kg/m^3; Si: 2330 kg/m^3)
- `c_p` = specific heat capacity (SiO2: 700 J/(kg*K); Si: 700 J/(kg*K))
- `V_heated` = volume of the heated region

The thermal frequency response:

```
H(f) = 1 / (1 + j * 2 * pi * f * tau)
```

3 dB thermal bandwidth:

```
f_th_3dB = 1 / (2 * pi * tau)
```

Typical values: `tau ~ 1-10 us`, giving `f_th_3dB ~ 15-150 kHz`.

For suspended/undercut structures: `tau ~ 50-200 us`, `f_th_3dB ~ 1-3 kHz`.

### 6.3 Published Parameters for SOI

| Parameter | Standard SOI | Suspended SOI | Source |
|-----------|-------------|---------------|--------|
| P_pi | 20-40 mW | 1-5 mW | Watts et al., OE 2013; Sun et al. 2010 |
| Heater length | 50-300 um | 50-200 um | Design-dependent |
| Thermal bandwidth | 10-150 kHz | 1-3 kHz | tau-dependent |
| Time constant | 1-10 us | 50-200 us | Structure-dependent |
| Heater material | TiN, NiCr, W | doped Si, TiN | Process-dependent |
| Heater resistance | 100-2000 ohm | 500-5000 ohm | Design-dependent |
| Thermal crosstalk at 50 um | -15 to -25 dB | -10 to -20 dB | Layout-dependent |
| Heater-to-waveguide gap | 1-3 um (vertical) | 0.5-1 um | Cladding thickness |
| Phase/power linearity | ~linear delta_phi vs P | ~linear | R_th constant approx. |
| Max temperature rise | ~100 K (reliability limit) | ~150 K | JEDEC thermal guidelines |

**Key references:**
- Watts, M. R. et al., "Adiabatic thermo-optic Mach-Zehnder switch," *Optics Letters*, vol. 38, no. 5, pp. 733-735, 2013.
- Harris, N. C. et al., "Efficient, compact and low loss thermo-optic phase shifter in silicon," *Optics Express*, vol. 22, no. 9, pp. 10487-10493, 2014.
- Jacques, M. et al., "Optimization of thermo-optic heater designs for silicon photonic micro-ring resonators," *Optics Express*, vol. 27, no. 8, pp. 10456-10471, 2019.
- Cocorullo, G. & Rendina, I., "Thermo-optical modulation at 1.5 um in silicon etalon," *Electronics Letters*, vol. 28, no. 1, pp. 83-85, 1992.

### 6.4 Simulation Model I/O

**Inputs:**
- `heater_length_um`: length of resistive heater
- `heater_resistance_ohm`: electrical resistance of the heater
- `power_mW`: applied electrical power (or voltage/current)
- `R_th_K_per_mW`: thermal resistance (or computed from geometry)
- `C_th_J_per_K`: thermal capacitance (or computed)
- `dn_dT`: thermo-optic coefficient (default 1.86e-4 for Si)
- `lambda_nm`: operating wavelength
- `waveguide_material`: "Si" | "SiN" | "SiO2"
- `crosstalk_neighbors`: list of (distance_um, target_waveguide_id)

**Outputs:**
- `delta_phi_rad`: induced phase shift
- `delta_T_K`: temperature rise at the waveguide
- `P_pi_mW`: power for pi phase shift
- `tau_us`: thermal time constant
- `f_3dB_kHz`: thermal bandwidth
- `crosstalk_rad_per_mW`: phase crosstalk coefficients to neighboring waveguides
- Frequency response `H(f)` for dynamic simulations

---

## 7. Spot-Size Converter (SSC) / Edge Coupler

### 7.1 Physical Basis

The SSC bridges the enormous mode-field diameter (MFD) mismatch between a single-mode optical fiber (MFD ~ 8-10 um at 1550 nm) and a submicron silicon waveguide (MFD ~ 0.3-0.5 um). The most common approach is an **inverse taper**: the silicon waveguide narrows adiabatically to a very small tip width (~60-200 nm), weakening the confinement until the mode expands into the surrounding lower-index cladding (SiO2 or polymer), matching the fiber mode.

### 7.2 Core Equations

#### Mode field diameter of a fiber

For a standard single-mode fiber (SMF-28), the Petermann-II MFD:

```
MFD_fiber = 2 * w_0
```

where `w_0` is the 1/e^2 mode field radius. For SMF-28 at 1550 nm: `w_0 ~ 5.2 um`, `MFD ~ 10.4 um`.

#### Mode field of the inverse taper tip

At the narrow tip of the inverse taper, the mode is delocalized into the cladding. The mode field radius depends on the tip width `w_tip`:

```
w_mode(w_tip) ~ w_clad * exp(-beta * w_tip / w_clad)    [approximate]
```

More precisely, from the waveguide dispersion relation, as `w_tip -> 0`:

```
n_eff(w_tip) -> n_clad
MFD(w_tip) -> large (delocalized mode)
```

The target is `MFD(w_tip) ~ MFD_fiber / 2` to `MFD_fiber`, depending on whether a lensed fiber or cleaved fiber is used.

#### Coupling efficiency (overlap integral)

The coupling efficiency between the fiber mode `E_f` and the waveguide tip mode `E_wg`:

```
eta = |integral(E_f * E_wg^* dA)|^2 / (integral(|E_f|^2 dA) * integral(|E_wg|^2 dA))
```

For two Gaussian modes with 1/e^2 radii `w_1` and `w_2`:

```
eta_overlap = (2 * w_1 * w_2 / (w_1^2 + w_2^2))^2
```

With a lateral offset `delta_x` and angular tilt `theta`:

```
eta(delta_x, theta) = eta_overlap * exp(-2 * delta_x^2 / (w_1^2 + w_2^2))
                      * exp(-(pi * n * (w_1^2 + w_2^2) * theta^2) / (2 * lambda^2))
```

#### Coupling loss

```
CL_dB = -10 * log10(eta_overlap * eta_taper * eta_Fresnel * eta_alignment)
```

where:
- `eta_overlap` = mode overlap integral (see above)
- `eta_taper` = adiabatic taper transmission (typically 0.9-0.99 for well-designed tapers)
- `eta_Fresnel` = Fresnel reflection loss at the facet: `eta_Fresnel = 1 - ((n_clad - 1)/(n_clad + 1))^2 ~ 0.96` for SiO2/air
- `eta_alignment` = alignment tolerance factor (packaging-dependent)

#### Adiabatic taper criterion

For the inverse taper to operate adiabatically (negligible mode conversion to higher-order or radiation modes):

```
dw/dz << w(z) * (n_eff_0(z) - n_eff_1(z)) / lambda
```

where `n_eff_0` and `n_eff_1` are the effective indices of the fundamental and first higher-order modes at local width `w(z)`. This criterion sets the minimum taper length.

Practically, for SOI inverse tapers from 450 nm to 80 nm tip width:

```
L_taper ~ 100-300 um    (for < 0.5 dB taper loss)
```

Shorter tapers are possible with optimized nonlinear taper profiles (e.g., parabolic or exponential shapes).

#### Taper profile optimization

Linear taper: `w(z) = w_tip + (w_wg - w_tip) * z / L_taper`

Parabolic taper: `w(z) = w_tip + (w_wg - w_tip) * (z / L_taper)^2`

Exponential taper: `w(z) = w_tip * exp(ln(w_wg / w_tip) * z / L_taper)`

The parabolic profile is generally superior because the taper rate is slower where the mode is most sensitive (near the tip).

### 7.3 Published Parameters for 220 nm SOI

| Parameter | Value | Source |
|-----------|-------|--------|
| Tip width | 60-200 nm | IMEC iSiPP50G; AIM Photonics |
| Taper length | 100-300 um | Foundry-dependent |
| Coupling loss (to SMF-28) | 1-3 dB | Pu et al., OL 2010; Shoji et al. 2002 |
| Coupling loss (to lensed fiber) | 0.5-2 dB | Smaller MFD mismatch |
| Mode field at tip | 2-5 um (in SiO2 cladding) | Tip width dependent |
| Facet preparation | Dicing + polishing or deep etch | Process-dependent |
| Polarization dependence | 0.1-0.5 dB | Asymmetric cross-section |
| Alignment tolerance (1 dB) | +/- 1-2 um (with polymer overlay) | Packaging spec |
| Return loss | > 30 dB (with angled facet) | 8-degree angle typical |
| Bandwidth (1 dB) | > 100 nm | Broadband by nature |
| Polymer overlay MFD | 3-4 um (SU-8, ~n=1.58) | Reduces fiber mismatch |
| SiO2 cladding MFD at tip | 4-6 um | Standard oxide cladding |

**Key references:**
- Shoji, T. et al., "Low loss mode size converter from 0.3 um square Si wire waveguides to single-mode fibres," *Electronics Letters*, vol. 38, no. 25, pp. 1669-1670, 2002.
- Pu, M. et al., "Ultra-low-loss inverted taper coupler for silicon-on-insulator ridge waveguide," *Optics Communications*, vol. 283, pp. 3678-3682, 2010.
- Almeida, V. R. et al., "Nanotaper for compact mode conversion," *Optics Letters*, vol. 28, no. 15, pp. 1302-1304, 2003.
- Gallagher, D. F. & Felici, T. P., "Eigenmode expansion methods for simulation of optical propagation in photonics," Proc. SPIE 4987, 2003.
- Cheben, P. et al., "Broadband polarization independent nanophotonic coupler for silicon waveguides with ultra-high efficiency," *Optics Express*, vol. 23, pp. 22553, 2015.

### 7.4 Simulation Model I/O

**Inputs:**
- `tip_width_nm`: inverse taper tip width
- `taper_length_um`: length of the taper section
- `waveguide_width_nm`: final (wide) waveguide width
- `taper_profile`: "linear" | "parabolic" | "exponential"
- `fiber_MFD_um`: mode field diameter of the coupling fiber
- `cladding_index`: refractive index of the cladding at the tip
- `coupling_loss_db`: total coupling loss (if using a lumped model)
- `alignment_offset_um`: lateral misalignment (for tolerance analysis)
- `facet_angle_deg`: facet angle for return loss calculation
- `wavelength_nm`: operating wavelength

**Outputs:**
- `coupling_loss_dB`: total fiber-to-waveguide coupling loss
- `eta_overlap`: mode overlap efficiency
- `eta_taper`: taper transmission efficiency
- `return_loss_dB`: Fresnel-limited return loss
- `alignment_sensitivity_dB_per_um`: coupling loss sensitivity to misalignment
- `MFD_at_tip_um`: mode field diameter at the taper tip
- Forward transfer matrix (1x1 complex scalar)

---

## 8. Waveguide Crossing

### 8.1 Physical Basis

Waveguide crossings are essential for routing in complex PICs. A naive crossing (two straight waveguides intersecting at 90 degrees) suffers from diffraction loss and crosstalk as the mode expands in the unguided (perpendicular) direction at the intersection. Advanced designs use mode expansion regions or subwavelength structures to minimize these penalties.

### 8.2 Core Equations

#### Naive crossing loss

For two orthogonal single-mode waveguides crossing without any special design, the insertion loss comes from diffraction of the mode through the intersection region of width `W_cross`:

```
IL_naive ~ -10 * log10(|integral(E_guided(x) * E_diffracted(x) dx)|^2 / integral(|E_guided|^2 dx)^2)
```

For a Gaussian mode of waist `w_0` crossing a gap of width `W_cross`:

```
IL_naive ~ -10 * log10(1 / (1 + (W_cross / z_R)^2))
```

where `z_R = pi * n * w_0^2 / lambda` is the Rayleigh range.

For a 500 nm SOI waveguide (w_0 ~ 0.3 um, n ~ 2.8 at 1550 nm):
- `z_R ~ 1.6 um`
- `W_cross = 0.5 um` (the crossing waveguide width)
- `IL_naive ~ 0.1-0.3 dB`

#### Crosstalk

Crosstalk arises from coupling of the diffracted field into the perpendicular waveguide mode:

```
X = -10 * log10(|integral(E_diffracted(y) * E_perp_mode(y) dy)|^2 / integral(|E_guided|^2 dx)^2)
```

For a naive crossing: `X ~ -15 to -25 dB` per crossing.

#### Multimode expansion crossing

The standard optimized crossing design uses adiabatic tapers to expand the mode into a wider multimode region before the crossing, reducing diffraction. The expanded Gaussian waist `w_exp` increases the Rayleigh range:

```
z_R_exp = pi * n * w_exp^2 / lambda
```

If `w_exp >> W_cross`:

```
IL_MME ~ -10 * log10(1 / (1 + (W_cross / z_R_exp)^2)) ~ very small
```

Typical values with multimode expansion: `IL < 0.02 dB`, `X < -40 dB`.

#### Bloch-mode crossing

Subwavelength grating (SWG) or photonic crystal designs at the intersection create an effectively isotropic medium that minimizes diffraction and crosstalk:

```
IL_Bloch ~ 0.01-0.02 dB per crossing
X_Bloch ~ -40 to -60 dB per crossing
```

The effective index of the SWG region:

```
n_eff_SWG^2 ~ f * n_Si^2 + (1-f) * n_SiO2^2    (for TE, fill factor f)
```

#### Scaling with number of crossings

For `N` independent crossings in series:

```
IL_total = N * IL_single    [dB]
```

Crosstalk accumulates incoherently (power addition):

```
X_total ~ X_single + 10 * log10(N)    [dB, worst case]
```

For coherent accumulation (worst case, all crosstalk in phase):

```
X_total_coherent ~ X_single + 20 * log10(N)    [dB]
```

The practical limit for SOI PICs is typically 10-50 crossings per waveguide path, contributing < 1 dB total loss with optimized designs.

### 8.3 Published Parameters for 220 nm SOI

| Parameter | Naive | Multimode expansion | Bloch/SWG | Source |
|-----------|-------|--------------------:|-----------|--------|
| Insertion loss (per crossing) | 0.1-0.3 dB | 0.01-0.05 dB | 0.01-0.02 dB | Bogaerts et al. 2007; Zhang et al. 2013 |
| Crosstalk (per crossing) | -15 to -25 dB | -35 to -45 dB | -40 to -60 dB | Sanchis et al. 2009; Johnson et al. 2015 |
| Footprint | ~1 um x 1 um | ~10 um x 10 um | ~5 um x 5 um | Design-dependent |
| Bandwidth (1 dB) | > 200 nm | > 100 nm | > 100 nm | Inherently broadband |
| Crossing angle | 90 degrees | 90 degrees | 60-90 degrees | 90 is standard |
| Taper length (each side) | N/A | 5-10 um | 2-5 um | Design-dependent |
| Expanded width | N/A | 1.5-3 um | 1-2 um (SWG region) | Design-dependent |

**Key references:**
- Bogaerts, W. et al., "Low-loss, low-cross-talk crossings for silicon-on-insulator nanophotonic waveguides," *Optics Letters*, vol. 32, no. 19, pp. 2801-2803, 2007.
- Sanchis, P. et al., "Highly efficient crossing structure for silicon-on-insulator waveguides," *Optics Letters*, vol. 34, no. 18, pp. 2760-2762, 2009.
- Zhang, Y. et al., "A CMOS-compatible, low-loss, and low-crosstalk silicon waveguide crossing," *IEEE Photonics Technology Letters*, vol. 25, no. 5, pp. 422-425, 2013.
- Johnson, S. G. et al., "Low-loss asymptotically single-mode propagation in large-core OmniGuide fibers," *Optics Express* (related crossing analysis), various years.
- Ma, Y. et al., "Ultralow loss single layer submicron silicon waveguide crossing for SOI optical interconnect," *Optics Express*, vol. 21, no. 24, pp. 29374-29382, 2013.

### 8.4 Simulation Model I/O

**Inputs:**
- `crossing_type`: "naive" | "multimode_expansion" | "bloch" | "swg"
- `insertion_loss_db`: loss per crossing
- `crosstalk_db`: crosstalk per crossing
- `n_crossings`: number of crossings on this path
- `wavelength_nm`: operating wavelength
- `crossing_angle_deg`: intersection angle (default 90)

**Outputs:**
- Forward transfer matrix (2x2 for a 4-port crossing):

```
S = [[r, t_cross],      # r = reflection, t_cross = crosstalk
     [t_main, r]]        # t_main = main transmission

where:
  t_main = sqrt(eta) * exp(j*phi)
  t_cross = sqrt(eta_cross) * exp(j*phi_cross)
  r ~ 0 (negligible reflection for optimized designs)
```

- `IL_total_dB`: cumulative loss for N crossings
- `X_total_dB`: cumulative crosstalk for N crossings
- Scattering matrix `S` (4x4 for a single crossing: 2 input ports, 2 output ports)

---

## Cross-Cutting Implementation Notes

### Material Constants Reference Table

| Constant | Symbol | Value | Unit |
|----------|--------|-------|------|
| Speed of light | c | 2.998e8 | m/s |
| Planck constant | h | 6.626e-34 | J*s |
| Electron charge | q | 1.602e-19 | C |
| Boltzmann constant | k_B | 1.381e-23 | J/K |
| Permittivity of free space | epsilon_0 | 8.854e-12 | F/m |
| Si refractive index (1550 nm) | n_Si | 3.476 | - |
| SiO2 refractive index (1550 nm) | n_SiO2 | 1.444 | - |
| Si permittivity | epsilon_Si | 11.7 * epsilon_0 | F/m |
| Ge permittivity | epsilon_Ge | 16.0 * epsilon_0 | F/m |
| Si intrinsic carrier conc. | n_i | 1.08e10 | cm^-3 |
| Si thermo-optic coeff. | dn/dT | 1.86e-4 | K^-1 |
| SiO2 thermal conductivity | k_SiO2 | 1.38 | W/(m*K) |
| Si thermal conductivity | k_Si | 148 | W/(m*K) |
| Si electron sat. velocity | v_sat_e | 1.0e7 | cm/s |
| Si hole sat. velocity | v_sat_h | 0.7e7 | cm/s |
| Ge electron sat. velocity | v_sat_e_Ge | 6.0e6 | cm/s |

### Scattering Matrix Convention

All component models should produce S-matrices following the convention used in `library.py`:

- Port ordering: `[in_ports..., out_ports...]` as returned by `component_all_ports()`
- `b = S @ a` where `a[i]` is the incident wave into port `i` and `b[i]` is the outgoing wave from port `i`
- Passivity constraint: `max(eigenvalues(S^H @ S)) <= 1`
- Reciprocity: `S = S^T` for all passive reciprocal components (i.e., everything except isolators)
- Unitarity: `S^H @ S = I` for lossless components

### Integration with Existing Library

The existing `photonstrust/components/pic/library.py` supports:
- 2-port components via `_two_port_scalar_matrix`
- 4-port couplers via `_matrix_coupler`
- Touchstone import via `touchstone_2port` and `touchstone_nport`
- Scattering matrices with optional reflections and return loss

New components should follow the pattern of registering in the `_LIB` dictionary with:
1. A `"ports"` entry (ComponentPorts)
2. A `"matrix_fn"` callable with signature `(params: dict, wavelength_nm: float | None) -> np.ndarray`

For wavelength-dependent components (AWG, ring, MZM), the `wavelength_nm` parameter is mandatory.

### Validation Requirements

Per the project's physics validation gates (see `03_physics_models.md`):
- Monotonicity: loss increases with length/frequency/voltage as physically expected
- Boundedness: all outputs within physical limits (0 <= eta <= 1, etc.)
- Cross-check: each model must match at least one published reference curve
- Determinism: fixed seed + config must reproduce outputs

---

## Summary Table: Component Readiness for Implementation

| Component | Equations Ready | Published Params | Ports | Priority |
|-----------|:-:|:-:|--------|----------|
| MMI Coupler | Yes | Yes | NxM (1x2, 2x2 common) | P1 |
| Y-Branch | Yes | Yes | 1x2 | P1 |
| MZM | Yes | Yes | 2-port (lumped) or 4-port (arms exposed) | P0 (modulator is critical for QKD TX) |
| Ge Photodetector | Yes | Yes | 1-port (electrical output, optical input) | P0 (detector is critical for QKD RX) |
| AWG | Yes | Yes | 1xN or NxM | P1 (WDM-QKD) |
| Thermo-Optic Heater | Yes | Yes | 2-port (optical) + electrical control | P0 (phase tuning essential) |
| SSC / Edge Coupler | Yes | Yes | 2-port | P1 (already has lumped model as `pic.edge_coupler`) |
| Waveguide Crossing | Yes | Yes | 4-port | P1 |

---

## Master Reference List

1. Soldano, L. B. & Pennings, E. C. M., *J. Lightwave Technol.* **13**(4), 615-627, 1995. (MMI theory)
2. Bachmann, M. et al., *Appl. Opt.* **33**, 3905-3911, 1994. (NxN MMI phase relations)
3. Besse, P. A. et al., *J. Lightwave Technol.* **14**(10), 2286-2293, 1996. (Tunable MMI splitting)
4. Soref, R. A. & Bennett, B. R., *IEEE J. Quantum Electron.* **QE-23**(1), 123-129, 1987. (Plasma dispersion)
5. Nedeljkovic, M. et al., *IEEE Photon. J.* **3**(6), 1171-1180, 2011. (Updated Soref-Bennett coefficients)
6. Reed, G. T. et al., *Nature Photonics* **4**, 518-526, 2010. (Si modulator review)
7. Thomson, D. J. et al., *IEEE Photon. Technol. Lett.* **24**(4), 234-236, 2012. (50 Gb/s modulator)
8. Michel, J. et al., *Nature Photonics* **4**, 527-534, 2010. (Ge photodetector review)
9. Vivien, L. et al., *Opt. Express* **20**(2), 1096-1101, 2012. (40 GHz Ge PD)
10. Smit, M. K. & van Dam, C., *IEEE JSTQE* **2**(2), 236-250, 1996. (AWG fundamentals)
11. Okamoto, K., *Fundamentals of Optical Waveguides*, 2nd ed., Academic Press, 2006. (AWG theory)
12. Pathak, S. et al., *IEEE Photon. J.* **6**(5), 2014. (SOI AWG comparison)
13. Cocorullo, G. & Rendina, I., *Electron. Lett.* **28**(1), 83-85, 1992. (Si thermo-optic coefficient)
14. Harris, N. C. et al., *Opt. Express* **22**(9), 10487-10493, 2014. (Efficient thermo-optic phase shifter)
15. Shoji, T. et al., *Electron. Lett.* **38**(25), 1669-1670, 2002. (Inverse taper coupler)
16. Almeida, V. R. et al., *Opt. Lett.* **28**(15), 1302-1304, 2003. (Nanotaper)
17. Bogaerts, W. et al., *Opt. Lett.* **32**(19), 2801-2803, 2007. (Waveguide crossing)
18. Sanchis, P. et al., *Opt. Lett.* **34**(18), 2760-2762, 2009. (Efficient SOI crossing)
19. Zhang, Y. et al., *Opt. Express* **21**(1), 1310-1316, 2013. (Compact Y-junction)
20. Xu, Q. et al., *Nature* **435**, 325-327, 2005. (Si electro-optic modulator)
21. Halir, R. et al., *Opt. Express* **20**, 13470, 2012. (Subwavelength coupler)
22. Dong, P. et al., *Opt. Express* **17**(25), 22484-22490, 2009. (Compact Si modulator)
23. Assefa, S. et al., *Nature* **464**, 80-84, 2010. (Ge APD)
24. Jacques, M. et al., *Opt. Express* **27**(8), 10456-10471, 2019. (Heater optimization)
25. Ma, Y. et al., *Opt. Express* **21**(24), 29374-29382, 2013. (Ultralow loss crossing)
