# Playwright UI checks

This project uses Playwright checks under `tests/`.

## 1) Install Playwright browser (one time)

```bash
npx playwright install chromium
```

## 2) Run UI tests

Playwright starts the local preview server automatically via `playwright.config.js`:

```bash
npm run test:ui
```

Headed mode:

```bash
npm run test:ui:headed
```

Notes:
- Tests expect `http://127.0.0.1:4173`.
- Current specs:
  - `ui.smoke.spec.js`
  - `ui.workspace.spec.js`
  - `ui.demo.spec.js`
  - `ui.project-flow.spec.js`
  - `ui.a11y.spec.js`
- If you already have preview running, the config reuses it.

Targeted runs:

```bash
npm run test:ui -- tests/ui.smoke.spec.js
npm run test:ui -- tests/ui.workspace.spec.js
npm run test:ui -- tests/ui.demo.spec.js
npm run test:ui -- tests/ui.project-flow.spec.js
npm run test:ui -- tests/ui.a11y.spec.js
```
