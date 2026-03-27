# Foundry PDK Specifications Research Report

Date: 2026-03-25

## Purpose

This document compiles published specifications, design rules, layer stacks, and
component parameters for six major silicon photonics (and silicon nitride)
foundry PDKs. All data herein is drawn from peer-reviewed publications,
open-source PDK repositories, published datasheets, conference proceedings,
and textbooks. No NDA-restricted data is included.

The goal is to provide a reference for building simulation models and populating
PhotonTrust PDK manifest files (`configs/pdks/*.pdk.json`) with
redistribution-safe, traceable numbers.

---

## 1. SiEPIC EBeam PDK (University of British Columbia)

### 1.1 Platform Specs

| Parameter | Value |
|---|---|
| Wafer size | 100 mm (4 inch) SOI wafers |
| Lithography | Electron-beam (e-beam) direct write, 100 keV |
| Core material | Crystalline silicon (c-Si) |
| Core thickness | 220 nm |
| BOX (buried oxide) | 2 um SiO2 |
| Cladding | Air (unclad) or SiO2 (oxide-clad), depending on process option |
| Operating wavelength | 1550 nm (C-band), 1310 nm (O-band) supported |
| Fabrication site | UBC nanofabrication facility; also CMC Microsystems shuttle service |

### 1.2 Design Rules

| Rule | Value | Source |
|---|---|---|
| Min strip waveguide width | 500 nm (nominal); functional down to ~400 nm | SiEPIC PDK docs; Chrostowski & Hochberg (2015) Ch. 5 |
| Min rib waveguide width | 500 nm (90 nm slab etch) | SiEPIC PDK GitHub |
| Min waveguide gap (coupling) | 200 nm | SiEPIC DRC rules |
| Min bend radius (strip, TE) | 5 um (loss < 0.01 dB/90-deg bend) | Chrostowski & Hochberg (2015) Table 5.1 |
| Min bend radius (rib) | 25 um | SiEPIC PDK documentation |
| Min feature size (e-beam) | ~60 nm (lithography limit, not design rule) | UBC e-beam process notes |
| Grid snapping | 1 nm (GDS database unit) | SiEPIC KLayout technology file |

### 1.3 Layer Stack

| Layer Name | GDS Layer/Datatype | Material | Thickness | Notes |
|---|---|---|---|---|
| Si (waveguide core) | 1/0 | c-Si | 220 nm | Full etch for strip WG |
| Si slab (rib) | 2/0 | c-Si | 90 nm slab remain | Partial etch for rib WG |
| SiO2 BOX | N/A (substrate) | SiO2 | 2 um | Buried oxide |
| SiO2 Cladding | 3/0 | SiO2 | ~1 um (when clad) | Optional oxide cladding |
| Metal heater | 11/0 or 31/0 | Ti/TiN or NiCr | ~120-150 nm | Thermal tuning layer |
| Si N-doped | 20/0 | n-type Si | 220 nm | For PN junction experiments |
| Si P-doped | 21/0 | p-type Si | 220 nm | For PN junction experiments |
| FloorPlan | 99/0 | -- | -- | Design boundary |
| Text/Labels | 10/0 | -- | -- | Component identification |
| DevRec | 68/0 | -- | -- | Device recognition layer |
| PinRec | 1/10 | -- | -- | Optical pin recognition |
| Devrec | 68/0 | -- | -- | Used by SiEPIC-Tools |

*Note:* GDS layer numbers are from the open-source SiEPIC-EBeam KLayout
technology file. Numbers vary between process runs. The above reflects the
publicly documented mapping as of the v0.5.x SiEPIC-Tools release.

### 1.4 Component Cells and Published Performance

#### 1.4.1 Grating Coupler (TE, 1550 nm)

| Parameter | Value | Source |
|---|---|---|
| Insertion loss (peak) | 3.0-5.5 dB (fiber-to-chip, single coupler) | Chrostowski & Hochberg (2015); Y. Wang et al., Opt. Express 22, 20652 (2014) |
| 1 dB bandwidth | ~30-35 nm | SiEPIC characterization data |
| 3 dB bandwidth | ~50-60 nm | Typical published values |
| Center wavelength | 1550 nm (tunable by period) | Design dependent |
| Fiber angle | 10-15 deg from vertical | Design dependent |
| Peak coupling efficiency | -3.0 dB (best demonstrated with apodization) | Wang et al. (2014) |
| Polarization | TE | -- |
| Cell name (SiEPIC) | `ebeam_gc_te1550` | SiEPIC-EBeam PDK |

#### 1.4.2 Grating Coupler (TM, 1550 nm)

| Parameter | Value | Source |
|---|---|---|
| Insertion loss (peak) | 5.0-7.0 dB | SiEPIC characterization |
| 1 dB bandwidth | ~35 nm | Typically broader than TE |
| Cell name | `ebeam_gc_tm1550` | SiEPIC-EBeam PDK |

#### 1.4.3 Strip Waveguide (TE)

| Parameter | Value | Source |
|---|---|---|
| Cross section | 500 nm x 220 nm | Standard SOI strip |
| Propagation loss (TE, 1550 nm) | 2-4 dB/cm (e-beam; sidewall roughness limited) | Chrostowski & Hochberg (2015) Ch. 5 |
| Effective index (TE0, 1550 nm) | ~2.44 | Simulation; Chrostowski textbook |
| Group index (TE0, 1550 nm) | ~4.18 | Simulation; measured values |
| Bend loss (5 um radius, 90 deg) | < 0.01 dB | Chrostowski & Hochberg Table 5.1 |

#### 1.4.4 Rib Waveguide

| Parameter | Value | Source |
|---|---|---|
| Cross section | 500 nm width, 220 nm ridge, 90 nm slab | SiEPIC PDK |
| Propagation loss | ~0.5-1.5 dB/cm | Lower than strip due to reduced sidewall interaction |
| Min bend radius | 25 um | SiEPIC design rules |

#### 1.4.5 Directional Coupler

| Parameter | Value | Source |
|---|---|---|
| Gap | 200 nm (nominal) | SiEPIC PDK |
| Coupling length for 3 dB | ~10-15 um (gap and wavelength dependent) | Simulation and measurement |
| Excess loss | < 0.1 dB | Chrostowski & Hochberg (2015) |
| Wavelength sensitivity | ~1-3%/nm coupling ratio change | Measured SiEPIC data |
| Cell name | `ebeam_dc_halfring_straight` | SiEPIC-EBeam PDK |

#### 1.4.6 Y-Branch (1x2 Splitter)

