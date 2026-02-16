# 03 - Configuration & Validation Gaps

---

## Research Anchors (Schema + Validation Tooling)

- JSON Schema (general): https://json-schema.org/
- JSON Schema draft 2020-12 (the `$schema` used in proposed examples): https://json-schema.org/draft/2020-12/json-schema-core.html
- Pydantic docs (runtime validation + types): https://docs.pydantic.dev/
- TypedDict (static typing for dict-shaped configs): PEP 589 https://peps.python.org/pep-0589/

## Status (2026-02-14)

- Implemented: lightweight scenario validation (`photonstrust/validation.py`) and `photonstrust run --validate-only`
  (see `docs/operations/phased_rollout/phase_38_config_validation_cli_validate_only/`).
- Not yet implemented: scenario `schema_version` + migrations, TypedDict/Pydantic migration, API-side jsonschema hard requirement.

## Finding 1: No runtime parameter validation after config loading

**Location:** `photonstrust/config.py` (all `_apply_*_defaults()` functions)

**Issue:** Defaults are applied via `setdefault()`, but no validation ensures
values are within physically meaningful ranges. A user could set `pde: 2.0` or
`connector_loss_db: -5` and the engine would proceed without warning.

**Correction:** Add a `validate_scenario()` function called after
`build_scenarios()`:

```python
# photonstrust/validation.py (new file)

from __future__ import annotations

class ConfigValidationError(ValueError):
    pass

_RULES = [
    # (path, check_fn, message)
    ("source.rep_rate_mhz",       lambda v: v > 0,          "must be > 0"),
    ("source.collection_efficiency", lambda v: 0 <= v <= 1, "must be in [0, 1]"),
    ("source.coupling_efficiency",   lambda v: 0 <= v <= 1, "must be in [0, 1]"),
    ("source.g2_0",                  lambda v: 0 <= v <= 1, "must be in [0, 1]"),
    ("source.mu",                    lambda v: v >= 0,      "must be >= 0"),
    ("detector.pde",                 lambda v: 0 <= v <= 1, "must be in [0, 1]"),
    ("detector.dark_counts_cps",     lambda v: v >= 0,      "must be >= 0"),
    ("detector.jitter_ps_fwhm",      lambda v: v >= 0,      "must be >= 0"),
    ("detector.dead_time_ns",        lambda v: v >= 0,      "must be >= 0"),
    ("detector.afterpulsing_prob",   lambda v: 0 <= v <= 1, "must be in [0, 1]"),
    ("channel.fiber_loss_db_per_km", lambda v: v >= 0,      "must be >= 0"),
    ("channel.connector_loss_db",    lambda v: v >= 0,      "must be >= 0"),
    ("timing.sync_drift_ps_rms",     lambda v: v >= 0,      "must be >= 0"),
]

def validate_scenario(scenario: dict) -> list[str]:
    """Validate a built scenario. Returns list of error messages (empty = OK)."""
    errors = []
    for path, check_fn, msg in _RULES:
        parts = path.split(".")
        value = scenario
        try:
            for part in parts:
                value = value[part]
        except (KeyError, TypeError):
            continue  # Optional field, skip
        try:
            if not check_fn(float(value)):
                errors.append(f"{path} = {value}: {msg}")
        except (ValueError, TypeError):
            errors.append(f"{path} = {value}: not a valid number")
    return errors
```

**Integration point:** In `photonstrust/sweep.py` or `cli.py`:

```python
from photonstrust.validation import validate_scenario, ConfigValidationError

for scenario in scenarios:
    errors = validate_scenario(scenario)
    if errors:
        raise ConfigValidationError(
            f"Invalid scenario '{scenario['scenario_id']}':\n" +
            "\n".join(f"  - {e}" for e in errors)
        )
```

**Implemented (v0.1.1):**
- `photonstrust/validation.py` exists and is called by `photonstrust/cli.py` for scenario runs (fail-fast).

---

## Finding 2: No config schema versioning for scenarios

**Location:** All `configs/*.yml` files

**Issue:** Graph configs have `schema_version: "0.1"` but scenario configs do
not. If the config format changes (e.g., renaming `dephasing_rate_per_ns`),
there is no way to detect or migrate old configs.

**Correction:**

1. Add `schema_version` to all scenario configs:

```yaml
# configs/demo1_default.yml
schema_version: "0.1"
scenario:
  id: demo1_default
  ...
```

2. Validate in `config.py`:

```python
CURRENT_SCHEMA_VERSION = "0.1"
SUPPORTED_VERSIONS = {"0.1"}

def load_config(path):
    config = yaml.safe_load(...)
    version = config.get("schema_version", "0.1")
    if version not in SUPPORTED_VERSIONS:
        raise ValueError(
            f"Config schema version {version!r} not supported. "
            f"Supported: {SUPPORTED_VERSIONS}"
        )
    return config
```

3. When breaking changes occur, bump the version and add a migration function:

