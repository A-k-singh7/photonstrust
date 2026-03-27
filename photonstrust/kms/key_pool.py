"""File-based simulated key pool for ETSI QKD 014 API."""

from __future__ import annotations

import base64
import json
import math
import os
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class KeyEntry:
    """A single QKD key in the pool."""

    key_id: str
    key_material_b64: str
    key_length_bits: int
    created_at: str
    consumed: bool = False
    consumed_by: str | None = None

    def as_dict(self) -> dict:
        return {
            "key_id": self.key_id,
            "key_material_b64": self.key_material_b64,
            "key_length_bits": self.key_length_bits,
            "created_at": self.created_at,
            "consumed": self.consumed,
            "consumed_by": self.consumed_by,
        }

    @classmethod
    def from_dict(cls, d: dict) -> KeyEntry:
        return cls(
            key_id=d["key_id"],
            key_material_b64=d["key_material_b64"],
            key_length_bits=d["key_length_bits"],
            created_at=d["created_at"],
            consumed=d.get("consumed", False),
            consumed_by=d.get("consumed_by"),
        )


@dataclass
class KeyPoolConfig:
    """Configuration for a simulated key pool."""

    sae_id_alice: str
    sae_id_bob: str
    key_size_bits: int = 256
    max_pool_size: int = 1000
    replenish_rate_keys_per_sec: float = 10.0
    seed: int | None = None

    def as_dict(self) -> dict:
        return {
            "sae_id_alice": self.sae_id_alice,
            "sae_id_bob": self.sae_id_bob,
            "key_size_bits": self.key_size_bits,
            "max_pool_size": self.max_pool_size,
            "replenish_rate_keys_per_sec": self.replenish_rate_keys_per_sec,
            "seed": self.seed,
        }


class SimulatedKeyPool:
    """In-memory + file-backed key pool for a single QKD link.

    The pool generates deterministic or random key material depending on
    whether a seed is set. Keys are consumed via ``get_enc_keys`` and
    ``get_dec_keys`` and can be persisted to JSON.
    """

    def __init__(self, config: KeyPoolConfig, pool_dir: Path) -> None:
        self.config = config
        self.pool_dir = Path(pool_dir)
        self._keys: dict[str, KeyEntry] = {}
        self._rng = random.Random(config.seed)
        self._replenish(count=min(100, config.max_pool_size))

    def _generate_key(self) -> KeyEntry:
        key_bytes = self._rng.randbytes(self.config.key_size_bits // 8)
        return KeyEntry(
            key_id=str(uuid.uuid4()),
            key_material_b64=base64.b64encode(key_bytes).decode("ascii"),
            key_length_bits=self.config.key_size_bits,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def _replenish(self, count: int = 10) -> None:
        available = sum(1 for k in self._keys.values() if not k.consumed)
        to_add = min(count, self.config.max_pool_size - available)
        for _ in range(max(0, to_add)):
            key = self._generate_key()
            self._keys[key.key_id] = key

    def status(self) -> dict:
        available = [k for k in self._keys.values() if not k.consumed]
        return {
            "source_KME_ID": f"kme_{self.config.sae_id_alice}",
            "target_KME_ID": f"kme_{self.config.sae_id_bob}",
            "master_SAE_ID": self.config.sae_id_alice,
            "slave_SAE_ID": self.config.sae_id_bob,
            "key_size": self.config.key_size_bits,
            "stored_key_count": len(available),
            "max_key_count": self.config.max_pool_size,
            "max_key_per_request": 128,
            "max_key_size": self.config.key_size_bits,
            "min_key_size": self.config.key_size_bits,
            "max_SAE_ID_count": 0,
        }

    def get_enc_keys(self, *, count: int = 1, key_size: int | None = None) -> list[KeyEntry]:
        """Get encryption key(s). Marks them as consumed."""
        if key_size and key_size != self.config.key_size_bits:
            raise ValueError(
                f"Requested key size {key_size} does not match pool key size "
                f"{self.config.key_size_bits}"
            )
        self._replenish(count)
        available = [k for k in self._keys.values() if not k.consumed]
        if len(available) < count:
            raise ValueError(
                f"Not enough keys: requested {count}, available {len(available)}"
            )
        result = available[:count]
        for k in result:
            k.consumed = True
            k.consumed_by = self.config.sae_id_alice
        return result

    def get_dec_keys(self, *, key_ids: list[str]) -> list[KeyEntry]:
        """Get decryption key(s) by ID."""
        result = []
        for kid in key_ids:
            key = self._keys.get(kid)
            if key is None:
                raise KeyError(f"Key '{kid}' not found in pool")
            result.append(key)
        return result

    def persist(self) -> Path:
        """Write pool state to disk."""
        self.pool_dir.mkdir(parents=True, exist_ok=True)
        path = self.pool_dir / "pool.json"
        data = {
            "config": self.config.as_dict(),
            "keys": [k.as_dict() for k in self._keys.values()],
        }
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return path

    @classmethod
    def load(cls, pool_dir: Path) -> SimulatedKeyPool:
        """Load pool state from disk."""
        path = Path(pool_dir) / "pool.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        config = KeyPoolConfig(**data["config"])
        pool = cls.__new__(cls)
        pool.config = config
        pool.pool_dir = Path(pool_dir)
        pool._keys = {k["key_id"]: KeyEntry.from_dict(k) for k in data["keys"]}
        pool._rng = random.Random(config.seed)
        return pool

    @classmethod
    def from_qkd_result(
        cls,
        result: dict,
        pool_dir: Path,
        *,
        sae_id_alice: str = "SAE_A",
        sae_id_bob: str = "SAE_B",
        key_size_bits: int = 256,
        max_pool_size: int = 1000,
        seed: int | None = None,
    ) -> SimulatedKeyPool:
        """Create a key pool from QKD simulation results."""
        results_list = result.get("results", [])
        if results_list:
            first = results_list[0]
            kr = first.get("key_rate_bps", first.get("key_rate_bps", 0))
            if isinstance(kr, (int, float)):
                rate = max(0.0, float(kr)) / key_size_bits
            else:
                rate = 10.0
        else:
            rate = 10.0

        config = KeyPoolConfig(
            sae_id_alice=sae_id_alice,
            sae_id_bob=sae_id_bob,
            key_size_bits=key_size_bits,
            max_pool_size=max_pool_size,
            replenish_rate_keys_per_sec=rate,
            seed=seed,
        )
        return cls(config, pool_dir)
