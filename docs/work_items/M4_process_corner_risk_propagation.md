# Research Brief: M4 — Process-Corner Risk Propagation

## Metadata
- Work item ID: M4
- Title: PDK Process-Corner Uncertainty Propagation to QKD Key Rate Distribution
- Date: 2026-03-01
- Priority: P1 — primary AIM Photonics unlock; direct commercial value
- Related modules: `photonstrust/pdk/`, `photonstrust/pic/simulate.py`,
  `photonstrust/pic/layout/verification/core.py`, `photonstrust/invdesign/`,
  `photonstrust/qkd.py`

---

## 1. Problem and Motivation

Photonic integrated circuit fabrication is subject to stochastic process
variation. Even on a well-controlled CMOS-compatible platform (e.g., AIM
Photonics 300nm Si₃N₄, IMEC iSiPP500G 220nm SOI), dimensional tolerances of
waveguides, coupling gaps, and etch depths create chip-to-chip variation in
optical performance. For a QKD transmitter PIC, this variation propagates
through the S-parameter response to the QKD key rate, potentially causing
the fabricated chip to deliver a dramatically lower (or zero) key rate than
the nominal design predicts.

**The gap:** PhotonTrust currently simulates only the nominal design point
(single set of component parameters, no variation). A chip that nominally
delivers 15 kbps at 50 km may deliver < 1 kbps at process slow corner, yet
the current tool gives no warning before the shuttle run.

**Economic impact:** AIM Photonics MPW shuttle runs cost $5,000–$50,000 per
design slot. A process-corner analysis that identifies high-risk designs before
submission avoids expensive fabrication failures. A foundry that offers this
capability as an integrated tool has a competitive advantage.

**What is needed:** A `photonstrust sweep --corners` command that:
1. Reads process-corner definitions from the PDK
2. Generates S-parameter perturbations for fast/typical/slow corners
3. Runs QKD key rate at each corner
4. Reports key rate distribution (min, nominal, max), yield fraction at target
   key rate, and sensitivity ranking of dominant process parameters

**Who benefits:**
- PIC design engineers at companies using AIM Photonics or IMEC shuttles
- AIM Photonics itself (reduces customer failure rate, improves shuttle ROI)
- NSF POSE reviewers looking for direct economic value over proprietary tools

---

## 2. Research Questions and Hypotheses

**RQ1:** For a typical QKD transmitter PIC on a 300nm Si₃N₄ platform, which
process parameters (waveguide width, coupling gap, etch depth, film thickness)
contribute most to QKD key rate variance? Is the key rate sensitivity dominated
by coupling efficiency variation or by insertion loss variation?

**RQ2:** Is the QKD key rate a monotone function of process corner severity,
or can there be non-monotone behaviour (e.g., a slow-corner chip with lower
coupling ratio that happens to produce less QBER)?

**RQ3:** What is the minimum number of corner evaluations needed to bound the
key rate distribution to within ±10% with 95% confidence? Is a 3-corner
(fast/nominal/slow) evaluation sufficient, or is Monte Carlo required?

**Hypothesis H1 (falsifiable):** For a directional coupler–based BB84 transmitter
PIC on 300nm Si₃N₄, the coupling gap variation (σ_gap ≈ 5 nm) is the dominant
source of key rate variance, contributing > 70% of the total key rate standard
deviation. This can be verified by fixing all parameters except gap and comparing
the resulting key rate range to the full corner sweep range.

**Hypothesis H2 (falsifiable):** The QKD key rate is monotone decreasing with
total on-chip insertion loss. Therefore, the worst-case (minimum) key rate occurs
at the slow process corner (maximum IL) for a fixed operating distance. This is
falsifiable if crosstalk at the fast corner (smaller gaps) induces enough QBER
to reduce key rate below the slow-corner value.

---

## 3. Related Work

### 3.1 Process Variation in Silicon Photonics