| Parameter | Value | Source |
|---|---|---|
| Splitting ratio | 50/50 nominal | Standard design |
| Excess loss | 0.2-0.5 dB | Published SiEPIC measurements |
| Bandwidth | > 100 nm (broadband) | Chrostowski & Hochberg (2015) |
| Cell name | `ebeam_y_1550` | SiEPIC-EBeam PDK |

#### 1.4.7 Ring Resonator

| Parameter | Value | Source |
|---|---|---|
| Radius | 5-30 um (typical designs) | SiEPIC PDK |
| FSR (R=5 um) | ~18.5 nm at 1550 nm | Calculated from n_g |
| Q factor (all-pass, R=5 um) | 10,000-50,000 (fabrication dependent) | SiEPIC measurements |
| Propagation loss in ring | 2-4 dB/cm | Same as strip waveguide |
| Thermal tuning sensitivity | ~0.08 nm/K (resonance shift) | Chrostowski & Hochberg (2015) |
| Cell name | `ebeam_dc_halfring_straight` (ring component) | SiEPIC-EBeam PDK |

#### 1.4.8 Mach-Zehnder Interferometer

| Parameter | Value | Source |
|---|---|---|
| Arm length imbalance | Design dependent (0-500 um) | SiEPIC test structures |
| Extinction ratio | 15-30 dB (dependent on coupler balance) | Measurement data |
| Insertion loss | 0.5-1.5 dB (total, two Y-branches or DCs) | SiEPIC published results |

### 1.5 Key References

1. Chrostowski, L. & Hochberg, M., *Silicon Photonics Design: From Devices to Systems*, Cambridge University Press (2015). ISBN: 978-1-107-08545-9
2. Y. Wang et al., "Design of broadband sub-wavelength grating couplers with low back reflection," Opt. Lett. 40, 4647 (2015).
3. SiEPIC-EBeam PDK GitHub: https://github.com/siepic/SiEPIC_EBeam_PDK
4. SiEPIC-Tools KLayout package: https://github.com/siepic/SiEPIC-Tools
5. SiEPIC program: https://siepic.ubc.ca/
6. CMC Microsystems fabrication service: https://www.cmc.ca/

### 1.6 Public vs NDA Boundary

| Category | Status |
|---|---|
| Layer stack (Si thickness, BOX, clad) | Public domain -- published in textbook and PDK |
| GDS layer/datatype numbers | Public -- in open-source KLayout technology file |
| Design rules (min width, gap, bend) | Public -- in open-source DRC deck |
| Component S-parameters (measured) | Partially public -- some published in papers; full measured sets may require SiEPIC account |
| PCell source code | Public -- open-source (MIT license) |
| Process corner data | Not public -- requires fabrication run data |

---

## 2. AIM Photonics (SUNY Polytechnic, Albany NY)

### 2.1 Platform Specs

| Parameter | Value |
|---|---|
| Wafer size | 300 mm (12 inch) |
| Lithography | 193 nm DUV (deep UV) immersion lithography |
| Core material | Crystalline silicon |
| Core thickness | 220 nm (silicon layer) |
| BOX (buried oxide) | 2 um SiO2 |
| Cladding | SiO2 (PECVD oxide, ~2-3 um) |
| Additional waveguide layer | SiN (silicon nitride), 150-200 nm, above Si layer |
| Metal layers | 2 metal levels (Al or Cu, per process variant) |
| Ge layer | Epitaxial germanium for photodetectors |
| Doping | N/P implants for PN junction modulators |
| Operating wavelength | C-band (1530-1565 nm) primary; O-band options |
| Fabrication site | SUNY Polytechnic Institute, Albany NY |
| Access model | Multi-project wafer (MPW) runs via AIM Photonics |

### 2.2 Design Rules

| Rule | Value | Source |
|---|---|---|
| Min strip WG width (Si) | 400-500 nm | AIM PDK v3.x published guidelines |
| Min rib WG width (Si) | 500 nm | AIM design manual |
| Min waveguide gap | 200-250 nm | AIM DRC deck |
| Min bend radius (strip, TE) | 5-10 um | AIM PDK; design dependent on WG type |
| Min metal width (M1) | ~0.5 um | AIM metal rules |
| Min metal spacing | ~0.5 um | AIM metal rules |
| SiN waveguide width | 800-1200 nm | AIM SiN layer design rules |
| Min SiN bend radius | 50-100 um | AIM PDK documentation |

### 2.3 Layer Stack (Published Cross-Section)

| Layer Name | Material | Thickness | Notes |
|---|---|---|---|
| Si substrate | c-Si | 725 um | Carrier wafer |
| BOX | SiO2 | 2 um | Buried oxide |
| Si waveguide | c-Si | 220 nm | Full etch (strip) or partial etch (rib, 90 nm slab) |
| SiN waveguide | Si3N4 | 150-200 nm | Above Si layer, separated by oxide spacer |
| Oxide spacer (Si to SiN) | SiO2 | ~100-200 nm | Interlayer dielectric |
| Ge PD layer | Ge | ~500 nm | Epitaxial Ge for photodetectors |
| Oxide ILD | SiO2 | ~1.5-2 um | Interlayer dielectric |
| Metal 1 (M1) | Al/Cu | ~0.5-1 um | Lower metal |
| Via 1 | W | -- | Metal 1 to Metal 2 connection |
| Metal 2 (M2) | Al/Cu | ~1-2 um | Upper metal / bond pads |
| Passivation | SiN/SiO2 | ~0.5 um | Top passivation |

*Note:* Exact GDS layer/datatype numbers for AIM are distributed under
the AIM PDK license and are generally not redistributable. The above
layer names and thicknesses are compiled from published papers and AIM
Photonics public presentations.

### 2.4 Component Cells and Published Performance

#### 2.4.1 Grating Coupler (TE, 1550 nm)

| Parameter | Value | Source |
|---|---|---|
| Insertion loss | 2.5-3.5 dB (fiber-to-chip) | AIM shuttle results; Orcutt et al. |
| 1 dB bandwidth | 30-40 nm | AIM published data |
| Fiber angle | ~10 deg | Standard configuration |

#### 2.4.2 Edge Coupler / Spot Size Converter

| Parameter | Value | Source |
|---|---|---|
| Insertion loss | 0.7-1.5 dB (per facet) | AIM published data |
| Bandwidth | > 100 nm (broadband) | Inherent advantage of edge coupling |
| Mode field match | Optimized for lensed fiber or fiber array | AIM SSC designs |

#### 2.4.3 Strip Waveguide (Si, TE)

