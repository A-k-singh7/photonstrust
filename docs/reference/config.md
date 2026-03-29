# Config Reference

PhotonTrust's main execution surface is config-driven:

```bash
photonstrust run <config.yml> --output <dir>
```

This page describes where those configs live, what the common layout looks
like, and which outputs you should expect.

## Where to Start

Use the catalog in `../../configs/README.md`. The most useful starting points
are:

- `../../configs/quickstart/qkd_quick_smoke.yml`
  - shortest QKD proof path
- `../../configs/quickstart/qkd_default.yml`
  - slightly less minimal QKD run
- `../../configs/quickstart/orbit_pass_envelope.yml`
  - orbit and satellite-oriented example
- `../../configs/product/`
  - product and pilot-oriented scenarios
- `../../configs/canonical/`
  - deterministic validation fixtures
- `../../graphs/demo8_qkd_link_graph.json`
  - graph input that compiles into a runnable config

## Common Layout

Most QKD configs revolve around these top-level sections:

- `schema_version`
- `source`
- `channel`
- `detector`
- `timing`
- `protocol`
- optional uncertainty, finite-key, or workflow-specific sections

The longer field-by-field parameter tables remain in
`../guide/config-reference.md`.

## Output Contract

A normal `run` command writes:

- `<output>/run_registry.json`
- `<output>/<scenario_id>/<band>/reliability_card.json`
- `<output>/<scenario_id>/<band>/report.html`
- `<output>/<scenario_id>/<band>/report.pdf`
- `<output>/<scenario_id>/<band>/results.json`

That output contract is the backbone of the current docs.

## Graph-Compiled Configs

If you do not want to hand-author YAML immediately, compile a graph first:

```bash
photonstrust graph compile graphs/demo8_qkd_link_graph.json --output results/graphs_demo
```

That produces:

- `compiled_config.yml`
- `assumptions.md`
- `compile_provenance.json`

The compiled config can then be executed with `photonstrust run`.

## Dependency Notes

The config itself does not guarantee every optional backend is installed.

- base QKD quickstart works with `pip install -e .`
- API/product workflows need `.[api]`
- QuTiP-backed flows need `.[qutip]`
- Qiskit-backed flows need `.[qiskit]`
- JAX should be treated as optional unless a specific path calls for it

## Related Docs

- `cli.md`
- `../guide/getting-started.md`
- `../guide/limitations.md`
- `../../configs/README.md`
