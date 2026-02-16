# 06 - Dependency & Security Findings

---

## Research Anchors (Supply Chain / Vulnerability Scanning)

- pip-audit (PyPA) docs: https://github.com/pypa/pip-audit
- OSV (vulnerability database + API): https://osv.dev/
- NIST SSDF: NIST SP 800-218, DOI: 10.6028/NIST.SP.800-218
- SLSA provenance levels/spec: https://slsa.dev/spec/v1.2/
- in-toto (supply chain integrity metadata): https://in-toto.io/
- Sigstore (signing / verification ecosystem): https://www.sigstore.dev/
- GitHub Dependabot configuration reference: https://docs.github.com/en/code-security/dependabot/dependabot-version-updates/configuration-options-for-the-dependabot.yml-file

## Finding 1: Outdated dependency lower bounds

This finding is less about "the latest version number" and more about
preventing **silent breakage** (new majors) while still tracking ecosystem
progress.

| Dependency | Current lower bound | Upgrade policy / notes |
|------------|---------------------|------------------------|
| numpy | `>= 1.24` | Add CI coverage for numpy 2.x. If compatible, prefer `numpy>=1.24,<3`. |
| qutip | `>= 4.7` | Test qutip 5.x in CI (optional dep). Keep lower bound for back-compat. |
| qiskit | `>= 1.0` (optional) | Codebase has stubs only. Either remove the extra until implemented, or ship a minimal working backend. |
| matplotlib | `>= 3.7` | Low risk; keep lower bound and rely on CI to catch breakage. |
| fastapi | `>= 0.110` (optional) | Track actively; pin only if regressions appear. |
| streamlit | `>= 1.28` (optional) | Track actively; pin only if regressions appear. |

**Correction:**

1. **numpy:** Test with both 1.x and 2.x. Update pin to `numpy>=1.24,<3`.
   Add CI matrix row for numpy 2.x to catch breakage.

2. **qutip:** Test migration to 5.x. The solver API changed:
   ```python
   # qutip 4.x
   result = qutip.mesolve(H, rho0, tlist, c_ops)
   # qutip 5.x (same API, but internal changes)
   result = qutip.mesolve(H, rho0, tlist, c_ops)  # mostly compatible
   ```
   Update pin to `qutip>=4.7` (keeps backward compat) and test with 5.x in CI.

3. **qiskit:** The codebase only has protocol stubs for Qiskit. Either:
   - Remove `qiskit` from dependencies until implementation exists
   - Or implement the circuit backend and update to `qiskit>=1.0`

**Recommended pyproject.toml changes:**

```toml
dependencies = [
    "numpy>=1.24",
    "pyyaml>=6.0",
    "matplotlib>=3.7",
]

[project.optional-dependencies]
qutip = ["qutip>=4.7"]
# qiskit = ["qiskit>=1.0"]  # Uncomment when circuit backend is implemented
```

---

## Finding 2: No SECURITY.md or vulnerability disclosure process

**Issue:** No way for security researchers to report vulnerabilities. No
process for handling CVEs in dependencies.

**Correction:** Create `SECURITY.md`:

```markdown
# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in PhotonTrust, please report it
responsibly:

1. **Do not** open a public GitHub issue.
2. Email security@photonstrust.dev (or use GitHub Security Advisories).
3. Include: description, reproduction steps, impact assessment.
4. We will acknowledge within 48 hours and provide a fix timeline.

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |

## Dependency Scanning

We use `pip-audit` in CI and Dependabot for automated vulnerability detection.
```

---

## Finding 3: No dependency scanning in CI

**Issue:** No automated CVE detection for Python or Node.js dependencies.

**Correction:**

1. Add `pip-audit` to CI (see doc 04).
2. Enable GitHub Dependabot (see doc 04).
3. For the web frontend, add `npm audit` to CI:

```yaml
- name: Audit Node dependencies
  working-directory: web
  run: npm audit --production || true
```

---

## Finding 4: Web frontend installs must remain deterministic

**Location:** `web/` directory

**Issue:** Deterministic installs require a committed lockfile and CI using
`npm ci` (not `npm install`). PhotonTrust currently has `web/package-lock.json`;
the main risk is accidental removal or CI drift.

**Correction:**

1. Ensure `web/package-lock.json` remains committed.
2. In CI, use `npm ci` instead of `npm install`.
3. Optionally add `npm audit` (Finding 3) for baseline CVE visibility.

---

## Finding 5: Qiskit dependency is a stub

**Location:** `photonstrust/protocols/circuits.py` (stub only)

**Issue:** `qiskit>=1.0` is listed as an optional dependency, but the codebase
only contains protocol constant stubs. Users who install `.[qiskit]` get no
functionality.

**Correction:**

Option A (remove): Remove from pyproject.toml until implemented:
```toml
# qiskit = ["qiskit>=1.0"]  # Planned for v0.3
```

Option B (document): Add a clear note:
```python
# photonstrust/protocols/circuits.py
"""Qiskit circuit backend (planned).

This module is a placeholder. Full Qiskit integration is planned for v0.3.
Currently, protocol circuits are represented as abstract gate sequences.
"""
```

---

## Summary

| Finding | Severity | Action |
|---------|----------|--------|
| Outdated numpy/qutip pins | Medium | Test with latest, update CI matrix |
| No SECURITY.md | Medium | Create vulnerability disclosure policy |
| No dep scanning | Medium | Add pip-audit + Dependabot |
| Web deterministic installs | Low | Keep lockfile + use `npm ci` in CI |
| Qiskit stub misleading | Low | Remove or document clearly |