| Parameter | Value | Source |
|---|---|---|
| Cross section | 500 nm x 220 nm | AIM standard |
| Propagation loss | 1.5-2.5 dB/cm | AIM shuttle measurements; DUV litho gives lower roughness than e-beam |
| n_eff (TE0, 1550 nm) | ~2.44 | Standard SOI value |

#### 2.4.4 SiN Waveguide

| Parameter | Value | Source |
|---|---|---|
| Cross section | 1000 nm x 200 nm (typical) | AIM SiN layer |
| Propagation loss | 0.5-1.0 dB/cm | AIM published specs |
| n_eff (TE0, 1550 nm) | ~1.7-1.8 | Depends on exact geometry and SiN stoichiometry |
| Application | Low-loss routing, WDM filters | Avoids TPA at moderate powers |

#### 2.4.5 PN Junction Modulator (Mach-Zehnder)

| Parameter | Value | Source |
|---|---|---|
| Modulation efficiency (V_pi * L) | ~2.0-2.5 V*cm | AIM published results |
| Bandwidth (electro-optic, 3 dB) | > 25 GHz | AIM 50G platform |
| Insertion loss (passive) | 3-6 dB (depending on arm length) | AIM data |
| Extinction ratio | 20-30 dB | Design and bias dependent |
| Data rate | 50 Gbps NRZ demonstrated | AIM publications |

#### 2.4.6 Ge Photodetector

| Parameter | Value | Source |
|---|---|---|
| Responsivity | 0.8-1.1 A/W at 1550 nm | AIM published specs |
| Dark current | < 10 nA (at -1V bias) | AIM characterization |
| 3 dB bandwidth | > 30 GHz | AIM 50G platform |
| Ge absorption length | 20-40 um | Design dependent |

#### 2.4.7 Thermal Phase Shifter

| Parameter | Value | Source |
|---|---|---|
| Heater efficiency | ~20-30 mW/pi phase shift | AIM published data |
| Response time | ~10-50 us | Thermal time constant |
| Insertion loss | < 0.3 dB | AIM data |
| Heater material | TiN or doped Si | Process dependent |

#### 2.4.8 MMI 2x2 Coupler

| Parameter | Value | Source |
|---|---|---|
| Excess loss | 0.2-0.5 dB | AIM published data |
| Imbalance | < 0.3 dB | AIM characterization |
| Bandwidth | > 60 nm | Broadband design |

### 2.5 Key References

1. AIM Photonics: https://www.aimphotonics.com/
2. Orcutt, J. et al., "Open foundry platform for high-performance electronic-photonic integration," Opt. Express 20, 12222-12232 (2012).
3. AIM Photonics PDK documentation (available via AIM Photonics Academy): https://www.aimphotonics.academy/
4. Timurdogan, E. et al., "An ultralow power athermal silicon modulator," Nature Communications 5, 4008 (2014).
5. AIM Photonics Institute publications: various IEEE and OSA conference papers from SUNY Poly.

### 2.6 Public vs NDA Boundary

| Category | Status |
|---|---|
| Platform overview (materials, thicknesses) | Public -- published in papers and presentations |
| Exact GDS layer numbers | Requires AIM PDK license (generally not redistributable) |
| Full DRC/LVS rule decks | Requires AIM PDK license |
| Component performance ranges | Public -- published in papers and shuttle reports |
| Compact models (S-parameters, SPICE) | Requires AIM PDK license |
| Process corner data | Proprietary -- requires NDA or shuttle participation |

---

## 3. IMEC iSiPP50G

### 3.1 Platform Specs

| Parameter | Value |
|---|---|
| Wafer size | 200 mm transitioning to 300 mm |
| Lithography | 193 nm DUV |
| Core material | Crystalline silicon |
| Core thickness | 220 nm |
| BOX thickness | 2 um SiO2 |
| Cladding | SiO2 |
| Platform name | iSiPP50G (integrated Silicon Photonics Platform, 50 Gbps) |
| Metal levels | 2 (M1 + M2) |
| Ge integration | Selective epitaxial Ge for photodetectors |
| Doping levels | Multiple N/P implant levels for modulators |
| Operating wavelength | C-band (1530-1565 nm) primary |
| Access | MPW via Europractice (IMEC) and CMC Microsystems |

### 3.2 Design Rules

| Rule | Value | Source |
|---|---|---|
| Min strip WG width | 400 nm | Absil et al., IEDM 2015; iSiPP50G design manual |
| Min rib WG width | 450 nm (130 nm slab) | IMEC design rules |
| Min WG gap | 200 nm | IMEC published DRC |
| Min bend radius (strip) | 5 um | Absil et al. |
| Min bend radius (rib) | 25 um | IMEC design rules |
| Min metal width (M1) | 0.5 um | IMEC metal rules |
| Min metal spacing | 0.5 um | IMEC metal rules |
| Si etch depth (full) | 220 nm | Full etch to BOX |
| Si etch depth (partial) | 70-90 nm (leaving 130-150 nm slab) | Rib waveguide partial etch |

### 3.3 Layer Stack

| Layer Name | Material | Thickness | Notes |
|---|---|---|---|
| Si substrate | c-Si | 725 um | Carrier wafer |
| BOX | SiO2 | 2 um | Buried oxide |
| Si waveguide (full etch) | c-Si | 220 nm | Strip waveguides |
| Si waveguide (partial etch) | c-Si | 220 nm (130 nm slab + 90 nm ridge) | Rib waveguides |
| Shallow etch | c-Si | 70 nm etch depth | Grating couplers, fiber couplers |
| Ge photodetector | Ge | ~300-500 nm | Selective epitaxy |
| Oxide ILD | SiO2 | ~1.5 um | Between Si and M1 |
| Metal 1 (M1) | Al | ~0.5 um | Lower routing / heaters |
| Via 1 | W | -- | M1-M2 |
| Metal 2 (M2) | Al | ~2 um | Bond pads, upper routing |
| Passivation | SiN/SiO2 | ~0.5 um | Top layer |

*Note:* Exact GDS layer assignments are part of the iSiPP50G PDK and are
not redistributable. The structural data above comes from published papers.

### 3.4 Component Cells and Published Performance

#### 3.4.1 Grating Coupler (TE)

| Parameter | Value | Source |
|---|---|---|
| Insertion loss | 2.0-3.5 dB | Absil et al., IEDM 2015; Europractice specs |
| 1 dB bandwidth | 30-40 nm | IMEC publications |
| Fiber angle | 10 deg from vertical | Standard |

#### 3.4.2 Strip Waveguide

