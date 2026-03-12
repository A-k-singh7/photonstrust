# Research Brief: M2 — ETSI QKD Standards Compliance Engine

## Metadata
- Work item ID: M2
- Title: Machine-Readable ETSI QKD Standards Compliance Checker
- Date: 2026-03-01
- Priority: P1 — unlocks DOE, DARPA, EU Quantum Flagship funding
- Related modules: `photonstrust/compliance/`, `photonstrust/pic/signoff.py`,
  `photonstrust/evidence/`, `photonstrust/qkd_protocols/`

---

## 1. Problem and Motivation

Every national quantum communication program (EU EuroQCI, UK NQCC, US DOE
Quantum Network Infrastructure, ESA EAGLE-1, CSA QEYSSat) is required to
demonstrate compliance with ETSI QKD standards during system procurement,
certification, and deployment phases. Currently this compliance assessment is
done manually: engineers read the ETSI documents, create Word/PDF checklists,
and annotate results by hand. There is no open, automated, reproducible tool
for generating machine-readable ETSI QKD compliance reports.

**The gap:** PhotonTrust already produces calibrated QKD simulation outputs
(key rate, QBER, link distance, component parameters). The ETSI standards
define explicit numerical thresholds and functional requirements. The mapping
from PhotonTrust outputs to ETSI requirement checks is mechanical and automatable.

**Why this is undeniable for government funders:**
- DOE's quantum network infrastructure programs (ONRAMP, OQNET) must comply
  with ETSI GS QKD 004 and 008
- EU Horizon Europe QKD projects must cite ETSI compliance in deliverables
- ESA EAGLE-1 system specification references ETSI QKD 002 and 011
- DARPA ONISQ program requires verifiable security parameters
An open tool that generates PDF/JSON compliance reports against named ETSI
standards is infrastructure that every one of these programs needs and none
currently have in open-source form.

**Who benefits:**
- National lab QKD system integrators (Oak Ridge, Argonne, Los Alamos)
- Quantum hardware companies submitting to government programs
- EU academic consortia writing Horizon Europe deliverables
- ESA/CNES satellite QKD program engineers

---

## 2. Research Questions and Hypotheses

**RQ1:** Which ETSI QKD standards contain numerical requirements that can be
checked deterministically from PhotonTrust simulation outputs, and which require
physical system measurements that are outside the scope of simulation?

**RQ2:** For requirements that mix simulation-checkable and measurement-required
criteria, what is the correct semantic to use — partial compliance, conditional
compliance, or simulation-only attestation?

**RQ3:** How should the compliance report express uncertainty? A simulated
key rate of 1200 bps at 50 km has a confidence interval depending on the
source model; the ETSI requirement "key rate > 1 kbps" is a threshold test.
What is the correct statistical framing for pass/fail under uncertainty?

**Hypothesis H1 (falsifiable):** At least 60% of the numerically checkable
requirements in ETSI GS QKD 004 and 008 can be verified directly from the
outputs of `compute_sweep()` without additional measurement inputs.

**Hypothesis H2 (falsifiable):** For ETSI GS QKD 011 component requirements,
the dominant compliance gaps for a standard InGaAs APD detector system will
be dark count rate (fails the ≤ 10⁴ cps threshold at elevated temperatures)
and detector efficiency (marginal compliance at η_d ≈ 0.15 vs. the preferred
η_d ≥ 0.20 recommendation).

---

## 3. Related Work

### 3.1 ETSI QKD Standards Relevant to PhotonTrust

| Standard | Title | Simulation-checkable? |
|----------|-------|----------------------|
| ETSI GS QKD 002 | Use cases | Partially (link scenarios) |
| ETSI GS QKD 004 | Functional requirements | Yes (key rate, QBER thresholds) |
| ETSI GS QKD 008 | Security specification | Yes (security parameters, ε bounds) |
| ETSI GS QKD 011 | Component requirements | Partially (detector, source specs) |
| ETSI GS QKD 014 | Protocol and data format | Structural (key delivery API shape) |
| ETSI GS QKD 015 | Control interface | Structural (control API shape) |

### 3.2 Existing Tools

No open-source tool currently performs ETSI QKD compliance checking.
Commercial tools (ID Quantique CERBERIS, Toshiba QKD) include internal
compliance checks but do not expose them. This is a genuine open-source gap.

