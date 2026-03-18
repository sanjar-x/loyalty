# src/modules/catalog/application/queries/read_models.py
"""
Read models (DTOs) for Catalog query handlers.

These models carry no business logic -- only data for the read side.
Used directly by query handlers without involving domain aggregates,
repositories, or the Unit of Work. Part of the application layer
(CQRS read side).
"""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel


class CategoryNode(BaseModel):
    """Recursive tree node for the category hierarchy read model.

    Attributes:
        id: Category UUID.
        name: Display name.
        slug: URL-safe identifier.
        full_slug: Materialized path.
        level: Tree depth (0 = root).
        sort_order: Ordering among siblings.
        parent_id: Parent UUID, or None for roots.
        children: Nested child nodes populated during tree assembly.
    """

    id: uuid.UUID
    name: str
    slug: str
    full_slug: str
    level: int
    sort_order: int
    parent_id: uuid.UUID | None = None
    children: list[CategoryNode] = []


class CategoryReadModel(BaseModel):
    """Read model for a single category (flat, no children)."""

    id: uuid.UUID
    name: str
    slug: str
    full_slug: str
    level: int
    sort_order: int
    parent_id: uuid.UUID | None = None


class CategoryListReadModel(BaseModel):
    """Paginated category list read model."""

    items: list[CategoryReadModel]
    total: int
    offset: int
    limit: int


class BrandReadModel(BaseModel):
    """Read model for a single brand."""

    id: uuid.UUID
    name: str
    slug: str
    logo_url: str | None = None
    logo_status: str | None = None


class BrandListReadModel(BaseModel):
    """Paginated brand list read model."""

    items: list[BrandReadModel]
    total: int
    offset: int
    limit: int


# ---------------------------------------------------------------------------
# AttributeGroup read models
# ---------------------------------------------------------------------------


class AttributeGroupReadModel(BaseModel):
    """Read model for a single attribute group."""

    id: uuid.UUID
    code: str
    name_i18n: dict[str, Any]
    sort_order: int


class AttributeGroupListReadModel(BaseModel):
    """Paginated attribute group list read model."""

    items: list[AttributeGroupReadModel]
    total: int
    offset: int
    limit: int
