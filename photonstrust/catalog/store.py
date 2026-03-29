"""File-based component catalog with search capabilities."""

from __future__ import annotations

import json
from pathlib import Path

from photonstrust.catalog.types import CatalogSearchResult, ComponentEntry

_BUILTIN_DIR = Path(__file__).parent / "data"


class ComponentCatalog:
    """Load, search, and extend the component catalog.

    Catalog entries are stored as JSON files in nested directories:
      <catalog_dir>/<category>/<component_id>.json

    Built-in entries ship with the package under ``catalog/data/``.
    User entries can be added to a separate user catalog directory.
    """

    def __init__(
        self,
        builtin_dir: Path | None = None,
        user_dir: Path | None = None,
    ) -> None:
        self._builtin_dir = Path(builtin_dir) if builtin_dir else _BUILTIN_DIR
        self._user_dir = Path(user_dir) if user_dir else None
        self._entries: dict[str, ComponentEntry] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        self._load_dir(self._builtin_dir)
        if self._user_dir and self._user_dir.is_dir():
            self._load_dir(self._user_dir)

    def _load_dir(self, root: Path) -> None:
        if not root.is_dir():
            return
        for json_path in sorted(root.rglob("*.json")):
            try:
                data = json.loads(json_path.read_text(encoding="utf-8"))
                entry = ComponentEntry.from_dict(data)
                self._entries[entry.component_id] = entry
            except (json.JSONDecodeError, KeyError, TypeError):
                continue

    def get(self, component_id: str) -> ComponentEntry:
        """Retrieve a component by its unique ID."""
        self._ensure_loaded()
        entry = self._entries.get(component_id)
        if entry is None:
            raise KeyError(f"Component '{component_id}' not found in catalog")
        return entry

    def search(
        self,
        *,
        category: str | None = None,
        subcategory: str | None = None,
        vendor: str | None = None,
        tags: list[str] | None = None,
        text_query: str | None = None,
        limit: int = 50,
    ) -> CatalogSearchResult:
        """Search the catalog with optional filters."""
        self._ensure_loaded()
        matches: list[ComponentEntry] = []
        query_info: dict = {}

        if category:
            query_info["category"] = category
        if subcategory:
            query_info["subcategory"] = subcategory
        if vendor:
            query_info["vendor"] = vendor
        if tags:
            query_info["tags"] = tags
        if text_query:
            query_info["text_query"] = text_query

        for entry in self._entries.values():
            if category and entry.category != category:
                continue
            if subcategory and entry.subcategory != subcategory:
                continue
            if vendor and (entry.vendor or "").lower() != vendor.lower():
                continue
            if tags and not set(tags).issubset(set(entry.tags)):
                continue
            if text_query:
                needle = text_query.lower()
                haystack = " ".join([
                    entry.component_id,
                    entry.category,
                    entry.subcategory,
                    entry.vendor or "",
                    entry.model or "",
                    entry.notes,
                    " ".join(entry.tags),
                ]).lower()
                if needle not in haystack:
                    continue
            matches.append(entry)

        total = len(matches)
        return CatalogSearchResult(
            matches=matches[:limit],
            total_count=total,
            query=query_info,
        )

    def list_categories(self) -> list[str]:
        """Return sorted list of unique categories."""
        self._ensure_loaded()
        return sorted({e.category for e in self._entries.values()})

    def list_vendors(self) -> list[str]:
        """Return sorted list of unique vendors (excluding None)."""
        self._ensure_loaded()
        return sorted({e.vendor for e in self._entries.values() if e.vendor})

    def add_entry(self, entry: ComponentEntry, catalog_dir: Path | None = None) -> Path:
        """Add or update a component entry and persist to disk."""
        target_dir = catalog_dir or self._user_dir or self._builtin_dir
        category_dir = target_dir / entry.category
        category_dir.mkdir(parents=True, exist_ok=True)
        out_path = category_dir / f"{entry.component_id}.json"
        out_path.write_text(
            json.dumps(entry.as_dict(), indent=2) + "\n",
            encoding="utf-8",
        )
        self._entries[entry.component_id] = entry
        return out_path

    def all_entries(self) -> list[ComponentEntry]:
        """Return all catalog entries."""
        self._ensure_loaded()
        return list(self._entries.values())
