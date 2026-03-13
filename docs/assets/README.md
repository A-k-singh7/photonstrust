# Documentation Assets

Use this directory for curated screenshots, diagrams, and other static assets
referenced by the main README or user-facing docs.

Suggested first additions:

- React landing screen screenshot
- compare / decision review screenshot
- certification / evidence screenshot
- PIC GDS and KLayout workflow screenshot

## Current Assets

- `ui-landing.png`
  - first-run landing and capability framing
- `ui-decision-review.png`
  - compare / decision review journey
- `ui-certification.png`
  - certification, approvals, and evidence export flow
- `ui-pic-gds-layout.png`
  - PIC setup and GDS/layout workflow surface

## Refreshing Screenshots

From the repository root:

```bash
cd web
node tests/helpers/capture-doc-assets.mjs
```
