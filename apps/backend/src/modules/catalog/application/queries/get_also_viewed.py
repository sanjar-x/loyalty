"""
Orchestrator: storefront "also viewed" products for PDP.

Combines:
1. Slug resolution (404 on miss).
2. :class:`ICoViewReader` — reads the refreshed co-view matrix.
3. Fallback to :class:`GetSimilarProductsHandler` when the matrix is cold
   (e.g. brand-new product with no co-views yet) so the endpoint always
   returns something useful.
4. :class:`GetStorefrontProductCardsByIdsHandler` — hydrates cards.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.queries.get_similar_products import (
    GetSimilarProductsHandler,
    GetSimilarProductsQuery,
)
from src.modules.catalog.application.queries.get_storefront_cards_by_ids import (
    GetStorefrontProductCardsByIdsHandler,
    GetStorefrontProductCardsByIdsQuery,
)
from src.modules.catalog.application.queries.read_models import (
    StorefrontProductCardReadModel,
)
from src.modules.catalog.domain.value_objects import ProductStatus
from src.modules.catalog.infrastructure.models import Product as OrmProduct
from src.shared.exceptions import NotFoundError
from src.shared.interfaces.activity import ICoViewReader


@dataclass(frozen=True)
class GetAlsoViewedProductCardsQuery:
    slug: str
    limit: int = 12


@dataclass(frozen=True)
class AlsoViewedProductCardsResult:
    items: list[StorefrontProductCardReadModel]
    is_fallback: bool
    """True when the co-view matrix had no data and the handler fell back
    to content-based similarity."""


class GetAlsoViewedProductCardsHandler:
    """Resolve slug and return "viewed together" product cards."""

    def __init__(
        self,
        session: AsyncSession,
        co_view_reader: ICoViewReader,
        similar_handler: GetSimilarProductsHandler,
        cards_handler: GetStorefrontProductCardsByIdsHandler,
    ) -> None:
        self._session = session
        self._co_view = co_view_reader
        self._similar = similar_handler
        self._cards = cards_handler

    async def handle(
        self, query: GetAlsoViewedProductCardsQuery
    ) -> AlsoViewedProductCardsResult:
        stmt = select(OrmProduct.id).where(
            OrmProduct.slug == query.slug,
            OrmProduct.status == ProductStatus.PUBLISHED,
            OrmProduct.is_visible.is_(True),
            OrmProduct.deleted_at.is_(None),
        )
        row = (await self._session.execute(stmt)).first()
        if row is None:
            raise NotFoundError(
                message=f"Product '{query.slug}' not found",
                details={"slug": query.slug},
            )

        is_fallback = False
        scores = await self._co_view.get_also_viewed(
            product_id=row.id, limit=query.limit
        )
        # Defensive: a stale/buggy co-view row could include the seed as
        # its own neighbour. Exclude it so the carousel never shows the
        # page the user is currently on.
        ranked_ids = [s.product_id for s in scores if s.product_id != row.id]

        if not ranked_ids:
            # Cold matrix (new product / no recent co-views) — fall back to
            # content similarity so PDP placement is never empty.
            similar = await self._similar.handle(
                GetSimilarProductsQuery(product_id=row.id, limit=query.limit)
            )
            ranked_ids = similar.product_ids
            is_fallback = True
        elif len(ranked_ids) < query.limit:
            # Partial co-view hit — pad with similar products (dedup) so
            # the PDP carousel fills the requested slots instead of
            # silently returning fewer cards.  Same-source fallback; we
            # keep ``is_fallback = False`` because the leading items are
            # still genuine co-views and flipping the flag would lie
            # about the signal quality.
            gap = query.limit - len(ranked_ids)
            similar = await self._similar.handle(
                GetSimilarProductsQuery(
                    product_id=row.id, limit=query.limit + len(ranked_ids)
                )
            )
            seen = set(ranked_ids)
            for pid in similar.product_ids:
                if gap <= 0:
                    break
                if pid in seen:
                    continue
                ranked_ids.append(pid)
                seen.add(pid)
                gap -= 1

        if not ranked_ids:
            return AlsoViewedProductCardsResult(items=[], is_fallback=is_fallback)

        cards = await self._cards.handle(
            GetStorefrontProductCardsByIdsQuery(product_ids=ranked_ids)
        )
        return AlsoViewedProductCardsResult(items=cards, is_fallback=is_fallback)
