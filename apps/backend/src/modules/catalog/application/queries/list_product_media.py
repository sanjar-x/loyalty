"""Query handler for listing product media assets."""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.queries.read_models import (
    MediaAssetListReadModel,
    MediaAssetReadModel,
)
from src.modules.catalog.infrastructure.models import MediaAsset as OrmMediaAsset
from src.shared.interfaces.logger import ILogger
from src.shared.pagination import paginate


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

    def __init__(self, session: AsyncSession, logger: ILogger) -> None:
        self._session = session
        self._logger = logger.bind(handler="ListProductMediaHandler")

    async def handle(self, query: ListProductMediaQuery) -> MediaAssetListReadModel:
        """Retrieve paginated media assets for a product.

        Args:
            query: Query parameters with product_id and pagination.

        Returns:
            Tuple of (media read models, total count).
        """
        base = (
            select(OrmMediaAsset)
            .where(OrmMediaAsset.product_id == query.product_id)
            .order_by(OrmMediaAsset.variant_id, OrmMediaAsset.sort_order)
        )

        items, total = await paginate(
            self._session,
            base,
            offset=query.offset,
            limit=query.limit,
            mapper=self._to_read_model,
        )

        return MediaAssetListReadModel(
            items=items,
            total=total,
            offset=query.offset,
            limit=query.limit,
        )

    @staticmethod
    def _to_read_model(orm: OrmMediaAsset) -> MediaAssetReadModel:
        return MediaAssetReadModel(
            id=orm.id,
            product_id=orm.product_id,
            variant_id=orm.variant_id,
            media_type=orm.media_type.value if orm.media_type else "",
            role=orm.role.value if orm.role else "",
            sort_order=orm.sort_order,
            storage_object_id=orm.storage_object_id,
            url=orm.url,
            is_external=orm.is_external,
            image_variants=orm.image_variants,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )
