"""Smart error classes with suggestions and remediation guidance."""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Available resource catalogs (used by suggestion catalog and error messages)
# ---------------------------------------------------------------------------

AVAILABLE_PROTOCOLS = (
    "bbm92", "bb84_decoy", "mdi_qkd", "amdi_qkd",
    "pm_qkd", "tf_qkd", "cv_qkd", "sns_tf_qkd", "di_qkd",
)

AVAILABLE_BANDS = ("nir_795", "nir_850", "o_1310", "c_1550")

AVAILABLE_DETECTORS = ("si_apd", "ingaas", "snspd")

# ---------------------------------------------------------------------------
# Base exception
# ---------------------------------------------------------------------------


class PhotonsTrustError(Exception):
    """Base exception for PhotonsTrust with suggestion support."""

    def __init__(
        self,
        message: str,
        *,
        suggestion: str = "",
        doc_link: str = "",
        context: dict | None = None,
    ):
        self.suggestion = suggestion
        self.doc_link = doc_link
        self.context = context or {}
        super().__init__(message)

    def __str__(self) -> str:
        parts = [super().__str__()]
        if self.suggestion:
            parts.append(f"\n  Suggestion: {self.suggestion}")
        if self.doc_link:
            parts.append(f"\n  See: {self.doc_link}")
        return "".join(parts)


# ---------------------------------------------------------------------------
# Concrete error subclasses
# ---------------------------------------------------------------------------


class ConfigError(PhotonsTrustError, ValueError):
    """Invalid configuration parameters."""


class PhysicsError(PhotonsTrustError, RuntimeError):
    """Physics constraint violation (e.g. negative loss, fidelity > 1)."""


class DependencyError(PhotonsTrustError, ImportError):
    """Missing optional dependency."""


class ProtocolError(PhotonsTrustError, ValueError):
    """Unknown or misconfigured QKD protocol."""


class ComponentError(PhotonsTrustError, ValueError):
    """Unknown or misconfigured PIC component."""


class ValidationError(PhotonsTrustError, ValueError):
    """Input validation failure."""


class NetworkError(PhotonsTrustError, ValueError):
    """Network topology or routing error."""


# ---------------------------------------------------------------------------
# Suggestion catalog  (~20 entries)
# ---------------------------------------------------------------------------

_SUGGESTION_CATALOG: list[tuple[re.Pattern[str], str]] = [
    # Protocol errors
    (
        re.compile(r"(?i)unsupported.*protocol|unknown.*protocol"),
        f"Available protocols: {', '.join(AVAILABLE_PROTOCOLS)}.",
    ),
    (
        re.compile(r"(?i)protocol.*not\s+found"),
        f"Check spelling. Available protocols: {', '.join(AVAILABLE_PROTOCOLS)}.",
    ),
    # Band / wavelength errors
    (
        re.compile(r"(?i)unknown\s+band|unsupported\s+band|invalid\s+band"),
        f"Available bands: {', '.join(AVAILABLE_BANDS)}.",
    ),
    (
        re.compile(r"(?i)wavelength.*out\s+of\s+range"),
        "Ensure wavelength_nm matches the selected band preset.",
    ),
    # Detector errors
    (
        re.compile(r"(?i)unknown\s+detector|unsupported\s+detector|invalid\s+detector"),
        f"Available detector classes: {', '.join(AVAILABLE_DETECTORS)}.",
    ),
    (
        re.compile(r"(?i)detector.*not\s+compatible"),
        "Check band-detector compatibility in presets.DETECTOR_ADJUSTMENTS.",
    ),
    # Physics constraint errors
    (
        re.compile(r"(?i)negative\s+(loss|value|distance|rate)"),
        "Physical quantities like loss, distance, and rate must be non-negative.",
    ),
    (
        re.compile(r"(?i)fidelity.*>\s*1|fidelity.*above\s+1"),
        "Fidelity must be in [0, 1]. Check your source/detector parameters.",
    ),
    (
        re.compile(r"(?i)probability.*>\s*1|probability.*above\s+1"),
        "Probabilities must be in [0, 1].",
    ),
    # Distance configuration errors
    (
        re.compile(r"(?i)distance.*step.*must\s+be.*>.*0"),
        "Use a positive step value, e.g. distance_km: {start: 0, stop: 100, step: 10}.",
    ),
    (
        re.compile(r"(?i)distance.*stop.*>=.*start|distance.*stop.*<.*start"),
        "Ensure stop >= start in distance_km range specification.",
    ),
    (
        re.compile(r"(?i)distance.*must\s+be\s+finite"),
        "Use finite numeric values for distance_km start and stop.",
    ),
    # Config / schema errors
    (
        re.compile(r"(?i)unsupported.*schema.*version"),
        "Migrate your config to schema_version '0.1'. See docs/audit/03_configuration_validation.md.",
    ),
    (
        re.compile(r"(?i)missing.*required.*field|required.*key"),
        "Check your YAML config against the scenario schema documentation.",
    ),
    # Dependency errors
    (
        re.compile(r"(?i)no\s+module\s+named|import.*failed|cannot\s+import"),
        "Install the missing package with: pip install <package-name>.",
    ),
    # Network errors
    (
        re.compile(r"(?i)no\s+route|unreachable\s+node|disconnected"),
        "Verify that the network topology is fully connected.",
    ),
    (
        re.compile(r"(?i)duplicate\s+node|node.*already\s+exists"),
        "Node IDs must be unique within a network topology.",
    ),
    # Component errors
    (
        re.compile(r"(?i)unknown\s+component|component.*not\s+found"),
        "Check the component catalog for available PIC components.",
    ),
    # General validation
    (
        re.compile(r"(?i)must\s+be\s+positive|must\s+be\s+>\s*0"),
        "The parameter requires a positive numeric value.",
    ),
    (
        re.compile(r"(?i)invalid.*config|bad.*configuration"),
        "Review your YAML configuration file for typos or missing keys.",
    ),
]


def suggest_fix(error: BaseException) -> str:
    """Return remediation text if the error message matches a known pattern.

    Parameters
    ----------
    error : BaseException
        The exception whose message should be matched against the catalog.

    Returns
    -------
    str
        A suggestion string if a match is found, otherwise ``""``.
    """
    msg = str(error)
    for pattern, suggestion in _SUGGESTION_CATALOG:
        if pattern.search(msg):
            return suggestion
    return ""
