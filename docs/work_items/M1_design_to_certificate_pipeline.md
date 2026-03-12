# Research Brief: M1 — Design-to-Certificate Pipeline

## Metadata
- Work item ID: M1
- Title: End-to-End Certify Pipeline — PIC Graph to Signed QKD Reliability Certificate
- Date: 2026-03-01
- Priority: P0 — produces the live demo that wins funding conversations
- Related modules: `photonstrust/pic/`, `photonstrust/pipeline/`, `photonstrust/cli.py`,
  `photonstrust/pdk/`, `photonstrust/qkd.py`, `photonstrust/evidence/`

---

## 1. Problem and Motivation

PhotonTrust currently operates as a collection of independent subsystems:
PIC graph compilation, PIC simulation, QKD key-rate computation, chip assembly,
signoff ladder, and Ed25519 evidence signing. Each works in isolation. No single
command traverses the full chain from a photonic circuit design to a
cryptographically signed QKD reliability certificate.

**The gap:** A user with a `graph.json` describing a PIC-based QKD transmitter
must manually orchestrate 6–8 separate commands, interpret intermediate JSON
reports, and manually connect simulation outputs to QKD protocol inputs. This is
not a user-facing tool; it is a collection of research scripts.

**What is needed:** A single `photonstrust certify graph.json` command that:

1. Compiles the graph into a PIC netlist
2. Runs DRC checks against the PDK design rules
3. Runs LVS-lite (topology consistency check)
4. Simulates S-parameters across the design wavelength range
5. Extracts chip-level insertion loss and coupling efficiency per channel
6. Maps PIC outputs to QKD scenario parameters (η_source term)
7. Computes QKD key rate over a configurable distance sweep
8. Compares key rate to PLOB bound and ETSI thresholds
9. Generates a signed reliability card with full provenance chain

**Who benefits:**
- PIC design teams who want to know "will this chip deliver a usable QKD key rate?"
  before committing to a $10K–$50K foundry shuttle run
- Foundry integration engineers at AIM Photonics demonstrating tool support for
  their PDK ecosystem
- NSF POSE reviewers looking for evidence that PhotonTrust replaces a Cadence
  + Synopsys workflow
- Any funder wanting a single live demo that shows the full stack

---

## 2. Research Questions and Hypotheses

**RQ1:** What is the minimal, physically correct mapping from PIC S-parameter
simulation outputs to QKD scenario input parameters, without introducing
assumptions that are not grounded in the photonic circuit model?

**RQ2:** What DRC and LVS checks are necessary-and-sufficient at the graph/netlist
level (pre-layout) to guarantee the compiled netlist is physically realisable,
without requiring a full GDS file?

**RQ3:** How do compound uncertainties in PIC fabrication (coupling efficiency,
insertion loss) propagate to the QKD key rate, and what is the correct
uncertainty representation in the signed reliability card?

**Hypothesis H1 (falsifiable):** The dominant PIC-to-QKD coupling parameter is
η_chip = Π_i T_i, the product of insertion losses of all optical elements in the
transmitter path. A 1 dB increase in η_chip insertion loss reduces the QKD key
rate by a factor proportional to Δη/η at the operating distance.

**Hypothesis H2 (falsifiable):** For a ring-resonator-based WDM QKD transmitter
on a 300nm SiN platform, the chip-level insertion loss budget must satisfy
η_chip > 10^(−2.0/10) = 0.63 (i.e., ≤ 2.0 dB total on-chip loss) to maintain
a positive key rate over 50 km of SMF at 1550 nm with a standard InGaAs APD
detector (PDE = 0.25, DCR = 1000 cps).

---

## 3. Related Work and Baseline Methods

### 3.1 Existing PhotonTrust Infrastructure (Do Not Rewrite)

| Module | What it does | Used in M1 |
|--------|-------------|------------|
| `graph/compiler.py` | graph.json → compiled netlist | Step 1 |
| `pic/simulate.py` | netlist → S-parameters (JAX chain/DAG solver) | Step 4 |
| `pic/layout/verification/core.py` | crosstalk budget check | Step 2 (extend) |
| `pic/assembly.py` | chip assembly report | Step 3 |
| `pdk/registry.py` | PDK design rules | Step 2 |
| `qkd.py:compute_sweep()` | key rate vs distance | Step 7 |
| `evidence/signing.py` | Ed25519 sign/verify | Step 9 |
| `pic/signoff.py` | signoff ladder | Step 8 |

