"""Discrete event simulation kernel."""

from __future__ import annotations

import heapq
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, List


TRACE_MODES = {"off", "summary", "sampled", "full"}


@dataclass(order=True)
class Event:
    time_ns: float
    priority: int
    event_type: str = field(compare=False)
    node_id: str = field(compare=False)
    seq: int = field(default=0)
    event_id: str = field(default="", compare=False)
    parent_event_ids: list[str] = field(default_factory=list, compare=False)
    payload: dict = field(compare=False, default_factory=dict)


class EventKernel:
    def __init__(self, seed: int = 0, *, trace_mode: str = "off", trace_sample_rate: float = 0.1) -> None:
        self.seed = seed
        self._queue: List[Event] = []
        self._log: List[Event] = []
        self._seq = 0
        mode = str(trace_mode or "off").strip().lower() or "off"
        if mode not in TRACE_MODES:
            raise ValueError(f"trace_mode must be one of: {', '.join(sorted(TRACE_MODES))}")
        self.trace_mode = mode
        self.trace_sample_rate = float(trace_sample_rate)
        if self.trace_sample_rate < 0.0:
            self.trace_sample_rate = 0.0
        if self.trace_sample_rate > 1.0:
            self.trace_sample_rate = 1.0
        self._trace_records: List[dict[str, Any]] = []
        self._trace_counts: dict[str, int] = {}

    def schedule(self, event: Event) -> None:
        event.seq = self._seq
        event.event_id = f"evt-{self._seq:010d}"
        self._seq += 1
        heapq.heappush(self._queue, event)

    def run(self, until_ns: float | None = None) -> List[Event]:
        while self._queue:
            event = heapq.heappop(self._queue)
            if until_ns is not None and event.time_ns > until_ns:
                # Preserve future events for subsequent run() calls.
                heapq.heappush(self._queue, event)
                break
            self._log.append(event)
            self._record_trace(event)
        return list(self._log)

    @property
    def log(self) -> List[Event]:
        return list(self._log)

    def trace_records(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self._trace_records]

    def trace_summary(self) -> dict[str, Any]:
        return {
            "trace_mode": self.trace_mode,
            "event_count": len(self._log),
            "recorded_count": len(self._trace_records),
            "counts_by_type": {k: self._trace_counts[k] for k in sorted(self._trace_counts.keys())},
        }

    def trace_hash(self) -> str:
        payload = {
            "trace_mode": self.trace_mode,
            "events": self.trace_records(),
            "summary": self.trace_summary(),
        }
        encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _record_trace(self, event: Event) -> None:
        key = str(event.event_type or "unknown")
        self._trace_counts[key] = int(self._trace_counts.get(key, 0)) + 1
        if self.trace_mode == "off":
            return
        if self.trace_mode == "summary":
            return
        if self.trace_mode == "sampled" and self._deterministic_sample_score(event.event_id) > self.trace_sample_rate:
            return

        self._trace_records.append(
            {
                "event_id": event.event_id,
                "t_ns": float(event.time_ns),
                "priority": int(event.priority),
                "type": str(event.event_type),
                "actor": str(event.node_id),
                "parent_event_ids": [str(v) for v in event.parent_event_ids],
                "payload_summary": self._payload_summary(event.payload),
                "ordering_key": [float(event.time_ns), int(event.priority), int(event.seq)],
            }
        )

    def _payload_summary(self, payload: dict) -> dict[str, Any]:
        if not isinstance(payload, dict):
            return {}
        out: dict[str, Any] = {}
        for key in sorted(payload.keys()):
            value = payload.get(key)
            if isinstance(value, (str, int, float, bool)) or value is None:
                out[str(key)] = value
            else:
                out[str(key)] = str(type(value).__name__)
        return out

    def _deterministic_sample_score(self, event_id: str) -> float:
        digest = hashlib.sha256(f"{self.seed}:{event_id}".encode("utf-8")).hexdigest()
        window = digest[:8]
        max_u32 = float(0xFFFFFFFF)
        return float(int(window, 16)) / max_u32
