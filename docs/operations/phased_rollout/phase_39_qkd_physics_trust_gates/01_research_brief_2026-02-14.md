# Phase 39 - QKD Physics Trust Gates (PLOB + Seeded Uncertainty + Airmass Model)

Date: 2026-02-14

## Goal

Add three "physics trust gates" that harden PhotonTrust outputs against:

- unphysical key-rate results (PLOB bound sanity),
- non-reproducible uncertainty bands (configurable seeding), and
- known-bad free-space link loss estimates at low elevation (airmass proxy).

This phase is intentionally scoped as *gates and correctness hardening*, not a full model upgrade.

## Primary Sources (Anchor References)

- PLOB repeaterless bound / rate-loss benchmark: Pirandola et al. (2017), Nature Communications, DOI: 10.1038/ncomms15043
- Optical airmass at low elevation: Kasten & Young (1989), Applied Optics, DOI: 10.1364/AO.28.004735

## Why These Gates Are High Leverage

1. PLOB sanity gate (fiber/free-space key-rate vs transmittance)
   - If a simple link model exceeds fundamental repeaterless bounds, it is a "stop the line" issue.
   - Even if the engine is conservative (often is), having an explicit bound test prevents regressions.
   - Note: protocol families that rely on intermediate measurement stations (e.g. TF-QKD) can exceed a
     direct-channel PLOB comparison. This repo does not implement TF/PM-QKD yet, so the check is safe
     as a baseline gate for current `compute_point()` usage.

2. Seeded uncertainty
   - Uncertainty bands must be reproducible for review, diffs, and evidence bundles.
   - A hardcoded seed is reproducible but not controllable; scientific workflows require explicit seeds.
   - Per-sample deterministic seeds (seed_base + sample_idx) keep results stable even if sampling is
     later parallelized.

3. Airmass model upgrade
   - The earlier plane-parallel `1/sin(h)` proxy becomes inaccurate or unstable near the horizon.
   - Kasten & Young (1989) is a standard empirical approximation that remains finite at low elevations.
   - Low elevation remains sensitive even with improved airmass; emit a warning below 5 degrees to
     make the regime explicit in logs/evidence.

## Scope Decisions

- Keep the uncertainty output format unchanged (dict keyed by distance) to avoid breaking report/card wiring.
- Implement Kasten & Young airmass inside `channels/free_space.py` without adding new config flags yet.
- Implement PLOB check as a unit test gate (not an in-engine runtime assertion) to avoid false positives
  for future protocols; revisit when TF/MDI models land.
