"""Application-layer integration ports for the catalog module.

Lives in the application layer (not domain) because the abstractions
here describe integration with external infrastructure (search backend)
rather than domain concepts. Same convention as
``src/modules/order/application/ports.py`` (``IPaymentGateway``,
``IDobroPostGateway``, etc.).

The Phase 2 SPEC stands up two implementations behind
:class:`IProductSearchService`:

* ``PostgresProductSearchService`` (default) — thin wrapper around the
  existing tsvector-based ``SearchProductsHandler`` /
  ``SearchSuggestHandler`` so the cart-flow keeps working unchanged
  while the new path is being validated.
* ``ElasticsearchProductSearchService`` — talks to self-hosted ES via
  the shared :mod:`src.infrastructure.elasticsearch` provider.

A feature flag (``Settings.SEARCH_PROVIDER``) chooses the binding at
DI assembly time so flipping providers requires a Railway env-var,
not a redeploy.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from src.modules.catalog.application.queries.read_models import (
    SearchSuggestionReadModel,
    StorefrontProductCardReadModel,
)
from src.shared.pagination import CursorPage


@dataclass(frozen=True)
class SearchProductsCriteria:
    """Engine-agnostic criteria for a storefront product search.

    Mirrors the public ``SearchProductsQuery`` shape used by the
    existing PG-backed handler so the presentation layer can pass the
    same object regardless of backend. Tuples / immutable defaults so
    instances are safely shareable across awaits.
    """

    q: str
    sort: str = "relevant"
    limit: int = 24
    cursor: str | None = None
    category_id: uuid.UUID | None = None
    brand_ids: tuple[uuid.UUID, ...] = field(default_factory=tuple)
    price_min: int | None = None
    price_max: int | None = None
    in_stock: bool | None = None
    attribute_filters: dict[str, tuple[str, ...]] = field(default_factory=dict)
    include_total: bool = False


@dataclass(frozen=True)
class SearchSuggestCriteria:
    """Engine-agnostic criteria for autocomplete suggestions."""

    q: str
    limit: int = 5
    lang: str | None = None


class IProductSearchService(ABC):
    """Port for the storefront product search backend.

    Both :meth:`search` and :meth:`suggest` are expected to translate
    backend-specific transport errors into
    :class:`src.shared.exceptions.SearchBackendError` (or a more
    specific subclass) so the global error handler renders the unified
    envelope. Caching / activity tracking stays outside the port — it
    is handled by the FastAPI router, which is identical across
    backends.
    """

    @abstractmethod
    async def search(
        self, criteria: SearchProductsCriteria
    ) -> CursorPage[StorefrontProductCardReadModel]:
        """Run a paginated product search and return card-shape read models."""

    @abstractmethod
    async def suggest(
        self, criteria: SearchSuggestCriteria
    ) -> list[SearchSuggestionReadModel]:
        """Return up to ``criteria.limit`` autocomplete suggestions."""


# ---------------------------------------------------------------------------
# Hydration port — write side (indexer + initial reindex CLI)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProductIndexDoc:
    """Read-side projection of a Product, shaped for Elasticsearch indexing.

    Matches the field layout declared in the v1 mapping (``products_v2``
    index, see ``SPEC - Elasticsearch Product Search.md § 4.1``). Plain
    dataclass — serialisation happens in :meth:`to_es_source`. ``None`` /
    empty defaults mirror the mapping defaults so a partially-populated
    doc still indexes cleanly.
    """

    product_id: uuid.UUID
    slug: str
    status: str
    is_visible: bool
    deleted: bool

    supplier_id: uuid.UUID | None = None
    supplier_type: str | None = None

    brand_id: uuid.UUID | None = None
    brand_name: str | None = None
    brand_slug: str | None = None
    brand_logo_url: str | None = None

    primary_category_id: uuid.UUID | None = None
    category_ids: tuple[uuid.UUID, ...] = field(default_factory=tuple)
    category_full_slug: str | None = None
    category_names_ru: str | None = None
    category_names_en: str | None = None

    title_ru: str | None = None
    title_en: str | None = None
    description_ru: str | None = None
    description_en: str | None = None

    tags: tuple[str, ...] = field(default_factory=tuple)
    tags_text: str | None = None
    country_of_origin: str | None = None
    source_url: str | None = None

    effective_price: int | None = None
    compare_at_price: int | None = None
    currency: str | None = None

    in_stock: bool = False
    variant_count: int = 0
    sku_count: int = 0
    sku_codes: tuple[str, ...] = field(default_factory=tuple)

    popularity_score: float = 0.0
    published_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    image_url: str | None = None
    image_variants: list[dict[str, Any]] | None = None

    variant_titles_ru: str | None = None
    variant_titles_en: str | None = None

    searchable_attribute_text_ru: str | None = None
    searchable_attribute_text_en: str | None = None
    searchable_attribute_aliases: str | None = None

    attribute_values: tuple[dict[str, Any], ...] = field(default_factory=tuple)

    def to_es_source(self) -> dict[str, Any]:
        """Render to the dict shape ``bulk_index`` consumes.

        Drops ``None`` values so the indexed doc stays lean and
        field-absence stays unambiguous in queries. ``_id`` is set
        from ``product_id`` so :func:`src.infrastructure.elasticsearch.bulk_index`
        can route the action.
        """
        raw: dict[str, Any] = {
            "_id": str(self.product_id),
            "product_id": str(self.product_id),
            "slug": self.slug,
            "status": self.status,
            "is_visible": self.is_visible,
            "deleted": self.deleted,
            "supplier_id": str(self.supplier_id) if self.supplier_id else None,
            "supplier_type": self.supplier_type,
            "brand_id": str(self.brand_id) if self.brand_id else None,
            "brand_name": self.brand_name,
            "brand_slug": self.brand_slug,
            "brand_logo_url": self.brand_logo_url,
            "primary_category_id": (
                str(self.primary_category_id) if self.primary_category_id else None
            ),
            "category_ids": [str(c) for c in self.category_ids],
            "category_full_slug": self.category_full_slug,
            "category_names_ru": self.category_names_ru,
            "category_names_en": self.category_names_en,
            "title_ru": self.title_ru,
            "title_en": self.title_en,
            "description_ru": self.description_ru,
            "description_en": self.description_en,
            "tags": list(self.tags),
            "tags_text": self.tags_text,
            "country_of_origin": self.country_of_origin,
            "source_url": self.source_url,
            "effective_price": self.effective_price,
            "compare_at_price": self.compare_at_price,
            "currency": self.currency,
            "in_stock": self.in_stock,
            "variant_count": self.variant_count,
            "sku_count": self.sku_count,
            "sku_codes": list(self.sku_codes),
            "popularity_score": self.popularity_score,
            "published_at": self.published_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "image_url": self.image_url,
            "image_variants": self.image_variants,
            "variant_titles_ru": self.variant_titles_ru,
            "variant_titles_en": self.variant_titles_en,
            "searchable_attribute_text_ru": self.searchable_attribute_text_ru,
            "searchable_attribute_text_en": self.searchable_attribute_text_en,
            "searchable_attribute_aliases": self.searchable_attribute_aliases,
            "attribute_values": list(self.attribute_values),
        }
        return {k: v for k, v in raw.items() if v is not None}


class IProductHydrationReader(ABC):
    """Port: read a Product from PG and project it to :class:`ProductIndexDoc`.

    Implementations join ``products`` with brands / categories / SKUs /
    media / attribute_values and apply the same priceability rules as
    the storefront PLP handler so the indexed doc carries the same
    numbers the customer sees.
    """

    @abstractmethod
    async def get(self, product_id: uuid.UUID) -> ProductIndexDoc | None:
        """Return the indexable projection, or ``None`` if the product is gone."""

    @abstractmethod
    def iter_indexable(
        self, *, batch_size: int = 500
    ) -> AsyncIterator[ProductIndexDoc]:
        """Yield indexable products (non-deleted) for the initial bulk reindex.

        Yields draft, published, and unpublished products alike — the
        adapter is responsible for stamping ``deleted=true`` /
        ``is_visible=false`` so query-time filters keep them out of
        public search. Streaming in batches (server-side cursor /
        keyset) so 10M-document reindex does not load the world into
        memory.
        """

    @abstractmethod
    def iter_product_ids_by_brand(
        self, brand_id: uuid.UUID
    ) -> AsyncIterator[uuid.UUID]:
        """Yield non-deleted product ids whose ``brand_id`` matches.

        Used by the brand-rename fan-out: ``brand_name`` is denormalised
        into every product doc, so an UPDATE to ``brands.name`` requires
        reindexing all affected products. Streams (yield-per-row) so a
        rename on a brand with 100k products doesn't load the id set
        into memory.
        """

    @abstractmethod
    def iter_product_ids_by_category(
        self, category_id: uuid.UUID
    ) -> AsyncIterator[uuid.UUID]:
        """Yield non-deleted product ids whose ``primary_category_id`` matches.

        Symmetric to :meth:`iter_product_ids_by_brand` for category
        renames / slug changes (``category_full_slug`` is denormalised
        on every product doc).
        """
