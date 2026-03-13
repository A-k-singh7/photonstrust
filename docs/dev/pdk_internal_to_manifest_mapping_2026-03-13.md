# PDK Internal-to-Manifest Mapping Table (2026-03-13)

## Purpose

Define a clearer mapping between PhotonTrust's internal PIC primitive kinds and
the manifest-level component cell names exposed in PDK JSON files.

## Mapping Table

| Internal primitive | Preferred manifest cell name | Typical ports | Notes |
|---|---|---|---|
| `pic.grating_coupler` | `grating_coupler_te` | `opt1,opt2` | IO coupling cell for TE coupling workflows |
| `pic.edge_coupler` | `edge_coupler_te` | `opt1,opt2` | edge-coupled IO alternative |
| `pic.waveguide` | `waveguide_straight` | `o1,o2` | straight propagation primitive |
| `pic.waveguide` | `waveguide_bend_euler` | `o1,o2` | layout/routing-oriented bend primitive; currently layout-focused at manifest level |
| `pic.coupler` | `mmi_2x2` | `in1,in2,out1,out2` | use MMI as the default manifest-level splitter/combiner representation |
| `pic.phase_shifter` | `phase_shifter` | `in,out` | thermal/electrical drive metadata belongs in component-cell metadata |
| `pic.ring` | `ring_resonator` | `bus_in,bus_out` | single-bus ring baseline representation |
| `pic.edge_coupler` | `spot_size_converter` | `opt1,opt2` | illustrative IO transition component; currently layout-focused |
| `pic.coupler` | `monitor_tap_1x2` | `in,through,tap` | illustrative monitor/tap representation; currently layout-focused |
| `pic.isolator_2port` | *(none yet)* | `in,out` | no current manifest-level public mapping |
| `pic.touchstone_2port` | `photodiode_ge` | `opt_in` | represented as an external-characterized packaged cell rather than a native primitive |
| `pic.touchstone_nport` | `awg_mux_demux` | package-defined | represented as a packaged wavelength-routing block at manifest level |

## Naming Rules

1. use stable, descriptive manifest cell names rather than foundry-native names
   as the public-facing identifier,
2. keep foundry-native naming in `library` + `cell`,
3. use metadata fields for drive type, nominal insertion loss, or packaged model
   hints,
4. use `support_level` to distinguish `modeled`, `layout_only`, and
   `characterized_external` cells,
5. avoid manifest names that are too vendor-specific unless the component is only
   meaningful in that vendor context.

## Example Pattern

```json
{
  "name": "phase_shifter",
  "library": "aim",
  "cell": "PHASE_SHIFTER_THERMO",
  "ports": ["in", "out"],
  "drive_type": "thermal",
  "nominal_il_db": 0.25
}
```

## Why this matters

This mapping keeps:

- internal component kinds stable for simulation and graph logic,
- manifest cell names stable for public interoperability,
- vendor-specific details explicit but secondary.
