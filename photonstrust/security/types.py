"""Security assessment data types."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AttackModel:
    """Describes a known quantum hacking attack."""

    attack_id: str
    attack_name: str
    attack_class: str
    description: str
    applicable_protocols: tuple[str, ...]
    applicable_detector_classes: tuple[str, ...]
    parameters: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "attack_id": self.attack_id,
            "attack_name": self.attack_name,
            "attack_class": self.attack_class,
            "description": self.description,
            "applicable_protocols": list(self.applicable_protocols),
            "applicable_detector_classes": list(self.applicable_detector_classes),
            "parameters": self.parameters,
        }


@dataclass(frozen=True)
class CountermeasureModel:
    """Describes a countermeasure against a specific attack."""

    countermeasure_id: str
    name: str
    target_attack: str
    effectiveness: float
    cost_factor: float
    parameters: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "countermeasure_id": self.countermeasure_id,
            "name": self.name,
            "target_attack": self.target_attack,
            "effectiveness": self.effectiveness,
            "cost_factor": self.cost_factor,
            "parameters": self.parameters,
        }


@dataclass(frozen=True)
class VulnerabilityAssessment:
    """Result of evaluating a single attack against a scenario."""

    attack_id: str
    attack_name: str
    severity: str
    exploitability_score: float
    information_gain: float
    metric_name: str
    metric_value: float
    metric_unit: str
    applicable: bool
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "attack_id": self.attack_id,
            "attack_name": self.attack_name,
            "severity": self.severity,
            "exploitability_score": self.exploitability_score,
            "information_gain": self.information_gain,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "metric_unit": self.metric_unit,
            "applicable": self.applicable,
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class CountermeasureEffectiveness:
    """Result of evaluating a countermeasure."""

    countermeasure_id: str
    name: str
    detection_probability: float
    residual_risk: float
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "countermeasure_id": self.countermeasure_id,
            "name": self.name,
            "detection_probability": self.detection_probability,
            "residual_risk": self.residual_risk,
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class ThreatAssessmentResult:
    """Aggregated threat assessment for a QKD scenario."""

    scenario_id: str
    protocol_name: str
    detector_class: str
    vulnerabilities: list[VulnerabilityAssessment] = field(default_factory=list)
    countermeasures: list[CountermeasureEffectiveness] = field(default_factory=list)
    overall_risk_score: float = 0.0
    overall_severity: str = "none"
    recommendations: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "scenario_id": self.scenario_id,
            "protocol_name": self.protocol_name,
            "detector_class": self.detector_class,
            "vulnerabilities": [v.as_dict() for v in self.vulnerabilities],
            "countermeasures": [c.as_dict() for c in self.countermeasures],
            "overall_risk_score": self.overall_risk_score,
            "overall_severity": self.overall_severity,
            "recommendations": list(self.recommendations),
        }
