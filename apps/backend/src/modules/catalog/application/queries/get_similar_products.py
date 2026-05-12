"""
Query handler: content-based similar products for a PDP.

Phase B1 of the recommendation roadmap.  Given a source ``product_id`` the
handler returns published products from the **same primary category**,
ranked by:

1. Same-brand bonus (shared brand => +score).
2. ``popularity_score`` (descending).

This is intentionally lightweight — no joins to the EAV attribute table, no
embeddings, no co-view signals.  Later phases layer richer signals on top of
the same presentation contract (``GET /storefront/products/{id}/similar``).

Returned ``product_ids`` are suitable for feeding into
:class:`GetStorefrontProductCardsByIdsHandler`.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import case, desc, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.value_objects import ProductStatus
from src.modules.catalog.infrastructure.models import Product as OrmProduct
from src.shared.interfaces.logger import ILogger

# Same-brand boost weight.  Chosen so that a same-brand product with zero
# views still outranks a different-brand product with up to 999 views.
_SAME_BRAND_BONUS = 1000


@dataclass(frozen=True)
class GetSimilarProductsQuery:
    product_id: uuid.UUID
    limit: int = 12


@dataclass(frozen=True)
class SimilarProductsResult:
    product_ids: list[uuid.UUID]


class GetSimilarProductsHandler:
    """Content-based nearest neighbours by category + brand + popularity."""

    def __init__(self, session: AsyncSession, logger: ILogger) -> None:
        self._session = session
        self._logger = logger.bind(handler="GetSimilarProductsHandler")

    async def handle(self, query: GetSimilarProductsQuery) -> SimilarProductsResult:
        limit = max(1, min(query.limit, 50))

        # Single round-trip: fetch the source product's category + brand.
        seed_stmt = select(
            OrmProduct.primary_category_id,
            OrmProduct.brand_id,
        ).where(OrmProduct.id == query.product_id)

        try:
            seed_row = (await self._session.execute(seed_stmt)).first()
        except SQLAlchemyError:
            self._logger.exception("similar.seed_lookup_failed")
            return SimilarProductsResult(product_ids=[])

        if seed_row is None or seed_row.primary_category_id is None:
            return SimilarProductsResult(product_ids=[])

        same_brand_bonus = case(
            (OrmProduct.brand_id == seed_row.brand_id, _SAME_BRAND_BONUS),
            else_=0,
        )

        stmt = (
            select(OrmProduct.id)
            .where(
                OrmProduct.primary_category_id == seed_row.primary_category_id,
                OrmProduct.id != query.product_id,
                OrmProduct.status == ProductStatus.PUBLISHED,
                OrmProduct.is_visible.is_(True),
                OrmProduct.deleted_at.is_(None),
            )
            .order_by(
                # COALESCE guards against NULL popularity_score which
                # would otherwise propagate NULL into the sum and place
                # unpopular-but-same-brand products in unpredictable
                # positions (PostgreSQL sorts NULLS FIRST on DESC by
                # default).  ``nullslast()`` on ``published_at`` prevents
                # products without a publish timestamp from floating to
                # the top of the tie-break.
                desc(same_brand_bonus + func.coalesce(OrmProduct.popularity_score, 0)),
                desc(OrmProduct.published_at).nullslast(),
                OrmProduct.id,  # stable tie-break
            )
            .limit(limit)
        )

        try:
            rows = (await self._session.execute(stmt)).all()
        except SQLAlchemyError:
            self._logger.exception("similar.query_failed")
            return SimilarProductsResult(product_ids=[])

        return SimilarProductsResult(product_ids=[r.id for r in rows])
