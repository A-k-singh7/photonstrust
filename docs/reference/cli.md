# CLI Reference

PhotonTrust's CLI is organized around a few command families. The most useful
ones for normal work are `run`, `graph compile`, `card validate`, `list`, and
`quickstart`.

Use `photonstrust <command> --help` for full flag details.

## First Commands

```bash
photonstrust list protocols
photonstrust run configs/quickstart/qkd_quick_smoke.yml --output results/smoke_quick
photonstrust card validate results/smoke_quick/demo1_quick_smoke/nir_850/reliability_card.json
photonstrust graph compile graphs/demo8_qkd_link_graph.json --output results/graphs_demo
```

## Core Run Commands

- `photonstrust run <config.yml> --output <dir>`
  - execute a scenario config and write run artifacts
- `photonstrust run <config.yml> --validate-only`
  - check a config without executing the run
- `photonstrust quickstart`
  - interactive wizard for a basic QKD setup
- `photonstrust demo <name>`
  - run a pre-built scenario

## Discovery Commands

- `photonstrust list protocols`
- `photonstrust list bands`
- `photonstrust list detectors`
- `photonstrust list scenarios`
- `photonstrust info <resource>`

Use these before writing or editing configs if you want to stay inside the
registered catalog surface.

## Graph and PIC Commands

- `photonstrust graph compile <graph.json|graph.ptg.toml> --output <dir>`
  - compile a graph into a runnable QKD config or PIC netlist
- `photonstrust fmt graphspec <graph.json|graph.ptg.toml>`
  - format GraphSpec inputs deterministically
- `photonstrust pic simulate <compiled_netlist.json> --output <dir>`
  - simulate a compiled PIC netlist
- `photonstrust pic crosstalk --gap-um <gap> --length-um <length> --wavelength-nm <nm>`
  - estimate parallel waveguide crosstalk

## Artifact and Evidence Commands

- `photonstrust card validate <reliability_card.json>`
  - validate a generated reliability card against schema
- `photonstrust card diff <left.json> <right.json>`
  - compare two cards
- `photonstrust bundle keygen`
- `photonstrust bundle sign`
- `photonstrust bundle verify`

## Certification and Governance Commands

- `photonstrust certify <graph>`
  - run the PIC to QKD certification orchestrator
- `photonstrust compliance check <input>`
  - build an ETSI-style compliance report
- `photonstrust m3 checkpoint`
  - run the M3 checkpoint lane
- `photonstrust satellite-chain`
  - execute satellite-chain workflow helpers
- `photonstrust sweep`
  - run PIC process-corner sweeps

## Output Expectations

The main commands write into an output directory under `results/` by default.
The most common outputs are:

- `run_registry.json`
- `reliability_card.json`
- `report.html`
- `report.pdf`
- `compiled_config.yml`
- `assumptions.md`
- provenance and results JSON files
