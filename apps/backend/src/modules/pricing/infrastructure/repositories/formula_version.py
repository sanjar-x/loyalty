"""SQLAlchemy-backed repository for ``FormulaVersion``."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.pricing.domain.entities.formula import FormulaVersion
from src.modules.pricing.domain.exceptions import FormulaVersionConflictError
from src.modules.pricing.domain.interfaces import (
    FormulaVersionListFilter,
    IFormulaVersionRepository,
)
from src.modules.pricing.domain.value_objects import FormulaStatus
from src.modules.pricing.infrastructure.models import FormulaVersionModel


class FormulaVersionRepository(IFormulaVersionRepository):
    """Data Mapper repository for the ``FormulaVersion`` aggregate."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_domain(model: FormulaVersionModel) -> FormulaVersion:
        version = FormulaVersion(
            id=model.id,
            context_id=model.context_id,
            version_number=model.version_number,
            status=FormulaStatus(model.status),
            ast=dict(model.ast or {}),
            published_at=model.published_at,
            published_by=model.published_by,
            version_lock=model.version_lock,
            created_at=model.created_at,
            updated_at=model.updated_at,
            updated_by=model.updated_by,
        )
        version.clear_domain_events()
        return version

    @staticmethod
    def _apply(model: FormulaVersionModel, version: FormulaVersion) -> None:
        # context_id + version_number are immutable after creation.
        model.status = version.status.value
        model.ast = dict(version.ast)
        model.published_at = version.published_at
        model.published_by = version.published_by
        model.version_lock = version.version_lock
        model.updated_by = version.updated_by

    # ------------------------------------------------------------------
    # Interface methods
    # ------------------------------------------------------------------

    async def add(self, version: FormulaVersion) -> FormulaVersion:
        model = FormulaVersionModel(
            id=version.id,
            context_id=version.context_id,
            version_number=version.version_number,
            status=version.status.value,
            ast=dict(version.ast),
            published_at=version.published_at,
            published_by=version.published_by,
            version_lock=version.version_lock,
            updated_by=version.updated_by,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_domain(model)

    async def update(self, version: FormulaVersion) -> FormulaVersion:
        # Row-level lock: serializes concurrent updaters of this aggregate
        # so the version_lock check below is safe against lost updates.
        # The lock is released when the enclosing transaction commits.
        stmt = (
            select(FormulaVersionModel)
            .where(FormulaVersionModel.id == version.id)
            .with_for_update()
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        if model is None:
            msg = f"FormulaVersion {version.id} disappeared before update"
            raise RuntimeError(msg)

        if model.version_lock != version.version_lock - 1:
            raise FormulaVersionConflictError(
                version_id=version.id,
                expected_version=version.version_lock - 1,
                actual_version=model.version_lock,
            )

        self._apply(model, version)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_domain(model)

    async def delete(self, version_id: uuid.UUID) -> None:
        await self._session.execute(
            delete(FormulaVersionModel).where(FormulaVersionModel.id == version_id)
        )
        await self._session.flush()

    async def get_by_id(self, version_id: uuid.UUID) -> FormulaVersion | None:
        model = await self._session.get(FormulaVersionModel, version_id)
        return self._to_domain(model) if model else None

    async def get_draft_for_context(
        self, context_id: uuid.UUID
    ) -> FormulaVersion | None:
        return await self._get_by_status(context_id, FormulaStatus.DRAFT)

    async def get_published_for_context(
        self, context_id: uuid.UUID
    ) -> FormulaVersion | None:
        return await self._get_by_status(context_id, FormulaStatus.PUBLISHED)

    async def _get_by_status(
        self, context_id: uuid.UUID, status: FormulaStatus
    ) -> FormulaVersion | None:
        stmt = select(FormulaVersionModel).where(
            FormulaVersionModel.context_id == context_id,
            FormulaVersionModel.status == status.value,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def list_by_context(
        self,
        context_id: uuid.UUID,
        filters: FormulaVersionListFilter | None = None,
    ) -> list[FormulaVersion]:
        stmt = (
            select(FormulaVersionModel)
            .where(FormulaVersionModel.context_id == context_id)
            .order_by(FormulaVersionModel.version_number.desc())
        )
        if filters is not None and filters.status is not None:
            stmt = stmt.where(FormulaVersionModel.status == filters.status.value)
        result = await self._session.execute(stmt)
        return [self._to_domain(m) for m in result.scalars().all()]

    async def get_max_version_number(self, context_id: uuid.UUID) -> int:
        stmt = select(
            func.coalesce(func.max(FormulaVersionModel.version_number), 0)
        ).where(FormulaVersionModel.context_id == context_id)
        result = await self._session.execute(stmt)
        return int(result.scalar_one())