### 3.2 The Missing Glue

What does not yet exist:
- `pipeline/certify.py` — orchestrator that calls all the above in sequence
- The **PIC-to-QKD parameter bridge** — the physical mapping from S-parameter
  simulation outputs to the `scenario.source` block consumed by `compute_point()`
- A unified **certify CLI command** in `cli.py`
- A **certificate schema** that bundles PIC report + QKD sweep + signoff + signature

### 3.3 Competing Approaches

No open-source tool performs this full chain. The closest approaches:
- Ansys Lumerical CML Compiler: goes from component models to circuit S-params,
  but stops at the photonics boundary — no QKD protocol layer
- GDSfactory + Meep: layout + FDTD simulation, no S-param → QKD bridge
- NetSquid: quantum network simulation, no PIC physical model
PhotonTrust is uniquely positioned to bridge all three.

---

## 4. Mathematical Formulation

### 4.1 PIC-to-QKD Parameter Bridge

The central physics of this milestone is the correct mapping from PIC simulation
outputs to QKD scenario parameters.

**PIC simulation output (from `simulate_pic_netlist`):**
```
S_ij(λ)   — scattering matrix elements, complex, function of wavelength λ
|S_21(λ)|² — power transmittance from port 1 to port 2 (insertion loss)
```

**QKD scenario input (consumed by `compute_point`):**
```
scenario.source.coupling_efficiency   = η_coupling
scenario.source.collection_efficiency = η_collection
scenario.channel.fiber_loss_db_per_km = α
```

**Correct mapping:**

The PIC chip sits between the photon source and the fiber channel. The optical
path for a QKD transmitter PIC is:

```
Source → [PIC input coupler] → [WG routing] → [modulator] → [output coupler] → Fiber
```

Define the chip insertion loss as the total on-chip loss in the transmitter path:

```
IL_chip_dB = −10 log₁₀ |S_out,in(λ₀)|²

where:
  S_out,in = compound S-parameter from photon source input port
             to fiber launch output port
  λ₀       = operating wavelength (e.g., 1550.0 nm for C-band)
```

Map to QKD parameters:
```
η_chip = |S_out,in(λ₀)|²   (linear power transmittance)
η_source_total = η_collection × η_coupling × η_chip

→ set scenario.source.coupling_efficiency = η_coupling × η_chip
   (absorb chip loss into the coupling efficiency term)
   leave scenario.source.collection_efficiency unchanged
```

**For wavelength-division multiplexed (WDM) transmitters:**
Each QKD channel k has its own insertion loss:
```
η_chip_k = |S_out_k, in(λ_k)|²
```
Run a separate QKD sweep per channel k. Aggregate key rates as:
```
R_total = Σ_k R_k
```

**Coupling efficiency from chip-to-fiber interface:**
The output coupler (grating coupler or edge coupler) contributes an additional
coupling loss:
```
IL_coupler_dB = PDK.component_cells["grating_coupler"].nominal_il_db
η_coupler     = 10^{−IL_coupler_dB / 10}
```
This is a PDK-level parameter, not derived from S-parameter simulation.
It must be included in η_source_total.

**Complete η_source chain:**
```
η_source_total = η_emitter × η_collection × η_chip × η_coupler

η_emitter    = source.collection_efficiency (photon generation efficiency)
η_collection = source.coupling_efficiency (fiber/chip input coupling)
η_chip       = |S_out,in(λ₀)|² (PIC on-chip transmittance from sim)
η_coupler    = PDK coupler IL (chip-to-fiber at output)
```

### 4.2 DRC at the Graph/Netlist Level (Pre-GDS)

Full DRC requires a GDS layout file (see M4 for process-corner DRC). At the
graph/netlist level, the following rules can be checked deterministically:

**Rule G1 — Minimum waveguide width (per PDK):**
```
∀ component c in netlist:
  width_um(c) ≥ PDK.design_rules.min_waveguide_width_um
```