### 3.3 Existing PhotonTrust Outputs Used by M2

- `compute_sweep()`: key_rate_bps, qber_percent at each distance
- `compute_point()`: Q_1, Y_1, e_1^ph, security_epsilon (from finite_key.py)
- `build_source_profile()`: g2_0, p_multi, emission_prob
- `build_detector_profile()`: pde, dark_counts_cps, dead_time
- `pic/signoff.py`: signoff ladder decision
- `evidence/signing.py`: Ed25519 for compliance report signing

---

## 4. Mathematical Formulation

### 4.1 ETSI GS QKD 004 — Functional Requirements

**Reference:** ETSI GS QKD 004 V2.1.1 (2020-08), Section 7

**Requirement F1 — Minimum secure key rate:**
```
Clause 7.2: The QKD module shall provide a minimum secret key output rate
            of K_min ≥ 1 kbps over the specified operational distance.

Check:  max(sweep.key_rate_bps) ≥ K_min
        at distance d ≤ D_spec (specified operational distance)

PhotonTrust check:
  PASS if compute_sweep(scenario, [D_spec]).key_rate_bps[0] ≥ K_min
  FAIL otherwise, with diagnostic: "key_rate={actual} < K_min={K_min} at d={D_spec}"
```

**Requirement F2 — Maximum QBER:**
```
Clause 7.3: The QBER shall not exceed E_max = 11% during normal operation.

Check:  QBER(d) ≤ 0.11 for all d ≤ D_spec

Physical basis: For BB84 with binary symmetric channel and standard post-processing,
  the secret key rate becomes zero when QBER > 1 − H₂⁻¹(1/2) ≈ 11%.
  Above this threshold, the Csiszár-Körner bound gives no positive key rate.

PhotonTrust check:
  PASS if max(sweep.qber_percent) / 100.0 ≤ 0.11 for all d ≤ D_spec
  FAIL otherwise; note: PhotonTrust enforces R=0 when QBER > threshold anyway
```

**Requirement F3 — Positive key rate across operating range:**
```
Clause 7.4: The QKD system shall maintain R > 0 over the entire specified
            operating distance range [D_min, D_max].

Check:  R(d) > 0 for all d in [D_min, D_max]

PhotonTrust check:
  PASS if min(key_rate_bps in range) > 0
  FAIL with: "key rate drops to zero at d_cutoff km, inside specified range"
```

**Requirement F4 — Composable security parameter:**
```
Clause 7.5: Security level shall be ε-composable with ε ≤ ε_target.
            Recommended: ε_target = 10^{−10} for 30-year security horizon.

Check:  finite_key_result.security_epsilon ≤ ε_target

PhotonTrust check (requires finite_key.enabled=true in scenario):
  PASS if security_epsilon ≤ 1e-10
  FAIL with: "ε={actual} > ε_target=1e-10; increase block size or reduce distance"
  SKIP if finite_key not configured (report as "not assessed")
```

### 4.2 ETSI GS QKD 008 — Security Specification

**Reference:** ETSI GS QKD 008 V1.1.1 (2010-12); GS QKD 008 V2.1.1 (2024)

**Requirement S1 — Non-zero single-photon gain:**
```
Clause 8.3: Q_1 > 0 (single-photon component of the gain must be positive).
            This ensures the key rate is not entirely attributable to
            multi-photon contributions exploitable by PNS attacks.

Check:  Q_1 > 0, equivalently Y_1 = η_total > 0

PhotonTrust check:
  PASS always if η_total > 0 (i.e., there is any optical path)
  FAIL if η_total = 0 (broken optical chain — caught by DRC R5 first)
```

**Requirement S2 — Phase error rate bounded below 0.5:**
```
Clause 8.4: e_1^ph < 0.5

Physical basis: If e_1^ph ≥ 0.5, the quantity 1 − H₂(e_1^ph) ≤ 0
  and no positive key rate is possible. The BB84 security proof (Shor-Preskill)
  requires e_1^ph < 0.5 for any distillation.

Check:  e_1^ph < 0.5

PhotonTrust check:
  PASS if e_1^ph < 0.5 (always true for e_d < 0.25 and Y_0 < Y_1)
  FAIL with diagnostic if e_d or background drives e_1^ph ≥ 0.5
```

