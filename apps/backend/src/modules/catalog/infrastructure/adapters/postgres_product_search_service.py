"""PostgreSQL implementation of :class:`IProductSearchService`.

A *delegating* adapter — wraps the existing tsvector-based
``SearchProductsHandler`` / ``SearchSuggestHandler`` rather than
duplicating their 800+ lines of query-building / cache / FTS logic.
Result: zero behaviour change on the request path, the only difference
is the indirection through the port.

When (if) the PG path is retired we can move the handler bodies into
this adapter and drop the handler classes. Doing it now would be a
600-line move with high regression surface; SPEC §7 phase plan
intentionally postpones it.
"""

from __future__ import annotations

from src.modules.catalog.application.ports import (
    IProductSearchService,
    SearchProductsCriteria,
    SearchSuggestCriteria,
)
from src.modules.catalog.application.queries.read_models import (
    SearchSuggestionReadModel,
    StorefrontProductCardReadModel,
)
from src.modules.catalog.application.queries.search_products import (
    SearchProductsHandler,
    SearchProductsQuery,
)
from src.modules.catalog.application.queries.search_suggest import (
    SearchSuggestHandler,
    SearchSuggestQuery,
)
from src.shared.pagination import CursorPage


class PostgresProductSearchService(IProductSearchService):
    """Adapter that wires the storefront search port onto the existing
    PostgreSQL tsvector handlers (default until ``SEARCH_PROVIDER`` is
    flipped to ``elasticsearch``).
    """

    def __init__(
        self,
        search_handler: SearchProductsHandler,
        suggest_handler: SearchSuggestHandler,
    ) -> None:
        self._search = search_handler
        self._suggest = suggest_handler

    async def search(
        self, criteria: SearchProductsCriteria
    ) -> CursorPage[StorefrontProductCardReadModel]:
        query = SearchProductsQuery(
            q=criteria.q,
            category_id=criteria.category_id,
            brand_ids=list(criteria.brand_ids) if criteria.brand_ids else None,
            price_min=criteria.price_min,
            price_max=criteria.price_max,
            in_stock=criteria.in_stock,
            attribute_filters=(
                {
                    code: list(values)
                    for code, values in criteria.attribute_filters.items()
                }
                if criteria.attribute_filters
                else None
            ),
            sort=criteria.sort,
            limit=criteria.limit,
            cursor=criteria.cursor,
            include_total=criteria.include_total,
        )
        return await self._search.handle(query)

    async def suggest(
        self, criteria: SearchSuggestCriteria
    ) -> list[SearchSuggestionReadModel]:
        return await self._suggest.handle(
            SearchSuggestQuery(q=criteria.q, limit=criteria.limit, lang=criteria.lang)
        )