**Rule G2 — Minimum coupling gap (per PDK):**
```
∀ directional coupler c:
  gap_um(c) ≥ PDK.design_rules.min_waveguide_gap_um
```

**Rule G3 — Minimum bend radius:**
```
∀ bend b with radius r_um:
  r_um ≥ PDK.design_rules.min_bend_radius_um
```
Bend loss formula for reference (Marcuse, 1976 approximation):
```
α_bend_dB/cm ≈ A exp(−B · r_um)
where A, B are empirical constants from PDK characterization
```
Below `min_bend_radius_um`, α_bend rises sharply and the PDK does not
guarantee S-parameter accuracy.

**Rule G4 — Port connectivity:**
```
∀ edge (u,v) in graph:
  port u exists on component type(u) AND
  port v exists on component type(v) AND
  port modes are compatible (e.g., both TE₀ or both TM₀)
```

**Rule G5 — No floating ports:**
```
∀ output port p not connected to an edge:
  component(p) ∈ {terminator, detector, fiber_launch}
  (i.e., every open port must be either a detector/output or explicitly terminated)
```

**Rule G6 — Crosstalk budget (existing, from layout/verification/core.py):**
```
∀ parallel waveguide run r:
  XT(gap_um(r), length_um(r), λ_nm) ≤ PDK.design_rules.max_crosstalk_db
```

**DRC severity levels:**
- ERROR: G1, G2, G3, G4 — design cannot be fabricated or simulated correctly
- WARNING: G5 — possible unintended port loss
- INFO: G6 — crosstalk may impact QBER but does not block tapeout

### 4.3 LVS-Lite at the Netlist Level

Full LVS (Layout vs Schematic) compares extracted GDS topology to schematic.
At the pre-GDS level, LVS-lite compares the compiled netlist topology to the
source graph specification:

**Check L1 — Block count consistency:**
```
|netlist.blocks| = |graph.blocks|
```

**Check L2 — Connection count consistency:**
```
|netlist.connections| = |graph.edges|
```

**Check L3 — Port mapping integrity:**
For each graph edge (block_A.port_X, block_B.port_Y):
```
netlist.connection maps block_A.port_X to block_B.port_Y
(same source and destination, no port renaming during compilation)
```

**Check L4 — Component kind preservation:**
```
∀ instance i: netlist.instance[i].kind = graph.instance[i].kind
(compilation must not substitute component types)
```

### 4.4 Signoff Ladder Integration

The certify pipeline produces a multi-stage signoff ladder (existing `signoff.py`,
extended to 5 levels):

```
Level 1: chip_assembly     — assembly report status + failed_links = 0
Level 2: drc               — all DRC ERROR rules pass
Level 3: lvs_lite          — all LVS-lite checks pass
Level 4: qkd_key_rate      — R > 0 at target distance AND R > threshold_bps
Level 5: plob_margin       — R > C_PLOB × safety_margin (e.g., 2×)
```

Final decision: GO if all 5 levels pass (or waived); HOLD otherwise.

### 4.5 Certificate Schema

The signed certificate is a JSON document:
```json
{
  "schema_version": "0.1",
  "kind": "pic.qkd_certificate",
  "run_id": "<hex>",
  "generated_at": "<ISO-8601>",
  "pic": {
    "graph_hash": "<sha256>",
    "pdk": "aim_photonics_300nm_sin",
    "drc_status": "pass",
    "lvs_status": "pass",
    "insertion_loss_db": 1.84,
    "eta_chip": 0.654,
    "wavelength_nm": 1550.0
  },
  "qkd": {
    "protocol": "BB84_decoy",
    "target_distance_km": 50.0,
    "key_rate_bps": 12400,
    "qber_percent": 3.1,
    "plob_margin": 4.2,
    "sweep_distances_km": [10, 20, 30, 40, 50],
    "sweep_key_rates_bps": [280000, 89000, 28000, 8800, 12400]
  },
  "signoff": {
    "decision": "GO",
    "ladder": [ ... ]
  },
  "signature": {
    "algorithm": "Ed25519",
    "public_key_pem": "...",
    "signature_b64": "..."
  },
  "provenance": {
    "photonstrust_version": "0.1.0",
    "python": "3.11.4",
    "platform": "..."
  }
}
```

