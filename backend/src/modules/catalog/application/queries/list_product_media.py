"""Query handler for listing product media assets."""

import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.infrastructure.models import MediaAsset as OrmMediaAsset


@dataclass(frozen=True)
class MediaAssetReadModel:
    """Read-only DTO for a media asset."""

    id: uuid.UUID
    product_id: uuid.UUID
    variant_id: uuid.UUID | None
    media_type: str
    role: str
    sort_order: int
    processing_status: str | None
    public_url: str | None
    is_external: bool
    external_url: str | None


@dataclass(frozen=True)
class ListProductMediaQuery:
    """Parameters for listing media assets of a product.

    Attributes:
        product_id: UUID of the parent product.
        offset: Number of records to skip.
        limit: Maximum number of records to return.
    """

    product_id: uuid.UUID
    offset: int = 0
    limit: int = 50


class ListProductMediaHandler:
    """List media assets for a product with DB-level pagination (CQRS read side)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: ListProductMediaQuery) -> tuple[list[MediaAssetReadModel], int]:
        """Retrieve paginated media assets for a product.

        Args:
            query: Query parameters with product_id and pagination.

        Returns:
            Tuple of (media read models, total count).
        """
        count_stmt = (
            select(func.count())
            .select_from(OrmMediaAsset)
            .where(OrmMediaAsset.product_id == query.product_id)
        )
        count_result = await self._session.execute(count_stmt)
        total: int = count_result.scalar_one()

        stmt = (
            select(OrmMediaAsset)
            .where(OrmMediaAsset.product_id == query.product_id)
            .order_by(OrmMediaAsset.variant_id, OrmMediaAsset.sort_order)
            .limit(query.limit)
            .offset(query.offset)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [self._to_read_model(orm) for orm in rows], total

    @staticmethod
    def _to_read_model(orm: OrmMediaAsset) -> MediaAssetReadModel:
        return MediaAssetReadModel(
            id=orm.id,
            product_id=orm.product_id,
            variant_id=orm.variant_id,
            media_type=orm.media_type.value if orm.media_type else "",
            role=orm.role.value if orm.role else "",
            sort_order=orm.sort_order,
            processing_status=orm.processing_status,
            public_url=orm.public_url,
            is_external=orm.is_external,
            external_url=orm.external_url,
        )
