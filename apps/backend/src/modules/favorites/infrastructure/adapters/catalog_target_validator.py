"""ACL adapter: validates that a (target_type, target_id) pair points
at a real, visible catalog entity before we record it as a favorite.

This is the single approved cross-module touchpoint between favorites
and catalog (whitelisted in ``tests/architecture/test_boundaries.py``).
Reads ORM rows directly to avoid pulling the catalog domain layer in.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.value_objects import ProductStatus
from src.modules.catalog.infrastructure.models import Brand, Product
from src.modules.favorites.domain.interfaces import (
    FavoriteTargetCheck,
    IFavoriteTargetValidator,
)
from src.modules.favorites.domain.value_objects import FavoriteTargetType


class CatalogTargetValidator(IFavoriteTargetValidator):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def check(
        self,
        *,
        target_type: FavoriteTargetType,
        target_id: uuid.UUID,
    ) -> FavoriteTargetCheck:
        if target_type is FavoriteTargetType.PRODUCT:
            return await self._check_product(target_id)
        if target_type is FavoriteTargetType.BRAND:
            return await self._check_brand(target_id)

        return FavoriteTargetCheck(
            target_type=target_type,
            target_id=target_id,
            exists=False,
            reason="unsupported_target_type",
        )

    async def _check_product(self, target_id: uuid.UUID) -> FavoriteTargetCheck:
        stmt = select(Product.id, Product.status, Product.deleted_at).where(
            Product.id == target_id
        )
        row = (await self._session.execute(stmt)).first()
        if row is None:
            return FavoriteTargetCheck(
                target_type=FavoriteTargetType.PRODUCT,
                target_id=target_id,
                exists=False,
                reason="product_not_found",
            )
        if row.deleted_at is not None:
            return FavoriteTargetCheck(
                target_type=FavoriteTargetType.PRODUCT,
                target_id=target_id,
                exists=False,
                reason="product_deleted",
            )
        if row.status != ProductStatus.PUBLISHED:
            return FavoriteTargetCheck(
                target_type=FavoriteTargetType.PRODUCT,
                target_id=target_id,
                exists=False,
                reason=f"product_not_published:{row.status.value}",
            )
        return FavoriteTargetCheck(
            target_type=FavoriteTargetType.PRODUCT,
            target_id=target_id,
            exists=True,
        )

    async def _check_brand(self, target_id: uuid.UUID) -> FavoriteTargetCheck:
        stmt = select(Brand.id).where(Brand.id == target_id)
        row = (await self._session.execute(stmt)).first()
        if row is None:
            return FavoriteTargetCheck(
                target_type=FavoriteTargetType.BRAND,
                target_id=target_id,
                exists=False,
                reason="brand_not_found",
            )
        return FavoriteTargetCheck(
            target_type=FavoriteTargetType.BRAND,
            target_id=target_id,
            exists=True,
        )
