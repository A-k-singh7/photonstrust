"""Strict runtime models for config and certificate payloads."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


_ALLOWED_ACCUMULATE_BACKENDS = {"numpy", "jax", "auto"}


class ModelMetadataModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    citation: str = Field(min_length=8)
    validity_domain: str = Field(min_length=8)
    uncertainty_model: str = Field(min_length=8)
    known_failure_regimes: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("known_failure_regimes", mode="before")
    @classmethod
    def _normalize_failure_regimes(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return ()
        rows: list[str] = []
        for raw in value:
            text = str(raw).strip()
            if text:
                rows.append(text)
        return tuple(rows)


class SeedLineageModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seed: int = Field(ge=0)
    source: str = Field(min_length=1)
    deterministic: bool = True


class OrbitProviderProvenanceModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_name: str = Field(min_length=1)
    provider_version: str = Field(min_length=1)
    source_hash: str = Field(min_length=8)
    trust_status: Literal["trusted", "untrusted", "unavailable"]


class SatelliteChainRuntimeModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    execution_mode: Literal["preview", "certification"] = "preview"
    rng_seed: int = Field(default=0, ge=0)
    enforce_trusted_backends: bool = True
    trusted_backends: tuple[str, ...] = ("numpy", "jax", "auto")
    uncertainty_budget: "SatelliteChainUncertaintyBudgetConfigModel" = Field(
        default_factory=lambda: SatelliteChainUncertaintyBudgetConfigModel()
    )

    @field_validator("trusted_backends", mode="before")
    @classmethod
    def _normalize_trusted_backends(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return ("numpy", "jax", "auto")

        rows = tuple(str(raw).strip().lower() for raw in value if str(raw).strip())
        if not rows:
            raise ValueError("trusted_backends must include at least one backend")

        unknown = [name for name in rows if name not in _ALLOWED_ACCUMULATE_BACKENDS]
        if unknown:
            raise ValueError(
                "trusted_backends contains unsupported backends: "
                + ", ".join(sorted(set(unknown)))
            )

        deduped: list[str] = []
        for name in rows:
            if name not in deduped:
                deduped.append(name)
        return tuple(deduped)


class SatelliteChainUncertaintyBudgetConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    rollup_method: Literal["rss"] = "rss"
    max_total_sigma_cps: float | None = Field(default=None, ge=0.0)
    require_complete: bool = True
    required_components: tuple[str, ...] = (
        "orbit_provider_sigma_cps",
        "parity_derived_sigma_cps",
    )

    @field_validator("required_components", mode="before")
    @classmethod
    def _normalize_required_components(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return (
                "orbit_provider_sigma_cps",
                "parity_derived_sigma_cps",
            )
        rows: list[str] = []
        for raw in value:
            text = str(raw).strip()
            if text and text not in rows:
                rows.append(text)
        return tuple(rows)


class SatelliteChainComputeModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    accumulate_backend: Literal["numpy", "jax", "auto"] = "numpy"


class SatelliteChainOrbitProviderModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="analytic", min_length=1)
    allow_fallback: bool = True
    trusted_providers: tuple[str, ...] = ("analytic",)
    expected_version: str | None = None
    expected_source_hash: str | None = None
    max_uncertainty_sigma_cps: float | None = Field(default=None, ge=0.0)
    reference_provider: str | None = None
    require_parity: bool = False
    tle_line1: str | None = None
    tle_line2: str | None = None
    tle_source: str | None = None
    parity_max_start_end_delta_s: float = Field(default=30.0, ge=0.0)
    parity_max_peak_elevation_delta_deg: float = Field(default=5.0, ge=0.0)
    parity_max_peak_slant_range_delta_km: float = Field(default=250.0, ge=0.0)
    parity_max_sample_count_delta: int = Field(default=20, ge=0)

    @field_validator("trusted_providers", mode="before")
    @classmethod
    def _normalize_trusted_providers(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return ("analytic",)
        rows = tuple(str(raw).strip() for raw in value if str(raw).strip())
        if not rows:
            raise ValueError("trusted_providers must include at least one provider")
        deduped: list[str] = []
        for name in rows:
            if name not in deduped:
                deduped.append(name)
        return tuple(deduped)


class SatelliteChainMissionModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str = Field(default="satellite_chain", min_length=1)
    compute: SatelliteChainComputeModel = Field(default_factory=SatelliteChainComputeModel)
    runtime: SatelliteChainRuntimeModel = Field(default_factory=SatelliteChainRuntimeModel)
    orbit_provider: SatelliteChainOrbitProviderModel = Field(default_factory=SatelliteChainOrbitProviderModel)


class SatelliteChainConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "0.1"
    satellite_qkd_chain: SatelliteChainMissionModel


class SatelliteChainCertificateInputsModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config_hash: str = Field(min_length=8)
    protocol: str = Field(min_length=1)
    accumulate_backend: Literal["numpy", "jax", "auto"]
    output_dir: str | None = None
    signing_key: str | None = None
    execution_mode: Literal["preview", "certification"] = "preview"
    seed_lineage: SeedLineageModel
    model_metadata: dict[str, ModelMetadataModel] = Field(default_factory=dict)
    orbit_provider: OrbitProviderProvenanceModel


class SatelliteChainGroundStationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    latitude_deg: float = Field(ge=-90.0, le=90.0)
    pic_cert_run_id: str | None = None
    eta_chip: float = Field(ge=0.0, le=1.0)
    eta_ground_terminal: float = Field(ge=0.0, le=1.0)


class SatelliteChainPassModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    altitude_km: float = Field(gt=0.0)
    elevation_min_deg: float = Field(ge=0.0, le=90.0)
    pass_duration_s: float = Field(ge=0.0)
    samples_evaluated: int = Field(ge=0)
    samples_with_positive_key_rate: int = Field(ge=0)
    key_bits_accumulated: float = Field(ge=0.0)
    mean_key_rate_bps: float = Field(ge=0.0)
    peak_key_rate_bps: float = Field(ge=0.0)
    peak_elevation_deg: float = Field(ge=0.0, le=90.0)


class SatelliteChainAnnualEstimateModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passes_per_day: float = Field(ge=0.0)
    clear_sky_probability: float = Field(ge=0.0, le=1.0)
    key_bits_per_year: float = Field(ge=0.0)
    key_mbits_per_year: float = Field(ge=0.0)
    notes: str | None = None


class SatelliteChainSignoffModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["GO", "HOLD"]
    key_rate_positive_at_zenith: bool
    annual_key_above_1mbit: bool
    provider_trusted: bool
    provider_parity_ok: bool
    provider_uncertainty_ok: bool
    uncertainty_budget_complete: bool
    uncertainty_budget_within_threshold: bool
    uncertainty_budget_ok: bool
    orbit_provider_trust_status: Literal["trusted", "untrusted", "unavailable"]
    hold_reasons: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("hold_reasons", mode="before")
    @classmethod
    def _normalize_hold_reasons(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return ()
        rows: list[str] = []
        for raw in value:
            text = str(raw).strip()
            if text:
                rows.append(text)
        return tuple(rows)


class SatelliteChainCertificateModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_version: Literal["0.1"]
    kind: Literal["satellite_qkd_chain_certificate"]
    run_id: str = Field(min_length=1)
    generated_at: str = Field(min_length=1)
    mission: str = Field(min_length=1)
    inputs: SatelliteChainCertificateInputsModel
    ground_station: SatelliteChainGroundStationModel
    pass_section: SatelliteChainPassModel = Field(alias="pass")
    uncertainty_budget: "SatelliteChainUncertaintyBudgetModel"
    annual_estimate: SatelliteChainAnnualEstimateModel | None = None
    signoff: SatelliteChainSignoffModel
    signature: dict[str, Any] | None = None
    artifacts: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)


def validate_satellite_chain_config(config: dict[str, Any]) -> SatelliteChainConfigModel:
    return SatelliteChainConfigModel.model_validate(config)


def validate_satellite_chain_certificate(certificate: dict[str, Any]) -> SatelliteChainCertificateModel:
    return SatelliteChainCertificateModel.model_validate(certificate)


class SatelliteChainUncertaintyBudgetComponentModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    sigma_cps: float | None = Field(default=None, ge=0.0)
    present: bool
    source: str = Field(min_length=1)


class SatelliteChainUncertaintyBudgetModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool
    rollup_method: Literal["rss"]
    required_components: tuple[str, ...] = Field(default_factory=tuple)
    missing_components: tuple[str, ...] = Field(default_factory=tuple)
    components: tuple[SatelliteChainUncertaintyBudgetComponentModel, ...] = Field(default_factory=tuple)
    total_sigma_cps: float = Field(ge=0.0)
    max_allowed_sigma_cps: float | None = Field(default=None, ge=0.0)
    is_complete: bool
    within_threshold: bool
    pass_: bool = Field(alias="pass")

    @field_validator("required_components", "missing_components", mode="before")
    @classmethod
    def _normalize_budget_components(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return ()
        rows: list[str] = []
        for raw in value:
            text = str(raw).strip()
            if text and text not in rows:
                rows.append(text)
        return tuple(rows)
