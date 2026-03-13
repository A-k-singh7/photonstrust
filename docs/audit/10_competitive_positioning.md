# 10 - Competitive Positioning Analysis

---

## Landscape: QKD & Quantum Networking Simulators

| Tool | Org | License | Physics depth | Reliability artifacts | PIC integration |
|------|-----|---------|--------------|----------------------|----------------|
| **NetSquid** | NetSquid / QuTech ecosystem | Proprietary (registration + ToS) | Deep (discrete-event) | None | None |
| **SeQUeNCe** | Argonne | BSD-3-Clause | Moderate | None | None |
| **QuNetSim** | TU Delft | MIT | Shallow (protocol-level) | None | None |
| **SimulaQron** | QuTech | BSD-3-Clause | Shallow | None | None |
| **PhotonTrust** | -- | AGPL-3.0 | Moderate-Deep (pluggable) | Reliability cards | GDS/KLayout |

Expanded competitive teardown (including PIC CAD + verification tooling and non-copying moat moves):
- `../research/deep_dive/22_competitor_gap_analysis_and_moat_moves.md`

## Primary Sources (Standards, Tool Docs, and Key Papers)

### Simulator / ecosystem references
- NetSquid product site (distribution model and ToS): https://netsquid.org/
- SeQUeNCe repository license (BSD-3-Clause): https://raw.githubusercontent.com/sequence-toolbox/SeQUeNCe/master/LICENSE
- QuNetSim repository license (MIT): https://raw.githubusercontent.com/tqsd/QuNetSim/master/LICENSE
- SimulaQron repository license (BSD-3-Clause): https://raw.githubusercontent.com/SoftwareQuTech/SimulaQron/master/LICENSE

### Protocol research targets (high leverage in 2024-2026)
- MDI-QKD (attack-surface reduction at measurement): Lo, Curty, Qi (2012) PRL, DOI: 10.1103/PhysRevLett.108.130503
- TF-QKD (rate scaling beyond repeaterless linear-loss scaling): Lucamarini et al. (2018) Nature, DOI: 10.1038/s41586-018-0066-6
- PM-QKD (practical TF-family variant): Ma et al. (2018) PRX, DOI: 10.1103/PhysRevX.8.031043

### "Reality check" experimental benchmarks
- Long-distance fiber QKD system benchmark: Boaron et al. (2018) PRL, "Secure quantum key distribution over 421 km of optical fiber", DOI: 10.1103/PhysRevLett.121.190502

### Satellite / free-space anchors
- Satellite-to-ground QKD demonstration: Liao et al. (2017) Nature, DOI: 10.1038/nature23655
- Satellite QKD overview/review: Bedington, Arrazola, Ling (2017) Nature, DOI: 10.1038/nature23675

### PIC layout / verification workflow anchors
- KLayout standalone DRC engine usage (`-b -r`): https://www.klayout.org/downloads/master/doc-qt5/manual/drc_basic.html
- KLayout command-line arguments reference: https://www.klayout.de/command_args.html
- gdsfactory ecosystem paper (design/sim/verification positioning + KLayout integration mentions): https://gdsfactory.github.io/photonics_paper/

---

## PhotonTrust's Unique Position

PhotonTrust is **not** a general-purpose quantum network simulator. It is a
**reliability and verification layer** that sits atop physics backends and
produces decision-grade trust artifacts. This distinction is critical.

### Core differentiators

1. **Reliability cards** -- No other tool produces machine-readable trust
   artifacts with evidence tiers, uncertainty bands, and operating envelopes.

2. **PIC layout integration** -- GDS extraction, KLayout runner, LVS-lite,
   and route verification. No other QKD simulator connects to photonic IC
   design flows.

   Minimal "trust artifact" contract for PIC verification (what the platform
   must output per run):
   - `inputs/`: GDS/OASIS, tech/PDK metadata, rule decks (or macro params)
   - `klayout/`: invoked command-line, macro(s) used, versions, logs
   - `reports/`: DRC summary (pass/fail + counts), annotated screenshots, rule waivers (if any)
   - `metrics/`: extracted route lengths, bend radii histograms, layer usage, checksum hashes
   - `provenance/`: SBOM + signing (later phases), deterministic hashes, timestamps

3. **Multi-band support** -- NIR (795 nm), O-band (1310 nm), C-band (1550 nm)
   with band-specific presets. Most simulators assume a single wavelength.

4. **Pluggable physics backends** -- QuTiP for full quantum modeling, analytic
   for fast sweeps, with transparent fallback. Other tools lock you into one
   fidelity level.

5. **Graph-based circuit compiler** -- Drag-drop JSON to engine config/netlist.
   Enables visual workflow design via the web UI.

