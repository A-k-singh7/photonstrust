"""Data types for QRNG simulation."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class QRNGSource:
    """Describes a quantum random number generation source."""

    source_type: str
    generation_rate_bps: float
    raw_entropy_per_bit: float
    parameters: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "source_type": self.source_type,
            "generation_rate_bps": self.generation_rate_bps,
            "raw_entropy_per_bit": self.raw_entropy_per_bit,
            "parameters": dict(self.parameters),
        }


@dataclass(frozen=True)
class EntropyEstimate:
    """Entropy estimation result."""

    min_entropy_per_bit: float
    shannon_entropy_per_bit: float
    sample_size: int
    estimator: str
    confidence: float

    def as_dict(self) -> dict:
        return {
            "min_entropy_per_bit": self.min_entropy_per_bit,
            "shannon_entropy_per_bit": self.shannon_entropy_per_bit,
            "sample_size": self.sample_size,
            "estimator": self.estimator,
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class ConditioningResult:
    """Result of randomness conditioning / extraction."""

    method: str
    input_bits: int
    output_bits: int
    compression_ratio: float
    output_min_entropy_per_bit: float

    def as_dict(self) -> dict:
        return {
            "method": self.method,
            "input_bits": self.input_bits,
            "output_bits": self.output_bits,
            "compression_ratio": self.compression_ratio,
            "output_min_entropy_per_bit": self.output_min_entropy_per_bit,
        }


@dataclass(frozen=True)
class QRNGResult:
    """End-to-end QRNG simulation result."""

    source: dict = field(default_factory=dict)
    entropy_estimate: dict = field(default_factory=dict)
    conditioning: dict | None = None
    output_rate_bps: float = 0.0
    quality_score: float = 0.0
    passes_nist_tests: bool = False
    diagnostics: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "source": dict(self.source),
            "entropy_estimate": dict(self.entropy_estimate),
            "conditioning": dict(self.conditioning) if self.conditioning else None,
            "output_rate_bps": self.output_rate_bps,
            "quality_score": self.quality_score,
            "passes_nist_tests": self.passes_nist_tests,
            "diagnostics": dict(self.diagnostics),
        }