**AIM Photonics 300nm Si₃N₄ platform (publicly documented specs):**
- Waveguide width: target ± 10 nm (1σ), ±20 nm (2σ)
- Film thickness (t_core): 295–305 nm (±5 nm, 1σ)
- Coupling gap: ±5 nm (1σ), ±10 nm (2σ)
- Propagation loss: 0.5–3 dB/cm (run-to-run variation)

**IMEC iSiPP500G 220nm SOI (published literature):**
- Waveguide width σ ≈ 5–15 nm (e-beam vs. 193nm lithography)
- Etch depth variation: ±5 nm (partial etch), ±10 nm (full etch)
- Strip waveguide n_eff variation: Δn_eff/Δw ≈ 0.15–0.25 per μm

**SiEPIC multi-project wafer (public runs):**
- Typical width variation: ±20 nm across wafer
- Temperature sensitivity: Δn_eff/ΔT ≈ 1.8 × 10⁻⁴ /K (Si), 2.5 × 10⁻⁵ /K (SiN)

### 3.2 Existing PhotonTrust Infrastructure

- `pdk/registry.py`: PDK dataclass with `design_rules` dict — extend to include
  `process_corners` and `sensitivity_coefficients`
- `pic/simulate.py`: `simulate_pic_netlist(netlist, wavelength_nm)` — call at
  each perturbed parameter point
- `pic/layout/verification/core.py`: `verify_crosstalk_budget()` — run at each
  corner to check crosstalk-induced QBER
- `invdesign/`: coupler_ratio.py, mzi_phase.py — can be used for sensitivity
  derivatives

### 3.3 Existing Approaches

The standard industry approach is worst-case corner analysis (3–5 corners),
supplemented by Monte Carlo for yield estimation. Tools used:
- Cadence Virtuoso + Spectre for EDA corner analysis (proprietary)
- Lumerical INTERCONNECT (proprietary, $20K+/yr)
- Custom Python scripts in research groups (not open, not calibrated)
PhotonTrust will provide the first open, PDK-calibrated corner analysis for
QKD transmitter PICs.

---

## 4. Mathematical Formulation

### 4.1 Waveguide Effective Index Perturbation

The effective index n_eff of a waveguide mode depends on the cross-sectional
geometry. For the fundamental TE mode of a rectangular Si₃N₄ waveguide on SiO₂:

**Width sensitivity (Δn_eff per nm width change):**
```
∂n_eff/∂w ≈ (n_core² − n_clad²) / (2 n_eff) × (E_y(w/2)²/⟨E_y²⟩)
```

For 300nm Si₃N₄ TE₀ at 1550nm (typical values from mode solver):
```
n_eff ≈ 1.68,  n_core(Si₃N₄) = 1.996,  n_clad(SiO₂) = 1.444
∂n_eff/∂w ≈ 1.5 × 10⁻³ per nm   (empirical from published mode solver data)
```

For 220nm SOI TE₀ at 1550nm:
```
n_eff ≈ 2.40,  n_core(Si) = 3.478,  n_clad(SiO₂) = 1.444
∂n_eff/∂w ≈ 3.0 × 10⁻³ per nm   (stronger confinement → higher sensitivity)
```

**Phase error from width perturbation over waveguide length L:**
```
Δφ = (2π/λ) × (∂n_eff/∂w) × Δw × L
```

For Δw = 10 nm, L = 1 mm, λ = 1550 nm:
```
Δφ_SiN ≈ (2π/1550 × 10⁻⁹) × (1.5 × 10⁻³ × 10 × 10⁻⁹) × (1 × 10⁻³)
        ≈ 0.061 rad  (small — weak sensitivity for SiN)

Δφ_SOI ≈ 0.121 rad  (doubles for SOI — more sensitive)
```

**MZI transmission under phase error:**
```
T_MZI(Δφ) = cos²(φ_design/2 + Δφ/2)
```

For φ_design = π (intensity modulator, nominally T=0 at null):
```
T_MZI ≈ sin²(Δφ/2) ≈ (Δφ/2)²  (small Δφ — leakage)
```
This leakage contributes to QBER in the QKD signal.