**Requirement S3 — Multi-photon fraction below PNS attack threshold:**
```
Clause 8.5: The multi-photon gain Q_{≥2} / Q_total < Δ_PNS
            where Δ_PNS is protocol-dependent (typically 0.1 for BB84).

For WCP source with Poisson statistics:
  Q_{≥2} = Σ_{n≥2} (μⁿ e^{-μ}/n!) · Y_n ≈ μ²/2 · Y_2 (dominant term)
  Q_total = Q_μ (full gain)

  Q_{≥2}/Q_total ≈ μ/2 · (Y_2/Y_1) × (Q_1/Q_total)
  For practical μ < 0.5: Q_{≥2}/Q_total < 0.1 generically satisfied

PhotonTrust check:
  PASS if μ < 0.6 (practical threshold for vacuum+weak decoy security)
  WARNING if 0.6 ≤ μ < 1.0 (elevated multi-photon risk, decoy bounds may be loose)
  FAIL if μ ≥ 1.0 (multi-photon regime; decoy-state analysis invalid without
                    strong decoy assumptions)
```

**Requirement S4 — Key distillation margin:**
```
Clause 8.7: The security analysis must demonstrate a positive distillable key
            under the worst-case coherent attack (not just individual attacks).

PhotonTrust status: All implemented protocols use GLLP (BB84) or Xu et al.
  (MDI-QKD) or Ma-Zeng-Zhou (TF-QKD) proofs, which are all proven secure
  against general coherent attacks. This is a statement-of-compliance item,
  not a numerical threshold.

Check:  protocol ∈ {BB84_decoy, MDI_QKD, TF_QKD, PM_QKD}
  → PASS with reference to the underlying security proof
  → list the proof paper DOI in the compliance report
```

### 4.3 ETSI GS QKD 011 — Component Requirements

**Reference:** ETSI GS QKD 011 V1.1.1 (2016-11)

**Requirement C1 — Source QBER contribution:**
```
Clause 6.2.1: The photon source shall contribute less than 1% to the total QBER.

Source QBER contribution: e_source = g₂(0) / 2
  (second-order correlation function; for ideal single-photon source g₂(0)=0)
  For WCP: g₂(0) = 1 (Poisson, no antibunching), but the effective source
  QBER contribution is e_d (optical misalignment), not g₂(0).
  For SPDC: g₂(0) ≈ μ/(1+μ) ≈ μ for small μ (thermal statistics).

PhotonTrust check:
  For WCP: source_qber_contribution = e_d (misalignment-dominated)
    PASS if e_d < 0.01
    WARNING if 0.01 ≤ e_d < 0.03 (typical lab: ~1.5%)
    FAIL if e_d ≥ 0.03
  For SPDC: source_qber_contribution ≈ μ / 2
    PASS if μ < 0.02
    WARNING if 0.02 ≤ μ < 0.1
```

**Requirement C2 — Detector dark count rate:**
```
Clause 6.3.1: Detector dark count rate DCR ≤ 10⁴ cps (10 kcps).

PhotonTrust check:
  PASS if detector.dark_counts_cps ≤ 1e4
  FAIL if detector.dark_counts_cps > 1e4
  Note: InGaAs APDs at 250K: DCR ~ 1–5 kcps (PASS)
        InGaAs APDs at 280K: DCR ~ 20–100 kcps (FAIL)
        SNSPDs: DCR ~ 1–100 cps (PASS by large margin)
```

**Requirement C3 — Detector efficiency:**
```
Clause 6.3.2: Photon detection efficiency η_d ≥ 10% (informative, recommended).

PhotonTrust check:
  PASS if detector.pde ≥ 0.10
  WARNING if 0.07 ≤ detector.pde < 0.10
  FAIL if detector.pde < 0.07
```

**Requirement C4 — Timing jitter:**
```
Clause 6.3.3: Timing jitter shall not limit the key rate by more than 10%.

Impact model: Effective detection efficiency in coincidence window:
  η_d_eff = η_d · erf(T_w / (2√2 σ_jitter))
  where T_w = coincidence window, σ_jitter = jitter σ (= FWHM/2.355)

  Key rate penalty from jitter: ΔR/R = 1 − η_d_eff/η_d

PhotonTrust check:
  PASS if ΔR/R < 0.10
  WARNING if 0.10 ≤ ΔR/R < 0.20
  FAIL if ΔR/R ≥ 0.20
```