6. **Satellite/free-space channel** -- OrbitVerify expansion for LEO downlinks
   with atmospheric, pointing, and turbulence models.

7. **Measurement ingestion** -- Real hardware data can be imported to calibrate
   the digital twin, closing the sim-to-hardware loop.

---

## Gaps vs. Mature Tools

### vs. NetSquid

| Feature | NetSquid | PhotonTrust | Gap |
|---------|----------|-------------|-----|
| Discrete-event kernel | Production-grade | Basic (EventKernel stub) | Large |
| Multi-hop network simulation | Yes (100s of nodes) | Repeater spacing only | Large |
| Protocol library depth | 20+ protocols | 3 stubs (swap, purify, teleport) | Large |
| Published validation | Nature papers | Internal benchmarks | Medium |
| Community size | Large academic user base | Early stage | Large |

**How to close the gap:**
- Do NOT try to replicate NetSquid. Instead, position as complementary.
- PhotonTrust produces the **reliability card**; NetSquid produces the
  **simulation trace**. They serve different decisions.
- Add an import path: `photonstrust import netsquid-trace.json` to generate
  reliability cards from NetSquid simulation outputs.

### vs. SeQUeNCe

| Feature | SeQUeNCe | PhotonTrust | Gap |
|---------|----------|-------------|-----|
| Heterogeneous networks | Yes (see upstream publications) | No | Medium |
| Protocol implementation | Full BB84/BBM92 | Key rate model only | Medium |
| Active development | Active (Argonne) | Active | -- |
| Documentation quality | Good API docs | Research docs (no API docs) | Medium |

**How to close the gap:**
- Add API documentation (Sphinx/mkdocs).
- Implement BB84 and BBM92 as full protocol classes (not just key rate models).
- Add a `photonstrust.network` module for multi-node topologies.

---

## Strategic Recommendations

### 1. Publish a comparison benchmark

Create a public benchmark dataset that compares PhotonTrust outputs against:
- Published experimental QKD results (e.g., Boaron et al. 2018 for 421 km-class fiber QKD)
- PLOB repeaterless bound
- NetSquid/SeQUeNCe outputs (where available)

This builds credibility and enables academic citation.

**Implementation:**
```bash
# Add to configs/canonical/
configs/canonical/validate_boaron_2018_421km.yml
configs/canonical/validate_plob_bound.yml
configs/canonical/validate_metro_typical.yml

# Add validation script
python scripts/validate_against_literature.py
```

### 2. Add ETSI/ISO compliance metadata

The ETSI GS QKD 016 Protection Profile and ISO/IEC 23837-1 define security
requirements for QKD. Adding compliance metadata to reliability cards
positions PhotonTrust as a certification-support tool.

### 3. Build gdsfactory interop

gdsfactory is the dominant open-source PIC design framework. Adding a
`photonstrust[gdsfactory]` optional dependency with direct component import
opens the photonic IC design community.

```python
# photonstrust/layout/gdsfactory_bridge.py
def import_gdsfactory_component(component):
    """Convert a gdsfactory Component to PhotonTrust route contract."""
    gds_path = component.write_gds()
    return extract_routes_from_gds(gds_path)
```

### 4. Add MDI-QKD and TF-QKD protocol models

These are two high-activity QKD research areas:
- MDI-QKD removes all detector side-channel attacks
- TF-QKD breaks the PLOB bound with single-photon interference

Adding these protocols would attract the research community.

### 5. Create a "Getting Started for Researchers" guide

Academic adoption requires:
- A 5-minute quickstart that produces a publishable figure
- A `CITATION.cff` for proper attribution
- Example Jupyter notebooks for common research workflows
- Clear documentation of which physics assumptions are made

---

## Positioning Statement

> PhotonTrust is the open-source toolkit for **certifying quantum link
> performance**. While general-purpose simulators model network behavior,
> PhotonTrust generates **reliability cards** -- machine-readable trust
> artifacts that document expected performance under uncertainty, calibrated
> against real hardware measurements, with evidence tiers aligned to
> emerging QKD certification standards.

---

## Adoption Roadmap

| Phase | Focus | Target audience |
|-------|-------|-----------------|
| v0.1 (current) | Core engine + reliability cards | Internal / early adopters |
| v0.2 | Published benchmarks + API docs + CITATION.cff | Academic researchers |
| v0.3 | gdsfactory interop + MDI/TF-QKD | PIC designers + QKD researchers |
| v0.4 | ETSI/ISO compliance metadata | Industry / certification bodies |
| v1.0 | Network topology + full protocol library | General quantum networking |

