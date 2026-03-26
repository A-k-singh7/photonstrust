"""Abstract base class and pydantic schemas for QKD protocols.

New QKD protocols should subclass ``QKDProtocolBase`` and implement the
three required class methods: ``meta()``, ``params_schema()``, and
``compute_point()``.  The registry in ``registry.py`` auto-discovers
all subclasses, so no manual registration is needed beyond creating
the module file.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from photonstrust.qkd_protocols.base import ProtocolApplicability
from photonstrust.qkd_types import QKDResult


class QKDProtocolMeta(BaseModel):
    """Declarative metadata every QKD protocol must provide."""

    protocol_id: str
    title: str
    aliases: tuple[str, ...] = ()
    description: str = ""
    channel_models: tuple[str, ...] = ("fiber",)
    gate_policy: dict[str, str] = {}

    model_config = {"frozen": True}


class QKDProtocolBase(ABC):
    """Abstract base for QKD protocol implementations.

    Subclasses must implement ``meta()``, ``params_schema()``, and
    ``compute_point()``.  Optionally override ``applicability()`` to
    restrict which channel models or scenarios the protocol supports.

    Example
    -------
    ::

        class BB84DecoyParams(BaseModel):
            mu: float = Field(0.5, gt=0.0, description="Signal intensity")
            misalignment_prob: float = Field(0.015, ge=0.0, le=0.5)

        class BB84DecoyProtocol(QKDProtocolBase):
            @classmethod
            def meta(cls):
                return QKDProtocolMeta(
                    protocol_id="bb84_decoy",
                    title="BB84 Decoy-State",
                    aliases=("bb84", "decoy"),
                )

            @classmethod
            def params_schema(cls):
                return BB84DecoyParams

            @classmethod
            def compute_point(cls, scenario, distance_km, runtime_overrides=None):
                return compute_point_bb84_decoy(scenario, distance_km, runtime_overrides)
    """

    @classmethod
    @abstractmethod
    def meta(cls) -> QKDProtocolMeta:
        """Return protocol metadata (id, title, aliases, etc.)."""

    @classmethod
    @abstractmethod
    def params_schema(cls) -> type[BaseModel]:
        """Return the pydantic model class for protocol-specific parameters."""

    @classmethod
    @abstractmethod
    def compute_point(
        cls,
        scenario: dict[str, Any],
        distance_km: float,
        runtime_overrides: dict[str, Any] | None = None,
    ) -> QKDResult:
        """Evaluate the protocol at a single distance point."""

    @classmethod
    def applicability(cls, scenario: dict[str, Any]) -> ProtocolApplicability:
        """Check whether this protocol can run on the given scenario.

        Default implementation always passes.  Override to restrict
        by channel model, detector type, etc.
        """
        return ProtocolApplicability(status="pass", reasons=())