```python
_MIGRATIONS = {
    ("0.1", "0.2"): _migrate_0_1_to_0_2,
}
```

---

## Finding 3: Dict structures not formally defined

**Issue:** Scenario, channel, detector, source, and timing configs are bare
`dict` objects with no formal schema. This makes it easy to misspell keys,
use wrong types, or miss required fields.

**Correction (immediate):** Use `TypedDict` for type checking:

```python
# photonstrust/types.py

from __future__ import annotations
from typing import TypedDict

class SourceConfig(TypedDict, total=False):
    type: str                     # required: "emitter_cavity" | "spdc"
    rep_rate_mhz: float
    collection_efficiency: float
    coupling_efficiency: float
    physics_backend: str
    emission_mode: str
    # emitter_cavity specific
    radiative_lifetime_ns: float
    purcell_factor: float
    dephasing_rate_per_ns: float
    g2_0: float
    drive_strength: float
    pulse_window_ns: float
    # spdc specific
    mu: float

class ChannelConfig(TypedDict, total=False):
    model: str                    # "fiber" | "free_space"
    fiber_loss_db_per_km: float
    dispersion_ps_per_km: float
    connector_loss_db: float
    # free_space specific
    elevation_deg: float
    tx_aperture_m: float
    rx_aperture_m: float
    beam_divergence_urad: float | None
    pointing_jitter_urad: float
    atmospheric_extinction_db_per_km: float
    turbulence_scintillation_index: float
    background_counts_cps: float

class DetectorConfig(TypedDict, total=False):
    class_: str  # "class" in YAML, renamed to avoid Python keyword
    pde: float
    dark_counts_cps: float
    jitter_ps_fwhm: float
    dead_time_ns: float
    afterpulsing_prob: float
    afterpulse_delay_ns: float
    physics_backend: str
    sample_count: int
    time_bin_ps: float
    background_counts_cps: float

class ScenarioConfig(TypedDict, total=False):
    scenario_id: str
    band: str
    wavelength_nm: float
    distances_km: list[float]
    source: SourceConfig
    channel: ChannelConfig
    detector: DetectorConfig
    timing: dict
    protocol: dict
    uncertainty: dict
    finite_key: dict
    execution_mode: str
```

**Correction (v0.2):** Migrate to Pydantic models for runtime validation:

```python
from pydantic import BaseModel, Field, field_validator

class SourceConfig(BaseModel):
    type: str
    rep_rate_mhz: float = Field(gt=0)
    collection_efficiency: float = Field(ge=0, le=1)
    coupling_efficiency: float = Field(ge=0, le=1)
    physics_backend: str = "analytic"

    @field_validator("type")
    @classmethod
    def validate_type(cls, v):
        if v not in ("emitter_cavity", "spdc"):
            raise ValueError(f"Unknown source type: {v}")
        return v
```

---

## Finding 4: jsonschema is optional and silently degrades

**Location:** `photonstrust/graph/schema.py`

**Issue:** Graph validation gracefully skips if `jsonschema` is not installed.
In the API server, this means malformed graph JSON is silently accepted.

**Correction:** Make schema validation mandatory in the API server:

```python
# photonstrust/api/server.py

def _validate_graph(graph_data: dict):
    try:
        import jsonschema
    except ImportError:
        raise RuntimeError(
            "jsonschema is required for API server graph validation. "
            "Install with: pip install 'photonstrust[dev]'"
        )
    from photonstrust.graph.schema import validate_graph
    validate_graph(graph_data)  # raises on error
```

---

## Finding 5: CLI lacks `--validate-only` flag

**Issue:** Users must run the full (expensive) simulation to discover config
errors. No way to dry-run and check config validity.

**Correction:** Add to `cli.py`:

```python
@cli.command()
@click.argument("config_path")
@click.option("--validate-only", is_flag=True, help="Validate config without running simulation")
def run(config_path, validate_only):
    config = load_config(config_path)
    scenarios = build_scenarios(config)
    for s in scenarios:
        errors = validate_scenario(s)
        if errors:
            click.echo(f"INVALID: {s['scenario_id']}")
            for e in errors:
                click.echo(f"  - {e}")
            raise SystemExit(1)
    if validate_only:
        click.echo(f"OK: {len(scenarios)} scenario(s) valid")
        return
    # ... proceed with simulation
```

**Implemented (v0.1.1):** `photonstrust run --validate-only` is now available (argparse CLI).

---

## Summary

| # | Finding | Severity | Fix |
|---|---------|----------|-----|
| 1 | No runtime param validation | Critical | Add `validate_scenario()` |
| 2 | No config versioning | High | Add `schema_version` field |
| 3 | No formal type definitions | Medium | TypedDict now, Pydantic later |
| 4 | jsonschema silently optional | Medium | Require in API server |
| 5 | No validate-only CLI mode | Medium | Add `--validate-only` flag |
