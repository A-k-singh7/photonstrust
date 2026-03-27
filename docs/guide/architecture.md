# Architecture

An overview of the PhotonTrust module organization, simulation pipeline, and
extension points.

---

## Module Organization

```
photonstrust/
├── easy.py                  # High-level API (start here!)
├── gallery.py               # 15 pre-built scenarios
├── visualize.py             # 12 plot functions
├── errors.py                # Smart error classes with suggestions
├── presets.py               # Band and detector preset tables
├── config.py                # Config loading, defaults, schema migration
├── validation.py            # Config validation and distance expansion
├── qkd.py                   # Core QKD engine (compute_sweep, compute_point)
├── qkd_types.py             # QKDResult dataclass
├── qkd_protocols/           # 9 protocol implementations
│   ├── registry.py          # Protocol dispatch and applicability checks
│   ├── common.py            # Protocol name normalization
│   ├── base.py              # QKDProtocolModule base, ProtocolApplicability
│   ├── bb84_decoy.py        # BB84 with decoy states
│   ├── bbm92.py             # BBM92 / E91 entanglement-based
│   ├── cv_qkd.py            # Continuous-variable (GG02)
│   ├── mdi_qkd.py           # Measurement-device-independent
│   ├── amdi_qkd.py          # Asynchronous MDI (mode-pairing)
│   ├── pm_qkd.py            # Phase-matching (also serves TF-QKD)
│   ├── sns_tf_qkd.py        # Sending-or-not-sending TF
│   ├── di_qkd.py            # Device-independent
│   ├── finite_key.py        # Finite-key analysis
│   └── pe_bounds.py         # Parameter estimation bounds
├── components/pic/          # PIC component models
│   ├── library.py           # Component registry
│   ├── mmi.py               # MMI couplers
│   ├── mzm.py               # Mach-Zehnder modulators
│   ├── awg.py               # Arrayed waveguide gratings
│   ├── ssc.py               # Spot-size converters
│   ├── y_branch.py          # Y-branch splitters
│   ├── crossing.py          # Waveguide crossings
│   ├── heater.py            # Thermo-optic heaters
│   ├── photodetector.py     # On-chip photodetectors
│   ├── crosstalk.py         # Parallel waveguide crosstalk model
│   └── compact_model.py     # Compact model framework
├── network/                 # Multi-node QKD network optimization
│   ├── types.py             # NetworkNode, NetworkLink, NetworkTopology
│   ├── routing.py           # Path computation (max-key-rate, shortest)
│   ├── max_flow.py          # Edmonds-Karp max-flow algorithm
│   ├── constrained_routing.py  # Constrained path optimization
│   ├── key_relay.py         # Trusted-node XOR key relay
│   ├── trusted_node.py      # Trusted-node management
│   ├── repeater_chain.py    # Quantum repeater chain modeling
│   ├── purification.py      # Entanglement purification
│   └── simulator.py         # Network-level simulation
├── orbit/                   # Satellite QKD scheduling
│   ├── constellation.py     # Walker-delta constellation generator
│   ├── scheduler.py         # Greedy pass scheduling and key volume
│   ├── weather.py           # Clear-sky probability models
│   ├── geometry.py          # Orbital geometry calculations
│   ├── pass_envelope.py     # Pass envelope computation
│   ├── diagnostics.py       # Orbit diagnostic tools
│   └── provider_manager.py  # External orbit-propagator integration
├── channels/                # Channel models
│   └── coexistence.py       # Classical/quantum WDM coexistence noise
├── calibrate/               # Detector, source, and channel calibration
│   ├── priors.py            # Bayesian prior definitions
│   └── pic_crosstalk.py     # PIC crosstalk calibration
├── reporting/               # Report generation
│   └── html_report.py       # Self-contained HTML report builder
├── interop/                 # External tool integration
│   └── ...                  # gdsfactory import/export
├── pic/                     # PIC-level tools
│   ├── drc.py               # Graph-level design rule checks
│   └── layout/              # Layout extraction and analysis
├── cli.py                   # Command-line interface
├── cli_helpers.py           # CLI formatting and display helpers
├── sdk.py                   # Low-level scripting API
├── sweep.py                 # Multi-scenario sweep runner
├── comparison.py            # Heralding comparison tools
├── repeater.py              # Repeater optimization
└── plots.py                 # Legacy plot functions
```

---

## Simulation Pipeline

When you call a high-level function like `simulate_qkd_link`, the following
steps occur:

```
1. User calls easy.simulate_qkd_link(protocol="bb84", distance_km=50)
       │
2. _expand_distances() normalizes the distance specification
   (float -> auto-sweep, list -> as-is, dict -> range expansion)
       │
3. _build_scenario() assembles a full scenario dict:
   ├── config.apply_source_defaults()      (emitter_cavity or SPDC)
   ├── config.apply_channel_defaults()     (fiber, free_space, satellite)
   ├── config.apply_detector_defaults()    (si_apd, ingaas, snspd)
   ├── config.apply_timing_defaults()      (sync drift)
   ├── config.resolve_band_wavelength()    (band preset -> wavelength)
   └── protocol-specific defaults          (mu, nu, phase_slices)
       │
4. qkd.compute_sweep(scenario) iterates over each distance:
   ├── registry.dispatch(protocol_name) -> protocol module
   ├── protocol.applicability_fn(scenario) -> pass/fail check
   └── protocol.evaluator(scenario, distance_km) -> QKDResult
       │
5. Results are wrapped in QKDLinkResult (or ProtocolComparison, etc.)
   with summary(), plot(), as_dict(), and other convenience methods.
```

### Scenario structure

The internal scenario dict has this shape:

```python
{
    "schema_version": "0.1",
    "band": "c_1550",
    "wavelength_nm": 1550,
    "distances_km": [0, 5, 10, ...],
    "source": { "type": "emitter_cavity", "rep_rate_mhz": 100, ... },
    "channel": { "model": "fiber", "fiber_loss_db_per_km": 0.20, ... },
    "detector": { "class": "snspd", "pde": 0.35, ... },
    "timing": { "sync_drift_ps_rms": 10 },
    "protocol": { "name": "bb84_decoy", ... },
    "finite_key": {},
    "uncertainty": { "seed": 42 },
}
```

---

## Extension Points

### Adding a new QKD protocol

1. Create a module in `qkd_protocols/` (e.g., `my_protocol.py`).
2. Implement a function with signature:
   ```python
   def compute_point_my_protocol(
       scenario: dict, distance_km: float, runtime_overrides: dict | None
   ) -> QKDResult:
   ```
3. Register it in `qkd_protocols/registry.py` by adding an entry to the
   `_PROTOCOLS` dict with a `QKDProtocolModule` instance.

### Adding a PIC component

1. Create a module in `components/pic/` (e.g., `my_component.py`).
2. Implement the component's S-parameter or transfer-matrix model.
3. Register it in `components/pic/library.py`.

### Adding a PDK

1. Create a JSON manifest in `configs/pdks/` with design rules and component
   parameter bounds.
2. Reference it by name in `design_pic(pdk="my_pdk")`.

### Adding a gallery scenario

1. Add a `ScenarioMeta` entry to the `_SCENARIOS` tuple in `gallery.py`.
2. Set the `runner` field to the appropriate `easy.py` function name.
3. Provide a `config` dict with the kwargs for that function.