| Parameter | Value | Source |
|---|---|---|
| Cross section | 450 nm x 220 nm (single mode) | IMEC standard |
| Propagation loss | 1.0-2.0 dB/cm | Absil et al.; depends on etch quality |
| DUV roughness advantage | Lower sidewall roughness than e-beam | Manufacturing advantage |

#### 3.4.3 PN Junction MZM (Carrier Depletion)

| Parameter | Value | Source |
|---|---|---|
| Modulation efficiency (V_pi * L) | 1.5-2.5 V*cm | Absil et al.; Pantouvaki et al. |
| EO bandwidth (3 dB) | > 30 GHz (with TW electrode design) | IMEC iSiPP50G publications |
| Data rate demonstrated | 50 Gbps NRZ, 100 Gbps PAM-4 | Pantouvaki et al., OFC papers |
| ER | > 5 dB (dynamic) | At 50 Gbps |
| On-chip loss | 4-8 dB (depending on modulator length and design) | IMEC published |
| Junction type | Lateral PN or interleaved PN | Design variants available |

#### 3.4.4 Ge Waveguide Photodetector

| Parameter | Value | Source |
|---|---|---|
| Responsivity | 0.9-1.1 A/W at 1550 nm | Absil et al. |
| Dark current | 1-10 nA (at -1V) | IMEC published data |
| 3 dB bandwidth | > 40 GHz | IMEC iSiPP50G |
| Active Ge length | 10-30 um | Design dependent |
| Bias voltage | -1 to -2 V | Standard operation |

#### 3.4.5 Thermal Phase Shifter

| Parameter | Value | Source |
|---|---|---|
| Efficiency | 15-25 mW/pi | IMEC data |
| Response time | ~10 us | Thermal limited |
| Insertion loss | < 0.2 dB | IMEC published |

#### 3.4.6 Ring Modulator

| Parameter | Value | Source |
|---|---|---|
| FSR | ~8-12 nm (radius dependent) | Standard Si ring |
| Q (loaded) | 5,000-15,000 | Design dependent |
| Modulation speed | > 25 Gbps | IMEC demonstrations |
| Tuning range | ~2 nm (PN depletion) + thermal | Combined EO + thermal |

### 3.5 Key References

1. Absil, P.P. et al., "Reliable 50Gb/s Silicon Photonics Platform for Next-Generation Data Center Optical Interconnects," IEEE IEDM 2015, pp. 34.2.1-34.2.4.
2. Pantouvaki, M. et al., "50Gb/s Silicon Photonics Platform for Short-Reach Optical Interconnects," OFC 2016.
3. Europractice IC service / IMEC SiPhotonics MPW: https://europractice-ic.com/technologies/photonics/imec/
4. Bogaerts, W. et al., "Silicon microring resonators," Laser Photonics Rev. 6, 47-73 (2012).
5. Srinivasan, S.A. et al., "56 Gb/s Germanium Waveguide Electro-Absorption Modulator," JLT 34, 419-424 (2016).

### 3.6 Public vs NDA Boundary

| Category | Status |
|---|---|
| Layer stack (materials, thicknesses) | Public -- published in IEDM and OFC papers |
| GDS layer numbers | Requires Europractice/IMEC PDK license |
| DRC rules (full deck) | Requires PDK license |
| Component performance ranges | Public -- extensively published |
| Compact models | Requires PDK license |
| Process corner statistics | Proprietary (NDA with IMEC) |

---

## 4. GlobalFoundries 45CLO (45SPCLO)

### 4.1 Platform Specs

| Parameter | Value |
|---|---|
| Wafer size | 300 mm (12 inch) |
| CMOS node | 45 nm SOI CMOS |
| Integration approach | Monolithic (photonics in CMOS BEOL/FEOL) |
| Core material | Crystalline silicon (from SOI CMOS) |
| Core thickness | ~300 nm (GF 45nm SOI body thickness, thinned to ~220 nm for photonic waveguides in some designs) |
| BOX | ~140 nm (standard 45SOI) -- this is thinner than typical photonics BOX |
| Platform name | GF 45CLO (45nm CMOS with Low-loss Optics) or 45SPCLO |
| Metal levels | CMOS BEOL (~10+ metal levels), subset used for photonics routing |
| Ge integration | Available for photodetectors (GF process) |
| Operating wavelength | O-band (1310 nm) primary; C-band available |
| Access | GF Fotonix shuttle (limited access, contact GF) |
| Key differentiator | Monolithic CMOS + photonics on same die |

### 4.2 Design Rules

| Rule | Value | Source |
|---|---|---|
| Min waveguide width | ~300-500 nm | Rakowski et al., OFC 2020; varies with WG type |
| Min waveguide gap | ~200 nm | GF published specs |
| Min bend radius | 5-10 um | GF publications |
| SOI body thickness for photonics | ~220 nm (thinned) or ~300 nm | Process variant |
| CMOS gate length | 45 nm | Standard GF 45SOI node |

*Note:* The 45CLO/45SPCLO design rules are more restrictive than standalone
photonics platforms due to CMOS compatibility constraints. Many rules inherit
from the 45nm CMOS DRC deck.

### 4.3 Layer Stack (Simplified Photonic Cross-Section)

| Layer | Material | Thickness | Notes |
|---|---|---|---|
| Si substrate | c-Si | bulk | Handle wafer |
| BOX | SiO2 | ~140 nm (45SOI) | Thinner than typical photonics -- substrate leakage concern at C-band |
| Si body (waveguide) | c-Si | ~300 nm (or ~220 nm thinned) | SOI body layer repurposed for photonic waveguides |
| Gate oxide | SiO2/HfO2 | ~1-2 nm | CMOS gate (not used for photonics directly) |
| Poly-Si | poly-Si | ~80-100 nm | CMOS gates; can be used for grating structures |
| SiN (BEOL) | Si3N4 | ~150-200 nm | Available SiN waveguide layer in BEOL |
| BEOL metals (M1-M10+) | Cu | various | CMOS interconnect stack |
| Ge | Ge | ~200-300 nm | Photodetector layer |

*Note:* The thin BOX (~140 nm) is a known limitation for C-band operation.
The platform primarily targets O-band (1310 nm) where substrate leakage is
less severe, though C-band operation is possible with careful design.

### 4.4 Component Performance (Published)

#### 4.4.1 Waveguide

| Parameter | Value | Source |
|---|---|---|
| Propagation loss (O-band, 1310 nm) | 0.7-1.5 dB/cm | Rakowski et al., OFC 2020 |
| Propagation loss (C-band, 1550 nm) | 1.5-3.0 dB/cm (higher due to thin BOX leakage) | GF publications |
| n_eff | ~2.5-2.7 (depends on WG geometry) | 45SOI process |

