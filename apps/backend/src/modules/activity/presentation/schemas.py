"""
Pydantic schemas for the admin activity analytics router.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Base model that serialises with camelCase aliases."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class TrendingProductEntry(CamelModel):
    """Single trending product entry with raw score."""

    product_id: uuid.UUID = Field(description="Product UUID")
    score: float = Field(description="Raw view-count score within the window")


class TrendingProductsResponse(CamelModel):
    """Response body for the admin trending analytics endpoint."""

    window: str = Field(description='Ranking window, e.g. "daily" or "weekly"')
    category_id: uuid.UUID | None = Field(
        default=None, description="Category filter, if any"
    )
    items: list[TrendingProductEntry] = Field(default_factory=list)


class SearchQueryEntry(CamelModel):
    """A single search term ranked by occurrence count."""

    query: str = Field(description="Normalised search query")
    count: float = Field(description="Occurrence count within the window")


class SearchAnalyticsResponse(CamelModel):
    """Response body for the admin search analytics endpoint."""

    popular: list[SearchQueryEntry] = Field(default_factory=list)
    zero_results: list[SearchQueryEntry] = Field(default_factory=list)
