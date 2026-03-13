# Repo Inventory Matrix (2026-03-13)

## Purpose

This matrix classifies the main repository areas so cleanup work can proceed in a
safe, staged, and reviewable way.

## Top-Level Inventory

| Path | Current role | Public value | Risk level | Recommended action |
|---|---|---:|---:|---|
| `photonstrust/` | Core Python package | High | Low | Keep as primary source tree |
| `web/` | React product surface | High | Low | Keep; continue modular cleanup |
| `ui/` | Legacy Streamlit UI | Medium | Medium | Keep for now, mark as legacy in docs |
| `tests/` | Python test suite | High | Medium | Reorganize into subfolders |
| `configs/` | Runnable scenario inputs | High | Medium | Reorganize by purpose |
| `graphs/` | Graph compiler inputs | High | Low | Keep; add README/index if needed |
| `examples/` | Small user examples | High | Low | Keep curated and minimal |
| `scripts/` | Maintainer automation | High | Medium | Reorganize by domain |
| `schemas/` | API/artifact schemas | High | Low | Keep; add schema index |
| `docs/` | Main documentation tree | High | Medium | Continue active vs archive split |
| `datasets/` | Benchmarks and measurements | Medium | High | Audit licensing/privacy immediately |
| `reports/` | Checked-in release/evidence docs | Medium | Medium | Keep only intentional evidence |
| `results/` | Generated outputs + some tracked evidence | Medium | High | Split policy between local outputs and versioned evidence |
| `tools/` | Auxiliary tooling | Medium | Low | Keep; document purpose |
| `notebooks/` | Notebook entry points | Medium | Low | Keep only curated notebooks |
| `open_source/` | Nested public subproject(s) | Medium | Medium | Decide whether to keep in-tree or externalize |
| `photonstrust_rs/` | Rust sibling component | Medium | High | Document role or move out of root scope |
| `requirements/` | Dependency pins/support files | Medium | Low | Keep if actively used |
| `.github/` | CI/workflows/templates | High | Low | Keep; continue workflow cleanup |
| `.venv/`, `.venv.production/`, `.benchmarks/`, `local/` | Local env/runtime areas | None | High | Keep ignored only; never treat as source |

## High-Risk Areas Requiring Explicit Policy

### `results/`

Current state:

- contains many local/generated outputs,
- also contains tracked validation and evidence-like artifacts,
- currently too broad for a clean OSS mental model.

Required action:

1. define tracked subtrees that are intentionally versioned,
2. mark all other subtrees as local/generated only,
3. move permanent evidence into `reports/` or a clearly documented evidence area where possible.

### `datasets/measurements/private/`

Current state:

- public repository contains a `private/` path under measurements.

Required action:

1. review whether contents are actually safe to publish,
2. either remove, rename, or document clearly,
3. add provenance and licensing metadata.

### `photonstrust_rs/`

Current state:

- contains its own `Cargo.toml`, `pyproject.toml`, and build logs,
- looks like a sibling project rather than a clean subpackage.

Required action:

1. decide if it is an active in-repo component,
2. if yes, document it clearly and remove build logs/target outputs from versioning,
3. if no, archive or move it out.

### `open_source/qiskit_protocols_public/`

Current state:

- looks like a nested public extract/subproject.

Required action:

1. decide whether nested subprojects are part of the main repo strategy,
2. if yes, document boundaries,
3. if no, remove from root scope and link externally.

## Immediate Keep / Review / Archive Decisions

### Keep and improve

- `photonstrust/`
- `web/`
- `tests/`
- `configs/`
- `graphs/`
- `examples/`
- `schemas/`
- `docs/`

### Keep but relabel/document

- `ui/`
- `reports/`
- `tools/`
- `notebooks/`

### Review before launch

- `datasets/`
- `results/`
- `open_source/`
- `photonstrust_rs/`

### Treat as local-only and never surface in docs

- `.venv/`
- `.venv.production/`
- `.benchmarks/`
- `local/`
- `tmp_*.pdf`

## Next Inventory Deliverables

1. `docs_cleanup_matrix_2026-03-13.md`
2. `test_naming_cleanup_matrix_2026-03-13.md`
3. `scripts_and_configs_cleanup_matrix_2026-03-13.md`
4. dataset and evidence retention review
