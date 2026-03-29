"""Component catalog data types."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ComponentEntry:
    """A single component in the catalog."""

    component_id: str
    category: str
    subcategory: str
    vendor: str | None
    model: str | None
    version: str
    params: dict
    tags: tuple[str, ...]
    datasheet_url: str | None = None
    notes: str = ""

    def as_dict(self) -> dict:
        return {
            "component_id": self.component_id,
            "category": self.category,
            "subcategory": self.subcategory,
            "vendor": self.vendor,
            "model": self.model,
            "version": self.version,
            "params": dict(self.params),
            "tags": list(self.tags),
            "datasheet_url": self.datasheet_url,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ComponentEntry:
        return cls(
            component_id=str(data["component_id"]),
            category=str(data["category"]),
            subcategory=str(data.get("subcategory", "")),
            vendor=data.get("vendor"),
            model=data.get("model"),
            version=str(data.get("version", "1.0")),
            params=dict(data.get("params", {})),
            tags=tuple(data.get("tags", ())),
            datasheet_url=data.get("datasheet_url"),
            notes=str(data.get("notes", "")),
        )


@dataclass(frozen=True)
class CatalogSearchResult:
    """Result of a catalog search query."""

    matches: list[ComponentEntry]
    total_count: int
    query: dict = field(default_factory=dict)
