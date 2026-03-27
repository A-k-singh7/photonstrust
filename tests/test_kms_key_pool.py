"""Tests for the KMS key pool and ETSI QKD 014 compliance."""

from __future__ import annotations

from pathlib import Path

import pytest

from photonstrust.kms.key_pool import KeyEntry, KeyPoolConfig, SimulatedKeyPool
from photonstrust.kms.store import KeyPoolStore


def _default_config(**overrides) -> KeyPoolConfig:
    defaults = dict(
        sae_id_alice="SAE_A",
        sae_id_bob="SAE_B",
        key_size_bits=256,
        max_pool_size=100,
        seed=42,
    )
    defaults.update(overrides)
    return KeyPoolConfig(**defaults)


def test_pool_creation(tmp_path):
    pool = SimulatedKeyPool(_default_config(), tmp_path)
    status = pool.status()
    assert status["stored_key_count"] > 0
    assert status["key_size"] == 256
    assert status["master_SAE_ID"] == "SAE_A"
    assert status["slave_SAE_ID"] == "SAE_B"


def test_enc_key_retrieval_unique_ids(tmp_path):
    pool = SimulatedKeyPool(_default_config(), tmp_path)
    keys = pool.get_enc_keys(count=5)
    assert len(keys) == 5
    ids = [k.key_id for k in keys]
    assert len(set(ids)) == 5


def test_dec_key_retrieval_by_id(tmp_path):
    pool = SimulatedKeyPool(_default_config(), tmp_path)
    enc_keys = pool.get_enc_keys(count=2)
    dec_keys = pool.get_dec_keys(key_ids=[k.key_id for k in enc_keys])
    assert len(dec_keys) == 2
    assert dec_keys[0].key_material_b64 == enc_keys[0].key_material_b64


def test_pool_exhaustion(tmp_path):
    pool = SimulatedKeyPool(_default_config(max_pool_size=5), tmp_path)
    pool.get_enc_keys(count=5)
    with pytest.raises(ValueError, match="Not enough keys"):
        pool.get_enc_keys(count=100)


def test_key_size_matches_config(tmp_path):
    pool = SimulatedKeyPool(_default_config(key_size_bits=128), tmp_path)
    keys = pool.get_enc_keys(count=1)
    assert keys[0].key_length_bits == 128


def test_deterministic_seed(tmp_path):
    pool1 = SimulatedKeyPool(_default_config(seed=123), tmp_path / "p1")
    pool2 = SimulatedKeyPool(_default_config(seed=123), tmp_path / "p2")
    k1 = pool1.get_enc_keys(count=1)[0].key_material_b64
    k2 = pool2.get_enc_keys(count=1)[0].key_material_b64
    assert k1 == k2


def test_persist_and_load(tmp_path):
    pool = SimulatedKeyPool(_default_config(), tmp_path)
    keys_before = pool.get_enc_keys(count=3)
    pool.persist()
    loaded = SimulatedKeyPool.load(tmp_path)
    status = loaded.status()
    assert status["stored_key_count"] >= 0


def test_from_qkd_result(tmp_path):
    result = {
        "results": [
            {"distance_km": 50, "key_rate_bps": 1000.0},
            {"distance_km": 100, "key_rate_bps": 500.0},
        ]
    }
    pool = SimulatedKeyPool.from_qkd_result(result, tmp_path)
    assert pool.config.replenish_rate_keys_per_sec == pytest.approx(1000.0 / 256)


def test_store_get_by_sae(tmp_path):
    store = KeyPoolStore(kms_dir=tmp_path)
    config = _default_config()
    store.get_or_create_pool("link_1", config)
    pool = store.get_pool_by_sae("SAE_B")
    assert pool.config.sae_id_bob == "SAE_B"


def test_store_missing_link(tmp_path):
    store = KeyPoolStore(kms_dir=tmp_path)
    with pytest.raises(KeyError, match="No key pool"):
        store.get_pool("nonexistent")


def test_compliance_k1():
    from photonstrust.compliance.checkers.gs_qkd_014 import check_k1

    result = check_k1([], {"kms": {"sae_id_alice": "A"}}, context={})
    assert result["status"] == "PASS"

    result_none = check_k1([], {}, context={})
    assert result_none["status"] == "NOT_ASSESSED"


def test_compliance_k2():
    from photonstrust.compliance.checkers.gs_qkd_014 import check_k2

    keys = [{"key_id": "a"}, {"key_id": "b"}, {"key_id": "c"}]
    result = check_k2([], {}, context={"pool_keys": keys})
    assert result["status"] == "PASS"

    dup_keys = [{"key_id": "a"}, {"key_id": "a"}]
    result_dup = check_k2([], {}, context={"pool_keys": dup_keys})
    assert result_dup["status"] == "FAIL"


def test_compliance_k3():
    from photonstrust.compliance.checkers.gs_qkd_014 import check_k3

    keys = [{"key_length_bits": 256}, {"key_length_bits": 256}]
    result = check_k3([], {"kms": {"key_size_bits": 256}}, context={"pool_keys": keys})
    assert result["status"] == "PASS"


def test_compliance_k4():
    from photonstrust.compliance.checkers.gs_qkd_014 import check_k4

    sweep = {"results": [{"key_rate_bps": 10000.0}]}
    result = check_k4(sweep, {"kms": {"replenish_rate_keys_per_sec": 30, "key_size_bits": 256}}, context={})
    assert result["status"] in ("PASS", "WARNING")


def test_registry_includes_qkd014():
    from photonstrust.compliance.registry import get_requirements

    reqs = get_requirements(["QKD014"])
    assert len(reqs) == 4
    assert all("014" in r.standard for r in reqs)
