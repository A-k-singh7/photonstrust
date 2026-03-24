"""Multi-link key pool store (file-based)."""

from __future__ import annotations

from pathlib import Path

from photonstrust.kms.key_pool import KeyPoolConfig, SimulatedKeyPool

_DEFAULT_KMS_DIR = Path("data/kms")


class KeyPoolStore:
    """Manages key pools for multiple QKD links."""

    def __init__(self, kms_dir: Path | None = None) -> None:
        self._kms_dir = Path(kms_dir) if kms_dir else _DEFAULT_KMS_DIR
        self._pools: dict[str, SimulatedKeyPool] = {}

    def get_or_create_pool(
        self,
        link_id: str,
        config: KeyPoolConfig,
    ) -> SimulatedKeyPool:
        if link_id in self._pools:
            return self._pools[link_id]

        pool_dir = self._kms_dir / link_id
        if (pool_dir / "pool.json").exists():
            pool = SimulatedKeyPool.load(pool_dir)
        else:
            pool = SimulatedKeyPool(config, pool_dir)

        self._pools[link_id] = pool
        return pool

    def get_pool(self, link_id: str) -> SimulatedKeyPool:
        if link_id in self._pools:
            return self._pools[link_id]

        pool_dir = self._kms_dir / link_id
        if (pool_dir / "pool.json").exists():
            pool = SimulatedKeyPool.load(pool_dir)
            self._pools[link_id] = pool
            return pool

        raise KeyError(f"No key pool found for link '{link_id}'")

    def list_links(self) -> list[dict]:
        result = []
        if self._kms_dir.is_dir():
            for d in sorted(self._kms_dir.iterdir()):
                if d.is_dir() and (d / "pool.json").exists():
                    result.append({"link_id": d.name, "pool_dir": str(d)})
        for lid in self._pools:
            if not any(r["link_id"] == lid for r in result):
                result.append({"link_id": lid, "pool_dir": str(self._kms_dir / lid)})
        return result

    def get_pool_by_sae(self, sae_id: str) -> SimulatedKeyPool:
        """Lookup a pool where the given SAE ID is either alice or bob."""
        for pool in self._pools.values():
            if sae_id in (pool.config.sae_id_alice, pool.config.sae_id_bob):
                return pool
        raise KeyError(f"No pool found for SAE '{sae_id}'")