#### 4.4.2 Modulator (MZM)

| Parameter | Value | Source |
|---|---|---|
| Modulation efficiency | ~2.0 V*cm | Rakowski et al. |
| EO bandwidth | > 30 GHz | GF 45CLO demonstrations |
| Data rate | 50-90 Gbps demonstrated | GF publications; Rahim et al. |
| Advantage | Co-integrated driver electronics | Monolithic CMOS+photonics |

#### 4.4.3 Ge Photodetector

| Parameter | Value | Source |
|---|---|---|
| Responsivity | 0.8-1.0 A/W at 1310 nm | GF published data |
| Bandwidth | > 30 GHz | GF 45CLO data |
| Dark current | < 50 nA | GF published |

#### 4.4.4 Grating Coupler

| Parameter | Value | Source |
|---|---|---|
| IL (O-band) | 2.5-4.0 dB | GF published specs |
| Bandwidth | 30-40 nm | Standard performance |

#### 4.4.5 Thermal Phase Shifter

| Parameter | Value | Source |
|---|---|---|
| Efficiency | 20-30 mW/pi | BEOL heater design |
| Material | CMOS metal (Cu) or BEOL resistor | Process dependent |

### 4.5 Key References

1. Rakowski, M. et al., "45nm CMOS - Silicon Photonics Monolithic Technology (45CLO) for next-generation, low power and high speed optical interconnects," OFC 2020, paper T3H.3.
2. Rahim, A. et al., "Open-Access Silicon Photonics Platforms in Europe," IEEE J. Sel. Topics Quantum Electron. 25, 8200818 (2019).
3. Stojanovic, V. et al., "Monolithic silicon-photonic platforms in state-of-the-art CMOS SOI processes," Opt. Express 26, 13106 (2018).
4. Sun, C. et al., "Single-chip microprocessor that communicates directly using light," Nature 528, 534-538 (2015). -- Related MIT/GF collaboration.
5. GlobalFoundries Fotonix platform: https://gf.com/technology-solutions/silicon-photonics/

### 4.6 Public vs NDA Boundary

| Category | Status |
|---|---|
| Platform overview, SOI thickness, BOX | Public -- published in OFC/Nature papers |
| Exact GDS layers and CMOS-photonics integration rules | Proprietary (requires GF NDA and 45CLO PDK license) |
| DRC/LVS deck | Proprietary |
| CMOS transistor models (SPICE) | Requires GF CMOS PDK license |
| Photonic component performance (ranges) | Public -- published in papers |
| Process corner / yield data | Proprietary |

---

## 5. Ligentec AN800 (Silicon Nitride, 800 nm)

### 5.1 Platform Specs

| Parameter | Value |
|---|---|
| Wafer size | 200 mm (8 inch) |
| Lithography | DUV (248 nm or 193 nm) stepper |
| Core material | Si3N4 (LPCVD stoichiometric silicon nitride) |
| Core thickness | 800 nm |
| Bottom cladding | SiO2 (thermal oxide), > 4 um |
| Top cladding | SiO2 (PECVD or LPCVD), > 4 um |
| Total cladding (top + bottom) | > 8 um |
| Platform name | AN800 (All-Nitride, 800 nm) |
| Refractive index (Si3N4, 1550 nm) | ~2.0 |
| Refractive index (SiO2, 1550 nm) | ~1.44 |
| Operating wavelength | 405 nm to 2350 nm (full visible to mid-IR) |
| Key advantages | Ultra-low loss, no TPA, high power handling, no free carriers |
| Fabrication site | Ligentec SA, Switzerland (EPFL spinoff) |
| Access | MPW service via Ligentec |

### 5.2 Design Rules

| Rule | Value | Source |
|---|---|---|
| Min waveguide width | ~500 nm (single mode guidance dependent on thickness and wavelength) | Pfeiffer et al.; Ligentec design guide |
| Single mode width range (1550 nm, 800 nm thick) | ~700-1500 nm (strongly confined TE/TM modes exist above ~600 nm) | Pfeiffer et al. |
| Min waveguide gap | ~300-500 nm | Ligentec published rules |
| Min bend radius (low loss) | 50-100 um (for < 0.01 dB/bend) | Pfeiffer et al. |
| Min bend radius (compact) | 20-30 um (moderate excess loss, ~0.01-0.05 dB/bend) | Ligentec data |
| Min feature size (DUV) | ~200 nm | Lithography limited |
| Cladding clearance | > 4 um top and bottom | Required for low substrate leakage |

### 5.3 Layer Stack

| Layer Name | Material | Thickness | Notes |
|---|---|---|---|
| Si substrate | c-Si | 725 um | Carrier wafer |
| Bottom cladding | SiO2 (thermal) | > 4 um (typically 4-6 um) | Thermal oxide or PECVD |
| Si3N4 waveguide core | Si3N4 (LPCVD) | 800 nm | Stoichiometric; deposited crack-free via Damascene or photonic Damascene process |
| Top cladding | SiO2 (LPCVD/PECVD) | > 4 um | Planarized |
| Metal heater (optional) | TiN or Pt | ~100-200 nm | For thermal tuning, above top cladding |

*Note:* Ligentec's key innovation is the "photonic Damascene" process that
enables crack-free deposition of thick (> 400 nm) Si3N4 films. This is
described in Pfeiffer et al., Optica 4, 684 (2017).

### 5.4 Component Performance (Published)

#### 5.4.1 Waveguide

| Parameter | Value | Source |
|---|---|---|
| Propagation loss (1550 nm, 800 nm thick core) | < 0.1 dB/cm (demonstrated ~0.03 dB/cm for wide WG) | Pfeiffer et al., Optica (2017); Ji et al., Optica (2017) |
| Propagation loss (1550 nm, standard widths) | 0.05-0.1 dB/cm | Ligentec published specs |
| Propagation loss (visible, 800 nm core) | 0.1-1.0 dB/cm (wavelength dependent) | Ligentec data for visible applications |
| n_eff (1550 nm, 1500 nm x 800 nm WG) | ~1.72-1.80 | Simulation / published |
| Group index | ~2.0-2.1 | Published |
| Power handling | > 1 W in-waveguide (no TPA in Si3N4) | Key advantage over Si platforms |
| Nonlinear index (n2) | ~2.4 x 10^-19 m^2/W | Intrinsic Si3N4 property |

#### 5.4.2 Ring Resonator

