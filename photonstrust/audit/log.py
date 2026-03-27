"""Append-only, hash-chained audit log with JSONL persistence."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from photonstrust.audit.types import AuditEntry, AuditQuery


class AuditLog:
    """Tamper-evident audit trail backed by a JSONL file."""

    def __init__(self, log_path: Path) -> None:
        self._log_path = Path(log_path)
        self._last_hash = self._load_last_hash()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def append(
        self,
        *,
        actor: str,
        action: str,
        resource_type: str,
        resource_id: str,
        details: dict | None = None,
    ) -> AuditEntry:
        """Create a new hash-chained entry and persist it."""
        entry_id = str(uuid.uuid4())
        timestamp_iso = datetime.now(timezone.utc).isoformat()

        # Build entry dict WITHOUT entry_hash
        entry_data: dict = {
            "entry_id": entry_id,
            "timestamp_iso": timestamp_iso,
            "actor": actor,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details or {},
            "previous_hash": self._last_hash,
        }

        # Compute entry_hash from canonical JSON of entry_data
        canonical = json.dumps(entry_data, sort_keys=True, separators=(",", ":"))
        entry_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        entry_data["entry_hash"] = entry_hash

        # Append to JSONL
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry_data, sort_keys=True) + "\n")

        self._last_hash = entry_hash

        return AuditEntry(**entry_data)

    def query(self, q: AuditQuery | None = None) -> list[AuditEntry]:
        """Read all entries from the JSONL file, optionally filtered."""
        entries = self._read_all()
        if q is None:
            return entries

        filtered: list[AuditEntry] = []
        for e in entries:
            if q.actor is not None and e.actor != q.actor:
                continue
            if q.action is not None and e.action != q.action:
                continue
            if q.resource_type is not None and e.resource_type != q.resource_type:
                continue
            if q.resource_id is not None and e.resource_id != q.resource_id:
                continue
            if q.start_iso is not None and e.timestamp_iso < q.start_iso:
                continue
            if q.end_iso is not None and e.timestamp_iso > q.end_iso:
                continue
            filtered.append(e)
            if len(filtered) >= q.limit:
                break

        return filtered

    def verify_chain(self) -> dict:
        """Verify the hash chain integrity of the entire log.

        Returns a dict with ``valid``, ``entries_checked``, and
        ``first_broken_at`` (index, or ``None`` when the chain is intact).
        """
        entries = self._read_all()
        if not entries:
            return {"valid": True, "entries_checked": 0, "first_broken_at": None}

        genesis_hash = "0" * 64
        previous_hash = genesis_hash

        for idx, entry in enumerate(entries):
            # Check previous_hash linkage
            if entry.previous_hash != previous_hash:
                return {
                    "valid": False,
                    "entries_checked": idx + 1,
                    "first_broken_at": idx,
                }

            # Recompute entry_hash
            entry_data = {
                "entry_id": entry.entry_id,
                "timestamp_iso": entry.timestamp_iso,
                "actor": entry.actor,
                "action": entry.action,
                "resource_type": entry.resource_type,
                "resource_id": entry.resource_id,
                "details": entry.details,
                "previous_hash": entry.previous_hash,
            }
            canonical = json.dumps(entry_data, sort_keys=True, separators=(",", ":"))
            expected_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

            if entry.entry_hash != expected_hash:
                return {
                    "valid": False,
                    "entries_checked": idx + 1,
                    "first_broken_at": idx,
                }

            previous_hash = entry.entry_hash

        return {
            "valid": True,
            "entries_checked": len(entries),
            "first_broken_at": None,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _read_all(self) -> list[AuditEntry]:
        """Parse every line of the JSONL file into AuditEntry objects."""
        if not self._log_path.exists():
            return []
        entries: list[AuditEntry] = []
        with open(self._log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                entries.append(AuditEntry(**data))
        return entries

    def _load_last_hash(self) -> str:
        """Return the entry_hash of the last entry, or the genesis hash."""
        if not self._log_path.exists():
            return "0" * 64
        last_line = ""
        with open(self._log_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    last_line = stripped
        if not last_line:
            return "0" * 64
        data = json.loads(last_line)
        return data.get("entry_hash", "0" * 64)
