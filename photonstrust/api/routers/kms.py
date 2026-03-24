"""ETSI GS QKD 014 northbound key management API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from photonstrust.kms.key_pool import KeyPoolConfig
from photonstrust.kms.store import KeyPoolStore

router = APIRouter(prefix="/v1/kms", tags=["kms"])

_store = KeyPoolStore()


@router.post("/links", status_code=201)
def create_kms_link(payload: dict) -> dict:
    """Register a QKD link for key delivery (PhotonTrust extension)."""
    try:
        link_id = str(payload["link_id"])
        config = KeyPoolConfig(
            sae_id_alice=str(payload["sae_id_alice"]),
            sae_id_bob=str(payload["sae_id_bob"]),
            key_size_bits=int(payload.get("key_size_bits", 256)),
            max_pool_size=int(payload.get("max_pool_size", 1000)),
            seed=payload.get("seed"),
        )
    except (KeyError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=f"Invalid payload: {exc}")

    pool = _store.get_or_create_pool(link_id, config)
    return {
        "link_id": link_id,
        "source_kme_id": f"kme_{config.sae_id_alice}",
        "target_kme_id": f"kme_{config.sae_id_bob}",
        "pool_status": pool.status(),
    }


@router.get("/links")
def list_links() -> dict:
    """List all registered KMS links."""
    return {"links": _store.list_links()}


@router.get("/api/v1/keys/{slave_sae_id}/status")
def key_status(slave_sae_id: str) -> dict:
    """ETSI QKD 014 - Get key supply status."""
    try:
        pool = _store.get_pool_by_sae(slave_sae_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"No pool for SAE '{slave_sae_id}'")
    return pool.status()


@router.post("/api/v1/keys/{slave_sae_id}/enc_keys")
def get_enc_keys(slave_sae_id: str, payload: dict | None = None) -> dict:
    """ETSI QKD 014 - Get encryption key(s)."""
    payload = payload or {}
    try:
        pool = _store.get_pool_by_sae(slave_sae_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"No pool for SAE '{slave_sae_id}'")

    count = int(payload.get("number", 1))
    key_size = payload.get("size")
    try:
        keys = pool.get_enc_keys(count=count, key_size=key_size)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "keys": [{"key_ID": k.key_id, "key": k.key_material_b64} for k in keys],
    }


@router.post("/api/v1/keys/{slave_sae_id}/dec_keys")
def get_dec_keys(slave_sae_id: str, payload: dict | None = None) -> dict:
    """ETSI QKD 014 - Get decryption key(s) by key ID."""
    payload = payload or {}
    try:
        pool = _store.get_pool_by_sae(slave_sae_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"No pool for SAE '{slave_sae_id}'")

    key_ids = [entry["key_ID"] for entry in payload.get("key_IDs", [])]
    if not key_ids:
        raise HTTPException(status_code=400, detail="No key_IDs provided")

    try:
        keys = pool.get_dec_keys(key_ids=key_ids)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return {
        "keys": [{"key_ID": k.key_id, "key": k.key_material_b64} for k in keys],
    }