### 4.4 ETSI GS QKD 002 — Use Case Compliance

**Reference:** ETSI GS QKD 002 V1.1.1 (2019-05)

This standard defines reference link scenarios. PhotonTrust scenario configs
can be tagged with a GS QKD 002 use case ID:

| Use case ID | Description | Distance | Protocol |
|-------------|-------------|----------|----------|
| UC-1 | Point-to-point metro | ≤ 100 km | BB84 |
| UC-2 | Long-haul with trusted relay | 100–1000 km | BB84 + relay |
| UC-3 | Satellite-to-ground | LEO orbit | MDI-QKD or BB84 free-space |
| UC-4 | Secure data centre interconnect | ≤ 20 km | Any |
| UC-5 | Mobile/portable QKD | ≤ 5 km | Any |

Compliance check: verify that the scenario meets the minimum key rate
(Requirement F1) under the distance constraint for the claimed use case.

### 4.5 Compliance Report Schema

```json
{
  "schema_version": "0.1",
  "kind": "etsi_qkd_compliance_report",
  "run_id": "<hex>",
  "generated_at": "<ISO-8601>",
  "standards_assessed": ["ETSI GS QKD 002", "ETSI GS QKD 004",
                          "ETSI GS QKD 008", "ETSI GS QKD 011"],
  "scenario_summary": {
    "protocol": "BB84_decoy",
    "target_distance_km": 50,
    "wavelength_nm": 1550.0
  },
  "requirements": [
    {
      "id": "GS-QKD-004-F1",
      "standard": "ETSI GS QKD 004",
      "clause": "7.2",
      "description": "Minimum secret key rate ≥ 1 kbps at operating distance",
      "status": "PASS",
      "computed_value": 12400,
      "threshold": 1000,
      "unit": "bps",
      "notes": "key_rate=12400 bps at d=50km"
    },
    {
      "id": "GS-QKD-008-S2",
      "standard": "ETSI GS QKD 008",
      "clause": "8.4",
      "description": "Phase error rate e_1^ph < 0.5",
      "status": "PASS",
      "computed_value": 0.034,
      "threshold": 0.5,
      "unit": "dimensionless",
      "notes": "e_1^ph=0.034 (well below threshold)"
    }
  ],
  "summary": {
    "total": 14,
    "pass": 12,
    "fail": 1,
    "warning": 1,
    "not_assessed": 0
  },
  "overall_status": "CONDITIONAL_PASS",
  "signature": { ... }
}
```

**Overall status semantics:**
- `PASS`: all checkable requirements pass
- `CONDITIONAL_PASS`: all FAIL=0, but WARNING > 0 (minor deviations)
- `FAIL`: at least one requirement has status FAIL
- `PARTIAL`: some requirements skipped (e.g., finite-key not configured)

---

## 5. Method Design

### 5.1 Compliance Module Architecture

```
photonstrust/compliance/
    __init__.py
    registry.py          # requirement registry with metadata
    checkers/
        __init__.py
        gs_qkd_002.py    # use case checks
        gs_qkd_004.py    # functional requirement checks
        gs_qkd_008.py    # security specification checks
        gs_qkd_011.py    # component requirement checks
    report.py            # aggregate + format compliance report
    cli_compliance.py    # 'photonstrust compliance check' subcommand
```

### 5.2 Requirement Registry (`registry.py`)

Each requirement is a dataclass:

```python
@dataclass(frozen=True)
class ETSIRequirement:
    id: str                    # e.g., "GS-QKD-004-F1"
    standard: str              # e.g., "ETSI GS QKD 004"
    version: str               # e.g., "V2.1.1 (2020-08)"
    clause: str                # e.g., "7.2"
    description: str
    check_fn: str              # function name in checkers module
    inputs_required: list[str] # keys from sweep_result / scenario
    category: str              # "functional", "security", "component", "use_case"
```

### 5.3 Checker Function Signature (All Checkers)

```python
def check_gs_qkd_004_f1(
    sweep_result: dict,
    scenario: dict,
    *,
    k_min_bps: float = 1000.0,
    d_spec_km: float | None = None,
) -> RequirementResult:
    """ETSI GS QKD 004 Clause 7.2 — Minimum secret key rate."""
    ...
    return RequirementResult(
        req_id="GS-QKD-004-F1",
        status="PASS" | "FAIL" | "WARNING" | "NOT_ASSESSED",
        computed_value=...,
        threshold=k_min_bps,
        unit="bps",
        notes="...",
    )
```

