"""ETSI QKD compliance public API."""

from __future__ import annotations

from photonstrust.compliance.registry import get_requirements, run_requirement
from photonstrust.compliance.report import build_compliance_report, render_pdf_report
from photonstrust.compliance.types import (
    ETSIRequirement,
    RequirementResult,
    STATUS_FAIL,
    STATUS_NOT_ASSESSED,
    STATUS_PASS,
    STATUS_WARNING,
)

__all__ = [
    "ETSIRequirement",
    "RequirementResult",
    "STATUS_PASS",
    "STATUS_FAIL",
    "STATUS_WARNING",
    "STATUS_NOT_ASSESSED",
    "get_requirements",
    "run_requirement",
    "build_compliance_report",
    "render_pdf_report",
]
