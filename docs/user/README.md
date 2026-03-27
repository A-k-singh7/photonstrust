# User Guides

This section is the entry point for people using the current PhotonTrust product
surfaces.

## Start Here

- `quickstart.md`
  - shortest CLI path to a working run
- `product-ui.md`
  - maintained React product walkthrough
- `../guide/getting-started.md`
  - exact first-run flow and expected outputs
- `../guide/use-cases.md`
  - choose the right path for your role
- `../../configs/README.md`
  - config catalog
- `../../examples/README.md`
  - lightweight code examples

## Main User Surfaces

- CLI and config-driven QKD workflows
- graph compile to runnable config flows
- React product UI in `web/`
- legacy Streamlit UI in `ui/`

## Good First Commands

```bash
photonstrust run configs/quickstart/qkd_quick_smoke.yml --output results/smoke_quick
photonstrust card validate results/smoke_quick/demo1_quick_smoke/nir_850/reliability_card.json
photonstrust graph compile graphs/demo8_qkd_link_graph.json --output results/graphs_demo
```