### 5.4 CLI Command

```
photonstrust compliance check <reliability_card.json or scenario.yml> [options]

Options:
  --standards TEXT    Comma-separated standards to check [all]
                      Options: GS-QKD-002, GS-QKD-004, GS-QKD-008, GS-QKD-011
  --use-case TEXT     ETSI GS QKD 002 use case ID (UC-1 through UC-5)
  --k-min FLOAT       Override minimum key rate threshold in bps [1000.0]
  --d-spec FLOAT      Override specified operational distance in km
  --output PATH       Output compliance report JSON
  --format TEXT       Output format: json, pdf, text [json]
  --signing-key PATH  Sign compliance report with Ed25519
  --strict            Exit non-zero if any requirement FAILS (not just WARNS)
```

### 5.5 PDF Report Generation

Use `reportlab` (already in optional deps as `pdf`) to generate a formatted
PDF compliance report suitable for inclusion in procurement submissions:

```
PhotonTrust ETSI QKD Compliance Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
System:     BB84 Decoy-State QKD, 50 km SMF
Generated:  2026-03-01T14:22:11Z
Run ID:     a3f9b21c44d8

ETSI GS QKD 004 — Functional Requirements
  F1  Key rate ≥ 1 kbps at 50 km          ● PASS   12,400 bps
  F2  QBER ≤ 11%                           ● PASS   3.1%
  F3  Positive rate over [10, 50] km       ● PASS
  F4  ε-composable, ε ≤ 10^{-10}          ○ NOT ASSESSED (finite_key disabled)

ETSI GS QKD 008 — Security Specification
  S1  Q_1 > 0                              ● PASS
  S2  e_1^ph < 0.5                         ● PASS   0.034
  S3  Multi-photon fraction < 10%          ● PASS   μ=0.5
  S4  Coherent-attack secure protocol      ● PASS   [GLLP 2004]

ETSI GS QKD 011 — Component Requirements
  C1  Source QBER contribution < 1%        ● PASS   e_d=0.5%
  C2  Dark count rate ≤ 10⁴ cps            ▲ WARNING 12,000 cps
  C3  Detection efficiency ≥ 10%           ● PASS   η_d=25%
  C4  Jitter penalty < 10%                 ● PASS   5.3%

Overall: CONDITIONAL PASS (1 warning, 0 failures)
Signature: Ed25519 verified ✓
```

---

## 6. Experimental Design

### 6.1 Test Suite

| Test | What it verifies |
|------|-----------------|
| `test_f1_pass_above_threshold` | key_rate=2000 → PASS |
| `test_f1_fail_below_threshold` | key_rate=500 → FAIL |
| `test_f2_pass_low_qber` | qber=0.03 → PASS |
| `test_f2_fail_high_qber` | qber=0.12 → FAIL |
| `test_s2_phase_error_boundary` | e_1^ph=0.499 → PASS, 0.501 → FAIL |
| `test_s3_mu_boundary` | μ=0.59 → PASS, μ=0.61 → WARNING |
| `test_c2_dcr_boundary` | DCR=9999 → PASS, DCR=10001 → FAIL |
| `test_c4_jitter_penalty_calculation` | Verify erf formula numerically |
| `test_report_schema_validation` | Output JSON validates against schema |
| `test_pdf_report_generated` | PDF file is non-empty and parseable |
| `test_signing_compliance_report` | Signed report verifies with public key |
| `test_cli_compliance_check_exits_zero` | CLI exits 0 on compliant input |
| `test_cli_compliance_strict_exits_nonzero` | `--strict` exits 1 on FAIL |

### 6.2 Reference Compliance Scenarios

Three reference scenarios committed to `configs/compliance/`:

1. `compliant_bb84_snspd.yml` — modern SNSPD system, all requirements PASS
2. `marginal_bb84_ingaas.yml` — InGaAs APD, C2 WARNING expected
3. `noncompliant_high_qber.yml` — high misalignment, F2 FAIL expected

These serve as regression tests: the compliance status of each reference
scenario is locked and must not change across code versions.