The entire JSON body (excluding the `signature` field) is serialised
canonically (sorted keys, no trailing whitespace) and signed with Ed25519.

---

## 5. Method Design

### 5.1 Pipeline Orchestrator (`pipeline/certify.py`)

```python
def run_certify(
    graph_path: Path,
    *,
    pdk_name: str = "generic_silicon_photonics",
    protocol: str = "BB84_decoy",
    distance_km_list: list[float] | None = None,
    target_distance_km: float = 50.0,
    wavelength_nm: float = 1550.0,
    signing_key_path: Path | None = None,
    output_dir: Path,
) -> dict:
    """Orchestrate the full design-to-certificate pipeline."""

    # Step 1: Load graph and compile
    graph = json.loads(graph_path.read_text())
    compiled = compile_graph(graph, require_schema=True)

    # Step 2: DRC check against PDK
    pdk = get_pdk(pdk_name)
    drc_report = run_graph_drc(compiled, pdk=pdk)
    if drc_report["error_count"] > 0:
        return _hold_report("drc_failed", drc_report)

    # Step 3: LVS-lite
    lvs_report = run_lvs_lite(graph, compiled)
    if not lvs_report["pass"]:
        return _hold_report("lvs_failed", lvs_report)

    # Step 4: S-parameter simulation
    sim_result = simulate_pic_netlist(
        compiled.compiled,
        wavelength_nm=wavelength_nm,
    )

    # Step 5: Extract η_chip from simulation
    eta_chip = _extract_eta_chip(sim_result, wavelength_nm=wavelength_nm)
    eta_coupler = _pdk_coupler_efficiency(pdk)

    # Step 6: Build QKD scenario with PIC-bridged params
    scenario = _build_qkd_scenario(
        protocol=protocol,
        eta_chip=eta_chip,
        eta_coupler=eta_coupler,
        pdk=pdk,
    )

    # Step 7: QKD sweep
    if distance_km_list is None:
        distance_km_list = [10, 20, 30, 40, 50, 75, 100]
    sweep = compute_sweep(scenario, distance_km_list)

    # Step 8: Signoff ladder
    assembly_report = assemble_pic_chip({"graph": graph})["report"]
    ladder = build_pic_signoff_ladder({
        "assembly_report": assembly_report,
        "drc_report": drc_report,
        "lvs_report": lvs_report,
        "qkd_sweep": sweep,
        "policy": {"target_distance_km": target_distance_km},
    })

    # Step 9: Build + sign certificate
    certificate = _build_certificate(
        graph=graph, pdk=pdk, drc_report=drc_report,
        lvs_report=lvs_report, eta_chip=eta_chip,
        sweep=sweep, ladder=ladder,
        wavelength_nm=wavelength_nm,
    )
    if signing_key_path is not None:
        certificate = sign_certificate(certificate, signing_key_path)

    # Write outputs
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "certificate.json").write_text(
        json.dumps(certificate, indent=2, sort_keys=True)
    )
    return certificate
```

### 5.2 η_chip Extraction Logic

```python
def _extract_eta_chip(sim_result: dict, wavelength_nm: float) -> float:
    """Extract chip insertion loss transmittance from simulation output."""
    # Try DAG solver output first (general circuits)
    dag = sim_result.get("dag") or {}
    output_powers = dag.get("output_powers") or {}
    if output_powers:
        # Sum all output port powers (normalised to unit input)
        total_out = sum(float(v) for v in output_powers.values())
        return min(1.0, max(0.0, total_out))

    # Fallback: chain solver total_loss_db
    chain = sim_result.get("chain") or {}
    total_loss_db = chain.get("total_loss_db")
    if total_loss_db is not None:
        return 10 ** (-float(total_loss_db) / 10.0)

    # Last resort: 1.0 (lossless — conservative, forces user to add real components)
    return 1.0
```

### 5.3 CLI Integration

Add `certify` subcommand to `photonstrust/cli.py`:

```
photonstrust certify <graph.json> [options]

Options:
  --pdk TEXT             PDK name or path to PDK manifest JSON [generic_silicon_photonics]
  --protocol TEXT        QKD protocol [BB84_decoy]
  --wavelength FLOAT     Operating wavelength in nm [1550.0]
  --target-distance FLOAT  Target QKD distance in km [50.0]
  --distances TEXT       Comma-separated distance sweep values in km
  --signing-key PATH     Path to Ed25519 private key PEM for signing
  --output PATH          Output directory [results/certify/<run_id>]
  --dry-run              Run DRC+LVS only, skip simulation and signing
  --require-go           Exit non-zero if final decision is HOLD
```

### 5.4 Reference Design for Demo

Create `graphs/demo_qkd_transmitter.json`:
A simple QKD transmitter PIC graph containing:
- 1 × input grating coupler
- 1 × MZI intensity modulator (for pulse shaping)
- 1 × variable attenuator (for mean-photon-number control)
- 1 × 50:50 directional coupler (for BB84 basis choice)
- 1 × phase modulator (for basis encoding)
- 2 × output grating couplers (Z-basis and X-basis outputs)
- 2 × waveguide delay lines (path length equalisation)

This design, when certified, should produce:
- DRC: all PASS (designed within AIM 300nm SiN design rules)
- LVS-lite: PASS
- η_chip ≈ 0.50 (−3 dB total on-chip loss for a realistic MZI-based transmitter)
- Key rate: > 10 kbps at 20 km with SNSPD detector
- Signoff decision: GO

---

## 6. Experimental Design

### 6.1 Validation Tests

**Unit tests:**

| Test | What it verifies |
|------|-----------------|
| `test_eta_chip_extraction_chain_solver` | Extracts η_chip from chain solver output |
| `test_eta_chip_extraction_dag_solver` | Extracts η_chip from DAG solver output |
| `test_drc_min_width_violation` | DRC correctly flags width < min_waveguide_width_um |
| `test_drc_min_gap_violation` | DRC correctly flags gap < min_waveguide_gap_um |
| `test_drc_all_pass_clean_graph` | DRC returns 0 errors for compliant netlist |
| `test_lvs_lite_block_count_mismatch` | L1 check catches extra block in netlist |
| `test_lvs_lite_connection_mismatch` | L3 check catches swapped port |
| `test_certify_dry_run_exits_zero` | Dry-run pipeline returns dict with no exceptions |
| `test_certify_full_pipeline_go_decision` | Reference design produces GO decision |
| `test_certificate_signature_verify` | Ed25519 signature on certificate is valid |

**Integration test:**

Run the full certify pipeline on `demo_qkd_transmitter.json` with the generic
PDK and BB84_decoy protocol. Assert:
- Certificate JSON is well-formed and schema-valid
- `signoff.decision == "GO"`
- `qkd.key_rate_bps > 0` at `target_distance_km`
- Signature verifies against the public key

**Regression test:**

Lock the certificate `run_id` (hash of inputs) for `demo_qkd_transmitter.json`.
On any code change, the run_id must remain identical (determinism guarantee).

### 6.2 Metrics

| Metric | Target |
|--------|--------|
| Full pipeline wall time | < 10 seconds on standard laptop |
| DRC check time | < 100 ms for graphs up to 100 components |
| LVS-lite check time | < 50 ms |
| S-parameter simulation | < 5 seconds (JAX chain solver, 7 wavelength points) |
| QKD sweep (7 distances) | < 2 seconds |

---

## 7. Risk and Failure Analysis

**Risk R1: JAX not installed in test environment**
The PIC simulator uses JAX. JAX is in `optional-dependencies.pic`.
Mitigation: Certify pipeline must gracefully degrade — if JAX is not available,
skip simulation step and emit `"simulation": "unavailable"` in the certificate.
DRC, LVS-lite, and QKD sweep remain operational without JAX.

**Risk R2: Graph has no output port (no optical output)**
If the graph has only input ports (e.g., just a detector PIC), η_chip extraction
will fail. Mitigation: `_extract_eta_chip` returns 1.0 with a warning if no
output power is found; document in certificate notes.