| Parameter | Value | Source |
|---|---|---|
| Intrinsic Q factor | > 10 million (demonstrated up to 37 million) | Pfeiffer et al. (2017); Ji et al. (2017) |
| Loaded Q | 1-10 million (coupling dependent) | Published data |
| FSR (R = 100 um) | ~2.3 nm at 1550 nm | Calculated from n_g |
| Application | Kerr frequency comb generation, filters, sensors | Key application area |
| Anomalous dispersion | Engineered via 800 nm thickness + width control | Enables soliton microcombs |

#### 5.4.3 Directional Coupler

| Parameter | Value | Source |
|---|---|---|
| Excess loss | < 0.05 dB | Ligentec published |
| Coupling length (50/50) | ~50-200 um (gap and width dependent) | Longer than Si due to lower index contrast |

#### 5.4.4 Edge Coupler / Spot Size Converter

| Parameter | Value | Source |
|---|---|---|
| IL (to SMF-28) | 0.5-1.5 dB per facet | Ligentec data |
| IL (to lensed fiber) | 0.3-0.8 dB per facet | Ligentec published |
| Mode size at facet | ~3-5 um (with inverse taper) | SSC design dependent |

#### 5.4.5 Thermal Phase Shifter

| Parameter | Value | Source |
|---|---|---|
| Efficiency | 30-50 mW/pi (less efficient than Si due to thicker cladding) | Ligentec data |
| Response time | ~50-100 us (thick cladding slows thermal response) | Published |
| Thermo-optic coefficient (Si3N4) | ~2.5 x 10^-5 /K | Intrinsic property (about 10x smaller than Si) |

### 5.5 Key References

1. Pfeiffer, M.H.P. et al., "Photonic Damascene process for integrated high-Q microresonator based nonlinear photonics," Optica 4, 684-691 (2017).
2. Ji, X. et al., "Ultra-low-loss on-chip resonators with sub-milliwatt parametric oscillation threshold," Optica 4, 619 (2017).
3. Kippenberg, T.J. et al., "Dissipative Kerr solitons in optical microresonators," Science 361, eaan8083 (2018).
4. Ligentec SA: https://www.ligentec.com/
5. Ligentec AN800 platform page: https://www.ligentec.com/technology/an-800/
6. Liu, J. et al., "High-yield, wafer-scale fabrication of ultralow-loss, dispersion-engineered silicon nitride photonic circuits," Nature Communications 12, 2236 (2021).

### 5.6 Public vs NDA Boundary

| Category | Status |
|---|---|
| Layer stack (Si3N4 thickness, cladding) | Public -- published in Optica/Nature papers |
| Loss specifications | Public -- widely published |
| Q factor achievements | Public -- headline results in papers |
| GDS layer numbers | Requires Ligentec PDK license |
| Full DRC deck | Requires Ligentec PDK license |
| Component compact models | Requires Ligentec design kit |
| Process corner statistics | Proprietary |
| Damascene process details | Published at process level; manufacturing details proprietary |

---

## 6. LioniX TriPleX (Si3N4/SiO2 Hybrid)

### 6.1 Platform Specs

| Parameter | Value |
|---|---|
| Wafer size | 100 mm or 150 mm |
| Lithography | Contact lithography and i-line stepper |
| Core material | Si3N4 (LPCVD) embedded in SiO2 cladding |
| Waveguide geometry | Multiple cross-sections: single-stripe, double-stripe (DS), asymmetric double-stripe (ADS), box-shell |
| Core thickness (single stripe) | 50-200 nm |
| Box-shell inner dimensions | ~1 um x 1 um (SiO2 filled Si3N4 box) |
| Cladding | SiO2 (thermal + LPCVD) |
| Total cladding | > 8 um |
| Refractive index (Si3N4) | ~2.0 at 1550 nm |
| Operating wavelength | 405 nm to 2350 nm |
| Key advantages | Ultra-low loss (< 0.01 dB/cm), stress management via box geometry, visible + near-IR operation |
| Fabrication site | LioniX International, Enschede, Netherlands |
| Access | Custom foundry runs and MPW |

### 6.2 Design Rules

| Rule | Value (ADS geometry) | Source |
|---|---|---|
| Min waveguide width (ADS top stripe) | ~1.0 um | Roeloffzen et al., JLT 2018 |
| Min waveguide width (ADS bottom stripe) | ~1.0 um | Roeloffzen et al. |
| ADS stripe separation | ~0.5-1.0 um | Design dependent |
| Min waveguide gap | ~2-5 um (relaxed due to low contrast) | LioniX design rules |
| Min bend radius (DS/ADS) | 100-500 um (for < 0.01 dB/bend) | Roeloffzen et al. |
| Min bend radius (box-shell) | 50-100 um | Box-shell allows tighter bends |
| Chip dimensions | Up to 20 mm x 20 mm | LioniX fabrication capability |

*Note:* The relaxed gap and bend radius rules compared to silicon photonics
reflect the lower index contrast (~0.5 vs ~1.5 for Si/SiO2). This means
TriPleX circuits are typically larger than SOI circuits but with dramatically
lower propagation loss.

### 6.3 Layer Stack

#### Single-Stripe Cross-Section

| Layer | Material | Thickness | Notes |
|---|---|---|---|
| Si substrate | c-Si | 525 um | Carrier |
| Bottom cladding | SiO2 | > 8 um | Thermal oxide |
| Si3N4 core | Si3N4 | 50-170 nm | Single stripe; very low loss |
| Top cladding | SiO2 | > 8 um | LPCVD or PECVD |

#### Asymmetric Double-Stripe (ADS) Cross-Section

| Layer | Material | Thickness | Notes |
|---|---|---|---|
| Bottom cladding | SiO2 | > 8 um | -- |
| Lower Si3N4 stripe | Si3N4 | ~175 nm | Wider; provides vertical asymmetry |
| Intermediate SiO2 | SiO2 | ~500 nm | Separates the two stripes |
| Upper Si3N4 stripe | Si3N4 | ~175 nm | Narrower than lower |
| Top cladding | SiO2 | > 8 um | -- |

#### Box-Shell Cross-Section

| Layer | Material | Thickness | Notes |
|---|---|---|---|
| Bottom cladding | SiO2 | > 8 um | -- |
| Si3N4 box shell | Si3N4 | ~50 nm walls, ~1 um x 1 um outer | Hollow Si3N4 rectangle filled with SiO2 |
| SiO2 fill | SiO2 | fills box interior | ~0.9 x 0.9 um |
| Top cladding | SiO2 | > 8 um | -- |

### 6.4 Component Performance (Published)

#### 6.4.1 Waveguide Loss

