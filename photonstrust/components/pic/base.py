"""Abstract base class and pydantic schemas for PIC components.

New PIC components should subclass ``PICComponentBase`` and implement
the three required class methods: ``meta()``, ``params_schema()``, and
``forward_matrix()``.  The registry in ``library.py`` auto-discovers
all subclasses, so no manual registration is needed beyond creating
the module file.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Literal

import numpy as np
from pydantic import BaseModel


class PICComponentMeta(BaseModel):
    """Declarative metadata every PIC component must provide."""

    kind: str
    title: str
    category: Literal["pic"] = "pic"
    description: str = ""
    in_ports: tuple[str, ...]
    out_ports: tuple[str, ...]
    port_domains: dict[str, str] = {}

    model_config = {"frozen": True}


class PICComponentBase(ABC):
    """Abstract base for PIC component implementations.

    Subclasses must implement ``meta()``, ``params_schema()``, and
    ``forward_matrix()``.  Optionally override ``scattering_matrix()``
    for bidirectional S-parameter support and ``ports()`` for
    parameter-dependent port layouts (e.g. AWG channel count).

    Example
    -------
    ::

        class MMIParams(BaseModel):
            n_ports_in: int = Field(2, ge=1, le=2)
            insertion_loss_db: float = Field(0.3, ge=0.0)

        class MMIComponent(PICComponentBase):
            @classmethod
            def meta(cls):
                return PICComponentMeta(
                    kind="pic.mmi", title="MMI Coupler",
                    in_ports=("in1", "in2"), out_ports=("out1", "out2"),
                )

            @classmethod
            def params_schema(cls):
                return MMIParams

            @classmethod
            def forward_matrix(cls, params, wavelength_nm=None):
                p = cls._as_dict(params)
                return mmi_forward_matrix(p, wavelength_nm)
    """

    @classmethod
    @abstractmethod
    def meta(cls) -> PICComponentMeta:
        """Return component metadata (kind, title, ports, etc.)."""

    @classmethod
    @abstractmethod
    def params_schema(cls) -> type[BaseModel]:
        """Return the pydantic model class for this component's parameters."""

    @classmethod
    @abstractmethod
    def forward_matrix(
        cls,
        params: BaseModel | dict[str, Any],
        wavelength_nm: float | None = None,
    ) -> np.ndarray:
        """Compute the forward (unidirectional) transfer matrix."""

    @classmethod
    def scattering_matrix(
        cls,
        params: BaseModel | dict[str, Any],
        wavelength_nm: float | None = None,
    ) -> np.ndarray:
        """Compute the full bidirectional scattering matrix.

        Optional — raises ``NotImplementedError`` by default.
        """
        raise NotImplementedError(
            f"{cls.__name__} does not implement scattering_matrix"
        )

    @classmethod
    def ports(cls, params: BaseModel | dict[str, Any] | None = None) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """Return ``(in_ports, out_ports)``.

        Override for components whose ports depend on parameters
        (e.g. AWG channel count, touchstone N-port).
        """
        m = cls.meta()
        return m.in_ports, m.out_ports

    @staticmethod
    def _as_dict(params: BaseModel | dict[str, Any]) -> dict[str, Any]:
        """Convert pydantic model to dict if needed."""
        if isinstance(params, dict):
            return params
        return params.model_dump()
