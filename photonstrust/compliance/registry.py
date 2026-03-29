"""ETSI QKD requirement registry and execution helpers."""

from __future__ import annotations

from typing import Any

from photonstrust.compliance.checkers.gs_qkd_002 import check_use_case
from photonstrust.compliance.checkers.gs_qkd_004 import check_f1, check_f2, check_f3, check_f4
from photonstrust.compliance.checkers.gs_qkd_005 import check_sp1, check_sp2, check_sp3, check_sp4, check_sp5
from photonstrust.compliance.checkers.gs_qkd_008 import check_s1, check_s2, check_s3, check_s4
from photonstrust.compliance.checkers.gs_qkd_011 import check_c1, check_c2, check_c3, check_c4
from photonstrust.compliance.checkers.gs_qkd_014 import check_k1, check_k2, check_k3, check_k4
from photonstrust.compliance.types import ETSIRequirement, RequirementResult, normalize_status


_REQ_004 = (
    ETSIRequirement(
        id="GS-QKD-004-F1",
        standard="GS-QKD-004",
        version="V2.1.1 (2020-08)",
        clause="7.2",
        description="Minimum secret key rate is met at specified operating distance.",
        check_fn=check_f1,
        inputs_required=("sweep_result", "scenario", "k_min_bps", "d_spec_km"),
        category="functional",
    ),
    ETSIRequirement(
        id="GS-QKD-004-F2",
        standard="GS-QKD-004",
        version="V2.1.1 (2020-08)",
        clause="7.3",
        description="QBER remains below the operational threshold over operating range.",
        check_fn=check_f2,
        inputs_required=("sweep_result", "scenario", "d_spec_km"),
        category="functional",
    ),
    ETSIRequirement(
        id="GS-QKD-004-F3",
        standard="GS-QKD-004",
        version="V2.1.1 (2020-08)",
        clause="7.4",
        description="Positive key rate is maintained across the operating distance range.",
        check_fn=check_f3,
        inputs_required=("sweep_result", "scenario"),
        category="functional",
    ),
    ETSIRequirement(
        id="GS-QKD-004-F4",
        standard="GS-QKD-004",
        version="V2.1.1 (2020-08)",
        clause="7.5",
        description="Composable finite-key epsilon target is satisfied when finite-key is enabled.",
        check_fn=check_f4,
        inputs_required=("sweep_result", "scenario", "epsilon_target"),
        category="functional",
    ),
)

_REQ_005 = (
    ETSIRequirement(
        id="GS-QKD-005-SP1",
        standard="GS-QKD-005",
        version="V1.1.1 (2022)",
        clause="5.2",
        description="Proof method is approved and applicable to the protocol family.",
        check_fn=check_sp1,
        inputs_required=("scenario",),
        category="security_proof",
    ),
    ETSIRequirement(
        id="GS-QKD-005-SP2",
        standard="GS-QKD-005",
        version="V1.1.1 (2022)",
        clause="5.3",
        description="Epsilon budget decomposition is valid (components sum correctly, all positive).",
        check_fn=check_sp2,
        inputs_required=("sweep_result", "scenario"),
        category="security_proof",
    ),
    ETSIRequirement(
        id="GS-QKD-005-SP3",
        standard="GS-QKD-005",
        version="V1.1.1 (2022)",
        clause="5.4",
        description="Smooth min-entropy lower bound computation is consistent with the proof method.",
        check_fn=check_sp3,
        inputs_required=("sweep_result", "scenario"),
        category="security_proof",
    ),
    ETSIRequirement(
        id="GS-QKD-005-SP4",
        standard="GS-QKD-005",
        version="V1.1.1 (2022)",
        clause="5.5",
        description="Privacy amplification output length is consistent with leftover hash lemma.",
        check_fn=check_sp4,
        inputs_required=("sweep_result", "scenario"),
        category="security_proof",
    ),
    ETSIRequirement(
        id="GS-QKD-005-SP5",
        standard="GS-QKD-005",
        version="V1.1.1 (2022)",
        clause="5.6",
        description="Parameter estimation uses appropriate statistical bound with valid configuration.",
        check_fn=check_sp5,
        inputs_required=("scenario",),
        category="security_proof",
    ),
)

_REQ_008 = (
    ETSIRequirement(
        id="GS-QKD-008-S1",
        standard="GS-QKD-008",
        version="V2.1.1 (2024)",
        clause="8.3",
        description="Single-photon gain/yield lower bound is strictly positive.",
        check_fn=check_s1,
        inputs_required=("sweep_result",),
        category="security",
    ),
    ETSIRequirement(
        id="GS-QKD-008-S2",
        standard="GS-QKD-008",
        version="V2.1.1 (2024)",
        clause="8.4",
        description="Single-photon phase error upper bound remains below 0.5.",
        check_fn=check_s2,
        inputs_required=("sweep_result", "scenario", "d_spec_km"),
        category="security",
    ),
    ETSIRequirement(
        id="GS-QKD-008-S3",
        standard="GS-QKD-008",
        version="V2.1.1 (2024)",
        clause="8.5",
        description="Decoy-state operating mu remains in practical multi-photon safe range.",
        check_fn=check_s3,
        inputs_required=("scenario",),
        category="security",
    ),
    ETSIRequirement(
        id="GS-QKD-008-S4",
        standard="GS-QKD-008",
        version="V2.1.1 (2024)",
        clause="8.7",
        description="Protocol family is covered by a curated coherent-attack proof set.",
        check_fn=check_s4,
        inputs_required=("scenario",),
        category="security",
    ),
)