| Geometry | Propagation Loss | Source |
|---|---|---|
| Single stripe (170 nm Si3N4) | < 0.01 dB/cm (1550 nm) | Roeloffzen et al., JLT 2018 |
| Double stripe (DS) | ~0.03-0.05 dB/cm | Roeloffzen et al. |
| Asymmetric double stripe (ADS) | ~0.06-0.1 dB/cm | Roeloffzen et al. |
| Box-shell | 0.05-0.1 dB/cm | LioniX publications |
| Visible (633 nm, single stripe) | ~0.1 dB/cm | Roeloffzen et al. |

#### 6.4.2 Directional Coupler

| Parameter | Value | Source |
|---|---|---|
| Excess loss | < 0.05 dB | Published |
| Coupling length (50/50, DS) | 200-2000 um (gap and width dependent) | Roeloffzen et al. |
| Wavelength sensitivity | lower than Si due to weaker dispersion | Inherent advantage |

#### 6.4.3 Ring Resonator

| Parameter | Value | Source |
|---|---|---|
| Ring radius (DS geometry) | 500-2000 um | Large due to low index contrast |
| Intrinsic Q | > 1 million (demonstrated > 5 million for single stripe) | Roeloffzen et al.; Oldenbeuving et al. |
| FSR (R=1mm) | ~0.25 nm at 1550 nm | Calculated from n_g |
| Application | Narrowband filters, sensors, microwave photonic filters | Key use case |

#### 6.4.4 Spot Size Converter / Fiber Coupling

| Parameter | Value | Source |
|---|---|---|
| Fiber coupling loss (SMF-28) | < 0.5 dB per facet | Roeloffzen et al. |
| Mode match approach | Taper to ~10 um mode field | Designed for butt-coupling to SMF |
| Advantage | Near-native fiber mode match | Key differentiator |

#### 6.4.5 Thermal Tuner

| Parameter | Value | Source |
|---|---|---|
| Heater material | Cr/Au or TiN | LioniX process options |
| Tuning efficiency | ~200-300 mW/pi (single stripe, thick cladding) | Roeloffzen et al. |
| Response time | ~1 ms (thick cladding) | Thermal limited |
| Note | Less efficient than Si due to low thermo-optic coefficient of Si3N4 and thick cladding | Power budget concern for large circuits |

#### 6.4.6 MZI Switch/Filter

| Parameter | Value | Source |
|---|---|---|
| Extinction ratio | > 30 dB | Roeloffzen et al. |
| Insertion loss | 0.3-0.5 dB (passive) | Published |
| Tuning range | Full 2*pi with heater | Thermal |

### 6.5 Key References

1. Roeloffzen, C.G.H. et al., "Low-loss Si3N4 TriPleX optical waveguides: Technology and applications overview," IEEE J. Sel. Topics Quantum Electron. 24, 4400321 (2018). Also in JLT 36, 1662-1671 (2018).
2. Wrhel, M. et al., "TriPleX: a versatile dielectric photonic platform," Adv. Opt. Technol. 4, 189-207 (2015).
3. Oldenbeuving, R.M. et al., "25 kHz narrow spectral bandwidth of a wavelength tunable diode laser with a short waveguide-based external cavity," Laser Physics Letters 10, 015708 (2013).
4. LioniX International: https://www.lionix-international.com/
5. LioniX TriPleX technology: https://www.lionix-international.com/photonics/triplex/

### 6.6 Public vs NDA Boundary

| Category | Status |
|---|---|
| Waveguide geometries (DS, ADS, box-shell) | Public -- published in journal papers |
| Loss specifications | Public -- headline results in JLT/JSTQE |
| Layer thicknesses | Public -- published cross-sections in papers |
| Design rules (min width, gap, bend) | Partially public -- general guidance in papers; detailed rules require design kit |
| GDS layer numbers | Requires LioniX design kit / NDA |
| Compact models | Requires design kit / collaboration |
| Process corner data | Proprietary |

---

## 7. Cross-Platform Comparison Summary

### 7.1 Waveguide Loss Comparison

| Platform | Core | Loss (dB/cm) @ 1550 nm | Min Bend Radius |
|---|---|---|---|
| SiEPIC EBeam | 220 nm Si (e-beam) | 2-4 | 5 um |
| AIM Photonics | 220 nm Si (DUV) | 1.5-2.5 | 5-10 um |
| IMEC iSiPP50G | 220 nm Si (DUV) | 1.0-2.0 | 5 um |
| GF 45CLO | ~220-300 nm Si (CMOS) | 0.7-3.0 | 5-10 um |
| AIM SiN | 200 nm SiN | 0.5-1.0 | 50-100 um |
| Ligentec AN800 | 800 nm Si3N4 | 0.03-0.1 | 20-100 um |
| LioniX TriPleX | 50-175 nm Si3N4 | < 0.01 - 0.1 | 50-2000 um |

### 7.2 Modulator Comparison

| Platform | Type | V_pi*L (V*cm) | BW (GHz) | Max Data Rate |
|---|---|---|---|---|
| AIM Photonics | PN MZM | 2.0-2.5 | > 25 | 50 Gbps NRZ |
| IMEC iSiPP50G | PN MZM | 1.5-2.5 | > 30 | 100 Gbps PAM-4 |
| GF 45CLO | PN MZM | ~2.0 | > 30 | 90 Gbps |
| Ligentec AN800 | Thermal only | N/A | ~kHz | N/A (no EO modulation) |
| LioniX TriPleX | Thermal only | N/A | ~kHz | N/A (no EO modulation) |

### 7.3 Photodetector Comparison

| Platform | Material | Responsivity (A/W) | BW (GHz) | Dark Current |
|---|---|---|---|---|
| AIM Photonics | Ge | 0.8-1.1 | > 30 | < 10 nA |
| IMEC iSiPP50G | Ge | 0.9-1.1 | > 40 | 1-10 nA |
| GF 45CLO | Ge | 0.8-1.0 | > 30 | < 50 nA |
| Ligentec AN800 | None (external) | N/A | N/A | N/A |
| LioniX TriPleX | None (external) | N/A | N/A | N/A |

### 7.4 Fiber Coupling Loss Comparison

| Platform | Grating Coupler (TE) | Edge Coupler |
|---|---|---|
| SiEPIC EBeam | 3.0-5.5 dB | 1.0-2.0 dB |
| AIM Photonics | 2.5-3.5 dB | 0.7-1.5 dB |
| IMEC iSiPP50G | 2.0-3.5 dB | 0.5-1.5 dB |
| GF 45CLO | 2.5-4.0 dB | N/A (published) |
| Ligentec AN800 | Not standard | 0.3-1.5 dB |
| LioniX TriPleX | Not standard | < 0.5 dB |