---

## 7. Risk and Failure Analysis

**Risk R1: ETSI standard version ambiguity**
ETSI has updated GS QKD 008 (V1 in 2010, V2 in 2024). Some numerical thresholds
differ between versions. Mitigation: implement for latest version (V2); document
which version each requirement is from; emit standard version in report header.

**Risk R2: Requirements outside simulation scope**
Several ETSI requirements cover physical hardware tamper-resistance, key
injection interfaces, and side-channel protections that PhotonTrust cannot
simulate. Mitigation: explicitly mark these as `NOT_ASSESSED` with a clear
explanation; never emit false PASSes for unsimulable requirements.

**Risk R3: Protocol coverage**
GS QKD 008 S4 (coherent-attack security) is currently provable only for
BB84 (GLLP), MDI-QKD (Xu 2014), and PM-QKD/TF-QKD (Ma 2018). BBM92 and
AMDI_QKD are in the registry but their security proofs are more nuanced.
Mitigation: mark S4 as PASS only for protocols with cited peer-reviewed proofs;
UNKNOWN for others.

---

## 8. Reproducibility Package

- Reference compliance reports: `results/compliance/reference/` (3 scenarios)
- Schema: `schemas/etsi_qkd_compliance_report.json`
- Script: `scripts/run_compliance_demo.py`
- CI: Add compliance check on `compliant_bb84_snspd.yml` to CV workflow
- Notebook: `examples/ETSI_Compliance_Check.ipynb`

---

## 9. Acceptance Criteria

**Scientific correctness:**
- [ ] All numerical thresholds correctly sourced from named ETSI clauses
- [ ] QBER threshold 11% derivable from H₂(e) = 1 (verified in test)
- [ ] Jitter penalty formula matches erf integral numerically (test vs. quad)
- [ ] `NOT_ASSESSED` never appears where a numerical check is possible

**Engineering correctness:**
- [ ] All 13 unit tests pass
- [ ] Three reference scenarios produce expected compliance statuses
- [ ] CLI exits correctly for `--strict` flag
- [ ] JSON output schema-validates
- [ ] PDF report generates without exceptions

**Product/reporting:**
- [ ] PDF output suitable for inclusion in a procurement document
- [ ] Signed compliance report verifiable by third party with public key only
- [ ] `photonstrust compliance check --help` shows all options

---

## 10. Decision

Proceed. Estimated effort: 2–3 weeks. No blocking dependencies on M1 or M3,
though it benefits from having a signed reliability card input to check against.
Can be developed in parallel with M1.

---

## Implementation Plan

### Step 1: Requirement registry and schema
- New file: `photonstrust/compliance/registry.py`
- New file: `schemas/etsi_qkd_compliance_report.json`

### Step 2: Checker functions for GS QKD 004
- New file: `photonstrust/compliance/checkers/gs_qkd_004.py`
- Functions: `check_f1`, `check_f2`, `check_f3`, `check_f4`

### Step 3: Checker functions for GS QKD 008
- New file: `photonstrust/compliance/checkers/gs_qkd_008.py`
- Functions: `check_s1`, `check_s2`, `check_s3`, `check_s4`

### Step 4: Checker functions for GS QKD 011
- New file: `photonstrust/compliance/checkers/gs_qkd_011.py`
- Functions: `check_c1`, `check_c2`, `check_c3`, `check_c4`

### Step 5: Checker functions for GS QKD 002 use cases
- New file: `photonstrust/compliance/checkers/gs_qkd_002.py`
- Functions: `check_use_case(use_case_id, sweep_result, scenario)`

### Step 6: Report aggregator
- New file: `photonstrust/compliance/report.py`
- Functions: `build_compliance_report(...)`, `render_pdf_report(...)`

### Step 7: CLI integration
- Edit: `photonstrust/cli.py` — add `compliance` subcommand group
- New file: `photonstrust/compliance/cli_compliance.py`

### Step 8: Reference scenarios and regression tests
- New dir: `configs/compliance/` with 3 reference YAML files
- New dir: `results/compliance/reference/` with 3 locked compliance JSONs
- New file: `tests/compliance/test_checkers.py`

### Step 9: PDF report
- Edit: `photonstrust/compliance/report.py` — add `render_pdf_report()`
  using `reportlab` (already in optional deps `pdf`)
