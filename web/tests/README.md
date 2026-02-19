# Playwright UI smoke checks

This project uses lightweight Playwright checks under `tests/`.

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
- Specs included: `ui.smoke.spec.js` and `ui.a11y.spec.js`.
- If you already have preview running, the config reuses it.
