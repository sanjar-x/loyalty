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
from dataclasses import dataclass, field

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
