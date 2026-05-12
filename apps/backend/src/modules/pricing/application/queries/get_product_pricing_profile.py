"""Query: read a ``ProductPricingProfile`` by product_id."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from src.modules.pricing.domain.exceptions import (
    ProductPricingProfileNotFoundError,
)
from src.modules.pricing.domain.interfaces import IProductPricingProfileRepository


@dataclass(frozen=True)
class GetProductPricingProfileQuery:
    product_id: uuid.UUID


@dataclass(frozen=True)
class ProductPricingProfileReadModel:
    """DTO returned by ``GetProductPricingProfileHandler``."""

    profile_id: uuid.UUID
    product_id: uuid.UUID
    context_id: uuid.UUID | None
    values: dict[str, Decimal]
    status: str
    version_lock: int
    created_at: datetime
    updated_at: datetime
    updated_by: uuid.UUID | None


class GetProductPricingProfileHandler:
    """Fetch an active (non-deleted) profile by ``product_id``."""

    def __init__(self, repo: IProductPricingProfileRepository) -> None:
        self._repo = repo

    async def handle(
        self, query: GetProductPricingProfileQuery
    ) -> ProductPricingProfileReadModel:
        profile = await self._repo.get_by_product_id(query.product_id)
        if profile is None:
            raise ProductPricingProfileNotFoundError(query.product_id)
        return ProductPricingProfileReadModel(
            profile_id=profile.id,
            product_id=profile.product_id,
            context_id=profile.context_id,
            values=dict(profile.values),
            status=profile.status.value,
            version_lock=profile.version_lock,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
            updated_by=profile.updated_by,
        )