_REQ_011 = (
    ETSIRequirement(
        id="GS-QKD-011-C1",
        standard="GS-QKD-011",
        version="V1.1.1 (2016-11)",
        clause="6.2.1",
        description="Source contribution to QBER stays below target bounds.",
        check_fn=check_c1,
        inputs_required=("scenario", "sweep_result"),
        category="component",
    ),
    ETSIRequirement(
        id="GS-QKD-011-C2",
        standard="GS-QKD-011",
        version="V1.1.1 (2016-11)",
        clause="6.3.1",
        description="Detector dark count rate does not exceed 10^4 cps threshold.",
        check_fn=check_c2,
        inputs_required=("scenario",),
        category="component",
    ),
    ETSIRequirement(
        id="GS-QKD-011-C3",
        standard="GS-QKD-011",
        version="V1.1.1 (2016-11)",
        clause="6.3.2",
        description="Detector efficiency meets recommended minimum level.",
        check_fn=check_c3,
        inputs_required=("scenario",),
        category="component",
    ),
    ETSIRequirement(
        id="GS-QKD-011-C4",
        standard="GS-QKD-011",
        version="V1.1.1 (2016-11)",
        clause="6.3.3",
        description="Timing jitter induced key-rate penalty remains within limits.",
        check_fn=check_c4,
        inputs_required=("scenario",),
        category="component",
    ),
)

_REQ_USE_CASE = ETSIRequirement(
    id="GS-QKD-002-UC1",
    standard="GS-QKD-002",
    version="V1.1.1 (2019-05)",
    clause="UseCase",
    description="Scenario satisfies claimed GS-QKD-002 use-case envelope and minimum key-rate gate.",
    check_fn=check_use_case,
    inputs_required=("scenario", "sweep_result", "use_case_id", "k_min_bps", "d_spec_km"),
    category="use_case",
)

_REQ_014 = (
    ETSIRequirement(
        id="GS-QKD-014-K1",
        standard="GS-QKD-014",
        version="V1.1.1 (2019-04)",
        clause="6.1",
        description="Key delivery interface exposes status endpoint.",
        check_fn=check_k1,
        inputs_required=("scenario",),
        category="key_delivery",
    ),
    ETSIRequirement(
        id="GS-QKD-014-K2",
        standard="GS-QKD-014",
        version="V1.1.1 (2019-04)",
        clause="6.2",
        description="Delivered keys use unique UUIDs.",
        check_fn=check_k2,
        inputs_required=("scenario",),
        category="key_delivery",
    ),
    ETSIRequirement(
        id="GS-QKD-014-K3",
        standard="GS-QKD-014",
        version="V1.1.1 (2019-04)",
        clause="6.3",
        description="Key size matches requested specification.",
        check_fn=check_k3,
        inputs_required=("scenario",),
        category="key_delivery",
    ),
    ETSIRequirement(
        id="GS-QKD-014-K4",
        standard="GS-QKD-014",
        version="V1.1.1 (2019-04)",
        clause="6.4",
        description="Key pool replenishment rate matches simulated QKD key rate.",
        check_fn=check_k4,
        inputs_required=("sweep_result", "scenario"),
        category="key_delivery",
    ),
)

_CANONICAL_REQUIREMENTS = (*_REQ_004, *_REQ_005, *_REQ_008, *_REQ_011, *_REQ_014)


def get_requirements(standards: list[str] | None) -> list[ETSIRequirement]:
    if not standards:
        return list(_CANONICAL_REQUIREMENTS)

    allowed = {_normalize_standard_id(value) for value in standards}
    allowed.discard("")
    out: list[ETSIRequirement] = []
    for req in _CANONICAL_REQUIREMENTS:
        if _normalize_standard_id(req.standard) in allowed:
            out.append(req)
    return out


def get_use_case_requirement() -> ETSIRequirement:
    return _REQ_USE_CASE


def run_requirement(
    req: ETSIRequirement,
    sweep_result: Any,
    scenario: dict[str, Any],
    *,
    context: dict[str, Any],
) -> RequirementResult:
    raw = req.check_fn(sweep_result, scenario, context=dict(context or {}))
    payload = raw if isinstance(raw, dict) else {}
    notes_raw = payload.get("notes")
    notes = [str(v) for v in notes_raw] if isinstance(notes_raw, list) else []

    return RequirementResult(
        req_id=req.id,
        standard=req.standard,
        clause=req.clause,
        description=req.description,
        status=normalize_status(payload.get("status")),
        computed_value=payload.get("computed_value"),
        threshold=payload.get("threshold"),
        unit=str(payload.get("unit")) if payload.get("unit") is not None else None,
        notes=notes,
    )


def _normalize_standard_id(value: Any) -> str:
    raw = str(value or "").strip().upper()
    if not raw:
        return ""
    normalized = raw.replace("_", "-").replace(" ", "")
    if "QKD002" in normalized:
        return "GS-QKD-002"
    if "QKD004" in normalized:
        return "GS-QKD-004"
    if "QKD005" in normalized:
        return "GS-QKD-005"
    if "QKD008" in normalized:
        return "GS-QKD-008"
    if "QKD011" in normalized:
        return "GS-QKD-011"
    if "QKD014" in normalized:
        return "GS-QKD-014"
    if raw.startswith("GS-QKD-"):
        return raw
    return raw
