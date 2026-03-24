"""Component catalog API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from photonstrust.catalog.store import ComponentCatalog
from photonstrust.catalog.types import ComponentEntry

router = APIRouter(prefix="/v1/catalog", tags=["catalog"])

_catalog = ComponentCatalog()


@router.get("/components")
def list_components(
    category: str | None = Query(None),
    subcategory: str | None = Query(None),
    vendor: str | None = Query(None),
    tags: str | None = Query(None, description="Comma-separated tag list"),
    q: str | None = Query(None, description="Free-text search"),
    limit: int = Query(50, ge=1, le=500),
) -> dict:
    """Search and list catalog components."""
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    result = _catalog.search(
        category=category,
        subcategory=subcategory,
        vendor=vendor,
        tags=tag_list,
        text_query=q,
        limit=limit,
    )
    return {
        "components": [e.as_dict() for e in result.matches],
        "total_count": result.total_count,
        "query": result.query,
    }


@router.get("/components/{component_id}")
def get_component(component_id: str) -> dict:
    """Get a single component by ID."""
    try:
        entry = _catalog.get(component_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Component '{component_id}' not found")
    return entry.as_dict()


@router.get("/categories")
def list_categories() -> dict:
    """List all component categories."""
    return {"categories": _catalog.list_categories()}


@router.get("/vendors")
def list_vendors() -> dict:
    """List all component vendors."""
    return {"vendors": _catalog.list_vendors()}


@router.post("/components", status_code=201)
def add_component(payload: dict) -> dict:
    """Add a user component to the catalog."""
    try:
        entry = ComponentEntry.from_dict(payload)
    except (KeyError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=f"Invalid component data: {exc}")
    _catalog.add_entry(entry)
    return {"component_id": entry.component_id, "status": "created"}
