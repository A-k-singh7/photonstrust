# 09 - Packaging Improvements

---

## Research Anchors (Packaging / Citability / Release Hygiene)

- PEP 621 (`pyproject.toml` project metadata): https://peps.python.org/pep-0621/
- PEP 517 (build system interface): https://peps.python.org/pep-0517/
- CITATION.cff specification: https://citation-file-format.github.io/
- Keep a Changelog (release notes conventions): https://keepachangelog.com/en/1.1.0/
- setuptools-scm configuration (note: modern key is `version_file`, older examples may show `write_to`): https://setuptools-scm.readthedocs.io/

## Current `pyproject.toml` gaps

The current file is functional but missing several fields that improve
discoverability, citability, and developer experience.

---

## Corrected `pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "photonstrust"
version = "0.1.0"
description = "Physics-calibrated quantum link reliability toolkit"
readme = "README.md"
license = "MIT"
requires-python = ">=3.9"
authors = [
    {name = "PhotonTrust Contributors"}
]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Science/Research",
    "Topic :: Scientific/Engineering :: Physics",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]
keywords = ["quantum", "qkd", "photonics", "reliability", "digital-twin"]

dependencies = [
    "numpy>=1.24",
    "pyyaml>=6.0",
    "matplotlib>=3.7",
]

[project.optional-dependencies]
qutip = ["qutip>=4.7"]
ui = ["streamlit>=1.28"]
pdf = ["reportlab>=4.0"]
dev = [
    "pytest>=7.4",
    "pytest-cov>=4.1",
    "jsonschema>=4.19",
    "ruff>=0.4",
]
qiskit = ["qiskit>=1.0"]
api = ["fastapi>=0.110", "uvicorn>=0.29"]
layout = ["gdstk>=0.9"]
docs = [
    "sphinx>=7.0",
    "sphinx-rtd-theme>=2.0",
    "myst-parser>=2.0",
]
all = [
    "photonstrust[qutip,qiskit,ui,pdf,api,layout]",
]

[project.urls]
Homepage = "https://github.com/photonstrust/photonstrust"
Documentation = "https://photonstrust.readthedocs.io"
Repository = "https://github.com/photonstrust/photonstrust"
Changelog = "https://github.com/photonstrust/photonstrust/blob/main/CHANGELOG.md"

[project.scripts]
photonstrust = "photonstrust.cli:main"

[tool.setuptools.packages.find]
where = ["."]
include = ["photonstrust*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "slow: marks tests as slow (deselect with -m 'not slow')",
    "requires_qutip: requires qutip installation",
    "requires_qiskit: requires qiskit installation",
    "requires_gdstk: requires gdstk installation",
]
filterwarnings = [
    "ignore::DeprecationWarning",
]

[tool.ruff]
target-version = "py39"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "W", "UP", "B", "SIM"]

[tool.coverage.run]
source = ["photonstrust"]
omit = ["*/tests/*", "*/ui/*"]

[tool.coverage.report]
fail_under = 70
```

---

## Changes from current pyproject.toml

| Addition | Purpose |
|----------|---------|
| `license = "MIT"` | Required for PyPI and adoption |
| `authors` | Attribution |
| `classifiers` | PyPI discoverability |
| `keywords` | Search ranking |
| `[project.urls]` | Links on PyPI page |
| `pytest-cov` in dev deps | Coverage reporting |
| `ruff` in dev deps | Linting |
| `docs` extra group | Documentation build deps |
| `all` extra group | Install everything at once |
| `[tool.pytest.ini_options]` | Test markers and config |
| `[tool.ruff]` | Lint configuration |
| `[tool.coverage]` | Coverage floor |

---

## Additional files to create

### `CITATION.cff`

For academic citability (GitHub renders this as a "Cite this repository" button):

```yaml
cff-version: 1.2.0
title: "PhotonTrust: Physics-Calibrated Quantum Link Reliability Toolkit"
message: "If you use this software, please cite it as below."
type: software
authors:
  - name: "PhotonTrust Contributors"
version: 0.1.0
date-released: "2026-02-14"
license: MIT
repository-code: "https://github.com/photonstrust/photonstrust"
keywords:
  - quantum key distribution
  - photonic integrated circuits
  - reliability engineering
  - digital twin
```

### `LICENSE`

If not already present, add the MIT license file.

### `.github/ISSUE_TEMPLATE/bug_report.yml`

```yaml
name: Bug Report
description: Report a bug in PhotonTrust
labels: [bug]
body:
  - type: textarea
    id: description
    attributes:
      label: Bug description
      placeholder: What happened?
    validations:
      required: true
  - type: textarea
    id: reproduce
    attributes:
      label: Steps to reproduce
      placeholder: |
        1. Run `photonstrust run configs/...`
        2. ...
  - type: input
    id: version
    attributes:
      label: PhotonTrust version
      placeholder: "0.1.0"
  - type: input
    id: python
    attributes:
      label: Python version
      placeholder: "3.11"
```

### `.github/ISSUE_TEMPLATE/feature_request.yml`

```yaml
name: Feature Request
description: Suggest a new feature
labels: [enhancement]
body:
  - type: textarea
    id: description
    attributes:
      label: Feature description
      placeholder: What would you like to see?
    validations:
      required: true
  - type: textarea
    id: use_case
    attributes:
      label: Use case
      placeholder: How would this help your workflow?
```

---

## Version management

Consider using `setuptools-scm` for automatic version derivation from git tags:

```toml
[build-system]
requires = ["setuptools>=68", "setuptools-scm>=8", "wheel"]

[tool.setuptools_scm]
version_file = "photonstrust/_version.py"
```

This eliminates manual version bumps. Tag with `git tag v0.1.0` and the
version is automatically set.

---

## Changelog format

Adopt [Keep a Changelog](https://keepachangelog.com/) format:

```markdown
# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- Evidence quality tiers in reliability cards (v1.1)
- Parameter validation layer (`photonstrust/validation.py`)
- PLOB bound sanity check test

### Changed
- Afterpulse jitter ratio now configurable (was hardcoded 0.25)

### Fixed
- GDS extract test compatibility with gdstk polygon round-trip
- Float drift in distance expansion

## [0.1.0] - 2026-02-14

### Added
- Initial release: QKD engine, reliability cards, graph compiler
- Multi-band support (NIR, O-band, C-band)
- QuTiP and analytic physics backends
- Streamlit dashboard, FastAPI server
- PIC simulation and GDS extraction
- Satellite orbit models
```

---

## Summary

| Improvement | Effort | Impact |
|-------------|--------|--------|
| Expand pyproject.toml fields | Low | High (PyPI, discoverability) |
| Add CITATION.cff | Low | Medium (academic adoption) |
| Add issue templates | Low | Medium (community engagement) |
| Add LICENSE file | Low | High (legal clarity) |
| Adopt Keep a Changelog | Low | Medium (release communication) |
| setuptools-scm versioning | Low | Medium (prevents version drift) |
| Add docs build system | Medium | High (documentation site) |
