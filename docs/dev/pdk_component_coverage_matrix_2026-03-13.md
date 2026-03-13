# PDK Component Coverage Matrix (2026-03-13)

## Purpose

Track how well PhotonTrust's manifest-level PDK coverage matches the internal PIC
component model and identify the highest-value gaps for foundry-facing workflows.

## Scope

This matrix compares:

1. internal PIC component primitives in `photonstrust/components/pic/library.py`
2. generic public PDK manifests under `configs/pdks/`
3. foundry-labeled or public-facing illustrative manifests currently represented by AIM Photonics and SiEPIC EBeam-style coverage

## PDK Manifests Currently Checked In

| PDK | Type | Component cells | Notes |
|---|---|---:|---|
| `aim_photonics` | foundry-labeled illustrative | 6 | illustrative only; not foundry-approved production data |
| `aim_photonics_300nm_sin` | foundry-labeled illustrative | 5 | corner-enabled illustrative manifest |
| `siepic_ebeam` | public-facing illustrative adapter | 6 | illustrative public EBeam-style adapter manifest |
| `generic_silicon_photonics` | generic | 5 | runtime generic silicon photonics manifest |
| `generic_sip_corners` | generic | 5 | generic corner-enabled manifest |

## Unique Manifest-Level Component Cells

- `grating_coupler_te`
- `edge_coupler_te`
- `ring_resonator`
- `waveguide_straight`
- `mmi_2x2`
- `phase_shifter`

Total unique manifest-level component names: `6`

## Internal PIC Primitive Set

Defined in `photonstrust/components/pic/library.py`:

- `pic.waveguide`
- `pic.grating_coupler`
- `pic.edge_coupler`
- `pic.phase_shifter`
- `pic.isolator_2port`
- `pic.ring`
- `pic.coupler`
- `pic.touchstone_2port`
- `pic.touchstone_nport`

Total internal PIC primitive kinds: `9`

## Coverage Matrix

| Internal primitive | Generic PDK support | AIM support | Current manifest cell example | Status | Priority |
|---|---|---|---|---|---|
| `pic.grating_coupler` | Yes | Yes | `grating_coupler_te` | covered | low |
| `pic.edge_coupler` | Yes | Yes | `edge_coupler_te` | covered | low |
| `pic.waveguide` | Yes | Yes | `waveguide_straight` | covered | low |
| `pic.coupler` | Yes | Yes | `mmi_2x2` | covered (illustrative) | low |
| `pic.ring` | Partial | Yes | `ring_resonator` | covered in illustrative adapters only | medium |
| `pic.phase_shifter` | Yes | Yes | `phase_shifter` | covered (illustrative) | low |
| `pic.isolator_2port` | No | No | -- | missing | low |
| `pic.touchstone_2port` | No | No | -- | missing at manifest layer | medium |
| `pic.touchstone_nport` | No | No | -- | missing at manifest layer | medium |

## Practical Interpretation

### Strongest current areas

- input/output optical IO cells are represented in every checked-in manifest
- waveguide, coupler/MMI, and phase shifter coverage now exist at both generic and AIM illustrative levels
- one ring-resonator cell exists in the AIM illustrative manifest

### Main weaknesses

- no richer waveguide family coverage (bend, taper, route primitives)
- no manifest-level Touchstone-backed packaged component catalog
- broader real foundry-family depth is still limited

## Highest-Value Next Additions

### Priority 1: deepen beyond the current illustrative adapter set

Phase 1 is now complete for the checked-in AIM and SiEPIC-style illustrative
manifests. The next high-value move is broadening or deepening beyond these
public-facing illustrative adapters.

### Priority 2: define mapping discipline

Add a stable mapping table between:

- internal primitive kind
- manifest cell name
- library/cell name
- port naming
- nominal loss / notes / intended workflow use

### Priority 3: add second public-facing adapter family

Even an illustrative or wrapper-level public PDK adapter for a second ecosystem
would improve credibility more than only deepening AIM coverage.

## Acceptance Criteria For Better Coverage

The next iteration should aim for:

1. all core primitives used by the PIC product flow mapped in at least one
   generic PDK
2. AIM illustrative manifests covering at least:
   - grating coupler
   - edge coupler
   - waveguide
   - coupler/MMI
   - phase shifter
   - ring resonator
3. at least one second public-facing adapter family covering the same core set
4. tests that fail if required coverage drops below that bar

## Phase 1 Status

Completed in the current working tree / branch:

1. `aim_photonics.pdk.json` now includes:
   - `waveguide_straight`
   - `mmi_2x2`
   - `phase_shifter`
2. `aim_photonics_300nm_sin.pdk.json` now includes:
   - `waveguide_straight`
   - `mmi_2x2`
   - `phase_shifter`
3. generic manifests now also include `phase_shifter`
4. coverage regression test added in `tests/test_pdk_component_coverage.py`
5. `siepic_ebeam.pdk.json` added as a second public-facing illustrative adapter family
