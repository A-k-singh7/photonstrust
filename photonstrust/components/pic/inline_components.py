"""PICComponentBase wrappers for components defined inline in library.py."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from photonstrust.components.pic.base import PICComponentBase, PICComponentMeta
from photonstrust.components.pic.library import (
    _matrix_waveguide,
    _matrix_insertion_loss_2port,
    _matrix_phase_shifter,
    _matrix_ring,
    _matrix_coupler,
    _matrix_touchstone_2port,
    _matrix_touchstone_nport,
    _touchstone_nport_ports,
)

# ---- Waveguide ----


class WaveguideParams(BaseModel):
    length_um: float = Field(0.0, ge=0.0, description="Waveguide length in micrometers")
    loss_db_per_cm: float = Field(0.0, ge=0.0, description="Propagation loss in dB/cm")
    neff: float | None = Field(None, gt=0.0, description="Effective refractive index")


class WaveguideComponent(PICComponentBase):
    @classmethod
    def meta(cls):
        return PICComponentMeta(
            kind="pic.waveguide", title="Waveguide",
            description="Optical waveguide with propagation loss and phase",
            in_ports=("in",), out_ports=("out",),
            port_domains={"in": "optical", "out": "optical"},
        )

    @classmethod
    def params_schema(cls):
        return WaveguideParams

    @classmethod
    def forward_matrix(cls, params, wavelength_nm=None):
        d = cls._as_dict(params)
        # Map pydantic field 'neff' to library key 'n_eff'
        if "neff" in d and d["neff"] is not None and "n_eff" not in d:
            d["n_eff"] = d["neff"]
        return _matrix_waveguide(d, wavelength_nm)


# ---- Grating Coupler ----


class GratingCouplerParams(BaseModel):
    insertion_loss_db: float = Field(0.0, ge=0.0, description="Insertion loss in dB")


class GratingCouplerComponent(PICComponentBase):
    @classmethod
    def meta(cls):
        return PICComponentMeta(
            kind="pic.grating_coupler", title="Grating Coupler",
            description="Fiber-to-chip grating coupler",
            in_ports=("in",), out_ports=("out",),
            port_domains={"in": "optical", "out": "optical"},
        )

    @classmethod
    def params_schema(cls):
        return GratingCouplerParams

    @classmethod
    def forward_matrix(cls, params, wavelength_nm=None):
        return _matrix_insertion_loss_2port(cls._as_dict(params), wavelength_nm)


# ---- Edge Coupler ----


class EdgeCouplerParams(BaseModel):
    insertion_loss_db: float = Field(0.0, ge=0.0, description="Insertion loss in dB")


class EdgeCouplerComponent(PICComponentBase):
    @classmethod
    def meta(cls):
        return PICComponentMeta(
            kind="pic.edge_coupler", title="Edge Coupler",
            description="Fiber-to-chip edge coupler",
            in_ports=("in",), out_ports=("out",),
            port_domains={"in": "optical", "out": "optical"},
        )

    @classmethod
    def params_schema(cls):
        return EdgeCouplerParams

    @classmethod
    def forward_matrix(cls, params, wavelength_nm=None):
        return _matrix_insertion_loss_2port(cls._as_dict(params), wavelength_nm)


# ---- Phase Shifter ----


class PhaseShifterParams(BaseModel):
    phase_rad: float = Field(0.0, description="Applied phase shift in radians")
    insertion_loss_db: float = Field(0.0, ge=0.0, description="Insertion loss in dB")


class PhaseShifterComponent(PICComponentBase):
    @classmethod
    def meta(cls):
        return PICComponentMeta(
            kind="pic.phase_shifter", title="Phase Shifter",
            description="Thermo-optic or electro-optic phase shifter",
            in_ports=("in",), out_ports=("out",),
            port_domains={"in": "optical", "out": "optical"},
        )

    @classmethod
    def params_schema(cls):
        return PhaseShifterParams

    @classmethod
    def forward_matrix(cls, params, wavelength_nm=None):
        return _matrix_phase_shifter(cls._as_dict(params), wavelength_nm)


# ---- Isolator (2-port) ----


class Isolator2PortParams(BaseModel):
    insertion_loss_db: float = Field(0.0, ge=0.0, description="Insertion loss in dB")


class Isolator2PortComponent(PICComponentBase):
    @classmethod
    def meta(cls):
        return PICComponentMeta(
            kind="pic.isolator_2port", title="Optical Isolator",
            description="Non-reciprocal 2-port optical isolator",
            in_ports=("in",), out_ports=("out",),
            port_domains={"in": "optical", "out": "optical"},
        )

    @classmethod
    def params_schema(cls):
        return Isolator2PortParams

    @classmethod
    def forward_matrix(cls, params, wavelength_nm=None):
        return _matrix_insertion_loss_2port(cls._as_dict(params), wavelength_nm)


# ---- Ring Resonator ----


class RingParams(BaseModel):
    insertion_loss_db: float = Field(0.0, ge=0.0, description="Bus insertion loss in dB")
    resonance_wavelength_nm: float | None = Field(
        None, gt=0.0, description="Resonance wavelength in nm"
    )
    fsr_nm: float | None = Field(None, gt=0.0, description="Free spectral range in nm")
    fwhm_nm: float | None = Field(
        None, gt=0.0, description="Full width at half maximum in nm"
    )


class RingComponent(PICComponentBase):
    @classmethod
    def meta(cls):
        return PICComponentMeta(
            kind="pic.ring", title="Ring Resonator",
            description="All-pass ring resonator filter",
            in_ports=("in",), out_ports=("out",),
            port_domains={"in": "optical", "out": "optical"},
        )

    @classmethod
    def params_schema(cls):
        return RingParams

    @classmethod
    def forward_matrix(cls, params, wavelength_nm=None):
        return _matrix_ring(cls._as_dict(params), wavelength_nm)


# ---- Directional Coupler ----


class CouplerParams(BaseModel):
    coupling_ratio: float = Field(0.5, ge=0.0, le=1.0, description="Power coupling ratio")
    insertion_loss_db: float = Field(0.0, ge=0.0, description="Excess insertion loss in dB")


class CouplerComponent(PICComponentBase):
    @classmethod
    def meta(cls):
        return PICComponentMeta(
            kind="pic.coupler", title="Directional Coupler",
            description="2x2 directional coupler / beam splitter",
            in_ports=("in1", "in2"), out_ports=("out1", "out2"),
            port_domains={
                "in1": "optical", "in2": "optical",
                "out1": "optical", "out2": "optical",
            },
        )

    @classmethod
    def params_schema(cls):
        return CouplerParams

    @classmethod
    def forward_matrix(cls, params, wavelength_nm=None):
        return _matrix_coupler(cls._as_dict(params), wavelength_nm)


# ---- Touchstone 2-port ----


class Touchstone2PortParams(BaseModel):
    file_path: str = Field(..., description="Path to Touchstone .s2p file")
    wavelength_nm: float | None = Field(
        None, gt=0.0, description="Evaluation wavelength in nm"
    )


class Touchstone2PortComponent(PICComponentBase):
    @classmethod
    def meta(cls):
        return PICComponentMeta(
            kind="pic.touchstone_2port", title="Touchstone 2-Port",
            description="2-port component from Touchstone S-parameter file",
            in_ports=("in",), out_ports=("out",),
            port_domains={"in": "optical", "out": "optical"},
        )

    @classmethod
    def params_schema(cls):
        return Touchstone2PortParams

    @classmethod
    def forward_matrix(cls, params, wavelength_nm=None):
        d = cls._as_dict(params)
        # Map pydantic field 'file_path' to library key 'path'
        if "file_path" in d and "path" not in d:
            d["path"] = d["file_path"]
        wl = wavelength_nm or d.get("wavelength_nm")
        return _matrix_touchstone_2port(d, wl)


# ---- Touchstone N-port ----


class TouchstoneNPortParams(BaseModel):
    file_path: str = Field(..., description="Path to Touchstone .sNp file")
    wavelength_nm: float | None = Field(
        None, gt=0.0, description="Evaluation wavelength in nm"
    )
    n_ports: int | None = Field(None, ge=1, description="Number of ports in the file")
    port_map: dict[str, list[str]] | None = Field(
        None, description="Mapping with 'in_ports' and 'out_ports' keys"
    )


class TouchstoneNPortComponent(PICComponentBase):
    @classmethod
    def meta(cls):
        return PICComponentMeta(
            kind="pic.touchstone_nport", title="Touchstone N-Port",
            description="N-port component from Touchstone S-parameter file",
            in_ports=(), out_ports=(),
            port_domains={},
        )

    @classmethod
    def params_schema(cls):
        return TouchstoneNPortParams

    @classmethod
    def forward_matrix(cls, params, wavelength_nm=None):
        d = cls._as_dict(params)
        if "file_path" in d and "path" not in d:
            d["path"] = d["file_path"]
        if d.get("port_map"):
            pm = d["port_map"]
            if "in_ports" in pm:
                d["in_ports"] = pm["in_ports"]
            if "out_ports" in pm:
                d["out_ports"] = pm["out_ports"]
        wl = wavelength_nm or d.get("wavelength_nm")
        return _matrix_touchstone_nport(d, wl)

    @classmethod
    def ports(cls, params=None):
        if params is None:
            return cls.meta().in_ports, cls.meta().out_ports
        d = cls._as_dict(params)
        if "file_path" in d and "path" not in d:
            d["path"] = d["file_path"]
        if d.get("port_map"):
            pm = d["port_map"]
            if "in_ports" in pm:
                d["in_ports"] = pm["in_ports"]
            if "out_ports" in pm:
                d["out_ports"] = pm["out_ports"]
        cp = _touchstone_nport_ports(d)
        return cp.in_ports, cp.out_ports
