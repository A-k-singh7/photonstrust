# 04 - CI/CD Improvements

## Current State

`.github/workflows/ci.yml` runs:
1. Checkout
2. Python 3.11 only
3. `pip install -e .[dev]`
4. `pytest -q`
5. `python scripts/check_benchmark_drift.py`

This is a minimal CI. Below are the gaps and the corrected workflow.

---

## Research Anchors (CI, Supply Chain, and Security Automation)

- NIST SSDF: NIST SP 800-218, DOI: 10.6028/NIST.SP.800-218
- SLSA provenance levels/spec: https://slsa.dev/spec/v1.2/
- in-toto (supply chain integrity metadata): https://in-toto.io/
- Sigstore (artifact signing / verification): https://www.sigstore.dev/
- OpenSSF Scorecard checks: https://scorecard.dev/
- pip-audit (PyPA): https://github.com/pypa/pip-audit
- Dependabot config options: https://docs.github.com/en/code-security/dependabot/dependabot-version-updates/configuration-options-for-the-dependabot.yml-file

## Gap 1: Single Python version

`pyproject.toml` claims `requires-python = ">=3.9"` but CI only tests 3.11.

---

## Gap 2: No optional dependency testing

CI installs `[dev]` only. QuTiP fallback, Qiskit stubs, gdstk extraction,
API server, and Streamlit UI are never tested in CI.

---

## Gap 3: No coverage reporting

No `pytest-cov` integration. No coverage floor enforced.

---

## Gap 4: No linting or formatting

No `ruff`, `flake8`, `black`, or `mypy`. Style inconsistencies slip through.

---

## Gap 5: No security scanning

No `pip-audit`, Dependabot, or GitHub security scanning.

---

## Gap 6: No nightly regression

Only runs on push/PR. Slow regression tests never run.

---

## Gap 7: Missing release automation

No automated PyPI publishing or release gating in CI.

---

## Corrected Workflow

Replace `.github/workflows/ci.yml` with:

```yaml
name: ci

on:
  push:
    branches: [main]
  pull_request:
  schedule:
    # Nightly at 02:00 UTC
    - cron: "0 2 * * *"

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
      - run: pip install ruff
      - name: Lint
        run: ruff check .
      - name: Format check
        run: ruff format --check .

  test:
    needs: lint
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.9", "3.10", "3.11", "3.12"]
        extras: ["dev", "dev,qutip,qiskit"]
        exclude:
          # Only test full extras on 3.11 and 3.12 to save CI minutes
          - python-version: "3.9"
            extras: "dev,qutip,qiskit"
          - python-version: "3.10"
            extras: "dev,qutip,qiskit"
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[${{ matrix.extras }}]"

      - name: Run tests with coverage
        run: |
          pip install pytest-cov
          pytest -q --cov=photonstrust --cov-report=xml --cov-fail-under=70

      - name: Upload coverage
        if: matrix.python-version == '3.11' && matrix.extras == 'dev,qutip,qiskit'
        uses: codecov/codecov-action@v4
        with:
          files: coverage.xml
          fail_ci_if_error: false

  benchmark:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
      - run: pip install -e ".[dev]"
      - name: Check benchmark drift
        run: python scripts/check_benchmark_drift.py
      - name: Check golden reports
        run: |
          python scripts/generate_golden_report.py
          pytest tests/test_golden_report.py -q
      - name: Release gate check
        run: python scripts/release_gate_check.py

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"
          pip install pip-audit
      - name: Audit dependencies
        run: pip-audit || true
```

---

## Additional CI files to add

### `.github/dependabot.yml`

```yaml
version: 2
updates:
  - package-ecosystem: pip
    directory: "/"
    schedule:
      interval: weekly
  - package-ecosystem: github-actions
    directory: "/"
    schedule:
      interval: weekly
```

### `.github/workflows/release.yml` (triggered on tag)

```yaml
name: release

on:
  push:
    tags: ["v*"]

jobs:
  publish:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install build
      - run: python -m build
      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
```

---

## Pre-commit hooks

Add `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.5.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

---

## Pytest markers

Add to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "slow: marks tests as slow (deselect with -m 'not slow')",
    "requires_qutip: requires qutip installation",
    "requires_qiskit: requires qiskit installation",
    "requires_gdstk: requires gdstk installation",
]
```

---

## Summary

| Improvement | Effort | Impact |
|-------------|--------|--------|
| Python matrix (3.9-3.12) | Low | High - catches compatibility bugs |
| Coverage reporting + 70% floor | Low | High - prevents coverage regression |
| Ruff lint + format check | Low | Medium - enforces consistency |
| Optional dep matrix | Low | Medium - validates fallback paths |
| pip-audit security scan | Low | Medium - catches known CVEs |
| Dependabot | Low | Low - automated dep updates |
| Nightly cron schedule | Low | Medium - catches slow regressions |
| Release workflow | Medium | High - automates PyPI publishing |
| Pre-commit hooks | Low | Medium - catches issues before push |