**Risk R3: QKD sweep returns all-zero key rates**
For a very lossy chip (η_chip < 0.01), the QKD key rate is zero at all distances.
Mitigation: pipeline reports HOLD at signoff Level 4; certificate still produced
with `decision: HOLD` and diagnostic pointing to `pic.insertion_loss_db` as the
limiting factor. This is the correct behaviour — it tells the designer what to fix.

**Risk R4: Signing key not provided**
Unsigned certificates are valid for development. For production/submission use,
the `--signing-key` flag is mandatory and the CI gate should enforce it.
Mitigation: add `--require-signed` flag that exits non-zero if no signature present.

---

## 8. Reproducibility Package

- Reference design: `graphs/demo_qkd_transmitter.json` (committed to repo)
- Reference certificate: `results/certify/reference/certificate.json` (committed)
- Reference public key: `results/certify/reference/public_key.pem` (committed)
- Script: `scripts/run_certify_demo.py`
- CI: `photonstrust certify graphs/demo_qkd_transmitter.json --dry-run` in CV workflow
- Notebook: `examples/Design_to_Certificate.ipynb` (open in Colab link)

---

## 9. Acceptance Criteria

**Scientific correctness:**
- [ ] η_chip derived from S-parameter sim is consistent with sum of component ILs
- [ ] QKD key rate at η_source_total = η_chip × η_nominal matches manual calculation
- [ ] PLOB bound is never violated in certify output

**Engineering correctness:**
- [ ] All unit tests pass
- [ ] Integration test: reference design produces GO in < 10s
- [ ] Regression test: run_id stable across commits
- [ ] CLI: `photonstrust certify --help` works
- [ ] Certificate schema validates against JSON schema

**Product/reporting:**
- [ ] Certificate JSON is human-readable and self-describing
- [ ] Dry-run mode exits 0 and produces a partial report
- [ ] `--require-go` mode exits non-zero on HOLD (for CI gating)
- [ ] Demo notebook runs end-to-end on Google Colab without local install

---

## 10. Decision

Proceed. M1 depends on M3 only for the arxiv preprint content, not technically.
M1 can be built in parallel with M3 arxiv writing. Estimated effort: 3 weeks.

---

## Implementation Plan

### Step 1: Graph-level DRC engine
- New file: `photonstrust/pic/drc.py`
- Functions: `run_graph_drc(netlist, pdk)` → `{"error_count", "warning_count", "items"}`
- Tests: `tests/pic/test_drc.py`

### Step 2: LVS-lite
- New file: `photonstrust/pic/lvs_lite.py`
- Functions: `run_lvs_lite(graph, compiled_netlist)` → `{"pass", "checks"}`
- Tests: `tests/pic/test_lvs_lite.py`

### Step 3: PIC-to-QKD bridge
- New file: `photonstrust/pipeline/pic_qkd_bridge.py`
- Functions: `extract_eta_chip(sim_result, wavelength_nm)`,
  `build_qkd_scenario_from_pic(eta_chip, eta_coupler, pdk, protocol, ...)`
- Tests: `tests/pipeline/test_pic_qkd_bridge.py`

### Step 4: Certificate schema
- New file: `schemas/pic_qkd_certificate.json`
- New function: `photonstrust/workflow/schema.py:pic_qkd_certificate_schema_path()`

### Step 5: Pipeline orchestrator
- New file: `photonstrust/pipeline/certify.py`
- Function: `run_certify(graph_path, *, pdk_name, protocol, ...)` → `dict`
- Tests: `tests/pipeline/test_certify.py`

### Step 6: CLI integration
- Edit: `photonstrust/cli.py` — add `certify` subcommand
- Edit: `pyproject.toml` — no changes needed (certify is a subcommand)

### Step 7: Reference design + demo
- New file: `graphs/demo_qkd_transmitter.json`
- New file: `scripts/run_certify_demo.py`
- New file: `examples/Design_to_Certificate.ipynb`

### Step 8: Extended signoff ladder (5 levels)
- Edit: `photonstrust/pic/signoff.py` — add Levels 2–5
- Tests: `tests/pic/test_signoff.py` — extend existing tests
