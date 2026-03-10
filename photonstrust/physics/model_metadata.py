"""Research-traceable metadata registry for production physics models."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from photonstrust.workflow.runtime_models import ModelMetadataModel


MODEL_METADATA_REGISTRY: dict[str, ModelMetadataModel] = {
    "orbit.pass_geometry.effective_thickness": ModelMetadataModel(
        citation=(
            "Vallado, D. A. Fundamentals of Astrodynamics and Applications, "
            "4th ed., Microcosm Press, 2013."
        ),
        validity_domain="LEO passes (300-1200 km), elevation 5-90 deg, dt >= 1 s.",
        uncertainty_model="Parametric sensitivity over extinction and turbulence settings.",
        known_failure_regimes=(
            "Non-LEO mission classes without dedicated orbit propagator validation.",
            "Extreme weather not captured by effective-thickness atmosphere model.",
        ),
    ),
    "channel.free_space.attenuation": ModelMetadataModel(
        citation="Bourgoin et al., Optics Express 21(1):1040-1062 (2013), doi:10.1364/OE.21.001040.",
        validity_domain="Clear-sky free-space QKD links with fixed-parameter atmosphere model.",
        uncertainty_model="Scintillation and background-rate perturbation with bounded inputs.",
        known_failure_regimes=(
            "Cloud-obscured and heavy-aerosol conditions.",
            "Adaptive optics feedback loops not represented in static attenuation model.",
        ),
    ),
    "detector.click_model.stochastic": ModelMetadataModel(
        citation="Hadfield, Nature Photonics 3, 696-705 (2009), doi:10.1038/nphoton.2009.230.",
        validity_domain="Single-photon detector click/noise simulation with calibrated PDE/DCR/jitter.",
        uncertainty_model="Monte Carlo shot-noise and afterpulse perturbation with explicit seed lineage.",
        known_failure_regimes=(
            "Detector saturation and latching outside calibrated count-rate envelope.",
            "Cryogenic drift without updated calibration inputs.",
        ),
    ),
    "qkd.bb84_decoy_asymptotic": ModelMetadataModel(
        citation="Lo, Ma, Chen, Phys. Rev. Lett. 94, 230504 (2005), doi:10.1103/PhysRevLett.94.230504.",
        validity_domain="Asymptotic decoy-state BB84 analysis with trusted source assumptions.",
        uncertainty_model="Propagation through channel and detector uncertainty bundles.",
        known_failure_regimes=(
            "Finite-key regimes when asymptotic approximation dominates security margin.",
            "Source side-channel leakage beyond modeled misalignment term.",
        ),
    ),
    "qkd.bbm92_asymptotic": ModelMetadataModel(
        citation="Bennett, Brassard, Mermin, Phys. Rev. Lett. 68, 557 (1992), doi:10.1103/PhysRevLett.68.557.",
        validity_domain="Entanglement-based BBM92 asymptotic key-rate estimation.",
        uncertainty_model="Background and visibility uncertainty propagated into QBER bounds.",
        known_failure_regimes=(
            "Finite-size effects without finite-key correction lane enabled.",
            "Multi-pair emissions outside configured source purity assumptions.",
        ),
    ),
    "backend.qiskit.repeater_primitive": ModelMetadataModel(
        citation="Qiskit documentation and SDK reference, https://qiskit.org/documentation.",
        validity_domain="Circuit-level repeater primitive parity checks for Bell-state swap probability.",
        uncertainty_model="Deterministic simulator parity threshold (absolute delta tolerance).",
        known_failure_regimes=(
            "Hardware execution noise not represented in statevector simulation mode.",
        ),
    ),
    "backend.qutip.emitter": ModelMetadataModel(
        citation="Johansson et al., Comput. Phys. Commun. 183, 1760-1772 (2012), doi:10.1016/j.cpc.2012.02.021.",
        validity_domain="Emitter dynamics in Lindblad/open-system form with calibrated cavity parameters.",
        uncertainty_model="Scenario-level Monte Carlo over cavity and dephasing parameters.",
        known_failure_regimes=(
            "Model mismatch for strongly driven non-Markovian emitter regimes.",
        ),
    ),
}


_BACKEND_MODEL_KEYS: dict[str, tuple[str, ...]] = {
    "analytic": (
        "qkd.bb84_decoy_asymptotic",
        "channel.free_space.attenuation",
    ),
    "stochastic": (
        "detector.click_model.stochastic",
    ),
    "qiskit": (
        "backend.qiskit.repeater_primitive",
    ),
    "qutip": (
        "backend.qutip.emitter",
    ),
}


def validate_model_metadata_registry(
    registry: Mapping[str, ModelMetadataModel | Mapping[str, Any]] | None = None,
) -> dict[str, ModelMetadataModel]:
    source = MODEL_METADATA_REGISTRY if registry is None else dict(registry)
    validated: dict[str, ModelMetadataModel] = {}
    for key, raw in source.items():
        name = str(key).strip()
        if not name:
            raise ValueError("model metadata key cannot be empty")
        if isinstance(raw, ModelMetadataModel):
            validated[name] = raw
        else:
            validated[name] = ModelMetadataModel.model_validate(raw)
    return validated


def model_metadata_for_keys(keys: Sequence[str]) -> dict[str, dict[str, Any]]:
    registry = validate_model_metadata_registry()
    payload: dict[str, dict[str, Any]] = {}
    for raw in keys:
        key = str(raw).strip()
        model = registry.get(key)
        if model is None:
            continue
        payload[key] = model.model_dump()
    return payload


def model_metadata_for_backend(backend_name: str) -> dict[str, dict[str, Any]]:
    normalized = str(backend_name or "").strip().lower()
    keys = _BACKEND_MODEL_KEYS.get(normalized, ())
    return model_metadata_for_keys(keys)