### 4.2 Directional Coupler Coupling Ratio Under Gap Variation

The power coupling coefficient κ² of a directional coupler (symmetric, lossless)
depends on the evanescent field overlap integral, which falls exponentially with
gap:

```
κ²(g) = κ₀² × exp(−2γ(g − g₀))
```
where:
- g₀ = nominal coupling gap (e.g., 200 nm for Si₃N₄)
- γ = mode field decay rate in the gap ≈ √(β² − k_clad²) ≈ 3–6 μm⁻¹
- κ₀² = nominal coupling ratio (e.g., 0.5 for 50:50 coupler)

**Sensitivity of coupling ratio to gap perturbation Δg:**
```
Δ(κ²) = −2γ κ₀² Δg

For γ = 4 μm⁻¹, κ₀² = 0.5, Δg = 5 nm:
Δ(κ²) = −2 × 4 × 0.5 × 0.005 μm = −0.020

→ κ²_fast_corner ≈ 0.52  (gap decreases by 5 nm → more coupling)
→ κ²_slow_corner ≈ 0.48  (gap increases by 5 nm → less coupling)
```

For an MZI-based BB84 basis splitter (nominally 50:50):
```
Splitting error: Δκ² = 0.02
Extinction ratio penalty: ΔER_dB ≈ 10 × Δκ² / (κ²(1−κ²)) ≈ 0.4 dB
```
This creates an asymmetric QBER contribution between basis states.

### 4.3 Propagation Loss Variation

Propagation loss α (dB/cm) varies with sidewall roughness, a stochastic
parameter that depends on lithography and etch quality:

```
α(w) ≈ α_scatt + α_absorption
α_scatt ∝ σ²_roughness × ⟨E_y(w/2)²⟩²  (volume current method)
```

For Si₃N₄ at 1550nm, run-to-run variation:
- Typical: 0.5–1.5 dB/cm
- Fast corner (lower roughness): α = 0.5 dB/cm
- Slow corner (higher roughness): α = 3.0 dB/cm

**Impact on total chip insertion loss for L_chip = 1 cm route:**
```
ΔIL_chip = (α_slow − α_nominal) × L_chip = (3.0 − 1.0) × 1 = 2 dB
```

**Impact on η_chip:**
```
η_chip_fast = 10^{−(0.5 × L_cm)/10} = 10^{−0.05} ≈ 0.89
η_chip_nominal = 10^{−(1.0 × L_cm)/10} = 10^{−0.10} ≈ 0.79
η_chip_slow  = 10^{−(3.0 × L_cm)/10} = 10^{−0.30} ≈ 0.50
```

### 4.4 Key Rate Sensitivity to η_chip

From the BB84 key rate formula (M1 formulation), the leading-order dependence
of key rate on total transmittance η = η_source × η_chip × η_channel × η_det:

```
Q_μ ≈ μ η e^{−μ}   (dominant single-photon term, dark counts negligible)
Q_1 ≈ μ e^{−μ} η

R ≈ q μ e^{−μ} η × [1 − H₂(e_d)]   (simplified, ignoring error correction term)
```

Therefore:
```
∂R/∂η_chip = R / η_chip

→ A 2 dB increase in chip IL (η_chip slow/nominal = 0.50/0.79 = 0.63)
  reduces key rate by factor 0.63 at the same operating distance.
```

For exponentially decreasing key rate with distance (R ∝ η_channel ∝ e^{−αL/10}):
```
ΔR_corner / R_nominal = η_chip_corner / η_chip_nominal
```

This is the "first-order transfer function" of process variation to key rate.

### 4.5 Monte Carlo Yield Estimation

For yield estimation, model each process parameter as an independent Gaussian:

