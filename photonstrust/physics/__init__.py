"""Physics backends for hardware-calibrated models."""

from photonstrust.physics.detector import DetectionStats, DetectorProfile, build_detector_profile, simulate_detector
from photonstrust.physics.emitter import SourceProfile, build_source_profile, get_emitter_stats
from photonstrust.physics.memory import MemoryStats, simulate_memory

__all__ = [
    "DetectionStats",
    "DetectorProfile",
    "MemoryStats",
    "SourceProfile",
    "build_detector_profile",
    "build_source_profile",
    "get_emitter_stats",
    "simulate_detector",
    "simulate_memory",
]
