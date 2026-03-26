# Getting Started with PhotonsTrust

PhotonsTrust is a simulation and design platform for quantum key distribution
(QKD) links, photonic integrated circuits, multi-node QKD networks, and
satellite-based quantum communication. This guide walks you through
installation, your first simulation, and the main features of the toolkit.

---

## Installation

Install from PyPI:

```bash
pip install photonstrust
```

Or install from source for development:

```bash
git clone https://github.com/photonstrust/photonstrust.git
cd photonstrust
pip install -e ".[dev]"
```

### Optional extras

| Extra   | What it adds                                    |
|---------|-------------------------------------------------|
| `dev`   | All development and test dependencies           |
| `cli`   | Rich tables and terminal formatting              |
| `qutip` | QuTiP backend for cavity quantum-optics models  |

Example:

```bash
pip install photonstrust[cli]
```

> **Note:** JAX is a required dependency and must be installed. If you see
> `"JAX not found"` errors, run `pip install jax`.

---

## Your First Simulation (3 lines)

```python
from photonstrust.easy import simulate_qkd_link

result = simulate_qkd_link(protocol="bb84", distance_km=50)
print(result.summary())
```

This simulates a BB84 decoy-state QKD link over a 0-50 km fiber sweep using
C-band (1550 nm) photons and SNSPD detectors. The `result` object is a
`QKDLinkResult` with convenience methods:

- `result.summary()` -- human-readable text summary
- `result.max_distance_km()` -- farthest distance with positive key rate
- `result.key_rate_at(30)` -- key rate at a specific distance (nearest match)
- `result.plot()` -- rate-vs-distance plot (requires matplotlib)
- `result.as_dict()` -- serializable dictionary

---

## Comparing Protocols (5 lines)

```python
from photonstrust.easy import compare_protocols

comp = compare_protocols(protocols=["bb84", "tf_qkd", "cv_qkd"])
print(comp.summary())
print(f"Best at 50 km: {comp.winner_at(50)}")
```

`compare_protocols` runs each protocol over the same distance sweep and returns
a `ProtocolComparison` object. Key methods:

- `comp.summary()` -- tabular comparison of peak rates and max distances
- `comp.winner_at(distance_km)` -- protocol name with the highest rate at that distance
- `comp.plot()` -- overlay chart of all protocols
- `comp.as_dict()` -- serializable dictionary

You can pass `distances` as a dict to control the sweep:

```python
comp = compare_protocols(
    protocols=["bb84", "tf_qkd"],
    distances={"start": 0, "stop": 300, "step": 10},
)
```

---

## Using the CLI

PhotonsTrust ships a command-line interface for quick exploration.

### List available resources

```bash
photonstrust list protocols
photonstrust list bands
photonstrust list detectors
photonstrust list scenarios
```

### Get detailed info

```bash
photonstrust info bb84
photonstrust info snspd
photonstrust info c_1550
```

### Run a pre-built demo scenario

```bash
photonstrust demo bb84_metro
photonstrust demo tf_long_haul
```

### Interactive quickstart wizard

```bash
photonstrust quickstart
```

### Run a YAML configuration file

```bash
photonstrust run my_config.yaml --output results/
```

---

## Generating Reports

Generate a self-contained HTML report from any simulation result:

```python
from photonstrust.easy import simulate_qkd_link
from photonstrust.reporting.html_report import generate_html_report

result = simulate_qkd_link(protocol="bb84", distance_km=50)
html = generate_html_report(result, title="BB84 Link Analysis")

with open("report.html", "w") as f:
    f.write(html)
```

The report includes rate-vs-distance charts, parameter tables, and protocol
metadata -- all embedded in a single HTML file with no external dependencies.

---

## Pre-built Scenarios

The scenario gallery provides 15 ready-to-run configurations spanning QKD
links, PIC design, network planning, and satellite scheduling.

```python
from photonstrust.gallery import list_scenarios, run_scenario

# Browse beginner QKD scenarios
for s in list_scenarios(category="qkd", difficulty="beginner"):
    print(f"{s.name}: {s.title}")

# Run one
result = run_scenario("bb84_metro")
print(result.summary())
```

You can override any scenario parameter:

```python
result = run_scenario("bb84_metro", distance_km=40, detector="ingaas")
```

### Example scenarios

| Name              | Category  | Difficulty   | Description                          |
|-------------------|-----------|--------------|--------------------------------------|
| `bb84_metro`      | qkd       | beginner     | BB84 over 20 km metro fiber          |
| `bbm92_campus`    | qkd       | beginner     | BBM92 entanglement on 5 km campus    |
| `tf_long_haul`    | qkd       | intermediate | TF-QKD sweep 0-400 km               |
| `cv_qkd_urban`    | qkd       | intermediate | CV-QKD urban link 0-30 km            |
| `satellite_leo`   | satellite | intermediate | LEO satellite constellation plan     |
| `pic_mzi_switch`  | pic       | beginner     | MZI optical switch design            |
| `network_3node`   | network   | beginner     | 3-node linear QKD network            |
| `repeater_chain`  | qkd       | advanced     | Multi-protocol repeater comparison   |

---

## Next Steps

- **[config-reference.md](config-reference.md)** -- Complete parameter reference for all source, channel, detector, protocol, and band settings.
- **[protocol-guide.md](protocol-guide.md)** -- Comparison table and decision flowchart for choosing the right QKD protocol.
- **[glossary.md](glossary.md)** -- Definitions of 50+ QKD and photonics terms.
- **[troubleshooting.md](troubleshooting.md)** -- Common errors, fixes, and performance tips.
- **[architecture.md](architecture.md)** -- Module map and simulation pipeline overview.
- Explore the `notebooks/cookbook/` directory for Jupyter notebook tutorials.