```
w ~ N(w₀, σ_w²)       where σ_w = 10 nm (1σ, Si₃N₄)
g ~ N(g₀, σ_g²)       where σ_g = 5 nm (1σ)
t ~ N(t₀, σ_t²)       where σ_t = 5 nm (1σ, film thickness)
α ~ N(α₀, σ_α²)       where σ_α = 0.5 dB/cm (1σ, propagation loss)
```

For N Monte Carlo samples (N = 1000 for 1% statistical uncertainty):

```python
for i in range(N_mc):
    params_i = sample_process_parameters(pdk, seed=seed + i)
    netlist_i = perturb_netlist(compiled_netlist, params_i)
    sim_i = simulate_pic_netlist(netlist_i, wavelength_nm=λ₀)
    eta_chip_i = extract_eta_chip(sim_i, λ₀)
    scenario_i = build_qkd_scenario(eta_chip=eta_chip_i, ...)
    result_i = compute_point(scenario_i, target_distance_km)
    key_rates[i] = result_i.key_rate_bps

yield_fraction = sum(kr > R_threshold for kr in key_rates) / N_mc
```

**Yield confidence interval (Clopper-Pearson exact):**
```
CI_95 = Beta(k+0.5, N−k+0.5) where k = number of passes
```

For N=1000 and yield=0.92: CI_95 = [0.906, 0.932]

### 4.6 Corner Definitions (PDK Manifest Extension)

Extend the PDK dataclass with `process_corners`:

```json
"process_corners": {
  "description": "AIM Photonics 300nm Si3N4 process corners (1σ / 2σ)",
  "parameters": {
    "waveguide_width_nm": {
      "nominal": 0.0, "fast_1sigma": +10.0, "slow_1sigma": -10.0,
      "fast_2sigma": +20.0, "slow_2sigma": -20.0, "unit": "nm_delta"
    },
    "coupling_gap_nm": {
      "nominal": 0.0, "fast_1sigma": -5.0, "slow_1sigma": +5.0,
      "fast_2sigma": -10.0, "slow_2sigma": +10.0, "unit": "nm_delta"
    },
    "film_thickness_nm": {
      "nominal": 300.0, "fast_1sigma": 305.0, "slow_1sigma": 295.0, "unit": "nm"
    },
    "propagation_loss_db_per_cm": {
      "nominal": 1.0, "fast_1sigma": 0.5, "slow_1sigma": 2.0,
      "fast_2sigma": 0.3, "slow_2sigma": 3.0, "unit": "dB/cm"
    }
  },
  "corner_sets": {
    "SS": {"waveguide_width_nm": "slow_1sigma", "coupling_gap_nm": "slow_1sigma",
           "propagation_loss_db_per_cm": "slow_1sigma"},
    "TT": {"waveguide_width_nm": "nominal", "coupling_gap_nm": "nominal",
           "propagation_loss_db_per_cm": "nominal"},
    "FF": {"waveguide_width_nm": "fast_1sigma", "coupling_gap_nm": "fast_1sigma",
           "propagation_loss_db_per_cm": "fast_1sigma"},
    "FS": {"waveguide_width_nm": "fast_1sigma", "coupling_gap_nm": "slow_1sigma",
           "propagation_loss_db_per_cm": "nominal"},
    "SF": {"waveguide_width_nm": "slow_1sigma", "coupling_gap_nm": "fast_1sigma",
           "propagation_loss_db_per_cm": "nominal"}
  }
}
```

Five corner set evaluation (SS, TT, FF, FS, SF) covers the main diagonal and
off-diagonal variations. Monte Carlo adds statistical completeness.

---

## 5. Method Design

### 5.1 Netlist Perturbation Engine

