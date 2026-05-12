"""SQLAlchemy-backed repository for ``ProductPricingProfile``."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.pricing.domain.entities import ProductPricingProfile
from src.modules.pricing.domain.exceptions import (
    ProductPricingProfileVersionConflictError,
)
from src.modules.pricing.domain.interfaces import IProductPricingProfileRepository
from src.modules.pricing.domain.value_objects import ProfileStatus
from src.modules.pricing.infrastructure.models import ProductPricingProfileModel


def _values_from_jsonb(raw: dict) -> dict[str, Decimal]:
    """Convert a JSONB blob back into ``dict[str, Decimal]``.

    Values are stored as strings to preserve decimal precision across the
    JSON round-trip; defensive ``Decimal(str(...))`` handles both legacy
    numeric-encoded rows and the canonical string form.
    """
    return {str(k): Decimal(str(v)) for k, v in (raw or {}).items()}


def _values_to_jsonb(values: dict[str, Decimal]) -> dict[str, str]:
    """Serialize ``dict[str, Decimal]`` for JSONB storage."""
    return {code: format(value, "f") for code, value in values.items()}


class ProductPricingProfileRepository(IProductPricingProfileRepository):
    """Data Mapper repository for ``ProductPricingProfile``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_domain(model: ProductPricingProfileModel) -> ProductPricingProfile:
        profile = ProductPricingProfile(
            id=model.id,
            product_id=model.product_id,
            context_id=model.context_id,
            values=_values_from_jsonb(model.values),
            status=ProfileStatus(model.status),
            version_lock=model.version_lock,
            created_at=model.created_at,
            updated_at=model.updated_at,
            updated_by=model.updated_by,
            is_deleted=model.is_deleted,
        )
        profile.clear_domain_events()
        return profile

    @staticmethod
    def _apply(
        model: ProductPricingProfileModel, profile: ProductPricingProfile
    ) -> None:
        model.product_id = profile.product_id
        model.context_id = profile.context_id
        model.values = _values_to_jsonb(profile.values)
        model.status = profile.status.value
        model.version_lock = profile.version_lock
        model.is_deleted = profile.is_deleted
        model.updated_by = profile.updated_by

    # ------------------------------------------------------------------
    # Interface methods
    # ------------------------------------------------------------------

    async def add(self, profile: ProductPricingProfile) -> ProductPricingProfile:
        model = ProductPricingProfileModel(
            id=profile.id,
            product_id=profile.product_id,
            context_id=profile.context_id,
            values=_values_to_jsonb(profile.values),
            status=profile.status.value,
            version_lock=profile.version_lock,
            is_deleted=profile.is_deleted,
            updated_by=profile.updated_by,
        )
        self._session.add(model)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise ProductPricingProfileVersionConflictError(
                product_id=profile.product_id,
                expected_version=0,
                actual_version=-1,
            ) from exc
        await self._session.refresh(model)
        return self._to_domain(model)

    async def update(self, profile: ProductPricingProfile) -> ProductPricingProfile:
        model = await self._session.get(ProductPricingProfileModel, profile.id)
        if model is None:
            # Caller is expected to have loaded the profile first; this is a
            # developer error, not a user-facing one.
            msg = f"ProductPricingProfile {profile.id} disappeared before update"
            raise RuntimeError(msg)

        if model.version_lock != profile.version_lock - 1:
            raise ProductPricingProfileVersionConflictError(
                product_id=profile.product_id,
                expected_version=profile.version_lock - 1,
                actual_version=model.version_lock,
            )

        self._apply(model, profile)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_domain(model)

    async def get_by_product_id(
        self,
        product_id: uuid.UUID,
        *,
        include_deleted: bool = False,
    ) -> ProductPricingProfile | None:
        stmt = select(ProductPricingProfileModel).where(
            ProductPricingProfileModel.product_id == product_id,
        )
        if not include_deleted:
            stmt = stmt.where(ProductPricingProfileModel.is_deleted.is_(False))
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_by_product_id_for_update(
        self,
        product_id: uuid.UUID,
    ) -> ProductPricingProfile | None:
        stmt = (
            select(ProductPricingProfileModel)
            .where(
                ProductPricingProfileModel.product_id == product_id,
                ProductPricingProfileModel.is_deleted.is_(False),
            )
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def count_references_to_variable_code(self, code: str) -> int:
        """Count active profiles whose ``values`` JSONB map contains ``code`` as a key.

        Uses the PG JSONB key-existence operator (``?``) via ``func.jsonb_exists``.
        """
        from sqlalchemy import func as _func

        stmt = select(_func.count()).where(
            ProductPricingProfileModel.is_deleted.is_(False),
            _func.jsonb_exists(ProductPricingProfileModel.values, code),
        )
        result = await self._session.execute(stmt)
        return int(result.scalar_one() or 0)
