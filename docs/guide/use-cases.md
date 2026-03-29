# PhotonTrust Use Cases

PhotonTrust is easiest to understand when you choose one role and one desired
output. The current docs optimize for three paths.

## Path Summary

| Persona | Start Here | Best For | Concrete Output |
|---------|------------|----------|-----------------|
| Researcher | `getting-started.md` | fast QKD scenario evaluation | reliability card, report, results JSON |
| Product evaluator | `../user/product-ui.md` | local UI review and guided flows | running UI plus shared run artifacts |
| Maintainer | `../dev/git_and_docs_workflow.md` | repo changes, docs sync, validation | clean diff, passing docs QA, updated docs |

## Researcher Path

Choose this path if you need to answer questions like:

- What does a quick QKD link run produce?
- How far can I get before key rate collapses?
- Which artifacts can I hand to someone else for review?

Recommended sequence:

1. `getting-started.md`
2. `reliability-card.md`
3. `../reference/config.md`
4. `../../configs/README.md`

Best concrete outputs:

- `reliability_card.json`
- `report.html`
- `report.pdf`
- `results.json`

## Product Evaluator Path

Choose this path if you need to answer questions like:

- What does the current product surface look like?
- Is there a usable local React workflow?
- How does the product layer sit on top of the same engine outputs?

Recommended sequence:

1. `../user/quickstart.md`
2. `../user/product-ui.md`
3. `../reference/cli.md`

Best concrete outputs:

- local UI at `http://127.0.0.1:5173`
- API health at `http://127.0.0.1:8000/healthz`
- screenshots in `../assets/`
- run artifacts under `results/`

## Maintainer Path

Choose this path if you need to answer questions like:

- Which docs must change with behavior changes?
- How do I keep the README and guide set aligned with the actual CLI?
- What is the minimum docs QA lane before opening a PR?

Recommended sequence:

1. `../dev/git_and_docs_workflow.md`
2. `../dev/testing.md`
3. `../reference/README.md`
4. `../../CONTRIBUTING.md`

Best concrete outputs:

- passing `pytest -q tests/test_docs_experience.py`
- clean `git diff --check`
- updated docs and changelog in the same branch

## When to Use the Broader Repo

PhotonTrust contains more than the front-door QKD wedge. Use the broader repo
when you specifically need:

- graph compile plus PIC simulation
- orbit and satellite scenario workflows
- certification, bundle, or compliance surfaces
- research and roadmap material under `../research/`

Those surfaces are real, but they are not the first thing a new reader should
have to parse.
