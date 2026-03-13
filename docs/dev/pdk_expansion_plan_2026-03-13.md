# PDK Expansion Plan (2026-03-13)

## Goal

Expand PhotonTrust's manifest-level PDK coverage so the PIC product story is
less generic and more credible for foundry-adjacent workflows.

## Current Problem

PhotonTrust already has:

- internal PIC primitives,
- PDK-aware layout hooks,
- GDS generation,
- KLayout packaging,
- foundry-sealed DRC/LVS/PEX workflow seams,

but the checked-in manifest-level cell catalog is still thin.

This creates a gap between:

1. what the product can do operationally, and
2. how convincing the public PDK/component story looks.

## Expansion Strategy

### Phase 1: deepen AIM illustrative coverage

Update:

- `configs/pdks/aim_photonics.pdk.json`
- `configs/pdks/aim_photonics_300nm_sin.pdk.json`

Status: implemented in the current branch.

Add representative cells for:

1. `phase_shifter`
2. `mmi_2x2` or equivalent coupler/splitter-combiner
3. `waveguide_straight`

Optional if cleanly justified:

4. a ring variant with clearer naming,
5. an illustrative bend or taper cell if the manifest model grows to support it.

### Phase 2: tighten generic manifest completeness

Ensure generic manifests cover the same essential core used in the product UI:

- IO coupling
- straight propagation
- splitting/combining
- phase tuning
- resonator path where relevant

Status: phase shifter coverage has also been added to the generic manifests in
the current branch.

### Phase 3: add a second public-facing adapter family

Add one more documented public-facing ecosystem adapter or illustrative wrapper,
subject to redistribution-safe metadata.

Status: implemented in the current branch via `configs/pdks/siepic_ebeam.pdk.json`
and alias support for `siepic` / `ebeam`.

## Proposed Target Cell Set

### Core target set for one credible PIC workflow

- `grating_coupler_te`
- `edge_coupler_te`
- `waveguide_straight`
- `mmi_2x2`
- `phase_shifter`
- `ring_resonator`

This is enough to support a stronger public story for:

- PIC design setup
- layout build
- GDS export
- extraction and KLayout packaging
- simple resonator/coupler examples

## Testing Plan

Add tests that:

1. load each PDK manifest,
2. assert required component-cell presence for a target set,
3. verify cell metadata consistency:
   - `name`
   - `library`
   - `cell`
   - `ports`
4. fail if AIM or generic manifests regress below the agreed minimum set.

Suggested test file:

- `tests/test_pdk_component_coverage.py`

Status: implemented.

## Documentation Plan

Update after implementation:

1. `configs/pdks/*.json` notes
2. `configs/README.md` if the PDK story changes materially
3. `docs/dev/pdk_component_coverage_matrix_2026-03-13.md`

## Guardrails

1. do not imply foundry-approved production readiness where the data is still
   illustrative,
2. keep the manifests redistribution-safe,
3. avoid embedding NDA-restricted PDK data,
4. prefer explicit notes over vague claims.

## Immediate Next Implementation Wave

1. expand `aim_photonics.pdk.json`
2. expand `aim_photonics_300nm_sin.pdk.json`
3. add `tests/test_pdk_component_coverage.py`
4. run targeted PDK and PIC tests

## Current Branch Outcome

The current branch now provides:

1. deeper AIM illustrative coverage,
2. stronger generic manifest completeness,
3. a second public-facing illustrative adapter family (`siepic_ebeam`),
4. a documented internal-kind to manifest-cell mapping table,
5. regression tests that fail if this minimum coverage bar regresses,
6. support-level metadata (`modeled`, `layout_only`, `characterized_external`) on public-facing adapter cells,
7. more than twenty additional manifest-level component entries across the expanded public-facing catalogs relative to the original baseline.