---

## 8. Mapping to PhotonTrust PDK Manifest Fields

The following table shows what published data can be encoded into PhotonTrust
`configs/pdks/*.pdk.json` manifests without requiring NDA access.

### 8.1 Fields Safely Encodable from Published Data

| Manifest Field | SiEPIC | AIM | IMEC | GF 45CLO | Ligentec | LioniX |
|---|---|---|---|---|---|---|
| `design_rules.min_waveguide_width_um` | 0.50 | 0.50 | 0.40 | 0.30 | 0.50 | 1.00 |
| `design_rules.min_waveguide_gap_um` | 0.20 | 0.25 | 0.20 | 0.20 | 0.30 | 2.00 |
| `design_rules.min_bend_radius_um` | 5.0 | 5.0 | 5.0 | 5.0 | 50.0 | 100.0 |
| `layer_stack[].material` | Yes | Yes | Yes | Partial | Yes | Yes |
| `layer_stack[].thickness_um` | Yes | Yes | Yes | Partial | Yes | Yes |
| `layer_stack[].gds_layer` | Yes (open) | No (PDK license) | No | No | No | No |
| `component_cells[].nominal_il_db` | Yes | Yes | Yes | Partial | Yes | Yes |
| `component_cells[].nominal_loss_db_per_cm` | Yes | Yes | Yes | Yes | Yes | Yes |
| Process corner coefficients | No | No | No | No | No | No |

### 8.2 Fields Requiring NDA or PDK License

| Data Type | Reason |
|---|---|
| Exact GDS layer/datatype numbers (non-open PDKs) | PDK license terms |
| Full DRC rule deck | Foundry IP |
| Full LVS extraction rules | Foundry IP |
| Compact models (S-param, SPICE) | Licensed design kit content |
| Process corner statistics (SS/FF/FS/SF) | Proprietary fab data |
| Mask layout of standard cells | Foundry IP |
| Via/contact rules in detail | CMOS PDK license (GF 45CLO) |

### 8.3 Recommended Approach for New Manifest Files

For foundries where GDS layer numbers are under NDA, manifests should:

1. Use placeholder layer numbers (e.g., 1/0 for core, 2/0 for cladding) with
   a note that these are illustrative.
2. Populate `design_rules` from published papers.
3. Populate `component_cells[].nominal_il_db` and related performance fields
   from published measurement data.
4. Set appropriate `support_level` metadata:
   - `"modeled"` for components with published specs that can be simulated
   - `"layout_only"` for components where only layout is representable
   - `"characterized_external"` for components needing external S-parameter data
5. Include `notes` citing the specific paper or publication for traceability.

---

## 9. Proposed New PDK Manifest Files

Based on this research, the following new manifests can be added to
`configs/pdks/`:

| File | Priority | Data Source Quality |
|---|---|---|
| `imec_isipp50g.pdk.json` | High | Strong published data (Absil, Pantouvaki et al.) |
| `gf_45clo.pdk.json` | Medium | Published data exists but less component-level detail |
| `ligentec_an800.pdk.json` | High | Well-published platform (Pfeiffer, Ji et al.) |
| `lionix_triplex.pdk.json` | Medium | Published data in Roeloffzen JLT 2018 |

*Note:* The existing `siepic_ebeam.pdk.json` and `aim_photonics.pdk.json`
should be updated with the more detailed specifications compiled in this
report. GDS layer numbers should only be included for open-source PDKs
(SiEPIC).

---

## 10. Consolidated Reference List

### Textbooks

- Chrostowski, L. & Hochberg, M., *Silicon Photonics Design: From Devices to Systems*, Cambridge University Press, 2015. ISBN 978-1-107-08545-9.
- Reed, G.T. & Knights, A.P., *Silicon Photonics: An Introduction*, Wiley, 2004.
- Bogaerts, W. & Chrostowski, L., "Silicon Photonics Circuit Design: Methods, Tools and Challenges," Laser & Photonics Reviews 12, 1700237 (2018).

### Platform / Foundry Papers

- Absil, P.P. et al., IEEE IEDM 2015, pp. 34.2.1-34.2.4. [IMEC iSiPP50G]
- Rakowski, M. et al., OFC 2020, paper T3H.3. [GF 45CLO]
- Pfeiffer, M.H.P. et al., Optica 4, 684-691 (2017). [Ligentec photonic Damascene]
- Roeloffzen, C.G.H. et al., IEEE JSTQE 24, 4400321 (2018). [LioniX TriPleX]
- Ji, X. et al., Optica 4, 619 (2017). [Si3N4 ultra-low loss]
- Liu, J. et al., Nature Communications 12, 2236 (2021). [Si3N4 wafer-scale]
- Rahim, A. et al., IEEE JSTQE 25, 8200818 (2019). [European SiPh platform survey]

### PDK and Tooling Resources

- SiEPIC-EBeam PDK: https://github.com/siepic/SiEPIC_EBeam_PDK
- SiEPIC-Tools: https://github.com/siepic/SiEPIC-Tools
- gdsfactory: https://github.com/gdsfactory/gdsfactory
- CORNERSTONE PDK (cspdk): https://github.com/gdsfactory/cspdk
- KLayout: https://www.klayout.de/
- Europractice (IMEC MPW): https://europractice-ic.com/technologies/photonics/imec/
- AIM Photonics: https://www.aimphotonics.com/
- AIM Photonics Academy: https://www.aimphotonics.academy/
- Ligentec: https://www.ligentec.com/
- LioniX International: https://www.lionix-international.com/
- GlobalFoundries Fotonix: https://gf.com/technology-solutions/silicon-photonics/

---

## 11. Caveats and Limitations

1. **All performance numbers are from published sources.** Actual performance on
   a specific fabrication run may differ due to process variation, design
   choices, and operating conditions.

2. **GDS layer/datatype numbers** are only redistributable for open-source PDKs
   (SiEPIC). For all other foundries, placeholder values should be used in
   manifest files.

3. **Process corner data** is not publicly available for any foundry. The
   corner values in existing manifests (`generic_sip_corners.pdk.json`,
   `aim_photonics_300nm_sin.pdk.json`) are illustrative estimates, not
   foundry-approved data.

4. **Compact models** (S-parameter files, Verilog-A, SPICE) require PDK
   licenses from the respective foundries.

5. **This report does not constitute engineering advice.** Designers should
   consult the official PDK documentation from each foundry before tapeout.

6. **Publication dates matter.** Foundry processes evolve. The specs reported
   here are from papers published through early 2025. Newer process revisions
   may offer improved performance.
