# Public Launch Hygiene Review (2026-03-13)

## Purpose

Capture the remaining public-release hygiene decisions for data, generated
artifacts, nested subprojects, and optional native components.

## Findings

### `datasets/measurements/private/`

- Currently tracked files appear to be synthetic starter templates.
- The folder name is potentially misleading for external readers.
- Risk: future contributors may assume it is acceptable to commit true private
  data there.

Action taken:

- added README files clarifying that current contents are synthetic starter
  bundles only.

Remaining action:

- consider renaming `private/` in a later breaking cleanup wave, or keep the
  name but enforce explicit review for any new data added there.

### `results/`

- Large local output surface remains under `results/`.
- Some tracked subtrees are intentional evidence and are widely referenced.
- This is acceptable for now, but should remain tightly controlled.

Recommended tracked-evidence allowlist:

- `results/release_gate/`
- `results/qutip_parity/`
- `results/research_validation/` when explicitly referenced by docs or reports

Everything else should be treated as generated/local unless documented otherwise.

### `photonstrust_rs/`

- This is an optional acceleration component.
- It contained tracked local build logs, which should not be part of a polished
  public repo.

Action taken:

- added README clarifying optional status,
- added ignore rules for local build log files.

Remaining action:

- decide whether `photonstrust_rs/` stays in-tree long term or becomes a linked
  sibling project.

### `open_source/qiskit_protocols_public/`

- This is effectively a nested subproject with its own git metadata.
- It needs explicit documentation because new contributors may assume it is part
  of the main repo lifecycle.

Action taken:

- added `open_source/README.md` to document the boundary.

## Recommended Next Hygiene Steps

1. fix the lingering `ruff` issue in `photonstrust/api/routers/graph.py`
2. decide and document a tracked-evidence allowlist for `results/`
3. decide long-term policy for `photonstrust_rs/` and `open_source/`
4. add screenshots and public-facing README polish before any public launch post