```python
def perturb_netlist(
    netlist: dict,
    process_params: dict,
    *,
    pdk: PDK,
) -> dict:
    """Return a perturbed copy of the netlist under given process parameters."""
    import copy
    perturbed = copy.deepcopy(netlist)

    Δw_nm  = process_params.get("waveguide_width_nm", 0.0)
    Δg_nm  = process_params.get("coupling_gap_nm", 0.0)
    α_dBcm = process_params.get("propagation_loss_db_per_cm",
                                 pdk.design_rules.get("propagation_loss_db_per_cm", 1.0))

    for instance in perturbed.get("instances", []):
        kind = instance.get("kind", "")
        params = instance.setdefault("params", {})

        if kind in ("waveguide", "delay_line"):
            # Width perturbation → propagation loss change
            # Model: Δα_dBcm ∝ -(Δw/w₀) × C_roughness (reduced roughness scatter)
            # Simplified: use α directly from process_params
            length_cm = float(params.get("length_um", 100.0)) * 1e-4
            params["insertion_loss_db"] = α_dBcm * length_cm

        elif kind in ("directional_coupler", "multimode_interferometer"):
            # Gap perturbation → coupling ratio shift
            g0 = float(params.get("gap_um", 0.2)) * 1e3  # convert to nm
            gamma_per_nm = 0.004  # μm⁻¹ → nm⁻¹ (γ ≈ 4 μm⁻¹)
            kappa0_sq = float(params.get("coupling_ratio", 0.5))
            delta_kappa_sq = -2 * gamma_per_nm * kappa0_sq * Δg_nm
            new_kappa_sq = max(0.0, min(1.0, kappa0_sq + delta_kappa_sq))
            params["coupling_ratio"] = new_kappa_sq

        elif kind == "ring_resonator":
            # Width perturbation → resonance wavelength shift
            # Δλ_res = λ_res × (∂n_eff/∂w) × Δw / n_g
            dn_dw_per_nm = pdk.sensitivity_coefficients.get("dn_eff_dw_per_nm", 1.5e-3)
            n_g = float(params.get("group_index", 1.75))
            lambda_res = float(params.get("resonance_nm", 1550.0))
            delta_lambda = lambda_res * (dn_dw_per_nm * Δw_nm) / n_g
            params["resonance_nm"] = lambda_res + delta_lambda

    return perturbed
```

### 5.2 Corner Sweep Engine

```python
def run_corner_sweep(
    graph_path: Path,
    *,
    pdk_name: str,
    protocol: str,
    target_distance_km: float,
    wavelength_nm: float,
    corner_set: str | None = None,      # None = all corners
    n_monte_carlo: int = 0,             # 0 = no MC
    mc_seed: int = 42,
    key_rate_threshold_bps: float = 1000.0,
    output_dir: Path,
) -> dict:
```

**Output structure:**
```json
{
  "kind": "pic.corner_sweep",
  "run_id": "<hex>",
  "nominal": {
    "key_rate_bps": 15400,
    "eta_chip": 0.654,
    "insertion_loss_db": 1.84
  },
  "corners": {
    "SS": {"key_rate_bps": 6200, "eta_chip": 0.501, "insertion_loss_db": 2.99},
    "TT": {"key_rate_bps": 15400, "eta_chip": 0.654, "insertion_loss_db": 1.84},
    "FF": {"key_rate_bps": 21800, "eta_chip": 0.741, "insertion_loss_db": 1.30},
    "FS": {"key_rate_bps": 13100, "eta_chip": 0.612, "insertion_loss_db": 2.13},
    "SF": {"key_rate_bps": 9800,  "eta_chip": 0.549, "insertion_loss_db": 2.60}
  },
  "monte_carlo": {
    "n_samples": 1000,
    "key_rate_mean_bps": 14200,
    "key_rate_std_bps": 3800,
    "key_rate_p5_bps": 7100,
    "key_rate_p95_bps": 21500,
    "yield_fraction": 0.923,
    "yield_ci_95": [0.906, 0.932]
  },
  "risk_assessment": {
    "worst_case_key_rate_bps": 6200,
    "worst_corner": "SS",
    "yield_above_threshold": 0.923,
    "risk_level": "MEDIUM",
    "dominant_sensitivity": "coupling_gap_nm",
    "sensitivity_rank": [
      {"parameter": "coupling_gap_nm", "variance_fraction": 0.71},
      {"parameter": "propagation_loss_db_per_cm", "variance_fraction": 0.22},
      {"parameter": "waveguide_width_nm", "variance_fraction": 0.07}
    ]
  }
}
```

