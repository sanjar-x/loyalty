"""
Orchestrator: storefront "similar products" for PDP placement.

Combines three steps so the router stays thin:

1. Resolve the source ``slug`` to a product ID (404 if missing).
2. Delegate ranking to :class:`GetSimilarProductsHandler` (content-based).
3. Hydrate the ranked IDs into product cards via
   :class:`GetStorefrontProductCardsByIdsHandler`.

Returns a cards list preserving the handler-provided order.
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


@dataclass(frozen=True)
class GetSimilarProductCardsQuery:
    slug: str
    limit: int = 12


@dataclass(frozen=True)
class SimilarProductCardsResult:
    items: list[StorefrontProductCardReadModel]


class GetSimilarProductCardsHandler:
    """Resolve slug and return content-similar product cards."""

    def __init__(
        self,
        session: AsyncSession,
        similar_handler: GetSimilarProductsHandler,
        cards_handler: GetStorefrontProductCardsByIdsHandler,
    ) -> None:
        self._session = session
        self._similar = similar_handler
        self._cards = cards_handler

    async def handle(
        self, query: GetSimilarProductCardsQuery
    ) -> SimilarProductCardsResult:
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

        ranked = await self._similar.handle(
            GetSimilarProductsQuery(product_id=row.id, limit=query.limit)
        )
        if not ranked.product_ids:
            return SimilarProductCardsResult(items=[])

        cards = await self._cards.handle(
            GetStorefrontProductCardsByIdsQuery(product_ids=ranked.product_ids)
        )
        return SimilarProductCardsResult(items=cards)
