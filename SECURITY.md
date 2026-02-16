# Security Policy

## Supported Versions

Security fixes are applied to the latest active branch.

| Version | Supported |
|---|---|
| 0.1.x | Yes |
| < 0.1.0 | No |

## Reporting a Vulnerability

If you discover a security vulnerability, report it privately first.

- Preferred: open a private GitHub Security Advisory report.
- Fallback: contact maintainers through an existing private channel.

Include the following in your report:

- clear description and affected surface,
- reproduction steps or proof of concept,
- expected impact and likely exploitability,
- version, commit, and environment details.

## Response Targets

- Initial acknowledgement target: within 2 business days.
- Initial triage target: within 5 business days.
- Status updates are shared at least weekly until resolution.

## Coordinated Disclosure

- Do not open a public issue for unpatched vulnerabilities.
- Coordinated disclosure is expected after a fix or mitigation is available.
- Credit is offered in release notes when requested.

## Dependency and Supply-Chain Monitoring

- Dependabot is enabled for Python, npm (`/web`), and GitHub Actions.
- CI workflow `security-baseline` runs `pip-audit` on push, pull request, and
  weekly schedule.
- `pip-audit` is a blocking check for runtime Python dependencies in CI.

## Frontend Deterministic Install Policy

- `web/package-lock.json` is mandatory and must remain committed.
- CI and automation use `npm ci` for deterministic installs.
- `npm install` is for local dependency authoring only and must be followed by
  lockfile review.
- Dependency update pull requests must include lockfile diffs.