### 5.3 Sensitivity Ranking

Using the Sobol first-order variance decomposition approximation via
corner evaluations:

```
Var(R) ≈ Σ_i (∂R/∂p_i)² × σ_pᵢ²

∂R/∂p_i ≈ (R_fast_i − R_slow_i) / (2 σ_pᵢ)   (central difference)

Sensitivity fraction for parameter i:
S_i = (∂R/∂p_i)² σ_pᵢ² / Var(R)
```

This gives the fractional contribution of each process parameter to total
key rate variance — the "sensitivity rank" reported in `risk_assessment`.

### 5.4 Risk Level Classification

```
risk_level = "LOW"    if yield > 0.99 AND worst_case_key_rate > R_threshold
risk_level = "MEDIUM" if yield > 0.90 AND worst_case_key_rate > R_threshold / 2
risk_level = "HIGH"   if yield ≤ 0.90 OR worst_case_key_rate ≤ R_threshold / 2
risk_level = "CRITICAL" if worst_case_key_rate = 0 (no key at any corner)
```

### 5.5 CLI Command

```
photonstrust sweep <graph.json> --corners [options]

Options:
  --pdk TEXT              PDK name or manifest path
  --protocol TEXT         QKD protocol [BB84_decoy]
  --target-distance FLOAT Distance in km for key rate evaluation [50.0]
  --wavelength FLOAT      Wavelength in nm [1550.0]
  --corners TEXT          Corner set to evaluate: all, SS, TT, FF, FS, SF [all]
  --monte-carlo INT       Number of MC samples (0=disabled) [0]
  --mc-seed INT           RNG seed for MC [42]
  --threshold FLOAT       Key rate threshold in bps for yield calculation [1000.0]
  --output PATH           Output directory
```

---

## 6. Experimental Design

### 6.1 Validation Tests

| Test | What it verifies |
|------|-----------------|
| `test_perturb_waveguide_il` | α perturbation changes IL monotonically |
| `test_perturb_coupler_gap_monotone` | Δg > 0 → lower coupling, Δg < 0 → higher coupling |
| `test_perturb_ring_resonance_shift` | Width change shifts resonance correctly |
| `test_corner_ss_worse_than_tt` | SS key rate < TT key rate (physics check) |
| `test_corner_ff_better_than_tt` | FF key rate > TT key rate (physics check) |
| `test_yield_fraction_bounded` | Yield ∈ [0, 1] always |
| `test_sensitivity_rank_sums_to_one` | Σ S_i = 1.0 (variance fractions) |
| `test_mc_deterministic_with_seed` | Same seed → identical MC results |
| `test_risk_level_critical_at_zero_keyrate` | Risk=CRITICAL when worst corner R=0 |
| `test_corner_sweep_schema_valid` | Output JSON schema-validates |

### 6.2 Reference Design Corner Analysis

Run corner sweep on `graphs/demo_qkd_transmitter.json` with AIM 300nm SiN
PDK corners. Lock expected outputs:

| Corner | Expected η_chip range |
|--------|-----------------------|
| FF     | 0.70 – 0.85 |
| TT     | 0.60 – 0.75 |
| SS     | 0.40 – 0.60 |

These ranges encode physical expectations. If a code change shifts any corner
outside these bounds, the test fails and the perturbation model must be audited.

---

## 7. Risk and Failure Analysis

**Risk R1: Linearisation error in corner perturbation**
The coupling ratio sensitivity formula (exponential gap dependence) is
linearised for small Δg. For Δg > 20 nm (2σ), the linear approximation
breaks down. Mitigation: add a `perturbation_warning` flag when Δg > 15 nm;
recommend full FDTD re-simulation for large perturbations.

