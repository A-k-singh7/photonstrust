# Research Report: gdsfactory Interop, Compact Models, Tapeout Flows, and Simulation Enhancements

Date: 2026-03-25
Related modules: `photonstrust.pic`, `photonstrust.components.pic`, `photonstrust.spice`,
`photonstrust.layout.pic`, `photonstrust.verification`

---

## Table of Contents

1. [Topic 1: gdsfactory Interop](#topic-1-gdsfactory-interop)
2. [Topic 2: Compact Models and S-Parameters](#topic-2-compact-models-and-s-parameters)
3. [Topic 3: Advanced Tapeout Flow](#topic-3-advanced-tapeout-flow)
4. [Topic 4: Simulation Engine Enhancements](#topic-4-simulation-engine-enhancements)

---

## Topic 1: gdsfactory Interop

### 1.1 Core API: Component, ComponentReference, Port, cross_sections

gdsfactory (https://github.com/gdsfactory/gdsfactory) is a Python library for
designing photonic, analog, quantum, and MEMS chips. Its architecture centers on
four core abstractions:

#### Component

The `Component` class is the fundamental canvas object. It stores polygons,
instances (references to other components), and ports. Key methods:

```python
import gdsfactory as gf

c = gf.Component("my_component")

# Add geometry
c.add_polygon([(0, 0), (10, 0), (10, 5), (0, 5)], layer=(1, 0))

# Add ports for connectivity
c.add_port(
    name="o1",
    center=(0, 2.5),
    width=0.5,
    orientation=180,
    layer=(1, 0),
    port_type="optical",
)

# Add instances of other components
ref = c.add_ref(gf.components.straight(length=10))

# Export
c.write_gds("output.gds")
c.write_oas("output.oas")  # OASIS format

# Query
c.ports          # dict of Port objects
c.settings       # construction parameters
c.info           # derived properties dict
c.bbox()         # bounding box (function in v8+)
c.get_netlist()  # extract circuit netlist
```

A `Component` can return ports by type (optical, electrical), return its netlist
for circuit simulation, and show itself in KLayout, matplotlib, or 3D.

#### Port

A Port defines an interface point on a component with these attributes:

| Attribute     | Description                                       |
|---------------|---------------------------------------------------|
| `name`        | Identifier string (e.g., "o1", "o2", "e1")       |
| `center`      | (x, y) position in microns                        |
| `width`       | Port width in microns                             |
| `orientation` | Direction in degrees (0, 90, 180, 270 for Manhattan) |
| `layer`       | GDS layer tuple (layer_number, datatype)          |
| `port_type`   | "optical", "electrical", "placement"              |

Port naming conventions are defined by cross-sections:
- `cross_section.strip` assigns `o1` (input), `o2` (output) for optical
- `cross_section.metal1` assigns `e1`, `e2` for electrical

In gdsfactory v8+, ports are stored in the GDS file directly (no separate
sidecar file). Port positions are snapped to grid in database units (DBU,
default 1 nm).

Filtering ports: `component.ports.filter(orientation=90)` returns only ports
with a specific orientation.

#### ComponentReference (Instance)

A `ComponentReference` places an instance of one Component inside another, with
position, rotation, and mirror transforms. In v8+, the term "Instance" is
preferred.

```python
ref = parent.add_ref(child_component)
ref.move((10, 20))
ref.rotate(90)
ref.mirror_x(port_name="o1")
```

Key changes in v8: `Reference` no longer has `get_ports_list()`; use
`ref.ports.filter(...)` instead.

#### CrossSection

A `CrossSection` defines the waveguide or routing profile (width, layer, cladding,
offsets). It is specified as a `CrossSectionSpec` -- a string name, a
`CrossSection` object, a factory function, or a dict.

```python
xs = gf.cross_section.strip(width=0.5, layer=(1, 0))
c = gf.components.straight(length=10, cross_section=xs)
```

### 1.2 Parameterized Components (PCells)

Components in gdsfactory are created by Python functions decorated with `@gf.cell`:

```python
@gf.cell
def my_coupler(gap: float = 0.2, length: float = 10.0) -> gf.Component:
    c = gf.Component()
    # ... build geometry using gap and length ...
    return c

# Calling the function returns a Component with those settings cached
coupler = my_coupler(gap=0.3, length=15.0)
coupler.settings  # {"gap": 0.3, "length": 15.0}
```

The `@gf.cell` decorator:
- Caches Components by their arguments (deterministic naming)
- Stores construction `settings` for traceability
- Enables netlisting and simulation from the same parameterization

### 1.3 Netlist Representation

gdsfactory provides `get_netlist()` to extract a circuit netlist from layout
connectivity. The netlist is a YAML-serializable dictionary with these top-level
keys:

```yaml
instances:
  mzi_1:
    component: mzi
    settings:
      delta_length: 10.0
  bend_1:
    component: bend_euler
    settings:
      radius: 10.0

connections:
  mzi_1,o2: bend_1,o1

ports:
  o1: mzi_1,o1
  o2: bend_1,o2

placements:
  mzi_1:
    x: 0
    y: 0
    rotation: 0
    mirror: false
  bend_1:
    x: 100
    y: 0
```

**Key sections:**
- `instances`: maps instance names to component specs + settings
- `connections`: pairs of `instance,port` strings indicating connected ports
- `ports`: top-level ports exposed by the composite component
- `placements`: x, y, rotation, mirror for each instance

**`get_netlist()` parameters:**
- `on_multi_connect`: "ignore" | "warn" | "error" for >2 overlapping ports
- `on_dangling_port`: "ignore" | "warn" | "error" for unconnected ports
- `instance_namer`: callable for naming instances (default: SmartNamer)
- `component_namer`: callable for naming component types (default: function_namer)
- `port_matcher`: callable to determine if two ports are connected

Two ports are considered connected when they have matching width, x, y, and
layer at the same position.

**Round-tripping:** A component can be rebuilt from its netlist YAML using
`gf.read.from_yaml()`, enabling netlist-driven layout.

### 1.4 Importing a gdsfactory Component and Extracting Data

```python
import gdsfactory as gf

c = gf.components.mzi(delta_length=10)

# Port names, positions, orientations
for port in c.ports:
    print(f"{port.name}: center={port.center}, width={port.width}, "
          f"orientation={port.orientation}, layer={port.layer}")

# Layer information
layers_used = c.layers  # set of (layer, datatype) tuples

# Instance hierarchy
for inst_name, inst in c.insts.items():  # v8+ API
    print(f"{inst_name}: component={inst.cell.name}")

# Settings and parameters
print(c.settings)  # {"delta_length": 10.0, ...}
print(c.info)      # derived properties

# Netlist extraction
netlist = c.get_netlist()
# netlist["instances"], netlist["connections"], netlist["ports"]
```

**Extracting polygon data:**
```python
# v8+: get_polygons_points() returns polygon vertices
polygons = c.get_polygons_points(layer=(1, 0))
# Returns list of Nx2 numpy arrays (polygon vertices)
```

### 1.5 Exporting to gdsfactory

```python
import gdsfactory as gf
import numpy as np

c = gf.Component("from_external")

# Add polygons from external data (e.g., simulation result)
vertices = np.array([(0, 0), (10, 0), (10, 5), (0, 5)])
c.add_polygon(vertices, layer=(1, 0))

# Add ports
c.add_port(name="o1", center=(0, 2.5), width=0.5,
           orientation=180, layer=(1, 0))
c.add_port(name="o2", center=(10, 2.5), width=0.5,
           orientation=0, layer=(1, 0))

# Add references to existing library components
straight = gf.components.straight(length=5)
ref = c.add_ref(straight)
ref.connect("o1", c.ports["o2"])

# Write output
c.write_gds("exported.gds")
```

**Array references:**
```python
ref = c.add_ref(child, columns=4, rows=2,
                column_pitch=100, row_pitch=50)
```

### 1.6 PDK Integration

A PDK in gdsfactory bundles three registries:

| Registry          | Contents                                    |
|-------------------|---------------------------------------------|
| `pdk.cells`       | Parameterized cell functions (ComponentSpec) |
| `pdk.cross_sections` | CrossSection factory functions           |
| `pdk.layers`      | LayerMap mapping names to (layer, datatype)  |

**Registration and activation:**
```python
from gdsfactory.pdk import Pdk

pdk = Pdk(
    name="my_foundry",
    cells={"straight": my_straight, "bend": my_bend},
    cross_sections={"strip": my_strip_xs},
    layers=LAYER,  # LayerMap class
)
pdk.activate()

# After activation, strings resolve to registered items:
c = gf.get_component("straight", length=10)
xs = gf.get_cross_section("strip")
layer = gf.get_layer("WG")  # returns (1, 0) tuple
```

### 1.7 Key gdsfactory PDKs

| PDK Package  | Foundry/Platform | Install | Notes |
|-------------|------------------|---------|-------|
| `gdsfactory.components` | Generic (no real foundry) | Built-in | Reference library, ~200+ components |
| `cspdk`     | CORNERSTONE Photonics | `pip install cspdk` | Open/public PDK, active development |
| `ubcpdk`    | SiEPIC EBeam (UBC) | `pip install ubcpdk` | Adapted from SiEPIC EBeam PDK |
| `skywater130` | SkyWater 130nm | `git clone gdsfactory/skywater130` | Primarily electronic, some photonic |
| `gf180mcu`  | GlobalFoundries 180nm | `git clone gdsfactory/gf180mcu` | Electronic PDK with gdsfactory |
| `vtt`       | VTT 3 um SOI | `git clone gdsfactory/vtt` | Thick SOI photonics |

GDSFactory+ (commercial) supports 26+ foundry PDKs including AMF, CompoundTek,
GlobalFoundries, Tower/Jazz, IMEC, and Ligentec.

### 1.8 Version Compatibility: gdsfactory 7.x vs 8.x/9.x

| Feature | v7 | v8+ |
|---------|-----|------|
| Ports in GDS | Stored in separate YAML | Stored in GDS file directly |
| Port units | Microns (float) | DBU (1nm default, integer snapped) |
| `get_polygons()` | Returns polygon edges | Renamed to `get_polygons_points()` |
| `ComponentReference` | Primary API | Replaced by `Instance` concept |
| `get_ports_list()` | Available on Reference | Removed; use `ports.filter()` |
| `bbox`, `dbbox` | Properties | Functions (must call `c.bbox()`) |
| Routing functions | Return route instances | Place instances in Component; must pass Component as first argument |
| DRC/connectivity | External | Built-in DRC, dummy fill, connectivity checks |

**Migration path:** gdsfactory provides a migration notebook
(`21_migration_guide_7_8.ipynb`). The current stable version is 9.x.

---

## Topic 2: Compact Models and S-Parameters

### 2.1 Touchstone Format (.sNp)

The Touchstone format is the de facto standard for storing N-port network
parameter data. Files use extension `.sNp` where N is the port count.

#### Option Line Format

```
# <frequency_unit> <parameter> <format> R <impedance>
```

| Field | Options | Default |
|-------|---------|---------|
| frequency_unit | Hz, kHz, MHz, GHz | GHz |
| parameter | S, Y, Z, G, H | S |
| format | MA (magnitude/angle), DB (dB/angle), RI (real/imaginary) | MA |
| impedance | Reference impedance in ohms | 50 |

Example: `# GHz S MA R 50`

#### Data Format by Port Count

**1-port (.s1p):**
```
! Comment line
# GHz S MA R 50
1.0   0.95   -15.3    ! freq  |S11|  ang(S11)
```

**2-port (.s2p):** Each line has 9 columns:
```
freq  S11_x  S11_y  S21_x  S21_y  S12_x  S12_y  S22_x  S22_y
```

**4-port (.s4p):** S-matrix written row-wise, 4 rows of 4 complex values per
frequency point (may span multiple lines).

#### Photonics Extensions

Ansys Lumerical extends Touchstone with optional group delay columns for optical
S-parameters. The Optical N-Port S-Parameter element supports single-mode with
arbitrary physical port count.

#### Version 2.0/2.1 Additions

Touchstone 2.0 (IBIS standard) adds:
- `[Version] 2.0` header
- `[Number of Ports]` explicit declaration
- `[Number of Frequencies]` count
- `[Network Data]` / `[End]` markers
- Mixed-mode S-parameter support
- `[Reference]` block for per-port impedance

Specification documents:
- https://ibis.org/touchstone_ver2.0/touchstone_ver2_0.pdf
- https://ibis.org/touchstone_ver2.1/touchstone_ver2_1.pdf

### 2.2 Python Libraries for S-Parameter Handling

#### scikit-rf (skrf)

The primary Python library for RF/microwave network analysis. Central object:
`skrf.Network`.

```python
import skrf as rf

# Load from Touchstone
ntwk = rf.Network("device.s2p")

# Access S-parameters
ntwk.s          # shape (n_freq, n_ports, n_ports), complex
ntwk.f          # frequency array in Hz
ntwk.z0         # reference impedance array

# Interpolation to new frequency grid
new_freq = rf.Frequency(1, 2, 1001, unit="GHz")
ntwk_interp = ntwk.interpolate(new_freq, kind="cubic", coords="polar")
# coords: "cart" (Re/Im) or "polar" (unwrapped phase/mag)

# Cascading 2-port networks
result = ntwk1 ** ntwk2 ** ntwk3

# Arbitrary N-port connections (sub-network growth)
combined = rf.connect(ntwk_a, port_a, ntwk_b, port_b)

# Write Touchstone
ntwk.write_touchstone("output.s2p")

# Plot
ntwk.plot_s_db()
ntwk.plot_s_smith()
```

**S-matrix construction from scratch:**
```python
import numpy as np

freq = rf.Frequency(190, 196, 601, unit="THz")  # optical C-band
s = np.zeros((len(freq), 2, 2), dtype=complex)

# Fill with model data
kappa = 0.3  # coupling coefficient
tau = np.sqrt(1 - kappa**2)  # through transmission
s[:, 0, 0] = tau    # S11 = through
s[:, 0, 1] = 1j * np.sqrt(kappa**2)  # S12 = cross
s[:, 1, 0] = 1j * np.sqrt(kappa**2)  # S21 = cross
s[:, 1, 1] = tau    # S22 = through

ntwk = rf.Network(frequency=freq, s=s, z0=1)  # z0=1 for optical
```

**Key features:**
- `Network.resample()`: match frequency grids before cascading
- `Network.stitch()`: concatenate networks along frequency axis
- `NetworkSet`: manage parameter sweeps, statistical analysis
- `Network.extrapolate_to_dc()`: extend measurements to DC

#### SAX (S + Autograd + XLA)

A JAX-based photonic circuit simulator from the gdsfactory ecosystem.

```python
import sax
import jax.numpy as jnp

# Models are plain Python functions returning SDicts
def coupler(coupling: float = 0.5, wl: float = 1.55):
    kappa = coupling**0.5
    tau = (1 - coupling)**0.5
    return {
        ("in0", "out0"): tau,
        ("in0", "out1"): 1j * kappa,
        ("in1", "out0"): 1j * kappa,
        ("in1", "out1"): tau,
    }

# Circuit defined as netlist dict
circuit, info = sax.circuit(
    netlist={
        "instances": {
            "lft": "coupler",
            "top": "straight",
            "rgt": "coupler",
        },
        "connections": {
            "lft,out0": "top,in0",
            "top,out0": "rgt,in0",
        },
        "ports": {
            "in0": "lft,in0",
            "in1": "lft,in1",
            "out0": "rgt,out0",
            "out1": "rgt,out1",
        },
    },
    models={"coupler": coupler, "straight": straight_model},
)

# Evaluate (supports JAX autodiff for optimization)
S = circuit(wl=1.55)
```

**Key properties:**
- SDict: `Dict[Tuple[str, str], complex | Array]` mapping port pairs to S-params
- Full JAX autodiff support for gradient-based optimization
- Direct interop with gdsfactory netlists via gplugins
- No special data structures -- pure functions and dicts

#### Simphony

A SPICE-like photonic circuit simulator from BYU CamachoLab.

```python
from simphony.library import siepic
from simphony import Simulator

gc = siepic.GratingCoupler()
wg = siepic.Waveguide(length=100e-6)
dc = siepic.DirectionalCoupler(gap=200e-9, coupling_length=10e-6)

# Connect components
gc["pin2"].connect(wg["pin1"])
wg["pin2"].connect(dc["pin1"])

# Simulate
sim = Simulator()
sim.multiconnect(gc, wg, dc)
result = sim.simulate()
```

**Model libraries included:**
- `siepic`: SiEPIC EBeam PDK models
- `sipann`: SiPANN (neural-network-based compact models from BYU)
- Layout-aware Monte Carlo simulation for yield estimation

### 2.3 SPICE Compact Models for Photonics

#### Lumerical CML (Compact Model Library)

Ansys Lumerical's CML Compiler automates creation of compact model libraries from
a single data source (measurements, 2D/3D simulations, or both):

- Input formats: JSON, .mat (MATLAB), CSV measurement data
- Output: INTERCONNECT CML and/or photonic Verilog-A models
- Data schema defines component types: waveguide, directional coupler,
  ring resonator, phase shifter, photodetector, etc.
- Each model includes: S-parameter data, bandwidth, statistical variations

#### Photonic Verilog-A

Lumerical's photonic Verilog-A extends standard Verilog-A to support:
- Multi-mode signal propagation
- Multi-channel (WDM) operation
- Bidirectional optical signals
- Can be simulated in Cadence Spectre for co-simulation

#### Simphony/PICwriter Model Format

Simphony models are Python classes inheriting from a base component class,
exposing S-parameter matrices as numpy arrays indexed by frequency. Models
are defined as transfer matrices or S-matrices evaluated at each wavelength.

### 2.4 Frequency-Dependent Simulation Methods

#### Broadband S-Matrix Assembly

Given component S-matrices at each frequency point, the circuit S-matrix is
assembled by solving the connection equations:

For a circuit with M internal connections, let the total unconnected S-matrix be
S_total (block-diagonal of all component S-matrices). The connected ports are
linked pairwise. The reduced S-matrix of the circuit is:

```
S_circuit = S_aa + S_ab * (I - S_bb)^{-1} * S_ba
```

where subscript `a` denotes external ports and `b` denotes internally connected
ports. This is evaluated at each frequency point independently.

#### Transfer Matrix Method (TMM) for Cascaded 2-Ports

For cascaded 2-port devices, the transfer matrix (ABCD matrix or T-matrix)
approach is efficient:

```
T_total = T_1 * T_2 * T_3 * ... * T_n
```

Conversion between S-parameters and T-parameters:

```
T11 = 1 / S21
T12 = -S22 / S21
T21 = S11 / S21
T22 = (S12 * S21 - S11 * S22) / S21 = det(S) / S21
```

In scikit-rf: `ntwk1 ** ntwk2` performs cascading via T-matrix multiplication.

#### Signal Flow Graph (Mason's Rule)

For general N-port networks, Mason's rule computes the transfer function from
a signal flow graph representation:

```
H = sum_k (G_k * Delta_k) / Delta
```

where:
- G_k is the gain of the k-th forward path
- Delta = 1 - sum(L1) + sum(L2) - sum(L3) + ...
- L1 = individual loop gains, L2 = products of non-touching loop pairs, etc.
- Delta_k = Delta with loops touching path k removed

This is particularly useful for ring resonator analysis where feedback loops
are explicit.

### 2.5 Model Fitting from Measurement Data

#### Ring Resonator Parameter Extraction

A ring resonator's through-port transmission in the all-pass configuration:

```
T(phi) = |t - a * exp(j*phi)|^2 / |1 - t* * a * exp(j*phi)|^2
```

where:
- `t` = self-coupling coefficient (through)
- `a` = single-pass amplitude transmission (round-trip loss = 1 - a^2)
- `phi = beta * L` = round-trip phase (beta = 2*pi*n_eff/lambda, L = circumference)

**Extractable parameters from measured spectrum:**

| Parameter | Extraction Method |
|-----------|-------------------|
| FSR (Free Spectral Range) | Spacing between adjacent resonance dips |
| Extinction Ratio (ER) | Ratio T_max / T_min at resonance |
| FWHM | Full-width at half-maximum of resonance dip |
| Q factor | lambda_res / FWHM |
| Group index n_g | lambda^2 / (FSR * L) |
| Coupling coefficient kappa^2 | From ER and Q via: kappa^2 = 1 - t^2 |
| Round-trip loss a | From ER: a = (T_max^{1/2} - T_min^{1/2}) / (T_max^{1/2} + T_min^{1/2}) (critical coupling assumed) |

#### Lorentzian Lineshape Fitting

Near resonance, the transmission follows an approximate Lorentzian:

```python
import numpy as np
from scipy.optimize import curve_fit

def lorentzian(lam, A, lam0, gamma, offset):
    """Inverted Lorentzian for ring resonator dip."""
    return offset - A / (1 + ((lam - lam0) / gamma)**2)

# Fit to measured data
popt, pcov = curve_fit(lorentzian, wavelengths, transmission,
                       p0=[0.8, 1550e-9, 0.1e-9, 1.0])
A, lam0, gamma, offset = popt
Q = lam0 / (2 * gamma)
```

#### Fano Lineshape

When a resonator couples to a continuum (e.g., multi-mode interference), the
lineshape becomes asymmetric (Fano):

```
T(epsilon) = (epsilon + q)^2 / (epsilon^2 + 1)
```

where `epsilon = 2*(lambda - lambda_res)/FWHM` is the reduced wavelength and
`q` is the Fano asymmetry parameter. Pure Lorentzian corresponds to |q| -> inf.

```python
def fano(lam, A, lam0, gamma, q, offset):
    eps = (lam - lam0) / gamma
    return offset + A * (eps + q)**2 / (eps**2 + 1)
```

---

## Topic 3: Advanced Tapeout Flow

### 3.1 DRC Engines

#### KLayout DRC (Open Source)

KLayout provides a built-in DRC engine with Ruby and Python scripting:

```ruby
# KLayout DRC script (.lydrc)
source("design.gds")

wg = input(1, 0)  # waveguide layer
metal = input(41, 0)

# Minimum width check
wg.width(0.4.um).output("min_width", "Waveguide width < 400nm")

# Minimum spacing
wg.space(0.3.um).output("min_space", "Waveguide spacing < 300nm")

# Enclosure check
metal.enclosing(wg, 1.0.um).output("enclosure", "Metal enclosure < 1um")

# Area check
wg.with_area(0, 0.1.um2).output("min_area", "Small polygon fragment")
```

**gdsfactory integration:**
```python
from gplugins.klayout.drc import write_drc_deck_macro

# Generate KLayout DRC macro from rules
write_drc_deck_macro(
    rules=[
        check_width(layer=(1, 0), min_width=0.4),
        check_space(layer=(1, 0), min_space=0.3),
        check_enclosing(layer1=(41, 0), layer2=(1, 0), min_enclosure=1.0),
        check_area(layer=(1, 0), min_area=0.1),
    ],
    output_path="my_drc.lydrc",
)
```

**Photonics-specific challenges in KLayout DRC:**
- Curved waveguide structures (bends, rings) generate many false errors
  with standard Manhattan-oriented rules
- Complex structures on waveguide layers can cause excessive memory usage
  and multi-hour runtimes
- SiEPIC-Tools (github.com/SiEPIC/SiEPIC-Tools) adds photonic-aware
  verification to KLayout

#### Siemens/Mentor Calibre

Calibre nmDRC is the industry standard for mask-level verification:

- Standard DRC decks flag thousands of false errors on curvilinear photonic shapes
- **Calibre eqDRC** solves this with equation-based rules that perform
  multi-dimensional tolerance checking on curves
- In a benchmark test of a 90-degree optical hybrid: standard deck flagged
  6,420 errors vs. only 15 real errors from the eqDRC deck

Calibre DRC rule deck structure (SVRF format):
```
LAYER WG 1
LAYER CLAD 2

RULE MIN_WG_WIDTH {
    INT WG < 0.4 OPPOSITE REGION
    // Flags regions where waveguide width < 400nm
}

RULE MIN_WG_SPACE {
    EXT WG < 0.3
    // Flags spacing < 300nm between waveguide edges
}
```

#### Synopsys IC Validator

Comparable functionality to Calibre; uses TCL-based rule decks. Relevant for
foundries that standardize on Synopsys flows. Supports hierarchical DRC and
incremental checking.

### 3.2 LVS for Photonics

Photonic LVS differs fundamentally from electronic LVS:

| Aspect | Electronic LVS | Photonic LVS |
|--------|----------------|--------------|
| Device recognition | Layer overlap (e.g., poly + active = transistor) | Recognition layers + text labels; most devices built on single WG layer |
| Connectivity | Geometry touching = electrical connection | Geometry touching may NOT mean optical connection (e.g., crossing waveguides) |
| Interconnect | Wires are ideal (zero delay) | Waveguides are devices (loss, delay, dispersion) |
| Geometry | Manhattan | Curvilinear (bends, tapers, rings) |
| Parameters | Gate length, width (Manhattan measurements) | Path length, bend radius, gap (curvilinear measurements) |

**Photonic LVS workflow:**
1. Device recognition via recognition layers and text labels
2. Basic connectivity extraction using conventional rules
3. Curvilinear property extraction: waveguide width, path length, bend radius
4. Parameter comparison against reference values from source netlist
5. Connectivity validation accounting for optical coupling rules

**Implementation approaches:**
- Calibre nmLVS with photonic extensions
- KLayout + SiEPIC-Tools for open-source LVS
- gdsfactory's `get_netlist()` for connectivity extraction

### 3.3 Parasitic Extraction for Photonic Circuits

#### Waveguide Parasitics

| Parasitic | Physical Origin | Typical Values (SOI) | Extraction Method |
|-----------|----------------|---------------------|-------------------|
| Propagation loss | Sidewall roughness, material absorption | 1-3 dB/cm at 1550nm | Layout path length * loss/cm |
| Group delay | Effective index, waveguide dispersion | n_g ~ 4.2 for strip WG | tau_g = n_g * L / c |
| Group velocity dispersion | Waveguide geometry + material | ~4400 ps/(nm*km) SOI strip | D = -(lambda/c) * d^2n_eff/dlambda^2 |
| Bend loss | Radiation at bends | <0.01 dB/90deg for R>5um | Sum over all bends |
| Crossing loss | Mode overlap at intersections | 0.02-0.2 dB per crossing | Count crossings |

#### Electrical Parasitics

For active devices (modulators, photodetectors, heaters):

| Parasitic | Origin | Typical Values |
|-----------|--------|---------------|
| Pad capacitance | Metal-dielectric-substrate stack | 20-100 fF |
| Routing resistance | Metal trace R = rho*L/(W*t) | 0.1-10 ohm |
| Junction capacitance | PN/PIN junction in modulator | 50-500 fF |
| Heater resistance | Doped silicon or TiN heater | 100-2000 ohm |

### 3.4 SPICE Netlist Generation

#### Mapping PIC Components to SPICE Models

```spice
* Photonic MZI modulator circuit
.subckt MZI_MOD in_opt out_opt ctrl_p ctrl_n

* Optical splitter (behavioral model)
X_split in_opt arm1 arm2 DIRECTIONAL_COUPLER kappa=0.5

* Phase shifter (electro-optic)
X_ps1 arm1 arm1_out PHASE_SHIFTER v_bias=ctrl_p
X_ps2 arm2 arm2_out PHASE_SHIFTER v_bias=ctrl_n

* Combiner
X_comb arm1_out arm2_out out_opt DIRECTIONAL_COUPLER kappa=0.5

.ends MZI_MOD
```

#### Mixed Electrical-Optical Simulation

**Lumerical INTERCONNECT + Cadence Spectre co-simulation:**
- Verilog-A Direct Programming Interface (DPI) synchronizes Spectre and
  INTERCONNECT at each time step
- Electrical domain: Spectre solves circuit equations (driver electronics,
  TIA, amplifiers)
- Optical domain: INTERCONNECT solves photonic circuit (modulator,
  waveguides, photodetector)
- Bidirectional data exchange at modulator (electrical -> phase) and
  photodetector (optical -> current)

**gplugins SPICE extraction:**
```python
from gplugins.klayout import get_netlist, get_l2n

# Extract from GDS
l2n = get_l2n("my_pic.gds")
netlist = get_netlist(l2n)

# Convert to SPICE format (Spectre, NgSpice, Xyce)
# Using vlsir-based parsers in gplugins
```

### 3.5 Tapeout Package Requirements

A complete photonic chip tapeout submission typically includes:

| Deliverable | Format | Contents |
|-------------|--------|----------|
| Layout data | GDSII (.gds) or OASIS (.oas) | Final merged layout, all layers |
| DRC report | Text/HTML/XML | Clean DRC or documented waivers |
| DRC waiver list | Spreadsheet/text | Rule ID, location, justification for each waiver |
| LVS report | Text/HTML | Matched/unmatched device count |
| Design intent | YAML/JSON + schematic | Connectivity, port map, expected behavior |
| Layer map | Table | Mapping of design layers to mask layers |
| Test structure map | GDS + spreadsheet | Location, purpose of each test structure |
| Simulation results | PDF/data files | Expected performance (transmission, bandwidth) |
| Fiber array map | Drawing + coordinates | Optical I/O positions for packaging |

**gdsfactory tapeout flow:**
```python
import gdsfactory as gf
from gplugins.klayout.drc import run_drc

# Design
chip = gf.Component("my_chip")
# ... add instances, routes, ports ...

# Export GDS
chip.write_gds("tapeout/my_chip.gds")

# Run DRC
drc_result = run_drc("tapeout/my_chip.gds", rules="foundry_rules.lydrc")

# Extract netlist
netlist = chip.get_netlist()

# Export settings for test/measurement
chip.write_netlist("tapeout/netlist.yml")
```

---

## Topic 4: Simulation Engine Enhancements

### 4.1 Broadband Simulation

Sweep wavelength across the band of interest and compute the transmission spectrum
at each wavelength point.

**Approach:**
1. Define frequency/wavelength grid (e.g., C-band: 1530-1565 nm, 1000 points)
2. Evaluate each component S-matrix at every wavelength point
3. Assemble circuit S-matrix at each point using sub-network growth
4. Extract port-to-port transmission: `T(lambda) = |S_{out,in}(lambda)|^2`

```python
import numpy as np

wavelengths = np.linspace(1.53e-6, 1.565e-6, 1000)
transmission = np.zeros(len(wavelengths))

for i, wl in enumerate(wavelengths):
    # Get component S-matrices at this wavelength
    s_coupler = coupler_model(wl, kappa=0.1)
    s_waveguide = waveguide_model(wl, length=100e-6, n_eff=2.44, loss_db_m=200)

    # Assemble circuit S-matrix
    s_circuit = assemble_circuit(s_coupler, s_waveguide, connections)

    # Extract transmission
    transmission[i] = np.abs(s_circuit[output_port, input_port])**2
```

**With SAX (vectorized, JAX-accelerated):**
```python
wl = jnp.linspace(1.53, 1.565, 1000)
S = circuit(wl=wl)  # evaluates all wavelengths at once via JAX vectorization
T = jnp.abs(S["out0", "in0"])**2
```

**With scikit-rf:**
```python
freq = rf.Frequency(191.5, 196.0, 1000, unit="THz")
# Each component Network must cover this frequency range
# Interpolate if needed: ntwk.interpolate(freq)
result = ntwk_coupler ** ntwk_waveguide ** ntwk_coupler
transmission_db = result.s_db[:, 1, 0]  # S21 in dB
```

### 4.2 Time-Domain Simulation

For modulated optical signals through a PIC (e.g., data communications):

**Approach 1: Frequency-domain transfer function method**
1. Compute circuit transfer function H(f) from S-parameters
2. FFT the input signal to frequency domain: X(f)
3. Multiply: Y(f) = H(f) * X(f)
4. IFFT to time domain: y(t)

```python
import numpy as np

# Input: modulated optical signal (baseband complex envelope)
dt = 1e-12  # 1 ps time step
t = np.arange(0, 1e-9, dt)
bitrate = 25e9  # 25 Gbps
bits = np.random.randint(0, 2, int(1e-9 * bitrate))
signal = np.repeat(bits, len(t) // len(bits))

# Transfer function from S-parameter sweep
# H(f) = S21(f) of the circuit
f = np.fft.fftfreq(len(t), dt)
H = interpolate_s21(f)  # from broadband simulation

# Apply
Y = np.fft.fft(signal) * H
output = np.fft.ifft(Y).real
```

**Approach 2: Direct time-domain (Lumerical INTERCONNECT)**
- Propagate time-domain envelopes through each component
- Each component applies its impulse response (IIR filter from S-params)
- Handles nonlinear effects (saturation, free-carrier dispersion)
- Necessary for: laser rate equations, photodetector shot noise, AGC loops

**Key equations for time-domain envelope propagation through waveguide:**
```
E_out(t) = E_in(t - tau_g) * exp(-alpha*L/2) * exp(j*phi(t))
```
where tau_g = n_g * L / c, alpha = loss coefficient, phi includes chromatic
dispersion.

### 4.3 Monte Carlo Yield Analysis

#### Methodology

Process variations in silicon photonics primarily affect:
- Waveguide width (typical 3-sigma: +/- 10-20 nm within-wafer)
- Silicon thickness (typical 3-sigma: +/- 5-10 nm wafer-to-wafer)
- Etch depth (affects partial etch for rib waveguides)

These cause variations in effective index -> resonance shifts, coupling
coefficient changes, loss changes.

**Layout-aware Monte Carlo flow:**

1. Define process variation model:
   ```python
   # Global variations (wafer-to-wafer)
   delta_w_global = np.random.normal(0, sigma_w_global)
   delta_t_global = np.random.normal(0, sigma_t_global)

   # Spatially correlated local variations
   # Using correlation length L_c and device positions
   delta_w_local = correlated_gaussian_field(positions, L_c, sigma_w_local)
   ```

2. Map geometry variations to model parameter variations:
   ```python
   # Sensitivity model: dn_eff/dw, dn_eff/dt
   dn_eff = (dn_eff_dw * delta_w) + (dn_eff_dt * delta_t)
   n_eff_varied = n_eff_nominal + dn_eff
   ```

3. Simulate circuit with perturbed parameters (100-1000 iterations):
   ```python
   results = []
   for trial in range(N_trials):
       # Sample variations
       delta_w = sample_width_variation()
       delta_t = sample_thickness_variation()

       # Update component models
       models_varied = update_models(nominal_models, delta_w, delta_t)

       # Simulate circuit
       S = circuit(wl=wl_grid, models=models_varied)
       results.append(extract_metrics(S))

   # Compute yield
   yield_pct = np.mean([r.meets_spec for r in results]) * 100
   ```

4. Generate yield statistics:
   - Histograms of key metrics (insertion loss, extinction ratio, bandwidth)
   - Yield vs. specification limit curves
   - Worst-case corners identification

**Correlated variation model (Cholesky decomposition):**
```python
# Correlation matrix for N devices
C = np.exp(-distances / correlation_length)  # NxN matrix
L = np.linalg.cholesky(C)

# Correlated samples
z = np.random.normal(0, 1, N)
delta_w = sigma_w * L @ z  # spatially correlated width variations
```

**Simphony layout-aware Monte Carlo:**
```python
from simphony.simulators import MonteCarloSweepSimulator

sim = MonteCarloSweepSimulator(num_sims=1000)
sim.multiconnect(circuit_components)
result = sim.simulate()
```

#### Key Sensitivity Coefficients for SOI Strip Waveguides (220nm x 500nm)

| Parameter | dn_eff/dw | dn_eff/dt |
|-----------|-----------|-----------|
| TE mode at 1550nm | ~1.5e-3 /nm | ~2.5e-3 /nm |
| TM mode at 1550nm | ~0.5e-3 /nm | ~3.0e-3 /nm |

### 4.4 Thermal Simulation Coupling

#### Thermo-Optic Effect in Silicon

Silicon has a high thermo-optic coefficient:
```
dn_Si/dT = 1.86 x 10^{-4} K^{-1}  (at 1550nm, 300K)
```

This means a 1 K temperature change shifts the effective index by ~1.86e-4,
causing a resonance wavelength shift in a ring resonator of:

```
d(lambda_res)/dT = lambda_res * (dn_eff/dT) / n_g
                 ~ 1550nm * 1.86e-4 / 4.2
                 ~ 69 pm/K
```

#### Thermal Simulation Coupling Workflow

1. **Thermal solve**: Compute temperature distribution T(x,y,z) given heater
   power dissipation and boundary conditions (heat equation):
   ```
   -div(k * grad(T)) = Q
   ```
   where k = thermal conductivity, Q = volumetric heat source

2. **Mode solve**: At each temperature, compute n_eff(T, lambda):
   ```
   n_eff(T) = n_eff(T_0) + (dn_eff/dT) * (T - T_0)
   ```

3. **Circuit simulation**: Use temperature-dependent n_eff in S-parameter models

**Python implementation:**
```python
def ring_resonator_thermal(wl, T, T_ref=300):
    """Ring resonator model with thermal tuning."""
    dn_eff_dT = 1.86e-4  # thermo-optic coefficient
    n_eff_0 = 2.44       # effective index at T_ref
    n_g = 4.2            # group index
    L = 2 * np.pi * radius  # ring circumference

    n_eff = n_eff_0 + dn_eff_dT * (T - T_ref)
    phi = 2 * np.pi * n_eff * L / wl

    # All-pass ring response
    a = np.exp(-alpha * L / 2)  # round-trip amplitude
    t = np.sqrt(1 - kappa**2)   # through coefficient

    E_out = (t - a * np.exp(1j * phi)) / (1 - t * a * np.exp(1j * phi))
    return np.abs(E_out)**2
```

**Multi-physics coupling flow:**
```
Heater power P_heat
    |
    v
Thermal solver (FEM: COMSOL, Elmer, DEVSIM, Lumerical HEAT)
    |
    v
Temperature distribution T(x,y,z)
    |
    v
Effective index update: n_eff(T, lambda)
    |
    v
Circuit simulator (SAX, INTERCONNECT, Simphony)
    |
    v
Spectral response at each temperature
```

**Tools for thermal-photonic coupling:**
- Lumerical HEAT solver + INTERCONNECT (commercial, integrated)
- DEVSIM (open-source, via gplugins): electro-thermal device simulation
- Elmer FEM (open-source, via gplugins): thermal + structural
- Palace (open-source, via gplugins): electromagnetic
- Custom Python FEM with FEniCS or scikit-fem

#### Material Thermo-Optic Coefficients

| Material | dn/dT (K^{-1}) at 1550nm | Notes |
|----------|--------------------------|-------|
| Silicon | 1.86 x 10^{-4} | Dominant in SOI platforms |
| SiO2 (thermal oxide) | 1.0 x 10^{-5} | Cladding |
| Si3N4 | 2.5 x 10^{-5} | SiN photonics platforms |
| SiOC | 2.5 x 10^{-4} | Emerging; higher than Si |
| Polymer (SU-8) | -1.0 x 10^{-4} | Negative; athermal designs |

---

## Summary: Python Library Recommendations

| Task | Primary Library | Alternatives |
|------|----------------|-------------|
| Layout design & PCells | gdsfactory | KLayout Python API |
| Netlist extraction | gdsfactory.get_netlist() | KLayout netlisting, gplugins |
| S-parameter handling | scikit-rf (skrf) | numpy (manual) |
| Circuit simulation | SAX (JAX-based) | Simphony, Lumerical INTERCONNECT |
| DRC | KLayout (open-source) | Calibre eqDRC (commercial) |
| LVS | KLayout + SiEPIC-Tools | Calibre nmLVS |
| SPICE netlist | gplugins (vlsir) | Manual generation |
| Thermal simulation | DEVSIM, Elmer (via gplugins) | Lumerical HEAT, COMSOL |
| Monte Carlo yield | Simphony, SAX + custom | Lumerical INTERCONNECT |
| Optimization | SAX + JAX (autodiff) | scipy.optimize |
| Touchstone I/O | scikit-rf | Custom parser |

---

## Key API Patterns and Data Structures

### gdsfactory Netlist Dict
```python
NetlistDict = {
    "instances": Dict[str, {"component": str, "settings": Dict}],
    "connections": Dict[str, str],  # "inst1,port1": "inst2,port2"
    "ports": Dict[str, str],       # "port_name": "inst,port"
    "placements": Dict[str, {"x": float, "y": float, "rotation": int, "mirror": bool}],
}
```

### SAX SDict
```python
SDict = Dict[Tuple[str, str], Union[complex, jnp.ndarray]]
# Example: {("o1", "o2"): 0.7+0.1j, ("o2", "o1"): 0.7+0.1j}
```

### scikit-rf Network
```python
ntwk.s     # np.ndarray, shape (n_freq, n_ports, n_ports), dtype=complex
ntwk.f     # np.ndarray, shape (n_freq,), frequency in Hz
ntwk.z0    # np.ndarray, shape (n_freq, n_ports), reference impedance
ntwk.name  # str
```

### Touchstone Data Structure (Internal)
```python
TouchstoneData = {
    "frequency_unit": str,    # "GHz", "MHz", "Hz", etc.
    "parameter": str,         # "S", "Y", "Z"
    "format": str,            # "MA", "DB", "RI"
    "impedance": float,       # reference impedance (ohms)
    "frequencies": np.ndarray,
    "data": np.ndarray,       # shape (n_freq, n_ports, n_ports), complex
}
```

---

## References and Documentation Links

### gdsfactory
- Repository: https://github.com/gdsfactory/gdsfactory
- Documentation: https://gdsfactory.github.io/gdsfactory/
- API reference: https://gdsfactory.github.io/gdsfactory/api.html
- PDK guide: https://gdsfactory.github.io/gdsfactory/notebooks/08_pdk.html
- Netlist extraction: https://gdsfactory.github.io/gdsfactory/_autosummary/gdsfactory.get_netlist.get_netlist.html
- Migration v7->v8: https://gdsfactory.github.io/gdsfactory/notebooks/21_migration_guide_7_8.html
- gplugins: https://github.com/gdsfactory/gplugins
- Component geometry: https://gdsfactory.github.io/gdsfactory/notebooks/00_geometry.html
- Instances and ports: https://gdsfactory.github.io/gdsfactory/notebooks/01_references.html
- YAML netlist: https://gdsfactory.github.io/gdsfactory/notebooks/10_yaml_component.html

### PDK Packages
- cspdk (CORNERSTONE): https://github.com/gdsfactory/cspdk
- ubcpdk (SiEPIC EBeam): https://gdsfactory.github.io/ubc/
- skywater130: https://github.com/gdsfactory/skywater130
- gf180mcu: https://github.com/gdsfactory/gf180mcu

### S-Parameters and Compact Models
- Touchstone v2.0 spec: https://ibis.org/touchstone_ver2.0/touchstone_ver2_0.pdf
- Touchstone v2.1 spec: https://ibis.org/touchstone_ver2.1/touchstone_ver2_1.pdf
- scikit-rf documentation: https://scikit-rf.readthedocs.io/en/latest/
- scikit-rf Networks tutorial: https://scikit-rf.readthedocs.io/en/latest/tutorials/Networks.html
- scikit-rf Connecting Networks: https://scikit-rf.readthedocs.io/en/latest/tutorials/Connecting_Networks.html
- SAX repository: https://github.com/flaport/sax
- SAX documentation: https://flaport.github.io/sax/
- Simphony: https://github.com/BYUCamachoLab/simphony
- Simphony documentation: https://simphonyphotonics.readthedocs.io/
- Lumerical CML Compiler: https://www.ansys.com/products/optics/cml-compiler
- Lumerical INTERCONNECT: https://www.ansys.com/products/optics/interconnect
- Ansys photonic Verilog-A: https://optics.ansys.com/hc/en-us/articles/18698429782291

### DRC, LVS, and Tapeout
- KLayout: https://www.klayout.de/
- KLayout DRC basics: https://www.klayout.org/downloads/master/doc-qt5/manual/drc_basic.html
- SiEPIC-Tools: https://github.com/SiEPIC/SiEPIC-Tools
- Calibre eqDRC for silicon photonics: https://blogs.sw.siemens.com/calibre/2015/11/17/design-rule-checking-for-silicon-photonics/
- gdsfactory DRC training: https://gdsfactory.github.io/gdsfactory-photonics-training/notebooks/11_drc.html
- gplugins SPICE netlist: https://gdsfactory.github.io/gplugins/notebooks/11_get_netlist_spice.html
- Cadence photonics flow: https://www.cadence.com/en_US/home/solutions/photonics.html

### Simulation and Yield
- SAX + gdsfactory circuit sim: https://gdsfactory.github.io/gplugins/notebooks/sax_01_sax.html
- Simphony Monte Carlo: https://simphonyphotonics.readthedocs.io/en/latest/tutorials/layout_aware.html
- Lumerical yield analysis: https://optics.ansys.com/hc/en-us/articles/360054921214
- Lumerical statistical compact models: https://optics.ansys.com/hc/en-us/articles/360055833233

### Physics References
- Ring resonator parameter extraction: https://opg.optica.org/oe/fulltext.cfm?uri=oe-17-21-18971&id=186494
- Silicon thermo-optic coefficient: https://opg.optica.org/oe/fulltext.cfm?uri=oe-27-19-27229&id=418762
- SOI waveguide dispersion: https://opg.optica.org/oe/abstract.cfm?uri=oe-14-9-3853
- Layout-aware yield prediction: https://pubs.acs.org/doi/10.1021/acsphotonics.2c01194
- Simphony paper (IEEE): https://ieeexplore.ieee.org/document/9149634
- Photonic LVS (DATE 2015): https://ieeexplore.ieee.org/document/7092582/