**Risk R2: Correlated process parameters**
In real fab, waveguide width and propagation loss are correlated (thinner
waveguides have higher sidewall roughness). The current model treats them as
independent. Mitigation: document independence assumption explicitly; add
`correlation_matrix` field to process_corners for future extension.

**Risk R3: Monte Carlo runtime**
N=1000 samples × full simulate_pic_netlist call may be slow (each call takes
~1s on CPU without JAX). Mitigation: (a) run JAX-JIT compilation once, then
batch via vmap; (b) use surrogate model (linear sensitivity) for MC samples,
only calling full simulator at 5-corner deterministic set.

**Risk R4: PDK process corner data is proprietary**
Real AIM Photonics corner data is in their NDA-protected PDK. The shipped
PDK manifest will use publicly documented typical values. Mitigation: provide
a `process_corners_placeholder` flag; encourage foundries to contribute their
own corner files using the defined JSON schema.

---

## 8. Reproducibility Package

- New file: `configs/pdks/aim_photonics_300nm_sin.pdk.json` — PDK manifest
  with process corners using publicly available typical specs
- Reference corner sweep result: `results/corner_sweep/demo_qkd_transmitter/`
- Script: `scripts/run_corner_sweep_demo.py`
- Tests: `tests/pic/test_corner_sweep.py`
- Notebook: `examples/Process_Corner_Risk.ipynb`

---

## 9. Acceptance Criteria

**Scientific correctness:**
- [ ] SS corner always gives lower key rate than TT for a lossy QKD transmitter
- [ ] FF corner always gives higher key rate than TT (less loss)
- [ ] Sensitivity fractions Σ = 1.0 (variance decomposition normalised)
- [ ] Yield CI 95% width ≤ 2/√N (Clopper-Pearson bound for N=1000)

**Engineering correctness:**
- [ ] All 10 unit tests pass
- [ ] MC results deterministic with fixed seed
- [ ] Corner sweep completes in < 30 seconds for 5-corner + 100 MC samples
- [ ] Output JSON schema-validates

**Product/reporting:**
- [ ] `--corners all` produces all 5 corner results
- [ ] `risk_level` and `dominant_sensitivity` always populated
- [ ] Results table human-readable in CLI output (using rich)

---

## 10. Decision

Proceed after M1 completes, as M4 extends the PIC simulation infrastructure
established in M1. Estimated effort: 2 weeks (1 week perturbation engine,
1 week corner sweep + MC + risk assessment).

---

## Implementation Plan

### Step 1: Extend PDK dataclass and manifests
- Edit: `photonstrust/pdk/registry.py` — add `process_corners`,
  `sensitivity_coefficients` fields to `PDK` dataclass
- New file: `configs/pdks/aim_photonics_300nm_sin.pdk.json`
- New file: `configs/pdks/generic_sip_corners.pdk.json` (generic Si₃N₄ corners)

### Step 2: Netlist perturbation engine
- New file: `photonstrust/pic/perturbation.py`
- Functions: `perturb_netlist(netlist, process_params, *, pdk)`,
  `sample_process_parameters(pdk, *, seed, sigma_multiplier=1.0)`

### Step 3: Corner sweep engine
- New file: `photonstrust/pic/corner_sweep.py`
- Functions: `run_corner_sweep(graph_path, *, ...)`,
  `compute_sensitivity_rank(corner_results, sigma_dict)`,
  `classify_risk_level(corner_results, threshold_bps)`

### Step 4: Schema + report
- New file: `schemas/pic_corner_sweep.json`
- Update `photonstrust/workflow/schema.py`

### Step 5: CLI integration
- Edit `photonstrust/cli.py`: add `--corners` flag to `sweep` subcommand
  (or add new `corner-sweep` subcommand)

### Step 6: Demo script, notebook, tests
- New file: `scripts/run_corner_sweep_demo.py`
- New file: `examples/Process_Corner_Risk.ipynb`
- New file: `tests/pic/test_corner_sweep.py`
